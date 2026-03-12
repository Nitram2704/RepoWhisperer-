from pathlib import Path

from docgen.models import CodeChunk
from docgen.parser.filter import build_gitignore_spec, should_parse
from docgen.parser.js_parser import parse_js_ts
from docgen.parser.python_parser import parse_python

PARSEABLE_EXTENSIONS = {".py", ".js", ".ts", ".tsx"}


def parse_file(path: Path, source: str) -> list[CodeChunk]:
    """Dispatch a file to the correct parser based on extension."""
    suffix = path.suffix.lower()
    if suffix == ".py":
        return parse_python(path, source)
    elif suffix in {".js", ".ts", ".tsx"}:
        return parse_js_ts(path, source)
    return []


def parse_directory(repo_root: Path) -> list[CodeChunk]:
    """Walk a directory, filter files, and parse all supported source files.
    
    This is the main entry point for the parser module.
    It enforces the security gate by calling should_parse() BEFORE reading file content.
    """
    spec = build_gitignore_spec(repo_root)
    all_chunks = []
    
    # Use rglob to walk recursively
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
            
        if path.suffix.lower() not in PARSEABLE_EXTENSIONS:
            continue
            
        # SECURITY GATE: Check if sensitive or gitignored BEFORE reading content
        if not should_parse(path, repo_root, spec):
            continue
            
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            chunks = parse_file(path, source)
            all_chunks.extend(chunks)
        except Exception:
            # Skip files that can't be read (e.g. permission issues)
            continue
            
    return all_chunks
