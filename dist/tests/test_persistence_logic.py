import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from viperos.models import Base, PendingConfirmation, Setting, CommandLog
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
    # Requirement: UnitTests should isolate local state using temporary SQLite databases
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

def test_confirmation_expiration_logic(db_session):
    core = VIPEROSCore(db_session)
    
    # 1. Create a confirmation that expires in 1 minute
    core.create_pending_confirmation("action_valid", "payload_1", timeout_minutes=1)
    
    # 2. Manually inject an expired confirmation
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    expired_time = now - datetime.timedelta(minutes=10)
    expired_entry = PendingConfirmation(
        action="action_expired",
        payload="payload_old",
        expiration_time=expired_time
    )
    db_session.add(expired_entry)
    db_session.commit()
    
    # 3. Assert only the valid one is returned
    # Requirement: Expired pending confirmations should not be executed (or retrieved as active)
    active = core.get_active_confirmations()
    assert len(active) == 1
    assert active[0].action == "action_valid"

def test_cleanup_removes_only_expired(db_session):
    core = VIPEROSCore(db_session)
    
    # Setup: 1 valid, 1 expired
    core.create_pending_confirmation("stay", "data", timeout_minutes=5)
    
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    expired_time = now - datetime.timedelta(seconds=1)
    db_session.add(PendingConfirmation(action="go", payload="data", expiration_time=expired_time))
    db_session.commit()
    
    deleted = core.cleanup_expired_confirmations()
    assert deleted == 1
    
    all_records = db_session.query(PendingConfirmation).all()
    assert len(all_records) == 1
    assert all_records[0].action == "stay"

def test_command_log_persistence(db_session):
    core = VIPEROSCore(db_session)
    core.log_command("test command", "success result")
    
    log = db_session.query(CommandLog).filter_by(command="test command").first()
    assert log is not None
    assert log.result == "success result"
    assert isinstance(log.created_at, datetime.datetime)

def test_confirmation_database_error_handling(db_session):
    core = VIPEROSCore(db_session)
    
    # To reliably trigger a database error in the 'try...except' block of VIPEROSCore,
    # we close the session and its underlying connection. 
    # In some SQLite configurations, simply closing the session isn't enough to raise
    # an exception on the next 'add' call, so we ensure the session is unusable.
    db_session.close()
    db_session.bind.dispose() 
    
    with pytest.raises(RuntimeError) as excinfo:
        core.create_pending_confirmation("fail", "data")
    
    assert "Database error" in str(excinfo.value)