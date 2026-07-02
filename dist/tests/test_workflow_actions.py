import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from viperos.models import Base, Workflow, WorkflowAction
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_add_app_to_workflow_success(db_session):
    core = VIPEROSCore(db_session)
    # Setup: Create a workflow first
    core.parse_and_execute("create workflow Startup")
    
    # Test: Add an app
    command = "add app Chrome to Startup"
    result = core.parse_and_execute(command)
    
    assert "Added app 'Chrome'" in result
    assert "to workflow 'Startup'" in result
    
    # Verify persistence
    workflow = db_session.query(Workflow).filter_by(name="Startup").one()
    action = db_session.query(WorkflowAction).filter_by(workflow_id=workflow.id).first()
    
    assert action is not None
    assert action.type == "launch_app"
    assert action.value == "Chrome"
    assert action.order == 0

def test_add_multiple_apps_increments_order(db_session):
    core = VIPEROSCore(db_session)
    core.parse_and_execute("create workflow Multi")
    
    core.parse_and_execute("add app Terminal to Multi")
    core.parse_and_execute("add app Slack to Multi")
    
    workflow = db_session.query(Workflow).filter_by(name="Multi").one()
    actions = db_session.query(WorkflowAction).filter_by(workflow_id=workflow.id).order_by(WorkflowAction.order).all()
    
    assert len(actions) == 2
    assert actions[0].value == "Terminal"
    assert actions[0].order == 0
    assert actions[1].value == "Slack"
    assert actions[1].order == 1

def test_add_app_to_nonexistent_workflow(db_session):
    core = VIPEROSCore(db_session)
    command = "add app VSCode to MissingWorkflow"
    
    result = core.parse_and_execute(command)
    
    assert "Error" in result
    assert "not found" in result
    
    count = db_session.query(WorkflowAction).count()
    assert count == 0

def test_add_app_invalid_syntax(db_session):
    core = VIPEROSCore(db_session)
    command = "add app JustAnApp" # Missing "to <workflow>"
    
    result = core.parse_and_execute(command)
    
    assert "Error" in result
    assert "Invalid syntax" in result