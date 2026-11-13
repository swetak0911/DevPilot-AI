"""
DevPilot AI - GitHub Actions YAML Validator & Linter
Performs syntax verification, GitHub Actions schema conformance checks,
and security/deprecation linting for workflow files.
Provides a native fallback parser when PyYAML is not installed in the environment.
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import re

try:
    import yaml
    HAS_PYYAML = True
except ImportError:
    yaml = None
    HAS_PYYAML = False


@dataclass
class LintIssue:
    rule: str
    message: str
    severity: str  # ERROR, WARNING, INFO
    line: Optional[int] = None
    step_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity,
            "line": self.line,
            "step_name": self.step_name
        }


@dataclass
class WorkflowValidationResult:
    is_valid: bool
    syntax_valid: bool
    schema_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    lint_issues: List[Dict[str, Any]] = field(default_factory=list)
    jobs_detected: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "syntax_valid": self.syntax_valid,
            "schema_valid": self.schema_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "lint_issues": self.lint_issues,
            "jobs_detected": self.jobs_detected
        }


def _parse_scalar(val: str) -> Any:
    val = val.strip()
    if not val:
        return None
    if val.startswith('"') and val.endswith('"') and len(val) >= 2:
        return val[1:-1]
    if val.startswith("'") and val.endswith("'") and len(val) >= 2:
        return val[1:-1]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in inner.split(","):
            cleaned = item.strip().strip("\"'")
            if cleaned:
                items.append(cleaned)
        return items
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() in ("null", "~"):
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        pass
    return val


def _parse_yaml_block(lines: List[str], start_idx: int, min_indent: int) -> Tuple[Any, int]:
    """Recursively parses a block of lines into dict or list structure."""
    # Find first non-empty, non-comment line
    idx = start_idx
    first_line = None
    first_indent = None
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            first_line = line
            first_indent = len(line) - len(line.lstrip(" "))
            break
        idx += 1

    if first_line is None or first_indent is None or first_indent < min_indent:
        return None, idx

    content = first_line.lstrip(" ")
    is_list = content.startswith("- ")

    if is_list:
        res_list = []
        while idx < len(lines):
            line = lines[idx]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                idx += 1
                continue
            cur_indent = len(line) - len(line.lstrip(" "))
            if cur_indent < min_indent:
                break
            if cur_indent > min_indent:
                break
            c_str = line.lstrip(" ")
            if not c_str.startswith("- "):
                break

            after_dash = c_str[2:].strip()
            if ":" in after_dash and not after_dash.startswith('"') and not after_dash.startswith("'"):
                # Dict item in list
                c_pos = after_dash.find(":")
                k1 = after_dash[:c_pos].strip().strip("\"'")
                v1_raw = after_dash[c_pos + 1:].strip()
                item_dict: Dict[str, Any] = {}
                item_dict[k1] = _parse_scalar(v1_raw) if v1_raw else None

                dict_indent = cur_indent + 2
                idx += 1
                while idx < len(lines):
                    sub_line = lines[idx]
                    sub_strip = sub_line.strip()
                    if not sub_strip or sub_strip.startswith("#"):
                        idx += 1
                        continue
                    sub_indent = len(sub_line) - len(sub_line.lstrip(" "))
                    if sub_indent < dict_indent or sub_line.lstrip(" ").startswith("- "):
                        break

                    c_pos2 = sub_line.find(":")
                    if c_pos2 != -1:
                        k2 = sub_line[:c_pos2].strip().strip("\"'")
                        v2_raw = sub_line[c_pos2 + 1:].strip()
                        if v2_raw in ("|", "|-", "|+", ">", ">-"):
                            multiline = []
                            idx += 1
                            while idx < len(lines):
                                ml_line = lines[idx]
                                ml_strip = ml_line.strip()
                                if not ml_strip:
                                    multiline.append("")
                                    idx += 1
                                    continue
                                ml_indent = len(ml_line) - len(ml_line.lstrip(" "))
                                if ml_indent <= sub_indent:
                                    break
                                multiline.append(ml_line.strip())
                                idx += 1
                            item_dict[k2] = "\n".join(multiline)
                        elif v2_raw != "":
                            item_dict[k2] = _parse_scalar(v2_raw)
                            idx += 1
                        else:
                            idx += 1
                            # Next block
                            n_idx = idx
                            n_ind = None
                            while n_idx < len(lines):
                                s = lines[n_idx].strip()
                                if s and not s.startswith("#"):
                                    n_ind = len(lines[n_idx]) - len(lines[n_idx].lstrip(" "))
                                    break
                                n_idx += 1
                            if n_ind is not None and n_ind > sub_indent:
                                nested, idx = _parse_yaml_block(lines, n_idx, n_ind)
                                item_dict[k2] = nested
                            else:
                                item_dict[k2] = None
                    else:
                        idx += 1
                res_list.append(item_dict)
            else:
                res_list.append(_parse_scalar(after_dash))
                idx += 1
        return res_list, idx
    else:
        # Dict
        res_dict = {}
        while idx < len(lines):
            line = lines[idx]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                idx += 1
                continue
            cur_indent = len(line) - len(line.lstrip(" "))
            if cur_indent < min_indent:
                break
            if cur_indent > min_indent:
                break

            colon_pos = line.find(":")
            if colon_pos == -1:
                idx += 1
                continue

            k = line[:colon_pos].strip().strip("\"'")
            rest = line[colon_pos + 1:].strip()

            if rest in ("|", "|-", "|+", ">", ">-"):
                multiline = []
                idx += 1
                while idx < len(lines):
                    sub_line = lines[idx]
                    sub_strip = sub_line.strip()
                    if not sub_strip:
                        multiline.append("")
                        idx += 1
                        continue
                    sub_indent = len(sub_line) - len(sub_line.lstrip(" "))
                    if sub_indent <= cur_indent:
                        break
                    multiline.append(sub_line.strip())
                    idx += 1
                res_dict[k] = "\n".join(multiline)
            elif rest != "":
                res_dict[k] = _parse_scalar(rest)
                idx += 1
            else:
                idx += 1
                n_idx = idx
                n_ind = None
                while n_idx < len(lines):
                    s = lines[n_idx].strip()
                    if s and not s.startswith("#"):
                        n_ind = len(lines[n_idx]) - len(lines[n_idx].lstrip(" "))
                        break
                    n_idx += 1
                if n_ind is not None and n_ind > cur_indent:
                    nested, idx = _parse_yaml_block(lines, n_idx, n_ind)
                    res_dict[k] = nested
                else:
                    res_dict[k] = None

            if k == "on":
                # Ensure YAML 1.1 boolean key compatibility
                res_dict[True] = res_dict.get(k)
        return res_dict, idx


def _parse_yaml_native(text: str) -> Dict[str, Any]:
    """Native YAML parser validating syntax and parsing hierarchical workflow mappings."""
    lines = text.splitlines()

    # 1. Structural syntax sanity check
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        in_single = False
        in_double = False
        in_bracket = 0
        colon_positions = []
        for ch_idx, ch in enumerate(stripped):
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "[" and not in_single and not in_double:
                in_bracket += 1
            elif ch == "]" and not in_single and not in_double:
                in_bracket -= 1
            elif ch == ":" and not in_single and not in_double and in_bracket == 0:
                if ch_idx == len(stripped) - 1 or stripped[ch_idx + 1] in (" ", "\t"):
                    colon_positions.append(ch_idx)

        if in_bracket != 0:
            raise ValueError(f"Unmatched brackets at line {lineno}: '{stripped}'")
        if in_single or in_double:
            raise ValueError(f"Unmatched quote at line {lineno}: '{stripped}'")
        if len(colon_positions) > 1:
            raise ValueError(f"Multiple colon mappings on single line at line {lineno}: '{stripped}'")

    res, _ = _parse_yaml_block(lines, 0, 0)
    return res if isinstance(res, dict) else {}


class YAMLValidator:
    """Validates and lints GitHub Actions workflow definitions."""

    DEPRECATED_ACTIONS = {
        "actions/checkout@v1": "actions/checkout@v4",
        "actions/checkout@v2": "actions/checkout@v4",
        "actions/checkout@v3": "actions/checkout@v4",
        "actions/setup-python@v1": "actions/setup-python@v5",
        "actions/setup-python@v2": "actions/setup-python@v5",
        "actions/setup-python@v3": "actions/setup-python@v5",
        "actions/setup-python@v4": "actions/setup-python@v5",
        "actions/setup-node@v1": "actions/setup-node@v4",
        "actions/setup-node@v2": "actions/setup-node@v4",
        "actions/setup-node@v3": "actions/setup-node@v4",
        "actions/upload-artifact@v1": "actions/upload-artifact@v4",
        "actions/upload-artifact@v2": "actions/upload-artifact@v4",
        "actions/upload-artifact@v3": "actions/upload-artifact@v4",
    }

    def validate(self, yaml_content: str) -> WorkflowValidationResult:
        """Runs syntax parsing, schema structure validation, and best practice linting."""
        errors: List[str] = []
        warnings: List[str] = []
        lint_issues: List[LintIssue] = []
        jobs_detected: List[str] = []

        if not yaml_content or not yaml_content.strip():
            return WorkflowValidationResult(
                is_valid=False,
                syntax_valid=False,
                schema_valid=False,
                errors=["Workflow content is empty."],
                warnings=[],
                lint_issues=[],
                jobs_detected=[]
            )

        # 1. Syntax Parsing (PyYAML if available, native fallback otherwise)
        parsed = None
        if HAS_PYYAML and yaml is not None:
            try:
                parsed = yaml.safe_load(yaml_content)
            except yaml.YAMLError as exc:
                line = getattr(getattr(exc, "problem_mark", None), "line", 0) + 1 if hasattr(exc, "problem_mark") else None
                msg = f"YAML Syntax Error: {str(exc).splitlines()[-1]}"
                lint_issues.append(LintIssue(
                    rule="yaml-syntax",
                    message=msg,
                    severity="ERROR",
                    line=line
                ))
                return WorkflowValidationResult(
                    is_valid=False,
                    syntax_valid=False,
                    schema_valid=False,
                    errors=[msg],
                    warnings=[],
                    lint_issues=[issue.to_dict() for issue in lint_issues],
                    jobs_detected=[]
                )
        else:
            try:
                parsed = _parse_yaml_native(yaml_content)
            except Exception as exc:
                msg = f"YAML Syntax Error: {exc}"
                lint_issues.append(LintIssue(
                    rule="yaml-syntax",
                    message=msg,
                    severity="ERROR"
                ))
                return WorkflowValidationResult(
                    is_valid=False,
                    syntax_valid=False,
                    schema_valid=False,
                    errors=[msg],
                    warnings=[],
                    lint_issues=[issue.to_dict() for issue in lint_issues],
                    jobs_detected=[]
                )

        syntax_valid = True

        if not isinstance(parsed, dict):
            errors.append("Root of GitHub Actions workflow must be a mapping (dictionary).")
            return WorkflowValidationResult(
                is_valid=False,
                syntax_valid=True,
                schema_valid=False,
                errors=errors,
                warnings=[],
                lint_issues=[],
                jobs_detected=[]
            )

        # 2. Schema Validation
        # Check 'name'
        if "name" not in parsed:
            warnings.append("Workflow is missing top-level 'name' attribute.")
        elif not isinstance(parsed["name"], str):
            errors.append("'name' attribute must be a string.")

        # Check 'on' triggers
        has_trigger = "on" in parsed or True in parsed
        if not has_trigger:
            errors.append("Workflow missing required 'on' trigger specification.")

        # Check 'permissions'
        if "permissions" not in parsed:
            warnings.append("No explicit top-level 'permissions' block defined; consider scoping least privileges.")
            lint_issues.append(LintIssue(
                rule="security-least-privilege",
                message="Workflow lacks explicit top-level permissions block. Defaults to read/write in some runner setups.",
                severity="WARNING"
            ))

        # Check 'jobs'
        if "jobs" not in parsed or not isinstance(parsed["jobs"], dict) or not parsed["jobs"]:
            errors.append("Workflow must contain a non-empty 'jobs' section.")
            schema_valid = len(errors) == 0
            return WorkflowValidationResult(
                is_valid=schema_valid,
                syntax_valid=syntax_valid,
                schema_valid=schema_valid,
                errors=errors,
                warnings=warnings,
                lint_issues=[issue.to_dict() for issue in lint_issues],
                jobs_detected=[]
            )

        # Validate each job
        jobs = parsed["jobs"]
        for job_id, job_data in jobs.items():
            jobs_detected.append(str(job_id))
            if not isinstance(job_data, dict):
                errors.append(f"Job '{job_id}' must be an object definition.")
                continue

            if "runs-on" not in job_data and "uses" not in job_data:
                errors.append(f"Job '{job_id}' missing 'runs-on' operating system definition.")

            steps = job_data.get("steps")
            if "uses" not in job_data:
                if steps is None or not isinstance(steps, list) or len(steps) == 0:
                    errors.append(f"Job '{job_id}' must define at least one step.")
                    continue

                has_checkout = False
                for idx, step in enumerate(steps):
                    if not isinstance(step, dict):
                        errors.append(f"Job '{job_id}' step #{idx+1} is not a valid step dictionary.")
                        continue

                    step_name = step.get("name", f"Step #{idx+1}")

                    if "uses" not in step and "run" not in step:
                        errors.append(f"Job '{job_id}' step '{step_name}' must specify either 'uses' or 'run'.")

                    uses_action = step.get("uses")
                    if uses_action:
                        if "actions/checkout" in uses_action:
                            has_checkout = True

                        for dep_action, rec_action in self.DEPRECATED_ACTIONS.items():
                            if uses_action.strip() == dep_action:
                                lint_issues.append(LintIssue(
                                    rule="deprecated-action",
                                    message=f"Action '{uses_action}' is deprecated. Upgrade to '{rec_action}'.",
                                    severity="WARNING",
                                    step_name=step_name
                                ))
                                warnings.append(f"Deprecated action '{uses_action}' in job '{job_id}'. Upgrade to '{rec_action}'.")

                        if uses_action.endswith("@main") or uses_action.endswith("@master"):
                            lint_issues.append(LintIssue(
                                rule="unpinned-action-ref",
                                message=f"Action '{uses_action}' uses mutable branch reference (@main/@master). Pin to full SHA or semver release tag.",
                                severity="WARNING",
                                step_name=step_name
                            ))

                    run_cmd = step.get("run")
                    if run_cmd:
                        if re.search(r"curl\s+.*\|\s*(ba)?sh", str(run_cmd)):
                            lint_issues.append(LintIssue(
                                rule="security-curl-pipe-bash",
                                message=f"Dangerous shell pipe detected in step '{step_name}': 'curl | sh'.",
                                severity="ERROR",
                                step_name=step_name
                            ))
                            errors.append(f"Security hazard in job '{job_id}' step '{step_name}': pipe to shell.")

                if not has_checkout and any("run" in s for s in steps if isinstance(s, dict)):
                    warnings.append(f"Job '{job_id}' executes commands without an 'actions/checkout' step.")
                    lint_issues.append(LintIssue(
                        rule="missing-checkout",
                        message=f"Job '{job_id}' runs bash scripts without prior 'actions/checkout' step.",
                        severity="WARNING"
                    ))

        schema_valid = len(errors) == 0
        is_valid = syntax_valid and schema_valid

        return WorkflowValidationResult(
            is_valid=is_valid,
            syntax_valid=syntax_valid,
            schema_valid=schema_valid,
            errors=errors,
            warnings=warnings,
            lint_issues=[issue.to_dict() for issue in lint_issues],
            jobs_detected=jobs_detected
        )


yaml_validator = YAMLValidator()
