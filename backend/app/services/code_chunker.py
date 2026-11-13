"""
Code Chunker Service
Decomposes source code files into semantic chunks by class, function, method,
and sliding context blocks while preserving file paths and line numbers.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.services.code_parser import code_parser, ParsedSymbol, ParseResult


@dataclass
class CodeChunkItem:
    symbol_name: str
    chunk_type: str  # function, async_function, method, class, interface, module, block
    start_line: int
    end_line: int
    content: str
    formatted_context: str
    token_count: int
    metadata: Dict[str, Any]


class CodeChunker:
    """Chunks code files with AST boundary awareness and sliding window fallback."""

    def __init__(self, max_chunk_lines: int = 80, overlap_lines: int = 15):
        self.max_chunk_lines = max_chunk_lines
        self.overlap_lines = overlap_lines

    def chunk_file(self, file_path: str, content: str) -> List[CodeChunkItem]:
        """
        Parses file AST and generates semantic chunks.
        If file has functions/classes, chunks along symbol boundaries.
        Large functions or non-code files are subdivided with sliding window chunking.
        """
        parse_result = code_parser.parse_source_code(file_path, content)
        lines = content.splitlines()
        chunks: List[CodeChunkItem] = []

        if parse_result.symbols:
            for sym in parse_result.symbols:
                sym_lines = sym.end_line - sym.start_line + 1
                if sym_lines <= self.max_chunk_lines:
                    chunks.append(self._create_symbol_chunk(file_path, sym))
                else:
                    # Subdivide large symbol into windowed sub-chunks
                    sub_chunks = self._sliding_window_chunks(
                        file_path=file_path,
                        lines=lines[sym.start_line - 1:sym.end_line],
                        base_line=sym.start_line,
                        symbol_name=sym.name,
                        chunk_type=f"{sym.symbol_type}_part"
                    )
                    chunks.extend(sub_chunks)
        else:
            # File without parsed symbols (configs, shell scripts, markdown, data)
            if len(lines) <= self.max_chunk_lines:
                chunks.append(self._create_module_chunk(file_path, content, 1, len(lines)))
            else:
                chunks.extend(self._sliding_window_chunks(
                    file_path=file_path,
                    lines=lines,
                    base_line=1,
                    symbol_name=file_path.split("/")[-1],
                    chunk_type="block"
                ))

        return chunks

    def _create_symbol_chunk(self, file_path: str, sym: ParsedSymbol) -> CodeChunkItem:
        formatted = (
            f"### Source: {file_path} (Lines {sym.start_line}-{sym.end_line})\n"
            f"### Symbol: {sym.name} | Type: {sym.symbol_type}\n"
            f"```\n{sym.content}\n```"
        )
        return CodeChunkItem(
            symbol_name=sym.name,
            chunk_type=sym.symbol_type,
            start_line=sym.start_line,
            end_line=sym.end_line,
            content=sym.content,
            formatted_context=formatted,
            token_count=sym.token_count,
            metadata={
                "file_path": file_path,
                "signature": sym.signature,
                "docstring": sym.docstring,
                "parent_name": sym.parent_name
            }
        )

    def _create_module_chunk(self, file_path: str, content: str, start_line: int, end_line: int) -> CodeChunkItem:
        filename = file_path.split("/")[-1]
        formatted = f"### Source: {file_path} (Lines {start_line}-{end_line})\n```\n{content}\n```"
        return CodeChunkItem(
            symbol_name=filename,
            chunk_type="module",
            start_line=start_line,
            end_line=end_line,
            content=content,
            formatted_context=formatted,
            token_count=max(len(content) // 4, 1),
            metadata={"file_path": file_path}
        )

    def _sliding_window_chunks(
        self,
        file_path: str,
        lines: List[str],
        base_line: int,
        symbol_name: str,
        chunk_type: str
    ) -> List[CodeChunkItem]:
        chunks: List[CodeChunkItem] = []
        total = len(lines)
        step = max(self.max_chunk_lines - self.overlap_lines, 1)

        for i in range(0, total, step):
            slice_lines = lines[i:i + self.max_chunk_lines]
            if not slice_lines:
                break
            start = base_line + i
            end = base_line + min(i + len(slice_lines) - 1, total - 1)
            content = "\n".join(slice_lines)
            formatted = f"### Source: {file_path} (Lines {start}-{end}) | Symbol: {symbol_name}\n```\n{content}\n```"
            chunks.append(CodeChunkItem(
                symbol_name=f"{symbol_name}[{start}-{end}]",
                chunk_type=chunk_type,
                start_line=start,
                end_line=end,
                content=content,
                formatted_context=formatted,
                token_count=max(len(content) // 4, 1),
                metadata={"file_path": file_path, "symbol_name": symbol_name}
            ))
            if i + self.max_chunk_lines >= total:
                break

        return chunks


code_chunker = CodeChunker()
