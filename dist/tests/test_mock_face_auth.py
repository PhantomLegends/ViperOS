import pytest
from fastapi.testclient import TestClient
from viperos.api import app

@pytest.fixture(name="client")
def fixture_client():
    """Provides a TestClient for FastAPI."""
    with TestClient(app) as c:
        yield c

def test_mock_face_auth_success(client):
    """
    Test that the mock face authentication endpoint returns success by default.
    Ensures compliance with :codeplain::AdditionalFunctionality:.
    """
    response = client.post("/auth/mock-face", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "authenticated" in data["message"]
    assert "No biometric data was transmitted" in data["message"]

def test_mock_face_auth_with_metadata(client):
    """
    Test that the endpoint accepts optional non-biometric metadata.
    """
    payload = {"metadata": {"device_id": "local_hw_01", "location": "study"}}
    response = client.post("/auth/mock-face", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_mock_face_auth_invalid_payload_type(client):
    """
    Test that sending non-JSON payload results in a 422 Unprocessable Entity error.
    """
    response = client.post("/auth/mock-face", content="plain text is not allowed")
    assert response.status_code == 422

def test_mock_face_auth_rejects_biometric_data(client):
    """
    Test defensive programming: ensure the API rejects fields that look like biometric data.
    This enforces the requirement that biometric data must remain local.
    """
    # Attempting to send an image blob or encoding should be rejected by the model validator
    payload = {
        "metadata": {"some": "data"},
        "image": "base64_encoded_string_that_should_not_be_sent"
    }
    response = client.post("/auth/mock-face", json=payload)
    
    # Validation error (Pydantic ValueError) returns 422
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("Biometric data must stay local" in err["msg"] for err in errors)

def test_mock_face_auth_rejects_photo_field(client):
    """
    Ensure 'photo' field is also rejected defensively.
    """
    payload = {"photo": "binary_data"}
    response = client.post("/auth/mock-face", json=payload)
    assert response.status_code == 422
    assert "Forbidden fields" in response.text