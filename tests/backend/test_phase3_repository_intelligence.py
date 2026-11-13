"""
Phase 3 Repository Intelligence Engine Test Suite
Tests file filtering, AST code parsing across languages, dependency analysis,
and database code chunk indexing.
"""
import pytest
from app.services.file_filter import file_filter
from app.services.code_parser import code_parser
from app.services.dependency_analyzer import dependency_analyzer
from app.services.repository_indexer import repository_indexer
from app.models.repository import Repository, RepositoryFile, CodeChunk


def test_file_filter_sensitive_and_ignored_files():
    """Verifies that .env files, private keys, binaries, and node_modules are safely filtered."""
    assert file_filter.is_sensitive_filename(".env") is True
    assert file_filter.is_sensitive_filename(".env.production") is True
    assert file_filter.is_sensitive_filename("id_rsa") is True
    assert file_filter.is_sensitive_filename("server.key") is True
    assert file_filter.is_sensitive_filename("main.py") is False

    assert file_filter.is_directory_ignored("node_modules") is True
    assert file_filter.is_directory_ignored(".venv") is True
    assert file_filter.is_directory_ignored("__pycache__") is True
    assert file_filter.is_directory_ignored("src") is False

    assert file_filter.is_binary_file("logo.png") is True
    assert file_filter.is_binary_file("archive.zip") is True
    assert file_filter.is_binary_file("app.py") is False

    # Path traversal rejection
    is_safe, reason = file_filter.is_safe_for_indexing("../secret.txt")
    assert is_safe is False
    assert "traversal" in reason.lower()


def test_file_filter_secret_scanning():
    """Verifies that exposed credentials trigger detection."""
    content_with_secret = "AWS_SECRET = 'AKIAIOSFODNN7EXAMPLE'\nAPI_KEY = 'secret_key: \"abcdef1234567890abcdef123456\"'"
    findings = file_filter.scan_for_secrets(content_with_secret)
    assert len(findings) >= 1
    assert any("AWS" in f["secret_type"] for f in findings)


def test_python_ast_parsing():
    """Verifies extraction of Python classes, functions, methods, and docstrings."""
    py_code = '''
"""Module docstring."""
import os
from typing import List

class AuthService:
    """Authentication management."""
    def __init__(self, key: str):
        self.key = key

    def verify_token(self, token: str) -> bool:
        """Verifies JWT token."""
        return len(token) > 0

async def login_user(username: str) -> dict:
    """Async user login."""
    return {"status": "ok"}
'''
    res = code_parser.parse_source_code("auth_service.py", py_code)
    assert res.language == "Python"
    assert len(res.symbols) >= 4  # AuthService, __init__, verify_token, login_user
    assert "os" in res.imports
    
    symbols_by_name = {s.name: s for s in res.symbols}
    assert "AuthService" in symbols_by_name
    assert symbols_by_name["AuthService"].symbol_type == "class"
    assert "login_user" in symbols_by_name
    assert symbols_by_name["login_user"].symbol_type == "async_function"
    assert "verify_token" in symbols_by_name
    assert symbols_by_name["verify_token"].symbol_type == "method"
    assert symbols_by_name["verify_token"].parent_name == "AuthService"


def test_javascript_typescript_parsing():
    """Verifies extraction of JavaScript/TypeScript functions, classes, and interfaces."""
    ts_code = '''
import React from 'react';
import { api } from './api';

export interface User {
    id: string;
    username: string;
}

export class UserManager {
    getUser() {}
}

export function fetchUserProfile(userId: string) {
    return api.get(`/users/${userId}`);
}

export const calculateTax = (amount: number) => {
    return amount * 0.2;
};
'''
    res = code_parser.parse_source_code("user.ts", ts_code)
    assert res.language == "TypeScript"
    assert "react" in res.imports or "./api" in res.imports
    names = {s.name for s in res.symbols}
    assert "User" in names
    assert "UserManager" in names
    assert "fetchUserProfile" in names
    assert "calculateTax" in names


def test_dependency_analyzer(tmp_path):
    """Verifies detection of languages, frameworks, and package managers from manifests."""
    # Create sample requirements.txt and package.json
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("fastapi>=0.111.0\nuvicorn>=0.30.0\ntorch>=2.0.0\n")

    pkg_file = tmp_path / "package.json"
    pkg_file.write_text('{"dependencies": {"react": "^18.2.0", "tailwindcss": "^3.4.0"}}')

    df_file = tmp_path / "Dockerfile"
    df_file.write_text("FROM python:3.11-slim\n")

    report = dependency_analyzer.analyze_directory(str(tmp_path))
    assert "Python" in report.detected_languages
    assert "JavaScript/TypeScript" in report.detected_languages
    assert "FastAPI" in report.detected_frameworks
    assert "React" in report.detected_frameworks
    assert "PyTorch" in report.detected_frameworks
    assert "Tailwind CSS" in report.detected_frameworks
    assert report.has_dockerfile is True


def test_repository_indexer_and_chunking(client, db):
    """Tests full repository indexing pipeline and CodeChunk creation."""
    # Create a test repository in DB
    repo = Repository(
        name="TestRepo",
        full_name="testuser/TestRepo",
        html_url="https://github.com/testuser/TestRepo",
        clone_url="https://github.com/testuser/TestRepo.git",
        default_branch="main"
    )
    db.add(repo)
    db.commit()

    # Index current project directory (backend/app)
    current_backend = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "app", "core")
    stats = repository_indexer.index_directory(db=db, repository_id=repo.id, root_dir=current_backend, force=True)
    
    assert stats["status"] == "COMPLETED"
    assert stats["files_indexed"] >= 3
    assert stats["symbols_extracted"] >= 5
    assert stats["chunks_created"] >= 5

    # Verify chunks in database
    chunks = db.query(CodeChunk).filter(CodeChunk.repository_id == repo.id).all()
    assert len(chunks) >= 5
    assert any(c.symbol_name in ("Settings", "hash_password", "verify_password") for c in chunks)
