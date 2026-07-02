from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field, root_validator
from typing import Optional, List, Any
import logging
from passlib.context import CryptContext
from contextlib import asynccontextmanager

from .models import Base, Workflow, User
from .core import VIPEROSCore
from .adapters import get_active_adapter

# Configure logging for production-ready debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security configuration
# bcrypt pinned to 4.0.1 and passlib 1.7.4 are handled via requirements.txt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite:///./viperos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles system startup and shutdown.
    Ensures SQLite tables exist before the API starts accepting requests.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Local SQLite database initialized successfully.")
    except Exception as e:
        logger.critical(f"Critical failure during database initialization: {e}", exc_info=True)
        # In a real production scenario, we might want to exit here
    yield

app = FastAPI(
    title="VIPER-OS Core API",
    description="Headless local-first automation runtime API",
    version="1.0.0",
    lifespan=lifespan
)

def get_db():
    """
    Dependency to provide a database session to routes.
    Ensures connections are closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CommandRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Text command to be parsed and executed.")

class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    stop_on_failure: bool = True
    continue_on_failure: bool = False
    retry_count: int = Field(default=0, ge=0)

class WorkflowResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    failure_policy: str
    retry_count: int

    class Config:
        from_attributes = True

class WorkflowRunRequest(BaseModel):
    name: str = Field(..., min_length=1)

class LoginRequest(BaseModel):
    username: str
    passcode: str

class FaceAuthRequest(BaseModel):
    """
    Request model for mock face authentication.
    Strictly forbids biometric data fields to ensure data stays local.
    """
    metadata: Optional[dict[str, Any]] = Field(
        default=None, 
        description="Optional non-biometric metadata for the request."
    )

    @root_validator(pre=True)
    def check_no_biometrics(cls, values):
        """Defensive check: Ensure no image or binary data is sent."""
        forbidden_keys = {"image", "photo", "biometric", "encoding", "blob"}
        found_forbidden = forbidden_keys.intersection(values.keys())
        if found_forbidden:
            logger.warning(f"Rejected request containing forbidden biometric keys: {found_forbidden}")
            raise ValueError(f"Biometric data must stay local. Forbidden fields: {found_forbidden}")
        return values

@app.get("/health")
def health():
    return {"status": "ready"}

@app.get("/system/info")
def system_info():
    try:
        adapter = get_active_adapter()
        return {
            "platform": adapter.get_name(), 
            "adapter": adapter.__class__.__name__
        }
    except Exception as e:
        logger.error(f"Failed to retrieve system info: {e}")
        raise HTTPException(status_code=500, detail="Could not determine system adapter configuration.")

@app.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == request.username).first()
        if not user:
            logger.warning(f"Login attempt failed: User '{request.username}' does not exist.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed: Invalid credentials."
            )
        
        if not pwd_context.verify(request.passcode, user.passcode_hash):
            logger.warning(f"Login attempt failed: Incorrect password for user '{request.username}'.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed: Invalid credentials."
            )
            
        return {"status": "success", "message": f"Welcome, {user.username}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during login process")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred during authentication: {str(e)}"
        )

@app.post("/auth/mock-face")
def mock_face_auth(request: FaceAuthRequest):
    """
    Exposes a mock face authentication endpoint.
    Complies with requirements:
    1. Biometric data remains local (not accepted here).
    2. Returns success by default.
    """
    try:
        logger.info("Mock face authentication endpoint invoked.")
        # Logic is kept minimal as it's a mock endpoint for local-first runtime.
        return {
            "status": "success", 
            "message": "Face authenticated (mock mode). No biometric data was transmitted."
        }
    except Exception as e:
        logger.error(f"Unexpected error in mock_face_auth: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during mock face auth: {str(e)}"
        )

@app.post("/command")
def post_command(request: CommandRequest, db: Session = Depends(get_db)):
    if not request.command:
        raise HTTPException(status_code=400, detail="Command text is required and cannot be empty.")
    
    try:
        core = VIPEROSCore(db=db)
        result = core.parse_and_execute(request.command)
        db.commit()
        return {"result": result}
    except Exception as e:
        db.rollback()
        logger.error(f"Command execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")

@app.get("/workflow/list", response_model=List[WorkflowResponse])
def list_workflows(db: Session = Depends(get_db)):
    try:
        workflows = db.query(Workflow).all()
        return workflows
    except Exception as e:
        logger.exception("Database error while listing workflows.")
        raise HTTPException(status_code=500, detail="Internal Server Error: Unable to retrieve workflow list.")

@app.post("/workflow/create")
def create_workflow(request: WorkflowCreateRequest, db: Session = Depends(get_db)):
    policy = "continue" if request.continue_on_failure else "stop"
    try:
        core = VIPEROSCore(db=db)
        workflow = core.workflow_manager.create_workflow(
            name=request.name,
            description=request.description or "",
            failure_policy=policy,
            retry_count=request.retry_count
        )
        db.commit()
        db.refresh(workflow)
        return {"id": workflow.id, "name": workflow.name, "status": "created"}
    except ValueError as ve:
        db.rollback()
        logger.warning(f"Workflow creation validation failed: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        logger.exception("Database error during workflow creation.")
        raise HTTPException(status_code=500, detail="Internal Server Error: Workflow could not be created.")

@app.post("/workflow/run")
def run_workflow(request: WorkflowRunRequest, db: Session = Depends(get_db)):
    try:
        core = VIPEROSCore(db=db)
        command_text = f"run {request.name}"
        result = core.parse_and_execute(command_text)
        
        # Check if the execution result indicates a missing workflow
        if "Error:" in result and "not found" in result:
             raise HTTPException(status_code=404, detail=result)
             
        db.commit()
        return {"workflow": request.name, "result": result}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Critical failure while running workflow '{request.name}'.")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")