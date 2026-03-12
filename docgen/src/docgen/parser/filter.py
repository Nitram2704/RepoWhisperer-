import os
from pathlib import Path

import pathspec

# Hardcoded absolute deny list for sensitive files
SENSITIVE_PATTERNS = [
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "*.pfx",
    "*.p12",
    "credentials*",
    "secrets*",
    "*_secret*",
    "config/production*",
    "*.keystore",
]


def is_sensitive(path: Path) -> bool:
    """Check if the given path matches any sensitive file patterns.
    
    This function checks metadata only, never reading file content.
    """
    for pattern in SENSITIVE_PATTERNS:
        if path.match(pattern):
            return True
    return False


def build_gitignore_spec(repo_root: Path) -> pathspec.PathSpec:
    """Build a pathspec from the repository's .gitignore file if it exists."""
    gitignore_path = repo_root / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return pathspec.PathSpec.from_lines("gitwildmatch", [])


def should_parse(path: Path, repo_root: Path, spec: pathspec.PathSpec) -> bool:
    """Determine if a file is safe to parse.
    
    1. Checks the hardcoded sensitive file deny list (must fail early).
    2. Checks the gitignore pathspec against the relative path.
    
    If it passes both, it is safe to read and parse.
    """
    if is_sensitive(path):
        return False
        
    try:
        relative = path.relative_to(repo_root)
        if spec.match_file(str(relative)):
            return False
    except ValueError:
        # If the path is somehow not relative to the repo_root, deny it
        return False
        
    return True
