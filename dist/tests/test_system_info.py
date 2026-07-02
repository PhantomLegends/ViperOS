import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from viperos.models import Base, CommandLog
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)

def test_system_info_command(db_session):
    core = VIPEROSCore(db_session)
    result = core.parse_and_execute("system info")
    
    # Assert output contains key information
    assert "System Info:" in result
    assert "Platform=" in result
    assert "Adapter=" in result
    
    # Assert persistence in CommandLog
    db_session.expire_all()
    log = db_session.query(CommandLog).filter_by(command="system info").first()
    assert log is not None
    assert result == log.result

def test_system_info_logging_on_exception(db_session, monkeypatch):
    core = VIPEROSCore(db_session)
    
    # Force an error in adapter to test defensive handling
    def mock_get_name():
        raise Exception("Hardware Failure")
    
    monkeypatch.setattr(core.adapter, "get_name", mock_get_name)
    
    result = core.parse_and_execute("system info")
    assert "Failed to retrieve system info" in result
    
    db_session.expire_all()
    log = db_session.query(CommandLog).filter_by(command="system info").first()
    assert "Hardware Failure" in log.result