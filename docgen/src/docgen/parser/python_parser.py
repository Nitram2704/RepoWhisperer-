import ast
from pathlib import Path
from typing import Optional

from docgen.models import CodeChunk


class _ChunkVisitor(ast.NodeVisitor):
    """AST Visitor that extracts functions and classes into CodeChunks."""
    
    def __init__(self, source_lines: list[str], file_path: str, parent: Optional[str] = None):
        self.source_lines = source_lines
        self.file_path = file_path
        self.parent = parent
        self.chunks: list[CodeChunk] = []

    def _extract_content(self, node: ast.AST) -> str:
        # AST lines are 1-indexed, slice is 0-indexed
        # Extract precisely from start to end line
        start_idx = node.lineno - 1
        end_idx = node.end_lineno
        return "\n".join(self.source_lines[start_idx:end_idx])

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        chunk = CodeChunk(
            file_path=self.file_path,
            language="python",
            chunk_type="function",
            name=node.name,
            content=self._extract_content(node),
            start_line=node.lineno,
            end_line=node.end_lineno,
            docstring=ast.get_docstring(node),
            parent=self.parent,
        )
        self.chunks.append(chunk)

        # Traverse nested definitions (inner functions)
        nested = _ChunkVisitor(self.source_lines, self.file_path, parent=node.name)
        nested.generic_visit(node)
        self.chunks.extend(nested.chunks)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        # Async functions behave exactly the same for our extraction needs
        chunk = CodeChunk(
            file_path=self.file_path,
            language="python",
            chunk_type="function",
            name=node.name,
            content=self._extract_content(node),
            start_line=node.lineno,
            end_line=node.end_lineno,
            docstring=ast.get_docstring(node),
            parent=self.parent,
        )
        self.chunks.append(chunk)

        nested = _ChunkVisitor(self.source_lines, self.file_path, parent=node.name)
        nested.generic_visit(node)
        self.chunks.extend(nested.chunks)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        chunk = CodeChunk(
            file_path=self.file_path,
            language="python",
            chunk_type="class",
            name=node.name,
            content=self._extract_content(node),
            start_line=node.lineno,
            end_line=node.end_lineno,
            docstring=ast.get_docstring(node),
            parent=self.parent,
        )
        self.chunks.append(chunk)

        # Traverse methods inside the class
        nested = _ChunkVisitor(self.source_lines, self.file_path, parent=node.name)
        nested.generic_visit(node)
        self.chunks.extend(nested.chunks)


def parse_python(path: Path, source: str) -> list[CodeChunk]:
    """Parse a Python source file and extract functions and classes as CodeChunks."""
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        # If the file has a syntax error, we can't parse it
        return []

    source_lines = source.splitlines()
    visitor = _ChunkVisitor(source_lines, str(path))
    visitor.visit(tree)
    
    return visitor.chunks
