import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from viperos.models import Base, Workflow, WorkflowAction
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
    # Use an in-memory database for isolated unit testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_add_url_to_workflow_success(db_session):
    core = VIPEROSCore(db_session)
    # Setup: Create a workflow
    core.parse_and_execute("create workflow Daily")
    
    # Test: Add a URL
    command = "add url https://news.ycombinator.com to Daily"
    result = core.parse_and_execute(command)
    
    assert "Added URL 'https://news.ycombinator.com'" in result
    assert "to workflow 'Daily'" in result
    
    # Verify persistence
    workflow = db_session.query(Workflow).filter_by(name="Daily").one()
    action = db_session.query(WorkflowAction).filter_by(workflow_id=workflow.id).first()
    
    assert action is not None
    assert action.type == "open_url"
    assert action.value == "https://news.ycombinator.com"
    assert action.order == 0

def test_add_url_workflow_not_found(db_session):
    core = VIPEROSCore(db_session)
    command = "add url http://localhost to GhostWorkflow"
    
    result = core.parse_and_execute(command)
    
    assert "Error" in result
    assert "GhostWorkflow" in result
    assert "not found" in result

def test_add_url_invalid_syntax(db_session):
    core = VIPEROSCore(db_session)
    # Missing 'to' keyword
    command = "add url https://google.com MyWorkflow"
    
    result = core.parse_and_execute(command)
    
    assert "Error: Invalid syntax" in result

def test_mixed_actions_order(db_session):
    core = VIPEROSCore(db_session)
    core.parse_and_execute("create workflow Mix")
    
    # Add app then URL
    core.parse_and_execute("add app Spotify to Mix")
    core.parse_and_execute("add url https://spotify.com to Mix")
    
    workflow = db_session.query(Workflow).filter_by(name="Mix").one()
    actions = (
        db_session.query(WorkflowAction)
        .filter_by(workflow_id=workflow.id)
        .order_by(WorkflowAction.order)
        .all()
    )
    
    assert len(actions) == 2
    assert actions[0].type == "launch_app"
    assert actions[0].order == 0
    assert actions[1].type == "open_url"
    assert actions[1].value == "https://spotify.com"
    assert actions[1].order == 1