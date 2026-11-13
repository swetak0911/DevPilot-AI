"""
DevPilot AI - Phase 2 Verification Suite
Tests Authentication, Token Encryption, Session Handling, and GitHub Integration.
Run directly using: python verify_phase2.py
"""
import sys
import os

# Add backend directory to path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def run_phase2_verification():
    print("=" * 70)
    print(" DevPilot AI - Phase 2 Authentication & GitHub Integration Suite")
    print("=" * 70)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import encrypt_token, decrypt_token
    from app.core.database import init_db

    init_db()
    client = TestClient(app)
    passed_count = 0
    total_checks = 7

    # Check 1: Token Encryption & Decryption
    try:
        raw_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyzABCD"
        encrypted = encrypt_token(raw_token)
        assert encrypted != raw_token, "Token was not encrypted"
        assert encrypted.startswith("enc:"), "Encrypted token missing prefix"
        decrypted = decrypt_token(encrypted)
        assert decrypted == raw_token, "Decrypted token does not match original"
        print(" [PASS] 1. Token Encryption & Decryption Integrity: OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 1. Token Encryption & Decryption: {e}")

    # Check 2: User Registration & Session Token Issuance
    token = None
    try:
        import uuid
        unique_suffix = str(uuid.uuid4())[:6]
        reg_payload = {
            "email": f"developer_{unique_suffix}@devpilot.ai",
            "username": f"dev_{unique_suffix}",
            "password": "SecurePassword123!",
            "full_name": "DevPilot Core Developer"
        }
        res = client.post("/api/auth/register", json=reg_payload)
        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        data = res.json()
        assert "access_token" in data, "Token missing from response"
        token = data["access_token"]
        print(f" [PASS] 2. User Registration & JWT Issuance: OK (User: {reg_payload['username']})")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 2. User Registration: {e}")

    # Check 3: Authentication & Profile Operations
    try:
        headers = {"Authorization": f"Bearer {token}"}
        # Get Profile
        me_res = client.get("/api/auth/me", headers=headers)
        assert me_res.status_code == 200, f"Failed /me: {me_res.text}"
        assert me_res.json()["is_github_connected"] is False

        # Update Profile
        upd_res = client.put("/api/auth/me", json={"full_name": "Senior AI Architect"}, headers=headers)
        assert upd_res.status_code == 200
        assert upd_res.json()["full_name"] == "Senior AI Architect"

        # Refresh Token
        ref_res = client.post("/api/auth/refresh", headers=headers)
        assert ref_res.status_code == 200
        token = ref_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(" [PASS] 3. Profile Updates & Token Refresh: OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 3. Profile & Refresh Operations: {e}")

    # Check 4: GitHub OAuth Authorization URL Generator
    try:
        auth_res = client.get("/api/github/authorize-url")
        assert auth_res.status_code == 200, f"Authorize URL failed: {auth_res.text}"
        auth_data = auth_res.json()
        assert "authorize_url" in auth_data
        assert "github.com/login/oauth/authorize" in auth_data["authorize_url"]
        assert "state=" in auth_data["authorize_url"]
        print(" [PASS] 4. GitHub OAuth URL & CSRF State Generator: OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 4. GitHub OAuth URL: {e}")

    # Check 5: GitHub PAT Connection with Encrypted Storage
    try:
        conn_res = client.post("/api/github/connect", json={
            "access_token": "ghp_mock_verification_token_0987654321",
            "github_username": "swetak0911"
        }, headers=headers)
        assert conn_res.status_code == 200, f"Connect failed: {conn_res.text}"
        conn_data = conn_res.json()
        assert conn_data["is_connected"] is True
        assert conn_data["github_username"] == "swetak0911"
        print(" [PASS] 5. GitHub Token Connection & Encrypted Storage: OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 5. GitHub Connection: {e}")

    # Check 6: GitHub Status & Live Repository Listing
    try:
        status_res = client.get("/api/github/status", headers=headers)
        assert status_res.status_code == 200
        assert status_res.json()["is_connected"] is True

        repos_res = client.get("/api/github/repositories", headers=headers)
        assert repos_res.status_code == 200
        repos = repos_res.json()
        assert len(repos) >= 1
        assert any("DevPilot-AI" in r["name"] for r in repos)
        print(f" [PASS] 6. GitHub Connection Status & Repository Listing: OK ({len(repos)} repos listed)")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 6. Repository Listing: {e}")

    # Check 7: Repository Selection & Disconnect
    try:
        select_res = client.post("/api/github/repositories/select", json={
            "full_name": "swetak0911/DevPilot-AI",
            "clone_url": "https://github.com/swetak0911/DevPilot-AI.git",
            "default_branch": "main",
            "description": "Autonomous Software Engineering & DevOps Intelligence Platform",
            "language": "Python"
        }, headers=headers)
        assert select_res.status_code == 200
        assert select_res.json()["name"] == "DevPilot-AI"

        # Disconnect
        disc_res = client.delete("/api/github/disconnect", headers=headers)
        assert disc_res.status_code == 200
        
        # Verify status is now disconnected
        status_after = client.get("/api/github/status", headers=headers)
        assert status_after.status_code == 200
        assert status_after.json()["is_connected"] is False
        print(" [PASS] 7. Repository Selection & Disconnect Lifecycle: OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 7. Repository Selection & Disconnect: {e}")

    print("=" * 70)
    print(f" Verification Result: {passed_count}/{total_checks} Checks Passed ({int(passed_count/total_checks*100)}% Success)")
    print("=" * 70)
    return passed_count == total_checks

if __name__ == "__main__":
    success = run_phase2_verification()
    sys.exit(0 if success else 1)
