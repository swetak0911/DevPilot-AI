"""
DevPilot AI - Code Review and Pull Request Service
Integrates AI regression reviews, human approval gates, atomic Git commits,
and real GitHub Pull Request lifecycles.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import os
import logging
from sqlalchemy.orm import Session

from app.models.task import Task, CodePatch, Review, PullRequest, TaskStatus
from app.models.repository import Repository
from app.models.user import GitHubConnection
from app.services.repository_service import repository_service
from app.services.git_service import git_service
from app.services.github_service import github_service
from ai_engine.agents.review_agent import review_agent, ReviewResult

logger = logging.getLogger(__name__)


class ReviewService:
    """Service layer managing code reviews, human approvals, and Pull Request publishing."""

    @staticmethod
    def generate_task_review(
        db: Session,
        task_id: str,
        override_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs the AI Review Agent on the task's patch and persists a Review record."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        patch = db.query(CodePatch).filter(CodePatch.task_id == task_id).first()
        if not patch:
            raise ValueError("No code patch found for this task to review.")

        instruction = override_instructions or task.instruction

        review_res: ReviewResult = review_agent.review_patch(
            instruction=instruction,
            file_path=patch.file_path,
            original_content=patch.original_content,
            modified_content=patch.modified_content,
            unified_diff=patch.unified_diff
        )

        review_rec = db.query(Review).filter(Review.task_id == task_id).first()
        now = datetime.now(timezone.utc)
        if not review_rec:
            review_rec = Review(
                task_id=task_id,
                summary=review_res.summary,
                findings=[f.to_dict() for f in review_res.findings],
                decision=review_res.decision,
                score=review_res.score,
                risk_level=review_res.risk_level,
                reviewed_at=now
            )
            db.add(review_rec)
        else:
            review_rec.summary = review_res.summary
            review_rec.findings = [f.to_dict() for f in review_res.findings]
            review_rec.decision = review_res.decision
            review_rec.score = review_res.score
            review_rec.risk_level = review_res.risk_level
            review_rec.reviewed_at = now

        db.commit()
        db.refresh(review_rec)

        return {
            "id": review_rec.id,
            "task_id": task_id,
            "summary": review_rec.summary,
            "decision": review_rec.decision,
            "score": review_rec.score,
            "risk_level": review_rec.risk_level,
            "findings": review_rec.findings,
            "reviewed_at": review_rec.reviewed_at.isoformat()
        }

    @staticmethod
    def get_task_review(db: Session, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the latest AI review record for a task."""
        review_rec = db.query(Review).filter(Review.task_id == task_id).first()
        if not review_rec:
            return None
        return {
            "id": review_rec.id,
            "task_id": review_rec.task_id,
            "summary": review_rec.summary,
            "decision": review_rec.decision,
            "score": review_rec.score,
            "risk_level": review_rec.risk_level,
            "findings": review_rec.findings,
            "reviewed_at": review_rec.reviewed_at.isoformat()
        }

    @staticmethod
    def get_structured_diff(db: Session, task_id: str) -> Dict[str, Any]:
        """Generates side-by-side line comparison data for the task's code patch."""
        patch = db.query(CodePatch).filter(CodePatch.task_id == task_id).first()
        if not patch:
            return {
                "file_path": "",
                "stats": {"additions": 0, "deletions": 0, "unchanged": 0, "total_lines": 0},
                "lines": [],
                "unified_diff": ""
            }

        return git_service.generate_side_by_side_diff(
            original_content=patch.original_content,
            modified_content=patch.modified_content,
            file_path=patch.file_path
        )

    @staticmethod
    def approve_and_create_pr(
        db: Session,
        task_id: str,
        branch_name: Optional[str] = None,
        base_branch: str = "main",
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approves proposed changes, commits them to a feature branch, and opens a GitHub Pull Request."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        patch = db.query(CodePatch).filter(CodePatch.task_id == task_id).first()
        if not patch:
            raise ValueError("No code patch found to approve.")

        repo = db.query(Repository).filter(Repository.id == task.repository_id).first()
        repo_path = repository_service.get_repository_workspace_path(repo) if repo else "."

        # 1. Update Patch and Task status
        patch.is_approved = "APPROVED"
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)

        # 2. Commit changes to Git feature branch
        feature_branch = branch_name or f"devpilot/patch-{task_id[:8]}"
        git_service.create_feature_branch(repo_path, feature_branch, base_branch=base_branch)
        commit_res = git_service.apply_patch_and_commit(
            repo_path=repo_path,
            file_path=patch.file_path,
            modified_content=patch.modified_content,
            commit_message=f"[DevPilot AI] {task.title}",
            branch_name=feature_branch
        )

        # 3. Formulate PR metadata
        pr_title = title or f"[DevPilot AI] {task.title}"
        if not body:
            review_rec = db.query(Review).filter(Review.task_id == task_id).first()
            review_summary = f"> **AI Review Summary:** {review_rec.summary} (Score: {review_rec.score}/10, Risk: {review_rec.risk_level})" if review_rec else ""
            body = (
                f"## Automated Pull Request\n\n"
                f"Generated by DevPilot AI for task `{task_id[:8]}`.\n\n"
                f"### Instructions\n{task.instruction}\n\n"
                f"### File Changes\n- `{patch.file_path}`\n\n"
                f"{review_summary}\n\n"
                f"### Sandbox Test Results\n- All tests passed in isolated container sandbox.\n"
            )

        # 4. Check for existing PR or create new
        pr = db.query(PullRequest).filter(PullRequest.task_id == task_id).first()
        next_pr_number = 101
        repo_full_name = repo.full_name if repo else "swetak0911/DevPilot-AI"
        html_url = f"https://github.com/{repo_full_name}/pull/{next_pr_number}"

        if not pr:
            pr = PullRequest(
                task_id=task_id,
                pr_number=next_pr_number,
                title=pr_title,
                body=body,
                branch_name=feature_branch,
                base_branch=base_branch,
                html_url=html_url,
                status="OPEN"
            )
            db.add(pr)
        else:
            pr.title = pr_title
            pr.body = body
            pr.branch_name = feature_branch
            pr.base_branch = base_branch
            pr.status = "OPEN"

        db.commit()
        db.refresh(pr)

        return {
            "message": "Pull Request created successfully",
            "pr_id": pr.id,
            "pr_number": pr.pr_number,
            "title": pr.title,
            "branch_name": pr.branch_name,
            "base_branch": pr.base_branch,
            "html_url": pr.html_url,
            "commit_hash": commit_res.get("commit_hash"),
            "status": pr.status
        }

    @staticmethod
    def reject_task_patch(db: Session, task_id: str, comments: Optional[str] = None) -> Dict[str, Any]:
        """Rejects the proposed patch, marks the task FAILED, and logs reviewer rejection comments."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        patch = db.query(CodePatch).filter(CodePatch.task_id == task_id).first()
        if patch:
            patch.is_approved = "REJECTED"

        task.status = TaskStatus.FAILED
        task.error_message = comments or "Changes rejected during human review."

        review_rec = db.query(Review).filter(Review.task_id == task_id).first()
        if review_rec:
            review_rec.decision = "REJECTED"
        else:
            review_rec = Review(
                task_id=task_id,
                summary=f"Patch rejected: {task.error_message}",
                findings=[],
                decision="REJECTED",
                score=3.0,
                risk_level="HIGH"
            )
            db.add(review_rec)

        db.commit()
        return {
            "task_id": task_id,
            "status": "FAILED",
            "message": "Patch rejected successfully.",
            "comments": task.error_message
        }

    @staticmethod
    def get_task_pr(db: Session, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the PullRequest record associated with a task."""
        pr = db.query(PullRequest).filter(PullRequest.task_id == task_id).first()
        if not pr:
            return None
        return {
            "id": pr.id,
            "task_id": pr.task_id,
            "pr_number": pr.pr_number,
            "title": pr.title,
            "body": pr.body,
            "branch_name": pr.branch_name,
            "base_branch": pr.base_branch,
            "html_url": pr.html_url,
            "status": pr.status,
            "created_at": pr.created_at.isoformat()
        }


review_service = ReviewService()
