"""
Repository Indexer Service
Safely scans repository files, extracts AST symbols and code chunks,
and persists indexed metadata and chunks into database. Supports incremental indexing.
"""
import os
import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.repository import Repository, RepositoryFile, CodeChunk
from app.services.file_filter import file_filter
from app.services.code_parser import code_parser
from app.services.dependency_analyzer import dependency_analyzer
from app.services.embeddings import embedding_service
import logging

logger = logging.getLogger(__name__)


class RepositoryIndexer:
    """Manages the full lifecycle of repository AST indexing and chunking."""

    @staticmethod
    def compute_file_sha256(filepath: str) -> str:
        """Computes SHA-256 hash of file content for change detection."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def index_directory(
        self,
        db: Session,
        repository_id: str,
        root_dir: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Walks root_dir, parses all safe source files, extracts functions & classes,
        and saves chunks into database.
        """
        start_time = time.perf_counter()
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise ValueError(f"Repository {repository_id} not found")

        # 1. Analyze dependencies and frameworks
        dep_report = dependency_analyzer.analyze_directory(root_dir)
        repo.primary_language = dep_report.primary_language
        repo.detected_frameworks = dep_report.detected_frameworks

        files_scanned = 0
        files_indexed = 0
        files_skipped = 0
        symbols_extracted = 0
        chunks_created = 0
        language_counts: Dict[str, int] = {}

        # 2. Walk directory and parse safe files
        for current_root, dirs, files in os.walk(root_dir):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if not file_filter.is_directory_ignored(d)]

            for filename in files:
                files_scanned += 1
                full_path = os.path.join(current_root, filename)
                rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")

                try:
                    file_size = os.path.getsize(full_path)
                except OSError:
                    files_skipped += 1
                    continue

                is_safe, reason = file_filter.is_safe_for_indexing(rel_path, file_size)
                if not is_safe:
                    files_skipped += 1
                    continue

                # Read content safely
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as exc:
                    logger.warning("Could not read file %s: %s", rel_path, exc)
                    files_skipped += 1
                    continue

                # Secret scan check
                secret_findings = file_filter.scan_for_secrets(content)
                if secret_findings:
                    logger.warning("Excluded file %s due to suspected exposed credentials", rel_path)
                    files_skipped += 1
                    continue

                # Compute content hash for incremental indexing
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

                # Check if file was already indexed and unchanged
                existing_file = db.query(RepositoryFile).filter(
                    RepositoryFile.repository_id == repository_id,
                    RepositoryFile.file_path == rel_path
                ).first()

                if existing_file and not force:
                    # Check if ast_metadata contains matching hash
                    cached_hash = existing_file.ast_metadata.get("content_hash")
                    if cached_hash == content_hash:
                        files_skipped += 1
                        continue

                # Parse AST symbols
                parse_result = code_parser.parse_source_code(rel_path, content)
                lang = parse_result.language
                language_counts[lang] = language_counts.get(lang, 0) + 1

                ast_meta = {
                    "content_hash": content_hash,
                    "symbol_count": len(parse_result.symbols),
                    "import_count": len(parse_result.imports),
                    "imports": parse_result.imports[:30]  # sample top 30
                }

                if existing_file:
                    existing_file.language = lang
                    existing_file.size_bytes = file_size
                    existing_file.line_count = parse_result.line_count
                    existing_file.ast_metadata = ast_meta
                    repo_file = existing_file
                    # Clear previous chunks for re-indexing
                    db.query(CodeChunk).filter(CodeChunk.file_id == repo_file.id).delete()
                else:
                    repo_file = RepositoryFile(
                        repository_id=repository_id,
                        file_path=rel_path,
                        file_name=filename,
                        extension=os.path.splitext(filename)[1],
                        language=lang,
                        size_bytes=file_size,
                        line_count=parse_result.line_count,
                        ast_metadata=ast_meta
                    )
                    db.add(repo_file)
                    db.flush()

                files_indexed += 1
                symbols_extracted += len(parse_result.symbols)

                # Create code chunks from extracted symbols (functions, classes)
                if parse_result.symbols:
                    for sym in parse_result.symbols:
                        chunk_text = f"{sym.name} {sym.signature or ''} {sym.content}"
                        emb = embedding_service.generate_embedding(chunk_text)
                        chunk = CodeChunk(
                            repository_id=repository_id,
                            file_id=repo_file.id,
                            chunk_type=sym.symbol_type,
                            symbol_name=sym.name,
                            start_line=sym.start_line,
                            end_line=sym.end_line,
                            content=sym.content,
                            token_count=sym.token_count,
                            embedding=emb,
                            embedding_model=embedding_service.model_name
                        )
                        db.add(chunk)
                        chunks_created += 1
                else:
                    # If no symbols found (e.g. small script, config, markdown), create file-level chunk
                    chunk_text = f"{filename} {content[:4000]}"
                    emb = embedding_service.generate_embedding(chunk_text)
                    chunk = CodeChunk(
                        repository_id=repository_id,
                        file_id=repo_file.id,
                        chunk_type="module",
                        symbol_name=filename,
                        start_line=1,
                        end_line=parse_result.line_count,
                        content=content[:4000],  # cap first 4000 chars
                        token_count=min(len(content) // 4, 1000),
                        embedding=emb,
                        embedding_model=embedding_service.model_name
                    )
                    db.add(chunk)
                    chunks_created += 1

        repo.is_indexed = True
        repo.last_indexed_at = datetime.now(timezone.utc)
        db.commit()

        elapsed = round(time.perf_counter() - start_time, 2)
        return {
            "repository_id": repository_id,
            "status": "COMPLETED",
            "files_scanned": files_scanned,
            "files_indexed": files_indexed,
            "files_skipped": files_skipped,
            "symbols_extracted": symbols_extracted,
            "chunks_created": chunks_created,
            "detected_languages": language_counts,
            "detected_frameworks": dep_report.detected_frameworks,
            "duration_seconds": elapsed
        }


repository_indexer = RepositoryIndexer()
