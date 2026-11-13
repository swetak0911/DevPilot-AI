"""
Repository Service
Coordinates workspace resolution, tree structure generation, AST indexing,
and safe file retrieval.
"""
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.repository import Repository, RepositoryFile, CodeChunk
from app.services.file_filter import file_filter
from app.services.repository_indexer import repository_indexer
from app.services.dependency_analyzer import dependency_analyzer
from app.schemas.repository import FileTreeNode


class RepositoryService:
    def get_repository_workspace_path(self, repo: Repository) -> str:
        """
        Resolves the local directory for the repository.
        If the repo is the active workspace 'DevPilot-AI', points directly to local project root.
        Otherwise, points to execution/workspaces/<repo_name>.
        """
        # Detect if this matches current local workspace
        current_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if repo.name == "DevPilot-AI" or "DevPilot-AI" in repo.full_name:
            return current_project_root

        # Stored workspace path
        workspace_dir = os.path.join(current_project_root, "execution", "workspaces", repo.name)
        os.makedirs(workspace_dir, exist_ok=True)
        return workspace_dir

    def get_file_tree(self, root_dir: str, max_depth: int = 5) -> List[FileTreeNode]:
        """Builds a real hierarchical directory tree starting from root_dir."""
        def _build_tree(current_dir: str, depth: int) -> List[FileTreeNode]:
            if depth > max_depth:
                return []
            nodes: List[FileTreeNode] = []
            try:
                entries = sorted(os.scandir(current_dir), key=lambda e: (not e.is_dir(), e.name.lower()))
            except OSError:
                return []

            for entry in entries:
                if entry.name.startswith(".") and entry.name not in (".env.example", ".gitignore", ".github"):
                    continue
                if file_filter.is_directory_ignored(entry.name):
                    continue

                rel_path = os.path.relpath(entry.path, root_dir).replace("\\", "/")

                if entry.is_dir():
                    children = _build_tree(entry.path, depth + 1)
                    nodes.append(FileTreeNode(
                        name=entry.name,
                        path=rel_path,
                        type="directory",
                        children=children
                    ))
                elif entry.is_file():
                    is_safe, _ = file_filter.is_safe_for_indexing(rel_path)
                    if not is_safe and not entry.name.endswith((".md", ".json", ".yml", ".yaml")):
                        continue
                    try:
                        size = entry.stat().st_size
                    except OSError:
                        size = 0
                    ext = entry.name.split(".")[-1] if "." in entry.name else None
                    nodes.append(FileTreeNode(
                        name=entry.name,
                        path=rel_path,
                        type="file",
                        size=size,
                        language=ext.upper() if ext else "TEXT"
                    ))
            return nodes

        return _build_tree(root_dir, 1)

    def read_repository_file(self, root_dir: str, relative_path: str) -> Dict[str, Any]:
        """Safely reads content of a repository file with strict path traversal guards."""
        normalized = os.path.normpath(relative_path).replace("\\", "/")
        if normalized.startswith("..") or os.path.isabs(normalized):
            raise HTTPException(status_code=400, detail="Path traversal attempt rejected.")

        full_path = os.path.join(root_dir, normalized)
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail=f"File '{relative_path}' not found in repository.")

        # Check safety
        is_safe, reason = file_filter.is_safe_for_indexing(normalized)
        if not is_safe and not normalized.endswith((".md", ".json", ".yml", ".yaml", ".txt")):
            raise HTTPException(status_code=403, detail=f"Access denied: {reason}")

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return {
                "file_path": normalized,
                "size_bytes": len(content),
                "line_count": len(content.splitlines()),
                "content": content
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to read file: {exc}")

    def get_extracted_symbols(self, db: Session, repository_id: str) -> List[Dict[str, Any]]:
        """Retrieves all indexed functions, methods, and classes for the repository."""
        chunks = db.query(CodeChunk).filter(
            CodeChunk.repository_id == repository_id,
            CodeChunk.chunk_type.in_(["function", "async_function", "method", "class", "interface"])
        ).order_by(CodeChunk.symbol_name).all()

        return [
            {
                "id": c.id,
                "name": c.symbol_name,
                "type": c.chunk_type,
                "file_path": c.file.file_path if c.file else "unknown",
                "start_line": c.start_line,
                "end_line": c.end_line,
                "token_count": c.token_count
            }
            for c in chunks
        ]


repository_service = RepositoryService()
