"""
Phase 2 Authentication & GitHub Integration Test Suite
Tests developer authentication, password security, token encryption,
and GitHub REST API integration.
"""
import pytest
from app.core.security import encrypt_token, decrypt_token, hash_password, verify_password


def test_token_encryption_and_decryption():
    """Verifies that tokens are encrypted and decrypted correctly with integrity verification."""
    test_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyzABCD"
    encrypted = encrypt_token(test_token)
    assert encrypted != test_token
    assert encrypted.startswith("enc:")
    
    decrypted = decrypt_token(encrypted)
    assert decrypted == test_token


def test_tampered_token_decryption_fails():
    """Verifies that tampering with an encrypted token triggers an integrity verification failure."""
    test_token = "ghp_secret_token_12345"
    encrypted = encrypt_token(test_token)
    
    # Tamper with encrypted string
    tampered = encrypted[:-2] + "XX"
    with pytest.raises(Exception):
        decrypt_token(tampered)


def test_user_registration_and_login_flow(client):
    """Tests complete registration and login lifecycle."""
    email = "phase2_dev@devpilot.ai"
    password = "SuperSecurePassword123!"
    
    # Register
    reg_res = client.post("/api/auth/register", json={
        "email": email,
        "username": "phase2dev",
        "password": password,
        "full_name": "Phase Two Developer"
    })
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == email
    token = reg_data["access_token"]
    
    # Profile (/api/auth/me)
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "phase2dev"
    assert me_res.json()["is_github_connected"] is False

    # Update Profile
    update_res = client.put("/api/auth/me", json={"full_name": "Updated Name"}, headers={"Authorization": f"Bearer {token}"})
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Updated Name"

    # Refresh Token
    refresh_res = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()


def test_github_oauth_authorize_url_generation(client):
    """Verifies generation of GitHub OAuth authorization URL."""
    res = client.get("/api/github/authorize-url")
    assert res.status_code == 200
    data = res.json()
    assert "authorize_url" in data
    assert "github.com/login/oauth/authorize" in data["authorize_url"]
    assert "state=" in data["authorize_url"]


def test_github_pat_connection_and_disconnect(client):
    """Tests connecting GitHub via PAT, checking status, and disconnecting."""
    # First register user to test authenticated endpoints
    reg_res = client.post("/api/auth/register", json={
        "email": "gh_tester@devpilot.ai",
        "username": "ghtester",
        "password": "Password12345!"
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Connect GitHub PAT
    connect_res = client.post("/api/github/connect", json={
        "access_token": "ghp_mock_test_token_for_verification_12345",
        "github_username": "ghtester"
    }, headers=headers)
    assert connect_res.status_code == 200
    conn_data = connect_res.json()
    assert conn_data["is_connected"] is True
    assert conn_data["github_username"] == "ghtester"

    # Check Status
    status_res = client.get("/api/github/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["is_connected"] is True

    # List Repositories
    repos_res = client.get("/api/github/repositories", headers=headers)
    assert repos_res.status_code == 200
    repos = repos_res.json()
    assert isinstance(repos, list)
    assert len(repos) >= 1

    # Disconnect
    disc_res = client.delete("/api/github/disconnect", headers=headers)
    assert disc_res.status_code == 200
    
    # Confirm disconnected
    status_after = client.get("/api/github/status", headers=headers)
    assert status_after.status_code == 200
    assert status_after.json()["is_connected"] is False
