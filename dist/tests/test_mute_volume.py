import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from viperos.models import Base
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_mute_volume_success(db_session):
    core = VIPEROSCore(db_session)
    # Mock the adapter
    core.adapter.mute_volume = MagicMock(return_value=True)
    
    result = core.parse_and_execute("mute volume")
    
    assert result == "System volume muted."
    core.adapter.mute_volume.assert_called_once()

def test_mute_volume_adapter_failure(db_session):
    core = VIPEROSCore(db_session)
    # Mock the adapter failure
    core.adapter.mute_volume = MagicMock(return_value=False)
    
    result = core.parse_and_execute("mute volume")
    
    assert "Error: Failed to mute system volume." in result
    core.adapter.mute_volume.assert_called_once()

def test_mute_volume_exception_handling(db_session):
    core = VIPEROSCore(db_session)
    # Mock an unexpected exception in adapter
    core.adapter.mute_volume = MagicMock(side_effect=Exception("Hardware unplugged"))
    
    result = core.parse_and_execute("mute volume")
    
    assert "Error: Hardware unplugged" in result
    core.adapter.mute_volume.assert_called_once()