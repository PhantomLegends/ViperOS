import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
# Import all models to ensure they are registered with Base.metadata
from viperos.models import Base, CommandLog, User, Workflow, WorkflowAction, Setting, PendingConfirmation
from viperos.api import app, get_db
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
    # Use StaticPool to maintain the in-memory database connection for the session
    engine = create_engine(
        "sqlite://", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    # This creates tables for all models imported above
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    # We yield the client here. The startup event of FastAPI (create_all) 
    # will run against the production engine, but the actual routes 
    # will use our overridden db_session.
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_post_command_success(client, db_session):
    # Test valid command via API
    response = client.post("/command", json={"command": "status"})
    assert response.status_code == 200
    assert "result" in response.json()
    
    # We need to refresh or ensure the session sees the latest data 
    # if the API committed it.
    db_session.expire_all()
    log = db_session.query(CommandLog).filter_by(command="status").first()
    assert log is not None
    assert "status" == log.command
    # The actual result string depends on implementation, but success is expected
    assert log.result is not None

def test_post_command_empty(client):
    # Test defensive validation for empty input
    response = client.post("/command", json={"command": ""})
    # Updated to 422 because CommandRequest model enforces min_length=1, 
    # causing Pydantic validation to fail before the manual check in the route.
    assert response.status_code == 422

def test_command_log_persistence_on_failure(db_session):
    # Test that even unknown commands are logged
    core = VIPEROSCore(db_session)
    core.parse_and_execute("unsupported_action_123")
    
    db_session.expire_all()
    log = db_session.query(CommandLog).filter_by(command="unsupported_action_123").first()
    assert log is not None
    assert "Unknown command" in log.result

def test_shell_command_routing(db_session):
    core = VIPEROSCore(db_session)
    # The adapter executes the shell command and returns the output.
    # For "echo test", the output is "test".
    result = core.parse_and_execute("shell echo test")
    assert "test" in result.lower()
    # The command verb 'echo' is usually not part of the output
    assert "echo" not in result.lower() or result.lower() == "echo test" # depending on adapter mock