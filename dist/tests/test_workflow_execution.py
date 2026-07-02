import pytest
from unittest.mock import MagicMock
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

@pytest.fixture
def core_with_mock_adapter(db_session):
    core = VIPEROSCore(db_session)
    core.adapter = MagicMock()
    # Mock return values for methods that might be called
    core.adapter.launch_app.return_value = True
    core.adapter.open_url.return_value = True
    return core

def test_run_workflow_retry_logic_success_on_last_try(core_with_mock_adapter, db_session):
    # Setup workflow with 2 retries (3 total attempts)
    wf = Workflow(name="retry_wf", failure_policy="stop", retry_count=2)
    db_session.add(wf)
    db_session.commit()
    
    act = WorkflowAction(workflow_id=wf.id, order=0, type="launch_app", value="flaky_app")
    db_session.add(act)
    db_session.commit()

    # Fail twice, succeed on third
    core_with_mock_adapter.adapter.launch_app.side_effect = [False, False, True]

    result = core_with_mock_adapter.parse_and_execute("run retry_wf")

    assert "completed" in result
    assert "1/1" in result
    assert core_with_mock_adapter.adapter.launch_app.call_count == 3

def test_run_workflow_retry_logic_exhausted(core_with_mock_adapter, db_session):
    # Setup workflow with 1 retry (2 total attempts)
    wf = Workflow(name="exhaust_wf", failure_policy="stop", retry_count=1)
    db_session.add(wf)
    db_session.commit()
    
    act = WorkflowAction(workflow_id=wf.id, order=0, type="launch_app", value="broken_app")
    db_session.add(act)
    db_session.commit()

    # Fail both times
    core_with_mock_adapter.adapter.launch_app.side_effect = [False, False]

    result = core_with_mock_adapter.parse_and_execute("run exhaust_wf")

    assert "Workflow failed at step 0" in result
    assert "failed after 2 attempt(s)" in result
    assert core_with_mock_adapter.adapter.launch_app.call_count == 2

def test_run_workflow_failure_policy_stop(core_with_mock_adapter, db_session):
    wf = Workflow(name="stop_wf", failure_policy="stop", retry_count=0)
    db_session.add(wf)
    db_session.commit()
    
    act1 = WorkflowAction(workflow_id=wf.id, order=0, type="launch_app", value="fail_me")
    act2 = WorkflowAction(workflow_id=wf.id, order=1, type="open_url", value="never_runs")
    db_session.add_all([act1, act2])
    db_session.commit()

    core_with_mock_adapter.adapter.launch_app.return_value = False

    result = core_with_mock_adapter.parse_and_execute("run stop_wf")

    assert "Workflow failed at step 0" in result
    assert "Total steps successfully completed: 0" in result
    core_with_mock_adapter.adapter.open_url.assert_not_called()

def test_run_workflow_failure_policy_continue(core_with_mock_adapter, db_session):
    wf = Workflow(name="cont_wf", failure_policy="continue", retry_count=0)
    db_session.add(wf)
    db_session.commit()
    
    act1 = WorkflowAction(workflow_id=wf.id, order=0, type="launch_app", value="fail_me")
    act2 = WorkflowAction(workflow_id=wf.id, order=1, type="open_url", value="run_me")
    db_session.add_all([act1, act2])
    db_session.commit()

    core_with_mock_adapter.adapter.launch_app.return_value = False
    core_with_mock_adapter.adapter.open_url.return_value = True

    result = core_with_mock_adapter.parse_and_execute("run cont_wf")

    assert "completed" in result
    assert "Actions executed: 1/2" in result
    assert "Errors encountered:" in result
    core_with_mock_adapter.adapter.open_url.assert_called_once()

def test_run_workflow_exception_handling(core_with_mock_adapter, db_session):
    # Ensure that if the adapter raises an unexpected exception, it's treated as a failure step
    wf = Workflow(name="crash_wf", failure_policy="stop", retry_count=0)
    db_session.add(wf)
    db_session.commit()
    
    act = WorkflowAction(workflow_id=wf.id, order=0, type="launch_app", value="crash_app")
    db_session.add(act)
    db_session.commit()

    core_with_mock_adapter.adapter.launch_app.side_effect = Exception("Hardware failure")

    result = core_with_mock_adapter.parse_and_execute("run crash_wf")

    assert "Workflow failed at step 0" in result
    assert "failed after 1 attempt(s)" in result