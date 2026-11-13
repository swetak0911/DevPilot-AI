"""
Task Workspace Manager
Provisions isolated temporary workspaces for task execution, safely copies files,
applies proposed patches, and ensures safe cleanup.
"""
import os
import shutil
from typing import Optional
import logging

from app.services.file_filter import file_filter

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages ephemeral task workspaces to prevent contamination of the main repository."""

    def __init__(self, base_workspaces_dir: Optional[str] = None):
        if not base_workspaces_dir:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            base_workspaces_dir = os.path.join(project_root, "execution", "workspaces")
        self.workspaces_dir = base_workspaces_dir
        os.makedirs(self.workspaces_dir, exist_ok=True)

    def create_isolated_workspace(self, task_id: str, source_repo_path: str) -> str:
        """
        Creates an isolated copy of source_repo_path inside execution/workspaces/{task_id}.
        Excludes sensitive files, virtualenvs, and node_modules.
        """
        dest_dir = os.path.join(self.workspaces_dir, f"task_{task_id}")
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)
        os.makedirs(dest_dir, exist_ok=True)

        if not os.path.exists(source_repo_path):
            return dest_dir

        for root, dirs, files in os.walk(source_repo_path):
            # Exclude ignored directories and scratch workspace folders
            dirs[:] = [
                d for d in dirs
                if not file_filter.is_directory_ignored(d)
                and d not in ("execution", "workspaces", ".git", ".pytest_cache")
            ]

            rel_root = os.path.relpath(root, source_repo_path)
            target_root = os.path.join(dest_dir, rel_root) if rel_root != "." else dest_dir
            os.makedirs(target_root, exist_ok=True)

            for file in files:
                if file_filter.is_sensitive_filename(file) or file.endswith(".pyc"):
                    continue
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_root, file)
                try:
                    shutil.copy2(src_file, dst_file)
                except Exception as exc:
                    logger.debug("Skipped copying %s: %s", src_file, exc)

        return dest_dir

    def apply_patch_to_workspace(
        self,
        workspace_path: str,
        file_path: str,
        modified_content: str
    ) -> bool:
        """Writes the patched content to the file within the isolated workspace."""
        clean_rel = file_path.replace("\\", "/").lstrip("/")
        full_path = os.path.join(workspace_path, clean_rel)

        # Path traversal guard
        normalized = os.path.abspath(full_path)
        if not normalized.startswith(os.path.abspath(workspace_path)):
            raise ValueError(f"Path traversal attempted: {file_path}")

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(modified_content)
        return True

    def cleanup_workspace(self, workspace_path: str) -> bool:
        """Safely removes the ephemeral workspace."""
        try:
            if os.path.exists(workspace_path) and "task_" in os.path.basename(workspace_path):
                shutil.rmtree(workspace_path, ignore_errors=True)
                return True
        except Exception as exc:
            logger.warning("Could not delete workspace %s: %s", workspace_path, exc)
        return False


workspace_manager = WorkspaceManager()
