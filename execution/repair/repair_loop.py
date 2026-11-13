"""
Self-Healing Bounded Repair Loop
Executes automated test-driven repair cycles with a strict upper bound (maximum 3 attempts).
Analyzes failure traces, prompts the Coding Agent with specific test failures,
validates repaired patches, and verifies fixes inside the isolated sandbox.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

from execution.sandbox.workspace_manager import workspace_manager
from execution.runners.test_runner import test_runner, StructuredTestReport
from ai_engine.agents.coding_agent import coding_agent, CodingResult
from ai_engine.agents.patch_validator import patch_validator, PatchValidationResult

logger = logging.getLogger(__name__)


@dataclass
class RepairResult:
    resolved: bool
    attempts_used: int
    final_patch: str
    final_modified_content: str
    attempt_reports: List[StructuredTestReport]
    status: str  # "RESOLVED" or "ATTEMPTS_EXHAUSTED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolved": self.resolved,
            "attempts_used": self.attempts_used,
            "final_patch": self.final_patch,
            "final_modified_content": self.final_modified_content,
            "attempt_reports": [r.to_dict() for r in self.attempt_reports],
            "status": self.status
        }


class RepairLoop:
    """Bounded automated repair loop that iteratively fixes failing tests."""

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def execute_repair_loop(
        self,
        task_id: str,
        repo_path: str,
        instruction: str,
        file_path: str,
        original_content: str,
        initial_diff: str,
        test_file: Optional[str] = None
    ) -> RepairResult:
        """
        Executes bounded test-and-repair loop up to max_attempts.
        """
        # 1. Create isolated workspace
        workspace = workspace_manager.create_isolated_workspace(task_id, repo_path)

        current_diff = initial_diff
        # Apply initial patch
        val_res = patch_validator.validate_and_apply(original_content, current_diff, file_path)
        current_content = val_res.applied_content or original_content

        workspace_manager.apply_patch_to_workspace(workspace, file_path, current_content)

        attempt_reports: List[StructuredTestReport] = []
        resolved = False
        attempts_used = 0

        for attempt in range(1, self.max_attempts + 1):
            attempts_used = attempt
            logger.info("Executing Sandbox Test Attempt %d/%d for task %s...", attempt, self.max_attempts, task_id)

            # Run tests in sandbox
            report: StructuredTestReport = test_runner.run_tests(
                workspace_path=workspace,
                test_file=test_file,
                attempt_number=attempt
            )
            attempt_reports.append(report)

            if report.all_passed:
                logger.info("Sandbox verification passed on attempt %d!", attempt)
                resolved = True
                break

            # If tests failed and attempts remain, trigger self-healing repair
            if attempt < self.max_attempts:
                failure_summary = "; ".join(
                    f"{f.test_name}: {f.message}" for f in report.failure_details[:3]
                )
                logger.info("Attempt %d failed (%s). Triggering Coding Agent repair iteration...", attempt, failure_summary)

                repair_prompt = (
                    f"REPAIR ITERATION {attempt + 1}: The previous code patch failed unit tests in sandbox.\n"
                    f"Task Instruction: {instruction}\n"
                    f"Target File: {file_path}\n"
                    f"Test Failure Details: {failure_summary}\n"
                    f"Please inspect the error trace and output a corrected, complete replacement file."
                )

                coding_res: CodingResult = coding_agent.generate_patch(
                    instruction=repair_prompt,
                    file_path=file_path,
                    original_content=original_content
                )

                # Validate repaired diff
                val_repair = patch_validator.validate_and_apply(
                    original_content,
                    coding_res.unified_diff,
                    file_path
                )

                if val_repair.is_valid and val_repair.applied_content:
                    current_diff = coding_res.unified_diff
                    current_content = val_repair.applied_content
                    workspace_manager.apply_patch_to_workspace(workspace, file_path, current_content)

        # Cleanup ephemeral workspace
        workspace_manager.cleanup_workspace(workspace)

        return RepairResult(
            resolved=resolved,
            attempts_used=attempts_used,
            final_patch=current_diff,
            final_modified_content=current_content,
            attempt_reports=attempt_reports,
            status="RESOLVED" if resolved else "ATTEMPTS_EXHAUSTED"
        )


repair_loop = RepairLoop()
