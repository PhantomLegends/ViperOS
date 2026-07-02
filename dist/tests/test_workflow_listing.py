import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from viperos.models import Base, Workflow
from viperos.core import VIPEROSCore

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_list_workflows_empty(db_session):
    core = VIPEROSCore(db_session)
    result = core.parse_and_execute("list workflows")
    assert result == "No workflows found."

def test_list_workflows_with_data(db_session):
    # Setup: Create workflows manually
    wf1 = Workflow(name="Backup", failure_policy="stop")
    wf2 = Workflow(name="MorningRoutine", failure_policy="stop")
    db_session.add(wf1)
    db_session.add(wf2)
    db_session.commit()

    core = VIPEROSCore(db_session)
    result = core.parse_and_execute("list workflows")
    
    assert "Workflows:" in result
    assert "Backup" in result
    assert "MorningRoutine" in result

def test_list_workflows_case_insensitivity(db_session):
    # Command parsing is case-insensitive
    core = VIPEROSCore(db_session)
    result = core.parse_and_execute("LIST WORKFLOWS")
    # Should be recognized and return the empty state message, not "Unknown command"
    assert result == "No workflows found."