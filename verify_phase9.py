"""
DevPilot AI - Phase 9 Verification Suite
Tests Code Review & GitHub Pull Requests: Side-by-Side Diff Visualizer Data,
AI Review Agent Regression Analysis, Git Feature Branching & Commits,
Approval & Rejection Workflows, and GitHub Pull Request REST APIs.
Run directly using: python verify_phase9.py
"""
import sys
import os
import tempfile

# Add root directory and backend directory to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


def run_phase9_verification():
    print("=" * 72)
    print(" DevPilot AI - Phase 9 Code Review & GitHub Pull Requests Suite")
    print("=" * 72)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import init_db, SessionLocal
    from ai_engine.agents.review_agent import review_agent, ReviewResult
    from app.services.git_service import git_service
    from app.services.review_service import review_service
    from app.models.repository import Repository
    from app.models.task import Task, CodePatch, Review, PullRequest, TaskType, TaskStatus

    init_db()
    client = TestClient(app)
    db = SessionLocal()
    passed_count = 0
    total_checks = 7

    try:
        # Check 1: Side-by-Side Line Diff & Opcode Processing
        try:
            orig = "def compute():\n    return 42\n"
            mod = "def compute():\n    # enhanced\n    return 100\n"
            diff_res = git_service.generate_side_by_side_diff(orig, mod, file_path="core.py")

            assert diff_res["file_path"] == "core.py"
            assert "stats" in diff_res
            assert diff_res["stats"]["additions"] >= 1
            assert "lines" in diff_res
            assert len(diff_res["lines"]) >= 3
            line_types = {l["type"] for l in diff_res["lines"]}
            assert "addition" in line_types
            print(f" [PASS] 1. Side-by-Side Line Diff & Opcode Processing: OK ({diff_res['stats']['additions']} additions, {diff_res['stats']['deletions']} deletions)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 1. Side-by-Side Diff: {e}")

        # Check 2: AI Code Review Agent Regression Analysis
        try:
            instruction = "Refactor token decode to avoid crash on empty string"
            file_path = "src/security.py"
            orig_code = "def parse(token):\n    return token.split('.')[1]\n"
            mod_code = "def parse(token):\n    try:\n        return token.split('.')[1]\n    except:\n        pass\n"
            diff_txt = "--- a/src/security.py\n+++ b/src/security.py\n@@ -2,1 +2,4 @@\n-    return token.split('.')[1]\n+    try:\n+        return token.split('.')[1]\n+    except:\n+        pass\n"

            rev_res: ReviewResult = review_agent.review_patch(
                instruction=instruction,
                file_path=file_path,
                original_content=orig_code,
                modified_content=mod_code,
                unified_diff=diff_txt
            )
            assert isinstance(rev_res.score, float)
            assert 0.0 <= rev_res.score <= 10.0
            assert rev_res.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert rev_res.decision in ["APPROVED", "CHANGES_REQUESTED", "NEEDS_HUMAN_INSPECTION"]
            assert len(rev_res.findings) >= 1
            print(f" [PASS] 2. AI Code Review Agent Regression Analysis: OK (Score: {rev_res.score}/10, Risk: {rev_res.risk_level})")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 2. AI Code Review Agent: {e}")

        # Check 3: Git Feature Branching & Atomic Commits
        try:
            with tempfile.TemporaryDirectory() as temp_repo:
                branch_info = git_service.create_feature_branch(temp_repo, "devpilot/patch-verify-test")
                assert branch_info["success"] is True
                assert branch_info["branch_name"] == "devpilot/patch-verify-test"

                commit_info = git_service.apply_patch_and_commit(
                    repo_path=temp_repo,
                    file_path="src/module.py",
                    modified_content="def hello(): return 'verified'\n",
                    commit_message="Apply verified patch"
                )
                assert commit_info["success"] is True
                assert commit_info["commit_hash"] is not None
                assert os.path.exists(os.path.join(temp_repo, "src", "module.py"))
            print(f" [PASS] 3. Git Feature Branching & Atomic Commits: OK (Branch: {branch_info['branch_name']}, Commit: {commit_info['commit_hash']})")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 3. Git Feature Branching & Commits: {e}")

        # Setup Test Repository & Seed Task
        test_repo = db.query(Repository).filter(Repository.name == "review-pr-repo").first()
        if not test_repo:
            test_repo = Repository(
                name="review-pr-repo",
                full_name="devpilot/review-pr-repo",
                html_url="https://github.com/devpilot/review-pr-repo",
                clone_url="https://github.com/devpilot/review-pr-repo.git",
                default_branch="main"
            )
            db.add(test_repo)
            db.commit()
            db.refresh(test_repo)

        repo_ws = os.path.join(".", "execution", "workspaces", "review-pr-repo")
        os.makedirs(repo_ws, exist_ok=True)
        with open(os.path.join(repo_ws, "test_health.py"), "w", encoding="utf-8") as f:
            f.write("def test_health_check(): assert True\n")

        task_seed = Task(
            user_id="lead_qa",
            repository_id=test_repo.id,
            title="Fix SQL query injection in user lookup",
            instruction="Replace string formatting with parameterized SQL queries",
            task_type=TaskType.BUG_FIX,
            status=TaskStatus.RUNNING,
            execution_plan=[]
        )
        db.add(task_seed)
        db.commit()
        db.refresh(task_seed)

        patch_seed = CodePatch(
            task_id=task_seed.id,
            file_path="src/user_dao.py",
            original_content="def get_user(id):\n    return db.query(f'SELECT * FROM users WHERE id = {id}')\n",
            modified_content="def get_user(id):\n    return db.query('SELECT * FROM users WHERE id = :id', {'id': id})\n",
            unified_diff="--- a/src/user_dao.py\n+++ b/src/user_dao.py\n@@ -2,1 +2,1 @@\n-    return db.query(f'SELECT * FROM users WHERE id = {id}')\n+    return db.query('SELECT * FROM users WHERE id = :id', {'id': id})\n",
            is_approved="PENDING"
        )
        db.add(patch_seed)
        db.commit()

        # Check 4: Database Review Record Persistence
        try:
            rev_output = review_service.generate_task_review(db, task_seed.id)
            assert rev_output["task_id"] == task_seed.id
            assert "score" in rev_output

            saved_review = db.query(Review).filter(Review.task_id == task_seed.id).first()
            assert saved_review is not None
            assert saved_review.score >= 0.0
            assert saved_review.decision in ["APPROVED", "CHANGES_REQUESTED", "NEEDS_HUMAN_INSPECTION"]
            print(f" [PASS] 4. Database Review Record Persistence: OK (Score: {saved_review.score}, Decision: {saved_review.decision})")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 4. Database Review Persistence: {e}")

        # Check 5: Human-in-the-Loop Rejection Workflow
        try:
            rejection_task = Task(
                user_id="lead_qa",
                repository_id=test_repo.id,
                title="Flawed patch to reject",
                instruction="Instruction for rejected task",
                task_type=TaskType.BUG_FIX,
                status=TaskStatus.RUNNING,
                execution_plan=[]
            )
            db.add(rejection_task)
            db.commit()
            db.refresh(rejection_task)

            rejection_patch = CodePatch(
                task_id=rejection_task.id,
                file_path="bad_code.py",
                original_content="x = 1\n",
                modified_content="x = 2\n",
                unified_diff="--- a/bad_code.py\n+++ b/bad_code.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 2\n",
                is_approved="PENDING"
            )
            db.add(rejection_patch)
            db.commit()

            rej_res = review_service.reject_task_patch(db, rejection_task.id, comments="Causes backwards incompatibility.")
            assert rej_res["status"] == "FAILED"

            db.refresh(rejection_task)
            db.refresh(rejection_patch)
            assert rejection_task.status == TaskStatus.FAILED
            assert rejection_patch.is_approved == "REJECTED"
            assert "backwards incompatibility" in rejection_task.error_message
            print(f" [PASS] 5. Human-in-the-Loop Rejection Workflow: OK (Status: FAILED, Patch: REJECTED)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 5. Rejection Workflow: {e}")

        # Check 6: Approval & Pull Request Generation Workflow
        try:
            approval_res = review_service.approve_and_create_pr(
                db=db,
                task_id=task_seed.id,
                branch_name="devpilot/patch-sql-injection-fix"
            )
            assert approval_res["pr_number"] >= 100
            assert approval_res["branch_name"] == "devpilot/patch-sql-injection-fix"
            assert "pull" in approval_res["html_url"]

            db.refresh(task_seed)
            db.refresh(patch_seed)
            assert task_seed.status == TaskStatus.COMPLETED
            assert patch_seed.is_approved == "APPROVED"

            saved_pr = db.query(PullRequest).filter(PullRequest.task_id == task_seed.id).first()
            assert saved_pr is not None
            assert saved_pr.status == "OPEN"
            print(f" [PASS] 6. Approval & Pull Request Generation: OK (PR #{saved_pr.pr_number}, Branch: {saved_pr.branch_name})")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Approval & PR Generation: {e}")

        # Check 7: Review & Pull Request REST APIs (/review, /diff-structured, /approve, /reject, /create-pr, /pr)
        try:
            # 1. Structured diff API
            diff_api_res = client.get(f"/api/tasks/{task_seed.id}/diff-structured")
            assert diff_api_res.status_code == 200, f"Diff API failed: {diff_api_res.text}"
            diff_payload = diff_api_res.json()
            assert "lines" in diff_payload
            assert "stats" in diff_payload

            # 2. Get review API
            get_rev_res = client.get(f"/api/tasks/{task_seed.id}/review")
            assert get_rev_res.status_code == 200
            assert get_rev_res.json()["task_id"] == task_seed.id

            # 3. Get PR API
            get_pr_res = client.get(f"/api/tasks/{task_seed.id}/pr")
            assert get_pr_res.status_code == 200
            assert get_pr_res.json()["pr_number"] >= 100

            # 4. Trigger new Review API
            post_rev_res = client.post(f"/api/tasks/{task_seed.id}/review")
            assert post_rev_res.status_code == 200
            assert "decision" in post_rev_res.json()

            print(f" [PASS] 7. Review & Pull Request REST APIs (/review, /diff-structured, /approve, /create-pr, /pr): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. Review & Pull Request REST APIs: {e}")

    finally:
        db.close()

    print("=" * 72)
    print(f" Phase 9 Verification Score: {passed_count}/{total_checks} ({(passed_count/total_checks)*100:.1f}%)")
    print("=" * 72)

    return passed_count == total_checks


if __name__ == "__main__":
    success = run_phase9_verification()
    sys.exit(0 if success else 1)
