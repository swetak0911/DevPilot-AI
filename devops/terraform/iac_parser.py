"""
DevPilot AI - HCL / Terraform IaC Parser & Formatter
Extracts structured blocks (resource, provider, variable, output) from Terraform configurations
and provides deterministic 'terraform fmt' code beautification without external binary dependencies.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


@dataclass
class HclBlock:
    block_type: str
    labels: List[str]
    attributes: Dict[str, Any]
    raw_content: str
    start_line: int


@dataclass
class HclFormatResult:
    formatted_hcl: str
    is_formatted: bool


@dataclass
class HclParseResult:
    blocks: List[HclBlock]
    resource_count: int
    provider_names: List[str]
    variables: List[str]
    outputs: List[str]


class IacParser:
    """Parses and formats Terraform / OpenTofu HCL code."""

    BLOCK_HEADER_RE = re.compile(
        r'^(resource|data|provider|variable|output|locals|terraform)\s*(?:\"([^\"]+)\"|\b(\w+)\b)?\s*(?:\"([^\"]+)\"|\b(\w+)\b)?\s*\{'
    )

    def parse(self, hcl_text: str) -> HclParseResult:
        """Parses HCL text into structured blocks and attributes."""
        lines = hcl_text.splitlines()
        blocks: List[HclBlock] = []
        providers: List[str] = []
        variables: List[str] = []
        outputs: List[str] = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Skip comments or blank lines
            if not line or line.startswith("#") or line.startswith("//"):
                i += 1
                continue

            m = self.BLOCK_HEADER_RE.match(line)
            if m:
                b_type = m.group(1)
                labels = [g for g in [m.group(2) or m.group(3), m.group(4) or m.group(5)] if g]

                # Extract block body by counting braces
                start_line = i + 1
                brace_depth = line.count("{") - line.count("}")
                block_lines = [lines[i]]
                i += 1

                while i < len(lines) and brace_depth > 0:
                    cur = lines[i]
                    brace_depth += cur.count("{") - cur.count("}")
                    block_lines.append(cur)
                    i += 1

                raw_body = "\n".join(block_lines)

                # Extract top-level attributes inside this block
                attrs = {}
                for bl in block_lines[1:-1]:
                    bl_s = bl.strip()
                    if "=" in bl_s and not bl_s.startswith("#") and not bl_s.startswith("//"):
                        k, v = bl_s.split("=", 1)
                        attrs[k.strip()] = v.strip().strip('"\'')

                block = HclBlock(
                    block_type=b_type,
                    labels=labels,
                    attributes=attrs,
                    raw_content=raw_body,
                    start_line=start_line
                )
                blocks.append(block)

                if b_type == "provider" and labels:
                    providers.append(labels[0])
                elif b_type == "variable" and labels:
                    variables.append(labels[0])
                elif b_type == "output" and labels:
                    outputs.append(labels[0])
            else:
                i += 1

        res_count = sum(1 for b in blocks if b.block_type == "resource")

        return HclParseResult(
            blocks=blocks,
            resource_count=res_count,
            provider_names=providers,
            variables=variables,
            outputs=outputs
        )

    def format_hcl(self, hcl_text: str) -> HclFormatResult:
        """Beautifies HCL and returns a structured HclFormatResult."""
        formatted = self.terraform_fmt(hcl_text)
        return HclFormatResult(formatted_hcl=formatted, is_formatted=True)

    def terraform_fmt(self, hcl_text: str) -> str:
        """
        Beautifies and standardizes HCL code:
        - 2-space indentation
        - Aligning '=' in contiguous assignment blocks
        - Clean single blank lines between blocks
        """
        lines = hcl_text.splitlines()
        formatted_lines: List[str] = []
        indent_level = 0
        assign_group: List[tuple[str, str, str]] = []  # (indent, key, value)

        def flush_assign_group():
            if not assign_group:
                return
            max_key_len = max(len(k) for _, k, _ in assign_group)
            for ind, k, v in assign_group:
                padded_key = k.ljust(max_key_len)
                formatted_lines.append(f"{ind}{padded_key} = {v}")
            assign_group.clear()

        for line in lines:
            stripped = line.strip()

            if not stripped:
                flush_assign_group()
                if formatted_lines and formatted_lines[-1] != "":
                    formatted_lines.append("")
                continue

            # Check brace closures
            if stripped.startswith("}"):
                flush_assign_group()
                indent_level = max(0, indent_level - 1)

            cur_indent = "  " * indent_level

            # Check if this is an attribute assignment line (not a block or comment)
            if "=" in stripped and not stripped.startswith("#") and not stripped.startswith("//") and not stripped.endswith("{"):
                parts = stripped.split("=", 1)
                k = parts[0].strip()
                v = parts[1].strip()
                assign_group.append((cur_indent, k, v))
            else:
                flush_assign_group()
                formatted_lines.append(f"{cur_indent}{stripped}")

            # Check brace openings
            if stripped.endswith("{"):
                indent_level += 1

        flush_assign_group()

        # Clean trailing empty lines and ensure single final newline
        result = "\n".join(formatted_lines).strip() + "\n"
        return result


iac_parser = IacParser()
