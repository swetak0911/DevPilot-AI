"""
DevPilot AI - Phase 3 Verification Suite
Tests Repository Intelligence, AST Code Parsing, Dependency Analysis,
and Incremental Code Chunk Indexing.
Run directly using: python verify_phase3.py
"""
import sys
import os

# Add backend directory to path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def run_phase3_verification():
    print("=" * 72)
    print(" DevPilot AI - Phase 3 Repository Intelligence Engine Suite")
    print("=" * 72)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import init_db, SessionLocal
    from app.services.file_filter import file_filter
    from app.services.code_parser import code_parser
    from app.services.dependency_analyzer import dependency_analyzer
    from app.services.repository_indexer import repository_indexer
    from app.models.repository import Repository, CodeChunk, RepositoryFile

    init_db()
    client = TestClient(app)
    passed_count = 0
    total_checks = 7

    # Check 1: File Filter Security & Sensitive Pattern Exclusion
    try:
        assert file_filter.is_sensitive_filename(".env") is True
        assert file_filter.is_sensitive_filename("id_rsa") is True
        assert file_filter.is_directory_ignored("node_modules") is True
        assert file_filter.is_directory_ignored(".venv") is True
        assert file_filter.is_binary_file("archive.zip") is True
        is_safe, reason = file_filter.is_safe_for_indexing("../etc/passwd")
        assert is_safe is False
        assert "traversal" in reason.lower()
        findings = file_filter.scan_for_secrets("AWS = 'AKIAIOSFODNN7EXAMPLE'")
        assert len(findings) >= 1
        print(" [PASS] 1. File Filter & Security Guard (Traversal, Secrets, Binaries): OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 1. File Filter Security: {e}")

    # Check 2: Multi-Language AST Code Parsing
    try:
        sample_code = '''
class SecurityManager:
    """Handles cryptography."""
    def encrypt_data(self, key: str, payload: str) -> str:
        """Encrypts payload."""
        return payload[::-1]

async def dispatch_event(event_name: str) -> bool:
    return True
'''
        res = code_parser.parse_source_code("security.py", sample_code)
        assert res.language == "Python"
        names = {s.name: s for s in res.symbols}
        assert "SecurityManager" in names
        assert names["SecurityManager"].symbol_type == "class"
        assert "encrypt_data" in names
        assert names["encrypt_data"].symbol_type == "method"
        assert "dispatch_event" in names
        assert names["dispatch_event"].symbol_type == "async_function"
        print(" [PASS] 2. Multi-Language AST Parsing (Classes, Functions, Methods): OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 2. AST Code Parsing: {e}")

    # Check 3: Dependency & Framework Analysis
    try:
        project_root = os.path.abspath(os.path.dirname(__file__))
        dep_report = dependency_analyzer.analyze_directory(project_root)
        assert "Python" in dep_report.detected_languages
        assert "FastAPI" in dep_report.detected_frameworks or "React" in dep_report.detected_frameworks
        assert dep_report.has_dockerfile is True
        print(f" [PASS] 3. Dependency & Framework Analysis: OK (Detected: {', '.join(dep_report.detected_frameworks)})")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 3. Dependency Analysis: {e}")

    # Check 4: Real Repository Indexing & Database Code Chunks
    try:
        db = SessionLocal()
        repo = db.query(Repository).filter(Repository.name == "DevPilot-AI").first()
        if not repo:
            repo = Repository(
                name="DevPilot-AI",
                full_name="swetak0911/DevPilot-AI",
                html_url="https://github.com/swetak0911/DevPilot-AI",
                clone_url="https://github.com/swetak0911/DevPilot-AI.git",
                default_branch="main"
            )
            db.add(repo)
            db.commit()
            db.refresh(repo)

        # Index backend/app directory
        backend_dir = os.path.join(project_root, "backend", "app")
        stats = repository_indexer.index_directory(db=db, repository_id=repo.id, root_dir=backend_dir, force=True)
        assert stats["status"] == "COMPLETED"
        assert stats["files_indexed"] >= 5
        assert stats["symbols_extracted"] >= 10
        assert stats["chunks_created"] >= 10

        chunks_count = db.query(CodeChunk).filter(CodeChunk.repository_id == repo.id).count()
        assert chunks_count >= 10
        db.close()
        print(f" [PASS] 4. Repository AST Indexing & Database Chunks: OK ({stats['symbols_extracted']} symbols extracted, {chunks_count} chunks persisted)")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 4. Repository Indexing: {e}")

    # Check 5: Real Hierarchical File Tree API Endpoint
    try:
        repos_res = client.get("/api/repositories")
        assert repos_res.status_code == 200
        repo_id = repos_res.json()[0]["id"]

        tree_res = client.get(f"/api/repositories/{repo_id}/tree")
        assert tree_res.status_code == 200
        tree = tree_res.json()
        assert len(tree) >= 1
        assert any(n["name"] in ("backend", "frontend", "README.md") for n in tree)
        print(f" [PASS] 5. Real Hierarchical File Tree Generation: OK ({len(tree)} root nodes)")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 5. File Tree Generation: {e}")

    # Check 6: Symbol Catalog & Dependency API Endpoints
    try:
        # Symbols
        sym_res = client.get(f"/api/repositories/{repo_id}/symbols")
        assert sym_res.status_code == 200
        sym_data = sym_res.json()
        assert sym_data["symbol_count"] >= 10
        assert len(sym_data["symbols"]) >= 10

        # Dependencies
        dep_res = client.get(f"/api/repositories/{repo_id}/dependencies")
        assert dep_res.status_code == 200
        dep_data = dep_res.json()
        assert "FastAPI" in dep_data["detected_frameworks"] or "React" in dep_data["detected_frameworks"]
        print(f" [PASS] 6. Extracted Symbols & Framework Inspection APIs: OK ({sym_data['symbol_count']} symbols in catalog)")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 6. Symbol Catalog & Dependencies API: {e}")

    # Check 7: Safe File Retrieval & Path Traversal Guard
    try:
        # Valid file read
        file_res = client.get(f"/api/repositories/{repo_id}/file?path=backend/app/main.py")
        assert file_res.status_code == 200
        assert "FastAPI" in file_res.json()["content"]

        # Path traversal rejection
        bad_res = client.get(f"/api/repositories/{repo_id}/file?path=../../windows/system32/cmd.exe")
        assert bad_res.status_code in (400, 403, 404)
        print(" [PASS] 7. Safe File Content Access & Path Traversal Guard: OK")
        passed_count += 1
    except Exception as e:
        print(f" [FAIL] 7. Safe File Access: {e}")

    print("=" * 72)
    print(f" Verification Result: {passed_count}/{total_checks} Checks Passed ({int(passed_count/total_checks*100)}% Success)")
    print("=" * 72)
    return passed_count == total_checks

if __name__ == "__main__":
    success = run_phase3_verification()
    sys.exit(0 if success else 1)
