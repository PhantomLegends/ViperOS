import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from viperos.api import app, get_db
from viperos.models import Base, Workflow

# We use a single engine with StaticPool for the duration of the test module
# but we will manage the table lifecycle strictly per test.
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Create tables for this specific test
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop tables after the test to ensure isolation for the next test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    # Override get_db to use the session from our fixture
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_api_create_workflow_success(client, db_session):
    payload = {
        "name": "API Workflow",
        "description": "Created via API",
        "stop_on_failure": False,
        "continue_on_failure": True,
        "retry_count": 3
    }
    response = client.post("/workflow/create", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Workflow"
    assert "id" in data

    # Verify in DB using the test session provided by the fixture
    # Use expire_all or refresh to ensure we see the changes committed by the API
    db_session.expire_all()
    wf = db_session.query(Workflow).filter_by(name="API Workflow").first()
    assert wf is not None
    assert wf.description == "Created via API"
    assert wf.failure_policy == "continue"
    assert wf.retry_count == 3

def test_api_create_workflow_duplicate_name(client):
    payload = {"name": "Unique"}
    # First creation
    client.post("/workflow/create", json=payload)
    
    # Try again
    response = client.post("/workflow/create", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_api_create_workflow_invalid_retry(client):
    payload = {
        "name": "Bad Retry",
        "retry_count": -1
    }
    response = client.post("/workflow/create", json=payload)
    # Pydantic validation handles negative numbers via Field(ge=0)
    assert response.status_code == 422 

def test_api_create_workflow_default_values(client, db_session):
    payload = {"name": "Defaults"}
    response = client.post("/workflow/create", json=payload)
    assert response.status_code == 200
    
    db_session.expire_all()
    wf = db_session.query(Workflow).filter_by(name="Defaults").first()
    assert wf is not None
    assert wf.failure_policy == "stop" # Default behavior
    assert wf.retry_count == 0

def test_api_list_workflows_empty(client):
    # This test now runs with a clean database thanks to the fixture
    response = client.get("/workflow/list")
    assert response.status_code == 200
    assert response.json() == []

def test_api_list_workflows_with_items(client, db_session):
    # Pre-populate using the session from the fixture
    db_session.add(Workflow(name="W1", description="Desc 1", failure_policy="stop", retry_count=1))
    db_session.add(Workflow(name="W2", description="Desc 2", failure_policy="continue", retry_count=5))
    db_session.commit()

    response = client.get("/workflow/list")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    
    w1 = next(item for item in data if item["name"] == "W1")
    assert w1["description"] == "Desc 1"
    assert w1["failure_policy"] == "stop"
    assert w1["retry_count"] == 1
    
    w2 = next(item for item in data if item["name"] == "W2")
    assert w2["description"] == "Desc 2"
    assert w2["failure_policy"] == "continue"
    assert w2["retry_count"] == 5