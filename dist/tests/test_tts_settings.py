import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from viperos.models import Base, Setting
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

def test_enable_tts_command(db_session):
    core = VIPEROSCore(db_session)
    result = core.parse_and_execute("enable tts")
    
    assert "TTS has been enabled" in result
    setting = db_session.query(Setting).filter_by(key="tts_enabled").first()
    assert setting is not None
    assert setting.value == "true"

def test_disable_tts_command(db_session):
    core = VIPEROSCore(db_session)
    # First enable it
    core.parse_and_execute("enable tts")
    # Then disable it
    result = core.parse_and_execute("disable tts")
    
    assert "TTS has been disabled" in result
    setting = db_session.query(Setting).filter_by(key="tts_enabled").first()
    assert setting is not None
    assert setting.value == "false"

def test_tts_setting_persistence(db_session):
    core = VIPEROSCore(db_session)
    core.parse_and_execute("enable tts")
    
    # Check that setting exists in DB
    setting = db_session.query(Setting).filter_by(key="tts_enabled").first()
    assert setting.value == "true"
    
    # Modify via command
    core.parse_and_execute("disable tts")
    db_session.expire_all()
    
    setting = db_session.query(Setting).filter_by(key="tts_enabled").first()
    assert setting.value == "false"