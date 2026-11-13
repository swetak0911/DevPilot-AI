"""
Sandbox Worker
Executes unit tests and commands in an isolated non-privileged Docker container,
with automatic fallback to a resource-bounded subprocess sandbox when Docker is inactive.
"""
import os
import subprocess
import time
import shutil
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    runner_type: str  # "docker" or "subprocess"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "timed_out": self.timed_out,
            "runner_type": self.runner_type
        }


class SandboxWorker:
    """Non-privileged execution sandbox with CPU, memory, and timeout limits."""

    def __init__(
        self,
        default_timeout: int = 30,
        memory_limit: str = "1024m",
        cpu_limit: str = "1.0"
    ):
        self.default_timeout = default_timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self._docker_available = self._check_docker_available()

    def _check_docker_available(self) -> bool:
        """Checks if Docker CLI and daemon are operational."""
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3
            )
            return res.returncode == 0
        except Exception:
            return False

    def run_command(
        self,
        command: Any,
        working_dir: str,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """
        Executes command in Docker sandbox if available, else in bounded subprocess.
        """
        if isinstance(command, str):
            import shlex
            command = shlex.split(command, posix=False)
        t = timeout or self.default_timeout
        if self._docker_available:
            try:
                return self._run_in_docker(command, working_dir, t)
            except Exception as exc:
                logger.warning("Docker execution failed: %s. Falling back to subprocess sandbox.", exc)

        return self._run_in_subprocess(command, working_dir, t, env)

    def _run_in_docker(
        self,
        command: List[str],
        working_dir: str,
        timeout: int
    ) -> ExecutionResult:
        """Executes inside a non-privileged, network-isolated Docker container."""
        start_time = time.perf_counter()
        abs_workdir = os.path.abspath(working_dir)

        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", self.memory_limit,
            "--cpus", self.cpu_limit,
            "-v", f"{abs_workdir}:/workspace",
            "-w", "/workspace",
            "python:3.11-slim"
        ] + command

        try:
            proc = subprocess.run(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            duration = round(time.perf_counter() - start_time, 2)
            return ExecutionResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_seconds=duration,
                timed_out=False,
                runner_type="docker"
            )
        except subprocess.TimeoutExpired:
            duration = round(time.perf_counter() - start_time, 2)
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Docker execution timed out after {timeout} seconds.",
                duration_seconds=duration,
                timed_out=True,
                runner_type="docker"
            )

    def _run_in_subprocess(
        self,
        command: List[str],
        working_dir: str,
        timeout: int,
        custom_env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Runs in bounded local subprocess with sanitized environment."""
        start_time = time.perf_counter()

        # Sanitize environment: keep standard OS path, remove secret keys
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "SYSTEMDRIVE": os.environ.get("SYSTEMDRIVE", "C:"),
            "WINDIR": os.environ.get("WINDIR", "C:\\Windows"),
            "TEMP": os.environ.get("TEMP", os.environ.get("TMP", "C:\\Temp")),
            "TMP": os.environ.get("TMP", os.environ.get("TEMP", "C:\\Temp")),
            "USERPROFILE": os.environ.get("USERPROFILE", ""),
            "APPDATA": os.environ.get("APPDATA", ""),
            "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
            "PYTHONPATH": working_dir,
            "PYTHONDONTWRITEBYTECODE": "1"
        }
        if custom_env:
            safe_env.update(custom_env)

        try:
            proc = subprocess.run(
                command,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=safe_env,
                timeout=timeout
            )
            duration = round(time.perf_counter() - start_time, 2)
            return ExecutionResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_seconds=duration,
                timed_out=False,
                runner_type="subprocess"
            )
        except subprocess.TimeoutExpired:
            duration = round(time.perf_counter() - start_time, 2)
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds.",
                duration_seconds=duration,
                timed_out=True,
                runner_type="subprocess"
            )
        except Exception as exc:
            duration = round(time.perf_counter() - start_time, 2)
            return ExecutionResult(
                exit_code=1,
                stdout="",
                stderr=f"Process launch error: {str(exc)}",
                duration_seconds=duration,
                timed_out=False,
                runner_type="subprocess"
            )


sandbox_worker = SandboxWorker()
