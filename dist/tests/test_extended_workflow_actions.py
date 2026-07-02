import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from viperos.models import Base, Workflow, WorkflowAction, Setting
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def core(db_session):
    c = VIPEROSCore(db_session)
    c.adapter = MagicMock()
    return c

def test_workflow_engine_supports_new_actions(core, db_session):
    # Setup workflow with diverse actions
    wf = Workflow(name="all_actions", failure_policy="continue")
    db_session.add(wf)
    db_session.commit()
    
    actions = [
        WorkflowAction(workflow_id=wf.id, order=0, type="open_file", value="C:/test.txt"),
        WorkflowAction(workflow_id=wf.id, order=1, type="open_folder", value="/home/user"),
        WorkflowAction(workflow_id=wf.id, order=2, type="run_command", value="echo hello"),
        WorkflowAction(workflow_id=wf.id, order=3, type="start_timer", value="0.01"),
        WorkflowAction(workflow_id=wf.id, order=4, type="set_volume", value="75"),
        WorkflowAction(workflow_id=wf.id, order=5, type="mute_volume", value=""),
        WorkflowAction(workflow_id=wf.id, order=6, type="enable_tts", value=""),
        WorkflowAction(workflow_id=wf.id, order=7, type="set_tts_speed", value="150")
    ]
    db_session.add_all(actions)
    db_session.commit()

    core.adapter.open_file.return_value = True
    core.adapter.open_folder.return_value = True
    core.adapter.run_command.return_value = True
    core.adapter.set_volume.return_value = True
    core.adapter.mute_volume.return_value = True
    core.adapter.set_tts_speed.return_value = True

    # Execute
    result = core.parse_and_execute("run all_actions")

    # Verify adapter calls
    core.adapter.open_file.assert_called_with("C:/test.txt")
    core.adapter.open_folder.assert_called_with("/home/user")
    core.adapter.run_command.assert_called_with("echo hello")
    core.adapter.set_volume.assert_called_with(75)
    core.adapter.mute_volume.assert_called()
    core.adapter.set_tts_speed.assert_called_with(150)

    # Verify DB persistence for TTS settings
    tts_enabled = db_session.query(Setting).filter_by(key="tts_enabled").first()
    tts_speed = db_session.query(Setting).filter_by(key="tts_speed").first()
    assert tts_enabled.value == "true"
    assert tts_speed.value == "150"
    assert "8/8" in result

def test_workflow_start_timer_invalid_value(core, db_session):
    wf = Workflow(name="timer_fail")
    db_session.add(wf)
    db_session.commit()
    db_session.add(WorkflowAction(workflow_id=wf.id, order=0, type="start_timer", value="not_a_number"))
    db_session.commit()

    result = core.parse_and_execute("run timer_fail")
    assert "failed at step 0" in result

def test_cli_set_tts_speed(core, db_session):
    result = core.parse_and_execute("set tts speed to 200")
    assert "speed set to 200" in result
    core.adapter.set_tts_speed.assert_called_with(200)
    
    setting = db_session.query(Setting).filter_by(key="tts_speed").first()
    assert setting.value == "200"