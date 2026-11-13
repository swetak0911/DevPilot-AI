"""
DevPilot AI - Terraform Execution Plan Risk Engine & Approval Gate
Analyzes Terraform execution plans, identifies destructive changes on persistent
cloud resources, and enforces a mandatory Human-in-the-Loop (HITL) approval gate.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re
import os
import time


@dataclass
class PlanAnalysisResult:
    to_add: int
    to_change: int
    to_destroy: int
    resources_to_create: List[str]
    resources_to_modify: List[str]
    resources_to_delete: List[str]
    destructive_changes: bool
    destructive_reasons: List[str]
    requires_human_approval: bool
    approval_status: str
    plan_summary: str


class TerraformPlanEngine:
    """Analyzes Terraform execution plan outputs and governs infrastructure approval gates."""

    PERSISTENT_RESOURCE_PATTERNS = [
        "aws_db_instance", "aws_rds_cluster", "aws_s3_bucket", "aws_ebs_volume",
        "aws_efs_file_system", "aws_dynamodb_table", "google_sql_database_instance",
        "azurerm_sql_database", "kubernetes_persistent_volume_claim"
    ]

    def __init__(self):
        # In-memory approval token registry
        self._approvals: Dict[str, Dict[str, Any]] = {}

    def analyze_plan(
        self,
        plan_text: str,
        plan_json: Optional[Dict[str, Any]] = None
    ) -> PlanAnalysisResult:
        """Analyzes a plan from stdout text or structured JSON."""
        to_add = 0
        to_change = 0
        to_destroy = 0
        creates: List[str] = []
        modifies: List[str] = []
        destroys: List[str] = []
        destructive_reasons: List[str] = []

        # 1. Parse JSON plan if supplied
        if plan_json and "resource_changes" in plan_json:
            for rc in plan_json.get("resource_changes", []):
                addr = rc.get("address", "resource")
                actions = rc.get("change", {}).get("actions", [])
                if "create" in actions and "delete" in actions:
                    destroys.append(addr)
                    creates.append(addr)
                    to_destroy += 1
                    to_add += 1
                elif "create" in actions:
                    creates.append(addr)
                    to_add += 1
                elif "delete" in actions:
                    destroys.append(addr)
                    to_destroy += 1
                elif "update" in actions:
                    modifies.append(addr)
                    to_change += 1

        # 2. Parse text plan
        else:
            lines = plan_text.splitlines()
            for line in lines:
                s = line.strip()
                # Check summary line: Plan: X to add, Y to change, Z to destroy.
                m = re.search(r"Plan:\s*(\d+)\s*to add,\s*(\d+)\s*to change,\s*(\d+)\s*to destroy", s, re.IGNORECASE)
                if m:
                    to_add = int(m.group(1))
                    to_change = int(m.group(2))
                    to_destroy = int(m.group(3))

                # Check resource action markers
                if s.startswith("#") and "will be created" in s:
                    res_name = s.split()[1]
                    creates.append(res_name)
                elif s.startswith("#") and "will be updated in-place" in s:
                    res_name = s.split()[1]
                    modifies.append(res_name)
                elif s.startswith("#") and ("will be destroyed" in s or "must be replaced" in s):
                    res_name = s.split()[1]
                    destroys.append(res_name)

            if to_add == 0 and creates:
                to_add = len(creates)
            if to_change == 0 and modifies:
                to_change = len(modifies)
            if to_destroy == 0 and destroys:
                to_destroy = len(destroys)

        # 3. Detect Destructive Changes on Persistent Resources
        has_destructive = False
        for res in destroys:
            for persistent in self.PERSISTENT_RESOURCE_PATTERNS:
                if persistent in res:
                    has_destructive = True
                    destructive_reasons.append(
                        f"Destructive action: Deleting or replacing persistent stateful resource '{res}'."
                    )
                    break

        if to_destroy > 0 and not has_destructive:
            has_destructive = True
            destructive_reasons.append(f"Plan deletes {to_destroy} resource(s).")

        requires_approval = has_destructive or to_destroy > 0 or to_change >= 3
        approval_status = "AWAITING_APPROVAL" if requires_approval else "AUTO_APPROVED"
        summary_str = f"Plan: {to_add} to add, {to_change} to change, {to_destroy} to destroy."

        return PlanAnalysisResult(
            to_add=to_add,
            to_change=to_change,
            to_destroy=to_destroy,
            resources_to_create=creates,
            resources_to_modify=modifies,
            resources_to_delete=destroys,
            destructive_changes=has_destructive,
            destructive_reasons=destructive_reasons,
            requires_human_approval=requires_approval,
            approval_status=approval_status,
            plan_summary=summary_str
        )

    def record_approval(
        self,
        approval_token: str,
        approver: str,
        approved: bool,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Records an explicit Human-in-the-Loop approval decision."""
        record = {
            "token": approval_token,
            "approver": approver,
            "status": "APPROVED" if approved else "REJECTED",
            "timestamp": time.time(),
            "comment": comment or ("Approved via DevPilot DevOps Console" if approved else "Rejected by developer")
        }
        self._approvals[approval_token] = record
        return record

    def get_approval(self, approval_token: str) -> Optional[Dict[str, Any]]:
        return self._approvals.get(approval_token)


terraform_plan_engine = TerraformPlanEngine()
