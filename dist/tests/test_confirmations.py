import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from viperos.models import Base, PendingConfirmation
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
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

def test_create_pending_confirmation(db_session):
    core = VIPEROSCore(db_session)
    action = "delete_file"
    payload = "/tmp/old_log.txt"
    
    conf = core.create_pending_confirmation(action, payload, timeout_minutes=10)
    
    assert conf.id is not None
    assert conf.action == action
    assert conf.payload == payload
    # Check expiration is in the future
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    assert conf.expiration_time > now

def test_get_active_confirmations_excludes_expired(db_session):
    core = VIPEROSCore(db_session)
    
    # Valid confirmation
    core.create_pending_confirmation("valid", "data", timeout_minutes=5)
    
    # Manually insert an expired confirmation
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    expired_time = now - datetime.timedelta(minutes=1)
    expired_conf = PendingConfirmation(
        action="expired_action",
        payload="some_payload",
        expiration_time=expired_time
    )
    db_session.add(expired_conf)
    db_session.commit()
    
    active = core.get_active_confirmations()
    
    assert len(active) == 1
    assert active[0].action == "valid"

def test_cleanup_expired_confirmations(db_session):
    core = VIPEROSCore(db_session)
    
    # 1. Add an expired one
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    expired_time = now - datetime.timedelta(minutes=10)
    db_session.add(PendingConfirmation(action="old", payload="p", expiration_time=expired_time))
    
    # 2. Add an active one
    core.create_pending_confirmation("new", "p", timeout_minutes=10)
    db_session.commit()
    
    deleted_count = core.cleanup_expired_confirmations()
    assert deleted_count == 1
    
    all_confs = db_session.query(PendingConfirmation).all()
    assert len(all_confs) == 1
    assert all_confs[0].action == "new"

def test_confirmation_persistence_error_handling(db_session):
    # To reliably trigger a failure that VIPEROSCore catches and turns into RuntimeError,
    # we can use a session that is explicitly in a state where it cannot commit.
    core = VIPEROSCore(db_session)
    
    # Close the underlying connection to ensure the session fails during the transaction.
    db_session.bind.dispose() 
    db_session.close()
    
    with pytest.raises(RuntimeError) as excinfo:
        core.create_pending_confirmation("fail", "data")
    
    assert "Database error" in str(excinfo.value)