"""
File Filter & Security Guard Service
Safely filters repository files to exclude sensitive secrets, binaries,
build outputs, and dependency folders.
"""
import os
import re
from typing import List, Tuple, Set

# Maximum file size to index (1 MB)
MAX_INDEXABLE_FILE_SIZE = 1 * 1024 * 1024

# Ignored directory names
IGNORED_DIRECTORIES: Set[str] = {
    ".git",
    ".svn",
    ".hg",
    ".idea",
    ".vscode",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    "out",
    ".next",
    ".nuxt",
    ".turbo",
    ".gradle",
    ".m2",
    "coverage",
    "htmlcov",
    ".tox",
}

# Sensitive file patterns that must NEVER be parsed, indexed, or sent to LLMs
SENSITIVE_FILE_PATTERNS: List[re.Pattern] = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r".*id_rsa.*", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
    re.compile(r".*\.pfx$", re.IGNORECASE),
    re.compile(r".*\.p12$", re.IGNORECASE),
    re.compile(r".*secret.*", re.IGNORECASE),
    re.compile(r".*credential.*", re.IGNORECASE),
    re.compile(r".*token.*", re.IGNORECASE),
    re.compile(r".*\.keystore$", re.IGNORECASE),
]

# Binary and non-source extensions
BINARY_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".svg", ".bmp", ".tiff",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
    ".class", ".jar", ".war", ".ear",
    ".pyc", ".pyo", ".pyd",
    ".whl", ".egg", ".tar", ".gz", ".zip", ".7z", ".rar",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".flac",
    ".db", ".sqlite", ".sqlite3",
    ".iso", ".img", ".dmg",
    ".woff", ".woff2", ".ttf", ".eot",
}

# Known secret patterns in content (e.g. AWS Keys, Private Key headers, JWTs)
CONTENT_SECRET_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("AWS Access Key ID", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Private Key Header", re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----")),
    ("GitHub Token Pattern", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}")),
    ("Generic High-Entropy API Key", re.compile(r"(?i)(api_key|apikey|secret_key|private_key)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]")),
]


class FileFilter:
    @staticmethod
    def is_directory_ignored(dir_name: str) -> bool:
        """Returns True if the directory should be skipped during scanning."""
        return dir_name in IGNORED_DIRECTORIES or dir_name.startswith(".cache")

    @staticmethod
    def is_sensitive_filename(filename: str) -> bool:
        """Returns True if the filename matches sensitive patterns (.env, keys, etc.)."""
        for pattern in SENSITIVE_FILE_PATTERNS:
            if pattern.match(filename):
                return True
        return False

    @staticmethod
    def is_binary_file(filename: str, sample_bytes: bytes = b"") -> bool:
        """Checks if file is binary by extension or null-byte heuristic."""
        _, ext = os.path.splitext(filename.lower())
        if ext in BINARY_EXTENSIONS:
            return True
        if sample_bytes and b"\x00" in sample_bytes[:1024]:
            return True
        return False

    @classmethod
    def is_safe_for_indexing(cls, relative_path: str, size_bytes: int = 0) -> Tuple[bool, str]:
        """
        Determines whether a file is safe and eligible for AST parsing and vector indexing.
        Returns (is_safe, reason).
        """
        # Path traversal guard
        normalized = os.path.normpath(relative_path)
        if normalized.startswith("..") or os.path.isabs(relative_path):
            return False, "Path traversal attempt detected"

        # Check path components for ignored directories
        parts = normalized.split(os.sep)
        for part in parts[:-1]:
            if cls.is_directory_ignored(part):
                return False, f"Directory '{part}' is ignored"

        filename = parts[-1]

        # Check sensitive patterns
        if cls.is_sensitive_filename(filename):
            return False, f"File matches sensitive pattern '{filename}'"

        # Check binary extensions
        if cls.is_binary_file(filename):
            return False, "Binary or media file"

        # Size check
        if size_bytes > MAX_INDEXABLE_FILE_SIZE:
            return False, f"File size exceeds maximum indexable limit ({size_bytes} > {MAX_INDEXABLE_FILE_SIZE} bytes)"

        return True, "Safe for indexing"

    @classmethod
    def scan_for_secrets(cls, content: str) -> List[Dict[str, str]]:
        """Scans source content for exposed secrets or credentials."""
        findings = []
        for name, pattern in CONTENT_SECRET_PATTERNS:
            for match in pattern.finditer(content):
                findings.append({
                    "secret_type": name,
                    "matched_snippet": match.group(0)[:12] + "..."  # redacted snippet
                })
        return findings


file_filter = FileFilter()
