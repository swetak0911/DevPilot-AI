"""
DevPilot AI - Phase 1 Foundation Verification Suite
Run directly using: python verify_phase1.py
"""
import sys
import os

# Add backend directory to path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

REQUIRED_PACKAGES = [
    ("fastapi", "FastAPI"),
    ("uvicorn", "Uvicorn"),
    ("pydantic", "Pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("sqlalchemy", "SQLAlchemy"),
    ("httpx", "HTTPX"),
]

def check_dependencies():
    missing = []
    for module_name, package_name in REQUIRED_PACKAGES:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)
    return missing

def run_checks():
    print("=" * 68)
    print(" DevPilot AI - Phase 1 Foundation Verification Suite")
    print("=" * 68)

    # Pre-check: Installed Packages
    missing = check_dependencies()
    if missing:
        print("\n [!] Missing Required Dependencies for Backend Foundation:")
        for pkg in missing:
            print(f"     - {pkg}")
        print("\n [*] Please install the dependencies by executing:")
        print("     pip install -r backend/requirements.txt")
        print("     OR run:")
        print("     pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy httpx pytest")
        print("\n" + "=" * 68)
        print(f" Verification Status: Dependency Installation Required ({len(missing)} missing)")
        print("=" * 68)
        return False

    passed_count = 0
    total_checks = 7

    # 1. Config & Settings Check
    try:
        from app.core.config import settings
        assert settings.APP_NAME == "DevPilot AI"
        print(" [PASS] 1. Configuration & Settings: OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 1. Configuration & Settings: {e}")

    # 2. Database Models & SQLite Initialization
    try:
        from app.core.database import init_db, SessionLocal
        from app.models import User, Repository, Task
        init_db()
        session = SessionLocal()
        session.close()
        print(" [PASS] 2. Database Schema & Tables Initialization: OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 2. Database Schema Initialization: {e}")

    # 3. Security (Password Hashing & JWT)
    try:
        from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
        hashed = hash_password("TestSecret123!")
        assert verify_password("TestSecret123!", hashed) is True
        token = create_access_token({"sub": "user-123", "email": "test@devpilot.ai"})
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        print(" [PASS] 3. Cryptography & JWT Token Processing: OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 3. Cryptography & JWT: {e}")

    # 4. FastAPI Application Setup & Route Discovery
    try:
        from app.main import app
        schema = app.openapi()
        paths = list(schema.get("paths", {}).keys())
        assert "/api/monitoring/health" in paths or any("health" in p for p in paths)
        print(f" [PASS] 4. FastAPI Routes Registered: {len(paths)} endpoints discovered via OpenAPI")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 4. FastAPI Application: {e}")

    # 5. API Testing with TestClient
    client = None
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        
        # Test Root & Health
        root_res = client.get("/")
        assert root_res.status_code == 200
        health_res = client.get("/api/monitoring/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "HEALTHY"
        print(" [PASS] 5. Root & Health Check Endpoints: 200 OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 5. TestClient Execution: {e}")

    # 6. Autonomous Engineering & Repository Endpoints
    if client is not None:
        try:
            # Repositories
            repo_res = client.get("/api/repositories")
            assert repo_res.status_code == 200
            repos = repo_res.json()
            assert len(repos) >= 1
            repo_id = repos[0]["id"]

            # Tasks Creation & Lifecycle
            task_res = client.post("/api/tasks", json={
                "repository_id": repo_id,
                "title": "Fix token validation boundary condition",
                "instruction": "Scan auth module, fix defect, run tests, and prepare PR",
                "task_type": "BUG_FIX"
            })
            assert task_res.status_code == 201
            task_id = task_res.json()["id"]

            start_res = client.post(f"/api/tasks/{task_id}/start")
            assert start_res.status_code == 200
            assert start_res.json()["status"] == "RUNNING"
            print(" [PASS] 6. Repository & Autonomous Task Lifecycle: OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Repository & Tasks Execution: {e}")
    else:
        print(" [SKIP] 6. Repository & Tasks Execution: Skipped due to client initialization failure")

    # 7. Predictive Intelligence & DevOps Endpoints
    if client is not None:
        try:
            # Repositories check for repo_id
            repos = client.get("/api/repositories").json()
            repo_id = repos[0]["id"]

            # CI/CD Workflow Generation
            cicd_res = client.post("/api/cicd/generate", json={
                "repository_id": repo_id,
                "include_linting": True,
                "include_tests": True
            })
            assert cicd_res.status_code == 200
            assert cicd_res.json()["validation_status"] == "VALID"

            # ML Defect Prediction
            defect_res = client.post("/api/ml/defect-prediction", json={
                "code_snippet": "def login(): eval(input())",
                "language": "python"
            })
            assert defect_res.status_code == 200
            assert defect_res.json()["has_defect"] is True

            # ML Deployment Risk
            risk_res = client.post("/api/ml/deployment-risk", json={
                "repository_id": repo_id,
                "files_changed": 5,
                "lines_added": 80,
                "lines_deleted": 10,
                "dependencies_changed": 0,
                "historical_failure_rate": 0.05
            })
            assert risk_res.status_code == 200
            assert "risk_score" in risk_res.json()
            print(" [PASS] 7. Deep Learning Inference & DevOps Engine: OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. ML & DevOps Execution: {e}")
    else:
        print(" [SKIP] 7. ML & DevOps Execution: Skipped due to client initialization failure")

    print("=" * 68)
    print(f" Verification Result: {passed_count}/{total_checks} Checks Passed ({int(passed_count/total_checks*100)}% Success)")
    print("=" * 68)
    return passed_count == total_checks

if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
