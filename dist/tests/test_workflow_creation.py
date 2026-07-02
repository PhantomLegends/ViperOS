import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from viperos.models import Base, Workflow, CommandLog
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_workflow_command_success(db_session):
    core = VIPEROSCore(db_session)
    command = "create workflow DailyBackup"
    
    result = core.parse_and_execute(command)
    
    assert "DailyBackup" in result
    assert "created successfully" in result
    
    # Verify persistence
    workflow = db_session.query(Workflow).filter_by(name="DailyBackup").first()
    assert workflow is not None
    assert workflow.failure_policy == "stop"
    
    # Verify command logging
    log = db_session.query(CommandLog).filter_by(command=command).first()
    assert log is not None
    assert "success" in log.result.lower()

def test_create_workflow_missing_name(db_session):
    core = VIPEROSCore(db_session)
    command = "create workflow  "
    
    result = core.parse_and_execute(command)
    
    assert "Error" in result
    assert "name cannot be empty" in result
    
    # Ensure no workflow was created
    count = db_session.query(Workflow).count()
    assert count == 0

def test_create_workflow_with_spaces(db_session):
    core = VIPEROSCore(db_session)
    command = "create workflow My New Workflow"
    
    result = core.parse_and_execute(command)
    
    assert "My New Workflow" in result
    workflow = db_session.query(Workflow).filter_by(name="My New Workflow").first()
    assert workflow is not None