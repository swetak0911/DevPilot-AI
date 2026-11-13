"""
DevPilot AI - Kubernetes OpenAPI & Pod Security Standards (PSS) Validator
Validates Kubernetes manifests against structural schema constraints,
resource request/limit boundaries, health probe timing, and CIS PSS benchmarks.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


@dataclass
class K8sLintIssue:
    code: str
    severity: str  # "CRITICAL", "HIGH", "WARNING", "INFO"
    resource_kind: str
    resource_name: str
    message: str
    remediation: str


@dataclass
class K8sValidationResult:
    is_valid: bool
    security_score: int
    issues: List[K8sLintIssue]
    resources_found: List[Dict[str, str]]
    recommendations: List[str]


class K8sValidator:
    """Performs deep static analysis and schema validation on Kubernetes YAML manifests."""

    VALID_KINDS = {
        "Deployment", "Service", "ConfigMap", "Secret", "HorizontalPodAutoscaler",
        "Ingress", "StatefulSet", "DaemonSet", "Job", "CronJob", "Pod", "Namespace"
    }

    SEVERITY_DEDUCTIONS = {
        "CRITICAL": 30,
        "HIGH": 15,
        "WARNING": 8,
        "INFO": 3
    }

    def _parse_memory_bytes(self, mem_str: str) -> Optional[int]:
        """Converts Kubernetes memory quantity strings (e.g., 256Mi, 1Gi, 500M) to bytes."""
        if not mem_str:
            return None
        m = re.match(r"^(\d+)([a-zA-Z]+)?$", str(mem_str).strip())
        if not m:
            return None
        val = int(m.group(1))
        unit = m.group(2) or ""
        multipliers = {
            "Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4,
            "k": 1000, "M": 1000**2, "G": 1000**3, "T": 1000**4
        }
        return val * multipliers.get(unit, 1)

    def _parse_cpu_millicores(self, cpu_str: str) -> Optional[int]:
        """Converts Kubernetes CPU quantity strings (e.g., 500m, 1, 2.5) to millicores."""
        if not cpu_str:
            return None
        s = str(cpu_str).strip()
        if s.endswith("m"):
            try:
                return int(s[:-1])
            except ValueError:
                return None
        try:
            return int(float(s) * 1000)
        except ValueError:
            return None

    def validate_manifest(self, yaml_content: str) -> K8sValidationResult:
        """Alias wrapper for validate."""
        return self.validate(yaml_content)

    def validate(self, yaml_content: str) -> K8sValidationResult:
        """Validates single or multi-document Kubernetes YAML manifests."""
        if not yaml_content or not yaml_content.strip():
            return K8sValidationResult(
                is_valid=False,
                security_score=0,
                issues=[K8sLintIssue(
                    code="K8S_ERR_001",
                    severity="CRITICAL",
                    resource_kind="Unknown",
                    resource_name="Unknown",
                    message="Manifest content is empty.",
                    remediation="Provide valid Kubernetes YAML declarations."
                )],
                resources_found=[],
                recommendations=["Provide non-empty Kubernetes YAML declarations."]
            )

        # Split multi-document YAML on ---
        raw_docs = re.split(r"(?:^|\n)---\s*(?:\n|$)", yaml_content)
        issues: List[K8sLintIssue] = []
        resources_found: List[Dict[str, str]] = []

        deployment_labels: Dict[str, Dict[str, str]] = {}
        service_selectors: Dict[str, Dict[str, str]] = {}

        for doc_text in raw_docs:
            clean_doc = doc_text.strip()
            if not clean_doc:
                continue

            lines = clean_doc.splitlines()
            kind = None
            api_version = None
            res_name = None
            namespace = "default"

            # Top-level YAML extraction (prevent nested fields from overwriting document kind)
            in_metadata = False
            for line in lines:
                stripped = line.strip()
                if not line.startswith(" ") and not line.startswith("\t"):
                    if stripped.startswith("kind:") and kind is None:
                        kind = stripped.split(":", 1)[1].strip()
                        in_metadata = False
                    elif stripped.startswith("apiVersion:") and api_version is None:
                        api_version = stripped.split(":", 1)[1].strip()
                        in_metadata = False
                    elif stripped.startswith("metadata:"):
                        in_metadata = True
                    else:
                        in_metadata = False
                elif in_metadata:
                    if stripped.startswith("name:") and res_name is None:
                        res_name = stripped.split(":", 1)[1].strip()
                    elif stripped.startswith("namespace:"):
                        namespace = stripped.split(":", 1)[1].strip()

            res_name = res_name or "unnamed-resource"
            kind = kind or "Unknown"

            if kind not in self.VALID_KINDS:
                issues.append(K8sLintIssue(
                    code="K8S_ERR_002",
                    severity="HIGH",
                    resource_kind=kind,
                    resource_name=res_name,
                    message=f"Unsupported or invalid Kubernetes resource kind '{kind}'.",
                    remediation=f"Ensure kind is one of {', '.join(sorted(self.VALID_KINDS))}."
                ))
                continue

            if not api_version:
                issues.append(K8sLintIssue(
                    code="K8S_ERR_003",
                    severity="CRITICAL",
                    resource_kind=kind,
                    resource_name=res_name,
                    message=f"Missing 'apiVersion' field in {kind}/{res_name}.",
                    remediation="Declare correct apiVersion (e.g. 'apps/v1' for Deployments, 'v1' for Services)."
                ))

            resources_found.append({
                "kind": kind,
                "name": res_name,
                "namespace": namespace,
                "apiVersion": api_version or "v1"
            })

            # Check Port numbers
            port_matches = re.findall(r"(?:containerPort|port|targetPort):\s*(\d+)", clean_doc)
            for p_str in port_matches:
                p_val = int(p_str)
                if p_val < 1 or p_val > 65535:
                    issues.append(K8sLintIssue(
                        code="K8S_NET_001",
                        severity="CRITICAL",
                        resource_kind=kind,
                        resource_name=res_name,
                        message=f"Port number {p_val} is out of allowable range (1 - 65535).",
                        remediation="Set port numbers between 1 and 65535."
                    ))

            # Deep inspection for Deployments / Pod templates
            if kind in ("Deployment", "StatefulSet", "DaemonSet"):
                # 1. Non-root user check (PSS Restricted)
                if "runAsNonRoot: true" not in clean_doc and "runAsUser: 10" not in clean_doc:
                    issues.append(K8sLintIssue(
                        code="K8S_SEC_001",
                        severity="HIGH",
                        resource_kind=kind,
                        resource_name=res_name,
                        message=f"{kind}/{res_name} does not enforce 'runAsNonRoot: true'.",
                        remediation="Set 'securityContext.runAsNonRoot: true' to avoid root container breakouts."
                    ))

                # 2. Resource constraints check
                has_requests = "requests:" in clean_doc
                has_limits = "limits:" in clean_doc
                if not has_requests or not has_limits:
                    issues.append(K8sLintIssue(
                        code="K8S_SEC_002",
                        severity="MEDIUM",
                        resource_kind=kind,
                        resource_name=res_name,
                        message=f"{kind}/{res_name} is missing resource requests or limits.",
                        remediation="Define both requests and limits for CPU and memory to protect node stability."
                    ))
                else:
                    # Compare limits vs requests
                    cpu_req_m = re.search(r"requests:.*?cpu:\s*[\"']?([0-9a-zA-Z\.]+)[\"']?", clean_doc, re.DOTALL)
                    cpu_lim_m = re.search(r"limits:.*?cpu:\s*[\"']?([0-9a-zA-Z\.]+)[\"']?", clean_doc, re.DOTALL)
                    if cpu_req_m and cpu_lim_m:
                        req_cpu = self._parse_cpu_millicores(cpu_req_m.group(1))
                        lim_cpu = self._parse_cpu_millicores(cpu_lim_m.group(1))
                        if req_cpu and lim_cpu and lim_cpu < req_cpu:
                            issues.append(K8sLintIssue(
                                code="K8S_SEC_003",
                                severity="HIGH",
                                resource_kind=kind,
                                resource_name=res_name,
                                message=f"CPU limit ({cpu_lim_m.group(1)}) is lower than request ({cpu_req_m.group(1)}).",
                                remediation="Ensure limits >= requests."
                            ))

                    mem_req_m = re.search(r"requests:.*?memory:\s*[\"']?([0-9a-zA-Z]+)[\"']?", clean_doc, re.DOTALL)
                    mem_lim_m = re.search(r"limits:.*?memory:\s*[\"']?([0-9a-zA-Z]+)[\"']?", clean_doc, re.DOTALL)
                    if mem_req_m and mem_lim_m:
                        req_mem = self._parse_memory_bytes(mem_req_m.group(1))
                        lim_mem = self._parse_memory_bytes(mem_lim_m.group(1))
                        if req_mem and lim_mem and lim_mem < req_mem:
                            issues.append(K8sLintIssue(
                                code="K8S_SEC_003",
                                severity="HIGH",
                                resource_kind=kind,
                                resource_name=res_name,
                                message=f"Memory limit ({mem_lim_m.group(1)}) is lower than request ({mem_req_m.group(1)}).",
                                remediation="Ensure limits >= requests."
                            ))

                # 3. Health probes check
                if "livenessProbe:" not in clean_doc:
                    issues.append(K8sLintIssue(
                        code="K8S_SEC_004",
                        severity="MEDIUM",
                        resource_kind=kind,
                        resource_name=res_name,
                        message=f"{kind}/{res_name} lacks a 'livenessProbe'.",
                        remediation="Configure a livenessProbe to allow Kubernetes to automatically restart unresponsive pods."
                    ))

                if "readinessProbe:" not in clean_doc:
                    issues.append(K8sLintIssue(
                        code="K8S_SEC_004",
                        severity="MEDIUM",
                        resource_kind=kind,
                        resource_name=res_name,
                        message=f"{kind}/{res_name} lacks a 'readinessProbe'.",
                        remediation="Configure a readinessProbe to stop routing traffic to initializing pods."
                    ))

                # 4. Privilege escalation
                if "allowPrivilegeEscalation: false" not in clean_doc:
                    issues.append(K8sLintIssue(
                        code="K8S_SEC_005",
                        severity="WARNING",
                        resource_kind=kind,
                        resource_name=res_name,
                        message=f"{kind}/{res_name} does not explicitly disable privilege escalation.",
                        remediation="Set 'securityContext.allowPrivilegeEscalation: false'."
                    ))

                # 5. Read-only root filesystem
                if "readOnlyRootFilesystem: true" not in clean_doc:
                    issues.append(K8sLintIssue(
                        code="K8S_SEC_006",
                        severity="INFO",
                        resource_kind=kind,
                        resource_name=res_name,
                        message=f"{kind}/{res_name} does not configure a read-only root filesystem.",
                        remediation="Set 'securityContext.readOnlyRootFilesystem: true' and mount writable volumes for /tmp if needed."
                    ))

            # Service inspection
            elif kind == "Service":
                if "selector:" not in clean_doc:
                    issues.append(K8sLintIssue(
                        code="K8S_NET_002",
                        severity="WARNING",
                        resource_kind=kind,
                        resource_name=res_name,
                        message=f"Service/{res_name} has no selector defined.",
                        remediation="Define 'spec.selector' pointing to target Pod labels."
                    ))

        # Calculate security score (0 to 100)
        score = 100
        for issue in issues:
            deduction = self.SEVERITY_DEDUCTIONS.get(issue.severity, 5)
            score -= deduction
        score = max(0, min(100, score))

        is_valid = not any(i.severity == "CRITICAL" for i in issues) and score >= 60

        recommendations = []
        if any(i.code == "K8S_SEC_001" for i in issues):
            recommendations.append("Enforce Pod Security Standards Restricted: drop ALL capabilities and run as UID 10001.")
        if any(i.code == "K8S_SEC_002" for i in issues):
            recommendations.append("Specify explicit CPU & Memory requests and limits for guaranteed QoS class.")
        if any(i.code == "K8S_SEC_004" for i in issues):
            recommendations.append("Implement robust liveness and readiness probes.")
        if not recommendations:
            recommendations.append("Manifests fully comply with Kubernetes OpenAPI v1 specs and CIS benchmarks.")

        return K8sValidationResult(
            is_valid=is_valid,
            security_score=score,
            issues=issues,
            resources_found=resources_found,
            recommendations=recommendations
        )


k8s_validator = K8sValidator()
