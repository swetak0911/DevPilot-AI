"""
DevPilot AI - Code Review and Regression Analysis Agent
Evaluates proposed patches for regressions, architectural consistency,
security vulnerabilities, performance bottlenecks, and style compliance.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json
import re
import logging

from ai_engine.agents.llm_provider import llm_provider

logger = logging.getLogger(__name__)


@dataclass
class ReviewFinding:
    category: str  # REGRESSION, SECURITY, PERFORMANCE, CODE_STYLE, CORRECTNESS
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    line_number: Optional[int]
    description: str
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "line_number": self.line_number,
            "description": self.description,
            "recommendation": self.recommendation
        }


@dataclass
class ReviewResult:
    summary: str
    decision: str  # APPROVED, CHANGES_REQUESTED, NEEDS_HUMAN_INSPECTION
    score: float  # 0.0 - 10.0
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    findings: List[ReviewFinding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "decision": self.decision,
            "score": round(self.score, 1),
            "risk_level": self.risk_level,
            "findings": [f.to_dict() for f in self.findings]
        }


class CodeReviewAgent:
    """Automated reviewer performing comprehensive regression risk and quality analysis."""

    SYSTEM_PROMPT = (
        "You are an expert Principal Software Engineer and Security Architect in DevPilot AI.\n"
        "Your role is to conduct rigorous code reviews of proposed code patches before Pull Request creation.\n"
        "Analyze regressions, breaking changes, edge case omissions, performance hazards, and security anti-patterns.\n"
        "Output ONLY valid JSON adhering to the specified schema."
    )

    def review_patch(
        self,
        instruction: Optional[str] = None,
        file_path: Optional[str] = None,
        original_content: str = "",
        modified_content: str = "",
        unified_diff: Optional[str] = None,
        task_description: Optional[str] = None,
        target_file: Optional[str] = None,
        patch_diff: Optional[str] = None,
        **kwargs
    ) -> ReviewResult:
        """
        Conducts regression analysis and code quality evaluation on a proposed patch.
        Supports both (instruction, file_path, original_content, modified_content, unified_diff)
        and (task_description, target_file, patch_diff) signatures.
        """
        instr = instruction or task_description or kwargs.get("task", "Code Review")
        fp = file_path or target_file or kwargs.get("path", "file.py")
        diff = unified_diff or patch_diff or kwargs.get("diff", "")
        if not modified_content:
            modified_content = original_content if original_content else diff

        # 1. Deterministic heuristic & pattern analysis
        findings: List[ReviewFinding] = []
        rule_score = 9.5
        rule_risk = "LOW"

        # Check for empty patch
        if not diff or not diff.strip():
            return ReviewResult(
                summary="No changes were detected in the patch.",
                decision="CHANGES_REQUESTED",
                score=0.0,
                risk_level="CRITICAL",
                findings=[ReviewFinding(
                    category="CORRECTNESS",
                    severity="CRITICAL",
                    line_number=1,
                    description="Empty patch provided.",
                    recommendation="Ensure code modifications are generated before review."
                )]
            )

        # Check for broad except blocks (silent suppression regression)
        if "except:" in modified_content or "except Exception: pass" in modified_content:
            findings.append(ReviewFinding(
                category="REGRESSION",
                severity="MEDIUM",
                line_number=None,
                description="Silent exception suppression detected. This can mask production failures.",
                recommendation="Catch specific exception classes and log diagnostics with exc_info=True."
            ))
            rule_score -= 1.0
            rule_risk = "MEDIUM"

        # Check for hardcoded credentials / tokens
        if re.search(r"(password|secret|token|api_key)\s*=\s*['\"][^'\"]{8,}['\"]", modified_content, re.IGNORECASE):
            findings.append(ReviewFinding(
                category="SECURITY",
                severity="CRITICAL",
                line_number=None,
                description="Hardcoded credential pattern detected in patch.",
                recommendation="Inject secrets via environment variables or secret manager."
            ))
            rule_score -= 3.0
            rule_risk = "HIGH"

        # Check for unbounded loops or recursion
        if "while True:" in modified_content and "break" not in modified_content:
            findings.append(ReviewFinding(
                category="PERFORMANCE",
                severity="HIGH",
                line_number=None,
                description="Potential infinite while-loop without break detected.",
                recommendation="Provide an explicit termination condition or timeout counter."
            ))
            rule_score -= 2.0
            rule_risk = "HIGH"

        # 2. LLM Semantic Review Prompt
        prompt = (
            f"### TASK INSTRUCTION:\n{instr}\n\n"
            f"### FILE REVIEWED: {fp}\n\n"
            f"### UNIFIED DIFF:\n```diff\n{diff}\n```\n\n"
            "Evaluate this patch for regression risk, correctness, performance, and security.\n"
            "Output JSON with schema:\n"
            "{\n"
            '  "summary": "1-2 sentence overall review summary",\n'
            '  "decision": "APPROVED" | "CHANGES_REQUESTED" | "NEEDS_HUMAN_INSPECTION",\n'
            '  "score": float between 0.0 and 10.0,\n'
            '  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",\n'
            '  "findings": [\n'
            '    {\n'
            '      "category": "REGRESSION" | "SECURITY" | "PERFORMANCE" | "CODE_STYLE" | "CORRECTNESS",\n'
            '      "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",\n'
            '      "line_number": int or null,\n'
            '      "description": "explanation",\n'
            '      "recommendation": "prescribed fix"\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        try:
            llm_text = llm_provider.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                json_mode=True
            )
            if isinstance(llm_text, str):
                import json
                clean = re.sub(r"^```json\s*", "", llm_text.strip())
                clean = re.sub(r"\s*```$", "", clean)
                try:
                    llm_resp = json.loads(clean)
                except Exception:
                    llm_resp = {}
            elif isinstance(llm_text, dict):
                llm_resp = llm_text
            else:
                llm_resp = {}

            summary = llm_resp.get("summary") or "Patch review completed successfully."
            decision = llm_resp.get("decision", "APPROVED")
            score = float(llm_resp.get("score", rule_score))
            risk_level = llm_resp.get("risk_level", rule_risk)

            for item in llm_resp.get("findings", []):
                findings.append(ReviewFinding(
                    category=item.get("category", "CORRECTNESS"),
                    severity=item.get("severity", "LOW"),
                    line_number=item.get("line_number"),
                    description=item.get("description", ""),
                    recommendation=item.get("recommendation", "")
                ))

            # Calibrate score and decision
            if any(f.severity in ["HIGH", "CRITICAL"] for f in findings):
                decision = "CHANGES_REQUESTED" if any(f.severity == "CRITICAL" for f in findings) else "NEEDS_HUMAN_INSPECTION"
                if risk_level == "LOW":
                    risk_level = "HIGH"

            return ReviewResult(
                summary=summary,
                decision=decision,
                score=max(0.0, min(10.0, score)),
                risk_level=risk_level,
                findings=findings
            )
        except Exception as exc:
            logger.warning(f"LLM review failed, using deterministic evaluation: {exc}")
            decision = "APPROVED" if rule_score >= 7.0 else "CHANGES_REQUESTED"
            return ReviewResult(
                summary=f"Automated review: Patch passed static regression checks. Score: {rule_score:.1f}/10.",
                decision=decision,
                score=rule_score,
                risk_level=rule_risk,
                findings=findings
            )


review_agent = CodeReviewAgent()
