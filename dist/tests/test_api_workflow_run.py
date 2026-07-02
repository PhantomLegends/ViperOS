import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock, patch

from viperos.api import app, get_db
from viperos.models import Base, Workflow, WorkflowAction, CommandLog
from viperos.adapters import BaseAdapter

# Setup test database with StaticPool for in-memory persistence across sessions
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
        # Drop tables after the test to ensure isolation
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

@patch("viperos.core.get_active_adapter")
def test_api_run_workflow_success(mock_get_adapter, client, db_session):
    # Mock Adapter
    mock_adapter = MagicMock(spec=BaseAdapter)
    mock_adapter.launch_app.return_value = True
    mock_adapter.get_name.return_value = "MockOS"
    mock_get_adapter.return_value = mock_adapter

    # Setup DB data using the test session
    wf = Workflow(name="test_wf", failure_policy="stop", retry_count=0)
    db_session.add(wf)
    db_session.commit()
    
    act = WorkflowAction(workflow_id=wf.id, order=0, type="launch_app", value="calc.exe")
    db_session.add(act)
    db_session.commit()

    # Execute API Call
    response = client.post("/workflow/run", json={"name": "test_wf"})
    
    assert response.status_code == 200
    data = response.json()
    assert "completed" in data["result"]
    assert data["workflow"] == "test_wf"

    # Verify CommandLog persistence
    db_session.expire_all()
    log = db_session.query(CommandLog).filter(CommandLog.command == "run test_wf").first()
    assert log is not None
    assert "completed" in log.result

def test_api_run_workflow_not_found(client):
    response = client.post("/workflow/run", json={"name": "ghost_workflow"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@patch("viperos.core.get_active_adapter")
def test_api_run_workflow_execution_failure(mock_get_adapter, client, db_session):
    # Mock Adapter to fail
    mock_adapter = MagicMock(spec=BaseAdapter)
    mock_adapter.launch_app.return_value = False
    mock_get_adapter.return_value = mock_adapter

    wf = Workflow(name="fail_wf", failure_policy="stop", retry_count=0)
    db_session.add(wf)
    db_session.commit()
    
    act = WorkflowAction(workflow_id=wf.id, order=0, type="launch_app", value="error_app")
    db_session.add(act)
    db_session.commit()

    response = client.post("/workflow/run", json={"name": "fail_wf"})
    
    assert response.status_code == 200 # Execution completed with failure message
    assert "failed at step 0" in response.json()["result"]