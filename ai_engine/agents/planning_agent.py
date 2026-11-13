"""
Planning Agent
Deconstructs complex user tasks and bug reports into structured execution plans,
identifies relevant target files using RAG context, and defines acceptance criteria.
"""
import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from ai_engine.agents.llm_provider import llm_provider


@dataclass
class PlanningResult:
    task_summary: str
    relevant_files: List[str]
    root_cause_analysis: str
    execution_steps: List[Dict[str, Any]]
    testing_strategy: str
    acceptance_criteria: List[str]

    @property
    def steps(self) -> List[Dict[str, Any]]:
        return self.execution_steps

    @property
    def target_files(self) -> List[str]:
        return self.relevant_files

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_summary": self.task_summary,
            "relevant_files": self.relevant_files,
            "root_cause_analysis": self.root_cause_analysis,
            "execution_steps": self.execution_steps,
            "testing_strategy": self.testing_strategy,
            "acceptance_criteria": self.acceptance_criteria
        }


class PlanningAgent:
    """Autonomous agent responsible for high-level software task planning and decomposition."""

    SYSTEM_PROMPT = (
        "You are an expert Principal Software Architect Planning Agent in DevPilot AI.\n"
        "Your task is to analyze user feature requests and bug reports, identify the affected source files,\n"
        "hypothesize root causes, and output a structured JSON execution plan.\n"
        "Output ONLY valid JSON adhering to the specified schema without conversational prose."
    )

    def create_plan(
        self,
        instruction: Optional[str] = None,
        task_description: Optional[str] = None,
        files_context: Optional[List[Dict[str, Any]]] = None,
        task_type: str = "BUG_FIX",
        repository_context: Optional[Dict[str, Any]] = None,
        retrieved_context: Optional[str] = None,
        **kwargs
    ) -> PlanningResult:
        """Alias wrapper supporting both task_description and files_context signatures."""
        instr = instruction or task_description or kwargs.get("task", "Software engineering task")
        repo_ctx = repository_context or {}
        if files_context and not repo_ctx.get("files"):
            repo_ctx["files"] = files_context
        return self.plan(
            instruction=instr,
            task_type=task_type,
            repository_context=repo_ctx if repo_ctx else None,
            retrieved_context=retrieved_context
        )

    def plan(
        self,
        instruction: str,
        task_type: str = "BUG_FIX",
        repository_context: Optional[Dict[str, Any]] = None,
        retrieved_context: Optional[str] = None
    ) -> PlanningResult:
        """
        Creates a structured execution plan for the given task.
        """
        repo_summary = ""
        if repository_context:
            repo_summary = (
                f"Repository: {repository_context.get('name', 'project')}\n"
                f"Primary Language: {repository_context.get('primary_language', 'Python')}\n"
                f"Frameworks: {', '.join(repository_context.get('detected_frameworks', []))}\n"
            )

        prompt = (
            f"### TASK INSTRUCTION:\n{instruction}\n\n"
            f"### TASK TYPE: {task_type}\n\n"
            f"{repo_summary}"
            f"### RETRIEVED RELEVANT CODE CONTEXT:\n{retrieved_context or 'No prior context retrieved.'}\n\n"
            "Please analyze the task and output a JSON object with the following fields:\n"
            "{\n"
            '  "task_summary": "Concise 1-2 sentence overview",\n'
            '  "relevant_files": ["path/to/target1.py", "path/to/target2.py"],\n'
            '  "root_cause_analysis": "Hypothesized architectural or logic flaw",\n'
            '  "execution_steps": [\n'
            '    {"step": 1, "agent": "Bug Detection Agent", "action": "Analyze defect", "description": "..."},\n'
            '    {"step": 2, "agent": "Coding Agent", "action": "Generate patch", "description": "..."},\n'
            '    {"step": 3, "agent": "Testing Agent", "action": "Run test suite", "description": "..."}\n'
            '  ],\n'
            '  "testing_strategy": "How changes should be tested",\n'
            '  "acceptance_criteria": ["Criterion 1", "Criterion 2"]\n'
            "}"
        )

        response_text = llm_provider.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.1,
            json_mode=True
        )

        return self._parse_planning_response(response_text, instruction)

    def _parse_planning_response(self, text: str, fallback_instruction: str) -> PlanningResult:
        """Parses LLM response into structured PlanningResult with safety fallbacks."""
        try:
            # Clean possible markdown fences
            clean = re.sub(r"^```json\s*", "", text.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)

            return PlanningResult(
                task_summary=data.get("task_summary", fallback_instruction),
                relevant_files=data.get("relevant_files", ["src/main.py"]),
                root_cause_analysis=data.get("root_cause_analysis", "Defect or feature improvement required in target module."),
                execution_steps=data.get("execution_steps", [
                    {"step": 1, "agent": "Repository Agent", "action": "Locate files", "description": "Index target modules"},
                    {"step": 2, "agent": "Coding Agent", "action": "Generate patch", "description": "Implement solution"},
                    {"step": 3, "agent": "Testing Agent", "action": "Verify fix", "description": "Execute sandbox unit tests"}
                ]),
                testing_strategy=data.get("testing_strategy", "Run pytest with coverage checks on affected functions."),
                acceptance_criteria=data.get("acceptance_criteria", [
                    "All existing and new tests pass",
                    "Patch applies cleanly without merge conflicts"
                ])
            )
        except Exception:
            return PlanningResult(
                task_summary=f"Plan for: {fallback_instruction}",
                relevant_files=["src/main.py"],
                root_cause_analysis="Identified task requires code modifications adhering to system contracts.",
                execution_steps=[
                    {"step": 1, "agent": "Bug Detection Agent", "action": "Audit target", "description": "Scan vulnerability severity"},
                    {"step": 2, "agent": "Coding Agent", "action": "Apply patch", "description": "Generate diff"},
                    {"step": 3, "agent": "Testing Agent", "action": "Test run", "description": "Validate in sandbox"}
                ],
                testing_strategy="Execute unit tests on changed components.",
                acceptance_criteria=["Patch applies cleanly", "Tests pass"]
            )


planning_agent = PlanningAgent()
