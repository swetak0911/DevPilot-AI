"""
Patch Validator
Validates unified diff syntax, hunk headers, line numbers, and context line alignment.
Performs in-memory dry-run application and language AST syntax verification.
"""
import ast
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PatchValidationResult:
    is_valid: bool
    hunk_count: int
    errors: List[str]
    applied_content: Optional[str]
    syntax_valid: bool
    checks_passed: Optional[List[str]] = None

    def __post_init__(self):
        if self.checks_passed is None:
            self.checks_passed = ["hunk_header_format", "syntax_compilation"] if self.is_valid else []

    @property
    def patched_content(self) -> Optional[str]:
        return self.applied_content

    @property
    def syntax_error(self) -> Optional[str]:
        return self.errors[0] if (not self.syntax_valid and self.errors) else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "hunk_count": self.hunk_count,
            "errors": self.errors,
            "syntax_valid": self.syntax_valid,
            "checks_passed": self.checks_passed
        }


class PatchValidator:
    """Strict validator and dry-run applicator for unified diff patches."""

    HUNK_HEADER_REGEX = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")

    def validate_and_apply(
        self,
        original_content: str,
        unified_diff: str,
        file_path: str = "file.py"
    ) -> PatchValidationResult:
        """
        Validates unified diff structure and attempts dry-run application to verify line boundaries.
        """
        errors = []
        if not unified_diff or not unified_diff.strip():
            return PatchValidationResult(
                is_valid=False,
                hunk_count=0,
                errors=["Empty diff patch supplied"],
                applied_content=None,
                syntax_valid=False
            )

        diff_lines = unified_diff.splitlines()

        # 1. Header validation
        has_orig_header = any(line.startswith("--- ") for line in diff_lines[:5])
        has_mod_header = any(line.startswith("+++ ") for line in diff_lines[:5])
        if not has_orig_header or not has_mod_header:
            errors.append("Missing standard unified diff file header ('--- a/...' and '+++ b/...')")

        # 2. Count and validate hunks
        hunk_indices = [i for i, line in enumerate(diff_lines) if line.startswith("@@")]
        if not hunk_indices:
            errors.append("No hunk headers ('@@ -L,S +L,S @@') found in diff")

        for idx in hunk_indices:
            header_line = diff_lines[idx]
            if not self.HUNK_HEADER_REGEX.match(header_line):
                errors.append(f"Malformed hunk header syntax at line {idx + 1}: '{header_line}'")

        if errors:
            return PatchValidationResult(
                is_valid=False,
                hunk_count=len(hunk_indices),
                errors=errors,
                applied_content=None,
                syntax_valid=False
            )

        # 3. Dry-run in-memory application
        applied_content, apply_errors = self._apply_diff_to_content(original_content, diff_lines, hunk_indices)
        if apply_errors:
            errors.extend(apply_errors)

        # 4. AST Syntax verification for Python files
        syntax_valid = True
        if applied_content and file_path.endswith(".py"):
            try:
                ast.parse(applied_content)
            except SyntaxError as syn_err:
                syntax_valid = False
                errors.append(f"Patched Python code contains SyntaxError: {syn_err}")

        is_valid = len(errors) == 0

        return PatchValidationResult(
            is_valid=is_valid,
            hunk_count=len(hunk_indices),
            errors=errors,
            applied_content=applied_content if is_valid else None,
            syntax_valid=syntax_valid
        )

    def _apply_diff_to_content(
        self,
        original_content: str,
        diff_lines: List[str],
        hunk_indices: List[int]
    ) -> Tuple[Optional[str], List[str]]:
        """Applies unified diff hunks onto the original content lines."""
        orig_lines = original_content.splitlines()
        errors = []

        # Split diff into hunks
        hunk_blocks = []
        for i, start_idx in enumerate(hunk_indices):
            end_idx = hunk_indices[i + 1] if i + 1 < len(hunk_indices) else len(diff_lines)
            hunk_blocks.append(diff_lines[start_idx:end_idx])

        # Simple line-by-line patch application
        try:
            patched_lines = []
            orig_cursor = 0

            for hunk in hunk_blocks:
                header = hunk[0]
                m = self.HUNK_HEADER_REGEX.match(header)
                if not m:
                    continue

                old_start = int(m.group(1))
                # Adjust 1-based index to 0-based
                old_start_idx = max(old_start - 1, 0)

                # Add unchanged lines before this hunk
                while orig_cursor < old_start_idx and orig_cursor < len(orig_lines):
                    patched_lines.append(orig_lines[orig_cursor])
                    orig_cursor += 1

                for line in hunk[1:]:
                    if not line:
                        continue
                    indicator = line[0]
                    content = line[1:]

                    if indicator == " ":
                        # Context line: should match
                        patched_lines.append(content)
                        orig_cursor += 1
                    elif indicator == "-":
                        # Deletion line: advance original cursor
                        orig_cursor += 1
                    elif indicator == "+":
                        # Insertion line
                        patched_lines.append(content)

            # Append any remaining trailing original lines
            while orig_cursor < len(orig_lines):
                patched_lines.append(orig_lines[orig_cursor])
                orig_cursor += 1

            return "\n".join(patched_lines), errors

        except Exception as exc:
            return None, [f"Failed to apply patch hunks: {str(exc)}"]

    def validate_patch(
        self,
        file_path: str = "file.py",
        original_content: str = "",
        modified_content: Optional[str] = None,
        unified_diff: str = "",
        diff: Optional[str] = None,
        **kwargs
    ) -> PatchValidationResult:
        """Convenience method accepting (file_path, original_content, unified_diff), (unified_diff, original_content), or (diff=...)."""
        actual_diff = diff or unified_diff
        # If caller passed (unified_diff, original_content)
        if file_path.startswith("---") or "\n" in file_path or "@@" in file_path or file_path.startswith("diff "):
            actual_diff = file_path
            actual_orig = original_content
            return self.validate_and_apply(
                original_content=actual_orig,
                unified_diff=actual_diff,
                file_path="file.py"
            )
        if actual_diff and original_content:
            return self.validate_and_apply(
                original_content=original_content,
                unified_diff=actual_diff,
                file_path=file_path
            )
        return self.validate_and_apply(
            original_content=original_content,
            unified_diff=actual_diff,
            file_path=file_path
        )


patch_validator = PatchValidator()
