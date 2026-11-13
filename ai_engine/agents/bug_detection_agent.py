"""
Bug Detection Agent
Leverages deep learning CodeBERT signals combined with LLM semantic reasoning
to isolate code defects, classify CWE categories, and pinpoint vulnerable line ranges.
"""
import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ai_engine.agents.llm_provider import llm_provider
from ai_engine.deep_learning.inference import defect_inference_engine, DefectPredictionResult


@dataclass
class BugReport:
    file_path: str
    defect_found: bool
    defect_type: str
    severity: str  # CLEAN, LOW, MEDIUM, HIGH, CRITICAL
    vulnerable_lines: Dict[str, int]  # {"start_line": int, "end_line": int}
    root_cause: str
    remediation_strategy: str
    codebert_probability: float
    detected_anti_patterns: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "defect_found": self.defect_found,
            "defect_type": self.defect_type,
            "severity": self.severity,
            "vulnerable_lines": self.vulnerable_lines,
            "root_cause": self.root_cause,
            "remediation_strategy": self.remediation_strategy,
            "codebert_probability": self.codebert_probability,
            "detected_anti_patterns": self.detected_anti_patterns
        }


class BugDetectionAgent:
    """Autonomous agent that performs deep semantic vulnerability and defect analysis."""

    SYSTEM_PROMPT = (
        "You are an expert Security Engineer and Bug Detection Agent in DevPilot AI.\n"
        "You analyze source code alongside CodeBERT deep learning defect signals to pinpoint exact vulnerabilities,\n"
        "classify CWE/OWASP categories, explain root causes, and prescribe remediation strategies.\n"
        "Output ONLY valid JSON adhering to the specified schema."
    )

    def analyze(
        self,
        file_path: str,
        file_content: str,
        task_instruction: Optional[str] = None
    ) -> BugReport:
        """
        Executes hybrid deep learning + LLM defect analysis on the provided code.
        """
        # 1. Run CodeBERT Deep Learning inference
        cb_res: DefectPredictionResult = defect_inference_engine.predict_defect(file_content)

        # 2. Formulate LLM reasoning prompt
        prompt = (
            f"### TARGET FILE: {file_path}\n"
            f"### CODE CONTENT:\n```\n{file_content}\n```\n\n"
            f"### CODEBERT DEFECT SIGNAL:\n"
            f"- Defect Probability: {cb_res.defect_probability*100:.1f}%\n"
            f"- Preliminary Severity: {cb_res.severity}\n"
            f"- Detected Anti-Patterns: {', '.join(cb_res.detected_anti_patterns) if cb_res.detected_anti_patterns else 'None'}\n"
            f"- Task Context: {task_instruction or 'General defect inspection'}\n\n"
            "Analyze this function and output a JSON object with the following fields:\n"
            "{\n"
            '  "defect_found": true,\n'
            '  "defect_type": "CWE-89: SQL Injection | Logic Flaw | Resource Leak | ...",\n'
            '  "severity": "CRITICAL | HIGH | MEDIUM | LOW | CLEAN",\n'
            '  "vulnerable_lines": {"start_line": 1, "end_line": 5},\n'
            '  "root_cause": "Detailed technical explanation of the failure mode",\n'
            '  "remediation_strategy": "Concrete prescription on how to refactor or sanitize"\n'
            "}"
        )

        response_text = llm_provider.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.1,
            json_mode=True
        )

        return self._parse_bug_report(response_text, file_path, cb_res)

    def _parse_bug_report(
        self,
        text: str,
        file_path: str,
        cb_res: DefectPredictionResult
    ) -> BugReport:
        """Parses the LLM response into a typed BugReport."""
        try:
            clean = re.sub(r"^```json\s*", "", text.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)

            defect_found = data.get("defect_found", cb_res.has_defect)
            severity = data.get("severity", cb_res.severity)

            # Ensure vulnerable_lines dict format
            vuln_lines = data.get("vulnerable_lines", {"start_line": 1, "end_line": 10})
            if not isinstance(vuln_lines, dict):
                vuln_lines = {"start_line": 1, "end_line": 10}

            return BugReport(
                file_path=file_path,
                defect_found=defect_found,
                defect_type=data.get("defect_type", cb_res.detected_anti_patterns[0] if cb_res.detected_anti_patterns else "General Defect"),
                severity=severity,
                vulnerable_lines=vuln_lines,
                root_cause=data.get("root_cause", cb_res.explanation),
                remediation_strategy=data.get("remediation_strategy", "Apply defensive input validation and context manager guards."),
                codebert_probability=cb_res.defect_probability,
                detected_anti_patterns=cb_res.detected_anti_patterns
            )
        except Exception:
            return BugReport(
                file_path=file_path,
                defect_found=cb_res.has_defect,
                defect_type=cb_res.detected_anti_patterns[0] if cb_res.detected_anti_patterns else "Code Defect",
                severity=cb_res.severity,
                vulnerable_lines={"start_line": 1, "end_line": 10},
                root_cause=cb_res.explanation,
                remediation_strategy="Refactor function with parameterized boundaries and proper exception handling.",
                codebert_probability=cb_res.defect_probability,
                detected_anti_patterns=cb_res.detected_anti_patterns
            )

    def scan_code(self, file_path: str, content: str = "", task_instruction: Optional[str] = None) -> BugReport:
        """Alias for analyze accepting 'content' kwarg."""
        return self.analyze(file_path=file_path, file_content=content, task_instruction=task_instruction)


bug_detection_agent = BugDetectionAgent()
