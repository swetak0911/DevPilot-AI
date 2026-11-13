"""Authentication Workflow Tests."""


def test_register_user(client):
    payload = {
        "email": "engineer@example.com",
        "username": "engineer",
        "password": "SecurePassword123!",
        "full_name": "Test Engineer"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["username"] == payload["username"]


def test_login_user(client):
    # Register first
    reg_payload = {
        "email": "login_test@example.com",
        "username": "logintest",
        "password": "SecurePassword123!",
    }
    client.post("/api/auth/register", json=reg_payload)

    # Login
    login_payload = {
        "email": "login_test@example.com",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "logintest"


def test_login_invalid_password(client):
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "WrongPassword!",
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401
