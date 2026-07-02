import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from passlib.context import CryptContext

from viperos.api import app, get_db
from viperos.models import Base, User

# Setup password context for test data preparation
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Setup in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def fixture_db_session():
    # Create tables in the in-memory database
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Create a test user
        hashed_pwd = pwd_context.hash("secret123")
        test_user = User(username="admin", passcode_hash=hashed_pwd)
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        # Define the override inside the fixture to capture the session 'db'
        def override_get_db():
            try:
                yield db
            finally:
                pass # The fixture handles closing

        app.dependency_overrides[get_db] = override_get_db
        
        yield db
    finally:
        db.close()
        # Clean up overrides and tables
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def fixture_client(db_session):
    """
    Provides a TestClient that depends on the db_session fixture 
    to ensure the database is seeded and dependency overrides are set.
    """
    with TestClient(app) as c:
        yield c

def test_login_success(client):
    response = client.post(
        "/auth/login",
        json={"username": "admin", "passcode": "secret123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "admin" in data["message"]

def test_login_invalid_username(client):
    response = client.post(
        "/auth/login",
        json={"username": "nonexistent", "passcode": "secret123"}
    )
    assert response.status_code == 401
    # Updated to match implementation in viperos/api.py
    assert "Invalid credentials" in response.json()["detail"]

def test_login_invalid_passcode(client):
    response = client.post(
        "/auth/login",
        json={"username": "admin", "passcode": "wrongpassword"}
    )
    assert response.status_code == 401
    # Updated to match implementation in viperos/api.py
    assert "Invalid credentials" in response.json()["detail"]

def test_login_empty_payload(client):
    response = client.post("/auth/login", json={})
    assert response.status_code == 422