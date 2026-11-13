"""
DevPilot AI - CI/CD Log Parser & Error Trace Extractor
Ingests raw runner logs, strips ANSI color codes, identifies step failure boundaries,
and extracts failing files, line numbers, and structured error traces.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import re


@dataclass
class ParsedCIError:
    failing_job: str
    failing_step: str
    error_message: str
    error_trace: str
    failing_file: Optional[str] = None
    failing_line: Optional[int] = None
    raw_logs_snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failing_job": self.failing_job,
            "failing_step": self.failing_step,
            "error_message": self.error_message,
            "error_trace": self.error_trace,
            "failing_file": self.failing_file,
            "failing_line": self.failing_line,
            "raw_logs_snippet": self.raw_logs_snippet
        }


class CILogParser:
    """Parses raw CI/CD console logs into normalized error representations."""

    ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    # Patterns for file and line number detection
    FILE_LINE_PATTERNS = [
        re.compile(r'File\s+"([^"]+)",\s+line\s+(\d+)', re.IGNORECASE),
        re.compile(r'([a-zA-Z0-9_\-/\\]+\.(?:py|ts|tsx|js|jsx|java|go|rs|yml|yaml)):(\d+)(?::(\d+))?', re.IGNORECASE),
        re.compile(r'at\s+.*?\(([^()]+):(\d+):(\d+)\)', re.IGNORECASE),
        re.compile(r'-->\s+([a-zA-Z0-9_\-/\\]+\.(?:rs|go|java)):(\d+):(\d+)', re.IGNORECASE)
    ]

    # Patterns indicating step headers
    STEP_HEADER_PATTERNS = [
        re.compile(r"##\[group\]Run\s+(.*)", re.IGNORECASE),
        re.compile(r"##\[section\]Starting:\s+(.*)", re.IGNORECASE),
        re.compile(r"Step\s+\d+/\d+\s*:\s*(.*)", re.IGNORECASE),
        re.compile(r"===\s*Step:\s*(.*?)\s*===", re.IGNORECASE),
        re.compile(r"Run\s+([a-zA-Z0-9_\-\s]+)", re.IGNORECASE)
    ]

    def strip_ansi(self, text: str) -> str:
        """Removes terminal escape color sequences from logs."""
        if not text:
            return ""
        return self.ANSI_ESCAPE_RE.sub("", text)

    def parse(
        self,
        logs: str,
        default_job: str = "test",
        default_step: str = "Execute Automated Tests"
    ) -> ParsedCIError:
        """Extracts failure boundaries, failing file, line, and message from logs."""
        clean_logs = self.strip_ansi(logs)
        lines = clean_logs.splitlines()

        detected_job = default_job
        detected_step = default_step
        failing_file = None
        failing_line = None
        error_lines: List[str] = []
        error_message = "Continuous integration step execution failed."

        # Pass 1: Discover failing job / step
        current_step = default_step
        for line in lines:
            # Check step header
            for pat in self.STEP_HEADER_PATTERNS:
                m = pat.search(line)
                if m:
                    current_step = m.group(1).strip()
                    break

            # Check if this line signals failure
            if any(marker in line.lower() for marker in [
                "##[error]", "error:", "failed", "traceback", "npm err!", "fatal:", "exception:"
            ]):
                detected_step = current_step
                error_lines.append(line.strip())

        # If job is lint related
        if any("lint" in s.lower() for s in [detected_step, clean_logs[:500]]):
            detected_job = "lint"
        elif any("docker" in s.lower() or "container" in s.lower() for s in [detected_step, clean_logs[:500]]):
            detected_job = "docker-build"

        # Pass 2: Extract failing file and line number
        for line in lines:
            for pat in self.FILE_LINE_PATTERNS:
                m = pat.search(line)
                if m:
                    extracted_path = m.group(1).replace("\\", "/")
                    # Filter out python lib / site-packages files
                    if "site-packages" not in extracted_path and "lib/python" not in extracted_path:
                        failing_file = extracted_path
                        try:
                            failing_line = int(m.group(2))
                        except (ValueError, IndexError):
                            failing_line = None
                        break
            if failing_file and failing_line:
                break

        # Pass 3: Extract most descriptive error message
        explicit_msg = None
        generic_error = None
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if any(prefix in stripped for prefix in [
                "AssertionError", "ModuleNotFoundError", "ImportError", "AttributeError",
                "TypeError", "ValueError", "SyntaxError", "NameError", "npm ERR!", "F401", "E501", "FAILED"
            ]):
                explicit_msg = stripped
                break
            elif "##[error]" in stripped:
                msg_cand = stripped.replace("##[error]", "").strip()
                if msg_cand and "exit code" not in msg_cand.lower():
                    generic_error = msg_cand
                elif not generic_error:
                    generic_error = msg_cand

        error_message = explicit_msg or generic_error or "Continuous integration step execution failed."

        # Pass 4: Build error trace snippet (around 15 relevant lines)
        trace_candidates = []
        capture = False
        for line in lines:
            stripped = line.strip()
            if any(k in stripped.lower() for k in ["traceback", "failures", "errors:", "##[error]", "npm err!"]):
                capture = True
            if capture:
                trace_candidates.append(line)
                if len(trace_candidates) >= 18:
                    break

        if not trace_candidates:
            # Fallback: take last 15 lines of log
            trace_candidates = lines[-15:] if len(lines) > 15 else lines

        error_trace = "\n".join(trace_candidates).strip()
        raw_snippet = "\n".join(lines[-25:] if len(lines) > 25 else lines).strip()

        return ParsedCIError(
            failing_job=detected_job,
            failing_step=detected_step,
            error_message=error_message,
            error_trace=error_trace,
            failing_file=failing_file,
            failing_line=failing_line,
            raw_logs_snippet=raw_snippet
        )


ci_log_parser = CILogParser()
