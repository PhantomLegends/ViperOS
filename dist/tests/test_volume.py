import pytest
from unittest.mock import MagicMock, patch
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

def test_set_volume_success(db_session):
    core = VIPEROSCore(db_session)
    # Mock the adapter to avoid actual system calls
    core.adapter.set_volume = MagicMock(return_value=True)
    
    result = core.parse_and_execute("set volume to 50")
    
    assert "Volume set to 50%" in result
    core.adapter.set_volume.assert_called_once_with(50)

def test_set_volume_invalid_range(db_session):
    core = VIPEROSCore(db_session)
    core.adapter.set_volume = MagicMock()
    
    result_high = core.parse_and_execute("set volume to 101")
    result_low = core.parse_and_execute("set volume to -5")
    
    assert "Error: Volume must be between 0 and 100." in result_high
    assert "Error: Volume must be between 0 and 100." in result_low
    core.adapter.set_volume.assert_not_called()

def test_set_volume_invalid_format(db_session):
    core = VIPEROSCore(db_session)
    core.adapter.set_volume = MagicMock()
    
    result = core.parse_and_execute("set volume to high")
    
    assert "Error: Invalid volume format" in result
    core.adapter.set_volume.assert_not_called()

def test_set_volume_adapter_failure(db_session):
    core = VIPEROSCore(db_session)
    core.adapter.set_volume = MagicMock(return_value=False)
    
    result = core.parse_and_execute("set volume to 20")
    
    assert "Error: Failed to set system volume." in result