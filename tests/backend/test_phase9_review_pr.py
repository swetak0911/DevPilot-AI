"""
Phase 9 Code Review and GitHub Pull Requests Test Suite
Tests Side-by-Side Diff generation, AI Review Agent regression analysis,
Git feature branching & commits, Human-in-the-loop approval & rejection workflows,
and GitHub Pull Request REST APIs.
"""
import pytest
import os

from ai_engine.agents.review_agent import review_agent, ReviewResult
from app.services.git_service import git_service
from app.services.review_service import review_service
from app.models.task import Task, CodePatch, Review, PullRequest, TaskStatus, TaskType
from app.models.repository import Repository


def test_side_by_side_diff_generation():
    """Verifies opcode extraction, line numbering, additions, deletions, and stats."""
    original = "def calculate_total(price, tax):\n    return price + tax\n"
    modified = "def calculate_total(price, tax):\n    # Added discount check\n    return max(0.0, price + tax)\n"

    diff_data = git_service.generate_side_by_side_diff(
        original_content=original,
        modified_content=modified,
        file_path="src/billing.py"
    )

    assert diff_data["file_path"] == "src/billing.py"
    assert "stats" in diff_data
    assert diff_data["stats"]["additions"] >= 1
    assert "lines" in diff_data
    assert len(diff_data["lines"]) >= 2

    # Check for line types
    types = {line["type"] for line in diff_data["lines"]}
    assert "context" in types
    assert "addition" in types or "deletion" in types


def test_ai_review_agent_regression_analysis():
    """Verifies regression detection, scoring, risk classification, and structured findings."""
    instruction = "Refactor authentication token parser"
    file_path = "src/auth.py"
    original = "def parse_token(t):\n    return jwt.decode(t, 'secret')\n"
    modified = "def parse_token(t):\n    try:\n        return jwt.decode(t, 'secret')\n    except:\n        pass\n"
    diff = "--- a/src/auth.py\n+++ b/src/auth.py\n@@ -2,1 +2,4 @@\n-    return jwt.decode(t, 'secret')\n+    try:\n+        return jwt.decode(t, 'secret')\n+    except:\n+        pass\n"

    res: ReviewResult = review_agent.review_patch(
        instruction=instruction,
        file_path=file_path,
        original_content=original,
        modified_content=modified,
        unified_diff=diff
    )

    assert isinstance(res.score, float)
    assert 0.0 <= res.score <= 10.0
    assert res.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert res.decision in ["APPROVED", "CHANGES_REQUESTED", "NEEDS_HUMAN_INSPECTION"]
    assert len(res.summary) > 5

    # Should detect broad except clause
    assert any("silent" in f.description.lower() or "exception" in f.description.lower() for f in res.findings)


def test_git_service_branching_and_commit(tmp_path):
    """Verifies creating a feature branch and applying an atomic commit."""
    repo_dir = str(tmp_path / "git_test_repo")
    os.makedirs(repo_dir, exist_ok=True)

    # 1. Feature branch
    branch_res = git_service.create_feature_branch(repo_dir, "devpilot/patch-feature-1")
    assert branch_res["success"] is True
    assert branch_res["branch_name"] == "devpilot/patch-feature-1"

    # 2. Apply patch and commit
    commit_res = git_service.apply_patch_and_commit(
        repo_path=repo_dir,
        file_path="service.py",
        modified_content="def hello(): return 'world'\n",
        commit_message="Add hello service"
    )
    assert commit_res["success"] is True
    assert commit_res["commit_hash"] is not None
    assert os.path.exists(os.path.join(repo_dir, "service.py"))


def test_review_service_persistence_and_approval(db_session):
    """Verifies Review persistence, approval workflow, and Pull Request record creation."""
    repo = Repository(
        name="review-repo",
        full_name="devpilot/review-repo",
        html_url="https://github.com/devpilot/review-repo",
        clone_url="https://github.com/devpilot/review-repo.git",
        default_branch="main"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    task = Task(
        user_id="lead_reviewer",
        repository_id=repo.id,
        title="Patch for authentication token cache",
        instruction="Fix cache eviction bug in Redis token store",
        task_type=TaskType.BUG_FIX,
        status=TaskStatus.RUNNING,
        execution_plan=[]
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    patch = CodePatch(
        task_id=task.id,
        file_path="src/cache.py",
        original_content="def get_token(k): return cache.get(k)\n",
        modified_content="def get_token(k): return cache.get(k) if cache else None\n",
        unified_diff="--- a/src/cache.py\n+++ b/src/cache.py\n@@ -1,1 +1,1 @@\n-def get_token(k): return cache.get(k)\n+def get_token(k): return cache.get(k) if cache else None\n",
        is_approved="PENDING"
    )
    db_session.add(patch)
    db_session.commit()

    # 1. Generate Review
    rev_data = review_service.generate_task_review(db_session, task.id)
    assert rev_data["task_id"] == task.id
    assert "summary" in rev_data
    assert "score" in rev_data

    # Check Review in DB
    saved_rev = db_session.query(Review).filter(Review.task_id == task.id).first()
    assert saved_rev is not None
    assert saved_rev.score >= 0.0

    # 2. Approve and Create PR
    pr_data = review_service.approve_and_create_pr(
        db=db_session,
        task_id=task.id,
        branch_name="devpilot/patch-cache-fix"
    )
    assert pr_data["pr_number"] >= 100
    assert pr_data["branch_name"] == "devpilot/patch-cache-fix"
    assert "pull" in pr_data["html_url"]

    # Verify task status & patch approval
    db_session.refresh(task)
    db_session.refresh(patch)
    assert task.status == TaskStatus.COMPLETED
    assert patch.is_approved == "APPROVED"


def test_rejection_workflow(db_session):
    """Verifies rejecting patch sets task to FAILED and updates Review decision."""
    repo = Repository(
        name="reject-repo",
        full_name="devpilot/reject-repo",
        html_url="https://github.com/devpilot/reject-repo",
        clone_url="https://github.com/devpilot/reject-repo.git",
        default_branch="main"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    task = Task(
        user_id="qa_reviewer",
        repository_id=repo.id,
        title="Defective patch test",
        instruction="Fix security leak",
        task_type=TaskType.BUG_FIX,
        status=TaskStatus.RUNNING,
        execution_plan=[]
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    patch = CodePatch(
        task_id=task.id,
        file_path="src/leak.py",
        original_content="x = 1\n",
        modified_content="x = 2\n",
        unified_diff="--- a/src/leak.py\n+++ b/src/leak.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 2\n",
        is_approved="PENDING"
    )
    db_session.add(patch)
    db_session.commit()

    reject_res = review_service.reject_task_patch(db_session, task.id, comments="Incomplete fix; breaks tests.")
    assert reject_res["status"] == "FAILED"

    db_session.refresh(task)
    db_session.refresh(patch)
    assert task.status == TaskStatus.FAILED
    assert patch.is_approved == "REJECTED"
    assert "Incomplete fix" in task.error_message
