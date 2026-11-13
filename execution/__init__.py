"""DevPilot AI - Testing, Sandbox Execution, and Self-Healing Repair Engine."""
import sys
from execution.runners import test_runner
from execution.repair import repair_loop
from execution.sandbox import docker_sandbox, workspace_manager
from execution.runners import error_analyzer

# Register convenience aliases
sys.modules["execution.test_runner"] = test_runner
sys.modules["execution.repair_loop"] = repair_loop
sys.modules["execution.docker_sandbox"] = docker_sandbox
sys.modules["execution.workspace_manager"] = workspace_manager
sys.modules["execution.error_analyzer"] = error_analyzer
