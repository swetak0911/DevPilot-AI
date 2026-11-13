"""
Error Trace Analyzer
Parses test runner stdout and stderr streams, isolates failed test cases,
extracts stack traces, and classifies root failure categories (Assertion, Syntax, Import, Runtime).
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class FailureDetail:
    test_name: str
    failure_type: str
    message: str
    traceback: str
    line_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "failure_type": self.failure_type,
            "message": self.message,
            "traceback": self.traceback,
            "line_number": self.line_number
        }


@dataclass
class StructuredTestReport:
    attempt_number: int
    all_passed: bool
    passed: int
    failed: int
    errors: int
    exit_code: int
    duration_seconds: float
    failure_details: List[FailureDetail]
    summary: str
    stdout: str
    stderr: str

    @property
    def status(self) -> str:
        return "PASSED" if self.all_passed else "FAILED"

    @property
    def passed_tests(self) -> int:
        return self.passed

    @property
    def duration_ms(self) -> float:
        return round(self.duration_seconds * 1000, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt_number": self.attempt_number,
            "all_passed": self.all_passed,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "failure_details": [f.to_dict() for f in self.failure_details],
            "summary": self.summary,
            "stdout": self.stdout,
            "stderr": self.stderr
        }


class ErrorAnalyzer:
    """Parses pytest / test runner output to extract structured failure metrics."""

    PYTEST_SUMMARY_REGEX = re.compile(
        r"(=+)\s*(?:(?P<passed>\d+)\s+passed)?(?:,\s*(?P<failed>\d+)\s+failed)?(?:,\s*(?P<errors>\d+)\s+errors?)?\s*in\s+(?P<duration>[\d\.]+)s"
    )
    FAILED_TEST_REGEX = re.compile(r"FAILED\s+([^\s:]+(?:::[\w_]+)+)\s*-\s*(.*)")

    def parse_test_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        attempt_number: int = 1,
        duration: float = 0.0
    ) -> StructuredTestReport:
        """
        Parses test runner output into a StructuredTestReport.
        """
        combined = stdout + "\n" + stderr

        passed = 0
        failed = 0
        errors = 0
        failures: List[FailureDetail] = []

        # 1. Parse Pytest summary counts
        match = self.PYTEST_SUMMARY_REGEX.search(stdout)
        if match:
            passed = int(match.group("passed") or 0)
            failed = int(match.group("failed") or 0)
            errors = int(match.group("errors") or 0)
        else:
            # Fallback simple count search
            p_match = re.search(r"(\d+)\s+passed", stdout)
            f_match = re.search(r"(\d+)\s+failed", stdout)
            e_match = re.search(r"(\d+)\s+error", stdout)
            if p_match:
                passed = int(p_match.group(1))
            if f_match:
                failed = int(f_match.group(1))
            if e_match:
                errors = int(e_match.group(1))

        # If exit_code is 0 and no failed tests were found, mark passed
        if exit_code == 0:
            if passed == 0 and failed == 0 and errors == 0:
                passed = 1
            all_passed = True
        else:
            all_passed = False
            if failed == 0 and errors == 0:
                failed = 1  # Unhandled non-zero exit code indicates failure

        # 2. Extract specific failed test cases & tracebacks
        failed_lines = self.FAILED_TEST_REGEX.findall(stdout)
        for t_name, reason in failed_lines:
            f_type = self._classify_failure_type(reason)
            failures.append(FailureDetail(
                test_name=t_name.strip(),
                failure_type=f_type,
                message=reason.strip(),
                traceback=self._extract_relevant_traceback(stdout, t_name)
            ))

        # Check for SyntaxError or ImportError in stderr/stdout
        if not failures and not all_passed:
            if "SyntaxError" in combined:
                failures.append(FailureDetail(
                    test_name="Syntax Compilation",
                    failure_type="SYNTAX_ERROR",
                    message="SyntaxError encountered during module import or execution.",
                    traceback=combined[:1000]
                ))
            elif "ImportError" in combined or "ModuleNotFoundError" in combined:
                failures.append(FailureDetail(
                    test_name="Module Import",
                    failure_type="IMPORT_ERROR",
                    message="Missing dependency or invalid import statement.",
                    traceback=combined[:1000]
                ))
            elif "AssertionError" in combined:
                failures.append(FailureDetail(
                    test_name="Assertion Check",
                    failure_type="ASSERTION_ERROR",
                    message="Assertion condition evaluated to False.",
                    traceback=combined[:1000]
                ))
            else:
                failures.append(FailureDetail(
                    test_name="Execution Failure",
                    failure_type="RUNTIME_ERROR",
                    message=f"Process exited with code {exit_code}.",
                    traceback=combined[:1000]
                ))

        summary = (
            f"Test execution passed ({passed} tests passed, 0 failed)."
            if all_passed else
            f"Test execution failed: {failed} failed, {errors} errors, {passed} passed."
        )

        return StructuredTestReport(
            attempt_number=attempt_number,
            all_passed=all_passed,
            passed=passed,
            failed=failed,
            errors=errors,
            exit_code=exit_code,
            duration_seconds=duration,
            failure_details=failures,
            summary=summary,
            stdout=stdout,
            stderr=stderr
        )

    def _classify_failure_type(self, reason: str) -> str:
        """Classifies the root failure pattern."""
        r_lower = reason.lower()
        if "assertionerror" in r_lower or "assert" in r_lower:
            return "ASSERTION_ERROR"
        if "syntaxerror" in r_lower:
            return "SYNTAX_ERROR"
        if "zerodivisionerror" in r_lower:
            return "ZERO_DIVISION"
        if "keyerror" in r_lower or "indexerror" in r_lower:
            return "OUT_OF_BOUNDS"
        if "typeerror" in r_lower:
            return "TYPE_ERROR"
        if "valueerror" in r_lower:
            return "VALUE_ERROR"
        if "timeout" in r_lower:
            return "TIMEOUT"
        return "RUNTIME_ERROR"

    def _extract_relevant_traceback(self, stdout: str, test_name: str) -> str:
        """Extracts the traceback section relevant to a specific test."""
        short_name = test_name.split("::")[-1]
        pattern = rf"(_{{3,}}\s+{re.escape(short_name)}\s+_{{3,}}[\s\S]*?)(?:_{{3,}}|\Z)"
        match = re.search(pattern, stdout)
        if match:
            return match.group(1)[:1500].strip()
        return stdout[-1000:].strip()


error_analyzer = ErrorAnalyzer()
