import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from viperos.models import Base, Setting
from viperos.core import VIPEROSCore
from viperos.voice import LocalVoiceInput

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

def test_tts_speed_range_validation(core):
    # Valid low
    res = core.parse_and_execute("set tts speed to 50")
    assert "TTS speed set to 50" in res
    
    # Valid high
    res = core.parse_and_execute("set tts speed to 400")
    assert "TTS speed set to 400" in res
    
    # Invalid low
    res = core.parse_and_execute("set tts speed to 49")
    assert "Error" in res
    assert "between 50 and 400" in res
    
    # Invalid high
    res = core.parse_and_execute("set tts speed to 401")
    assert "Error" in res

def test_voice_input_command_routing(core):
    voice = LocalVoiceInput(core)
    core.adapter.get_name.return_value = "MockOS"
    
    # Simulate speaking a command
    result = voice.simulate_voice_command("system info")
    
    assert "System Info" in result
    assert "MockOS" in result
    # Ensure it went through core logic
    core.adapter.get_name.assert_called()

def test_conditional_tts_output(core, db_session):
    # 1. TTS Disabled by default
    core.parse_and_execute("status")
    core.adapter.speak.assert_not_called()
    
    # 2. Enable TTS
    core.parse_and_execute("enable tts")
    
    # 3. Next command should trigger speak
    core.parse_and_execute("status")
    core.adapter.speak.assert_called()
    
    # Verify the text passed to speak contains the status
    args, _ = core.adapter.speak.call_args
    assert "System online" in args[0]

def test_tts_feedback_fails_gracefully(core, db_session):
    # Enable TTS
    core.parse_and_execute("enable tts")
    
    # Mock speak to raise exception
    core.adapter.speak.side_effect = Exception("Audio device busy")
    
    # Command should still return string result even if speak fails
    result = core.parse_and_execute("status")
    assert "System online" in result