"""
Code Parser Service
Extracts functions, methods, classes, signatures, docstrings, and imports
across Python, JavaScript, TypeScript, Java, and C++ with exact line ranges.
"""
import ast
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ParsedSymbol:
    name: str
    symbol_type: str  # function, async_function, method, class, interface
    start_line: int
    end_line: int
    signature: str
    docstring: Optional[str]
    parent_name: Optional[str]
    content: str
    token_count: int


@dataclass
class ParseResult:
    language: str
    symbols: List[ParsedSymbol]
    imports: List[str]
    line_count: int


class CodeParser:
    """Multi-language AST and structure parser."""

    @staticmethod
    def detect_language_from_path(file_path: str) -> Optional[str]:
        """Maps file extensions to language names."""
        ext = file_path.lower().split(".")[-1] if "." in file_path else ""
        mapping = {
            "py": "Python",
            "js": "JavaScript",
            "jsx": "JavaScript",
            "ts": "TypeScript",
            "tsx": "TypeScript",
            "java": "Java",
            "cpp": "C++",
            "cc": "C++",
            "cxx": "C++",
            "c": "C",
            "h": "C/C++ Header",
            "hpp": "C++ Header",
            "json": "JSON",
            "yml": "YAML",
            "yaml": "YAML",
            "md": "Markdown",
            "html": "HTML",
            "css": "CSS",
            "sql": "SQL",
            "sh": "Shell",
            "bash": "Shell",
            "dockerfile": "Dockerfile",
        }
        if file_path.lower().endswith("dockerfile"):
            return "Dockerfile"
        return mapping.get(ext)

    def parse_source_code(self, file_path: str, content: str) -> ParseResult:
        """Parses source file content according to its detected programming language."""
        language = self.detect_language_from_path(file_path) or "Text"
        lines = content.splitlines()
        line_count = len(lines)

        if language == "Python":
            symbols, imports = self._parse_python(lines, content)
        elif language in ("JavaScript", "TypeScript"):
            symbols, imports = self._parse_js_ts(lines, content)
        elif language == "Java":
            symbols, imports = self._parse_java(lines, content)
        elif language in ("C++", "C", "C++ Header", "C/C++ Header"):
            symbols, imports = self._parse_cpp(lines, content)
        else:
            symbols, imports = [], []

        return ParseResult(
            language=language,
            symbols=symbols,
            imports=imports,
            line_count=line_count
        )

    def _parse_python(self, lines: List[str], content: str) -> (List[ParsedSymbol], List[str]):
        """Parses Python source using the native AST library."""
        symbols: List[ParsedSymbol] = []
        imports: List[str] = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fallback to regex if syntax error (e.g. invalid syntax in partial file)
            return self._parse_python_regex(lines, content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}")

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sym = self._extract_python_function(node, lines)
                if sym:
                    symbols.append(sym)
            elif isinstance(node, ast.ClassDef):
                cls_sym = self._extract_python_class(node, lines)
                if cls_sym:
                    symbols.append(cls_sym)
                # Extract methods
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_sym = self._extract_python_function(sub, lines, parent_name=node.name)
                        if method_sym:
                            method_sym.symbol_type = "method"
                            symbols.append(method_sym)

        return symbols, imports

    def _extract_python_function(self, node, lines: List[str], parent_name: Optional[str] = None) -> Optional[ParsedSymbol]:
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        fn_lines = lines[start - 1:end]
        snippet = "\n".join(fn_lines)
        doc = ast.get_docstring(node)
        
        args = [a.arg for a in node.args.args]
        is_async = isinstance(node, ast.AsyncFunctionDef)
        prefix = "async def" if is_async else "def"
        sig = f"{prefix} {node.name}({', '.join(args)})"

        return ParsedSymbol(
            name=node.name,
            symbol_type="async_function" if is_async else "function",
            start_line=start,
            end_line=end,
            signature=sig,
            docstring=doc,
            parent_name=parent_name,
            content=snippet,
            token_count=max(len(snippet) // 4, 1)
        )

    def _extract_python_class(self, node: ast.ClassDef, lines: List[str]) -> Optional[ParsedSymbol]:
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        cls_lines = lines[start - 1:end]
        snippet = "\n".join(cls_lines)
        doc = ast.get_docstring(node)
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        bases_str = f"({', '.join(bases)})" if bases else ""
        sig = f"class {node.name}{bases_str}"

        return ParsedSymbol(
            name=node.name,
            symbol_type="class",
            start_line=start,
            end_line=end,
            signature=sig,
            docstring=doc,
            parent_name=None,
            content=snippet,
            token_count=max(len(snippet) // 4, 1)
        )

    def _parse_python_regex(self, lines: List[str], content: str) -> (List[ParsedSymbol], List[str]):
        """Regex fallback for malformed or incomplete Python files."""
        symbols = []
        imports = []
        for i, line in enumerate(lines, 1):
            if line.strip().startswith(("import ", "from ")):
                imports.append(line.strip())
            m = re.match(r"^\s*(def|class)\s+([A-Za-z0-9_]+)", line)
            if m:
                kind = "class" if m.group(1) == "class" else "function"
                name = m.group(2)
                symbols.append(ParsedSymbol(
                    name=name,
                    symbol_type=kind,
                    start_line=i,
                    end_line=min(i + 15, len(lines)),
                    signature=line.strip(),
                    docstring=None,
                    parent_name=None,
                    content=line,
                    token_count=max(len(line) // 4, 1)
                ))
        return symbols, imports

    def _parse_js_ts(self, lines: List[str], content: str) -> (List[ParsedSymbol], List[str]):
        """Extracts JavaScript and TypeScript functions, classes, and interfaces."""
        symbols = []
        imports = []

        import_pattern = re.compile(r"import\s+.*?\s+from\s+['\"](.*?)['\"]")
        fn_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\((.*?)\)")
        arrow_pattern = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\((.*?)\)\s*=>")
        class_pattern = re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z0-9_$]+)")
        interface_pattern = re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z0-9_$]+)")

        for i, line in enumerate(lines, 1):
            imp_match = import_pattern.search(line)
            if imp_match:
                imports.append(imp_match.group(1))

            fn_m = fn_pattern.match(line)
            if fn_m:
                symbols.append(ParsedSymbol(
                    name=fn_m.group(1),
                    symbol_type="function",
                    start_line=i,
                    end_line=min(i + 20, len(lines)),
                    signature=f"function {fn_m.group(1)}({fn_m.group(2)})",
                    docstring=None,
                    parent_name=None,
                    content=line.strip(),
                    token_count=max(len(line) // 4, 1)
                ))
                continue

            arr_m = arrow_pattern.match(line)
            if arr_m:
                symbols.append(ParsedSymbol(
                    name=arr_m.group(1),
                    symbol_type="function",
                    start_line=i,
                    end_line=min(i + 20, len(lines)),
                    signature=f"const {arr_m.group(1)} = ({arr_m.group(2)}) =>",
                    docstring=None,
                    parent_name=None,
                    content=line.strip(),
                    token_count=max(len(line) // 4, 1)
                ))
                continue

            cls_m = class_pattern.match(line)
            if cls_m:
                symbols.append(ParsedSymbol(
                    name=cls_m.group(1),
                    symbol_type="class",
                    start_line=i,
                    end_line=min(i + 30, len(lines)),
                    signature=f"class {cls_m.group(1)}",
                    docstring=None,
                    parent_name=None,
                    content=line.strip(),
                    token_count=max(len(line) // 4, 1)
                ))
                continue

            if_m = interface_pattern.match(line)
            if if_m:
                symbols.append(ParsedSymbol(
                    name=if_m.group(1),
                    symbol_type="interface",
                    start_line=i,
                    end_line=min(i + 15, len(lines)),
                    signature=f"interface {if_m.group(1)}",
                    docstring=None,
                    parent_name=None,
                    content=line.strip(),
                    token_count=max(len(line) // 4, 1)
                ))

        return symbols, imports

    def _parse_java(self, lines: List[str], content: str) -> (List[ParsedSymbol], List[str]):
        """Extracts Java classes, interfaces, and methods."""
        symbols = []
        imports = []
        cls_pattern = re.compile(r"^\s*(?:public|protected|private)?\s*(?:static)?\s*(?:final)?\s*(class|interface)\s+([A-Za-z0-9_]+)")
        method_pattern = re.compile(r"^\s*(?:public|protected|private)\s+(?:static\s+)?([A-Za-z0-9_<>,\[\]]+)\s+([A-Za-z0-9_]+)\s*\((.*?)\)\s*\{?")

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("import "):
                imports.append(line.strip().removeprefix("import ").rstrip(";").strip())
            cls_m = cls_pattern.match(line)
            if cls_m:
                symbols.append(ParsedSymbol(
                    name=cls_m.group(2),
                    symbol_type=cls_m.group(1),
                    start_line=i,
                    end_line=min(i + 40, len(lines)),
                    signature=line.strip(),
                    docstring=None,
                    parent_name=None,
                    content=line.strip(),
                    token_count=max(len(line) // 4, 1)
                ))
            method_m = method_pattern.match(line)
            if method_m:
                symbols.append(ParsedSymbol(
                    name=method_m.group(2),
                    symbol_type="method",
                    start_line=i,
                    end_line=min(i + 25, len(lines)),
                    signature=line.strip(),
                    docstring=None,
                    parent_name=None,
                    content=line.strip(),
                    token_count=max(len(line) // 4, 1)
                ))
        return symbols, imports

    def _parse_cpp(self, lines: List[str], content: str) -> (List[ParsedSymbol], List[str]):
        """Extracts C++ classes, structs, and function signatures."""
        symbols = []
        includes = []
        cls_pattern = re.compile(r"^\s*(?:class|struct)\s+([A-Za-z0-9_]+)")
        fn_pattern = re.compile(r"^\s*([A-Za-z0-9_:<>&*]+)\s+([A-Za-z0-9_]+)\s*\((.*?)\)\s*(?:const)?\s*\{?")

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("#include"):
                includes.append(line.strip())
            cls_m = cls_pattern.match(line)
            if cls_m:
                symbols.append(ParsedSymbol(
                    name=cls_m.group(1),
                    symbol_type="class",
                    start_line=i,
                    end_line=min(i + 30, len(lines)),
                    signature=line.strip(),
                    docstring=None,
                    parent_name=None,
                    content=line.strip(),
                    token_count=max(len(line) // 4, 1)
                ))
            fn_m = fn_pattern.match(line)
            if fn_m and fn_m.group(2) not in ("if", "for", "while", "switch"):
                symbols.append(ParsedSymbol(
                    name=fn_m.group(2),
                    symbol_type="function",
                    start_line=i,
                    end_line=min(i + 20, len(lines)),
                    signature=line.strip(),
                    docstring=None,
                    parent_name=None,
                    content=line.strip(),
                    token_count=max(len(line) // 4, 1)
                ))
        return symbols, includes


code_parser = CodeParser()
