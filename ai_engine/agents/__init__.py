"""
LLM Coding Agents Subsystem.
Includes Multi-Provider LLM abstraction, Planning Agent, Bug Detection Agent,
Coding Agent, Patch Validator, and Agent Orchestrator.
"""
from ai_engine.agents.llm_provider import LLMProvider, llm_provider
from ai_engine.agents.planning_agent import PlanningAgent, planning_agent, PlanningResult
from ai_engine.agents.bug_detection_agent import BugDetectionAgent, bug_detection_agent, BugReport
from ai_engine.agents.coding_agent import CodingAgent, coding_agent, CodingResult
from ai_engine.agents.patch_validator import PatchValidator, patch_validator, PatchValidationResult
from ai_engine.agents.agent_orchestrator import AgentOrchestrator, agent_orchestrator

__all__ = [
    "LLMProvider",
    "llm_provider",
    "PlanningAgent",
    "planning_agent",
    "PlanningResult",
    "BugDetectionAgent",
    "bug_detection_agent",
    "BugReport",
    "CodingAgent",
    "coding_agent",
    "CodingResult",
    "PatchValidator",
    "patch_validator",
    "PatchValidationResult",
    "AgentOrchestrator",
    "agent_orchestrator"
]
