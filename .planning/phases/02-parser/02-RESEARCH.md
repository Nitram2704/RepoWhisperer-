# Phase 2: Parser - Research

**Researched:** 2026-03-10
**Domain:** AST-based code chunking — Python `ast` stdlib, tree-sitter Python bindings, gitignore file filtering, sensitive file exclusion
**Confidence:** HIGH (tree-sitter API) / HIGH (Python ast) / HIGH (pathspec) / HIGH (sensitive file exclusion)

---

## Summary

Phase 2 builds the parser layer that converts `.py`, `.js`, `.ts`, and `.tsx` source files into `CodeChunk` dataclass instances. The `CodeChunk` dataclass is already fully defined in `src/docgen/models.py` from Phase 1 — this phase populates it. The two parsing backends are fixed decisions: stdlib `ast` for Python (zero extra dependencies) and tree-sitter for JS/TS (the only robust option for JavaScript/TypeScript AST extraction from Python).

The most critical API fact verified in this research: **tree-sitter's Python bindings broke their API in v0.22/v0.23**. The old pattern `Language(tspython.language())` passing an integer no longer works. The current (v0.25.2) pattern is `Language(tspython.language())` where `tspython.language()` returns a capsule object, and `Parser` now takes `language` as a constructor argument: `Parser(PY_LANGUAGE)`. The old `parser.set_language()` call also changed. Code following the v0.21 pattern will fail silently or with confusing errors at runtime.

The gitignore filtering and sensitive file exclusion must be implemented as a single filtering step before any parsing begins. The standard library for gitignore matching is `pathspec` (v1.0.4, Jan 2026), and the sensitive file exclusion is a hardcoded deny-list checked via `pathlib.Path.match()` patterns.

**Primary recommendation:** Install `tree-sitter==0.25.2`, `tree-sitter-javascript==0.25.0`, `tree-sitter-typescript==0.23.2`, and `pathspec==1.0.4`. Implement Python parsing with `ast.NodeVisitor` and JS/TS parsing with `Language` + `Parser` using the v0.22+ API. Apply gitignore + deny-list filtering before instantiating any parser.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ast` (stdlib) | built-in (Python 3.10+) | Python AST parsing | Zero dependencies, ships with Python; `ast.FunctionDef`, `ast.AsyncFunctionDef`, `ast.ClassDef` nodes give exact line ranges and docstrings via `ast.get_docstring()` |
| `tree-sitter` | 0.25.2 | Core tree-sitter parsing engine | Official Python bindings; v0.25.2 is the latest stable (Sep 2025); supports incremental parsing, typed queries, pre-compiled wheels for all major platforms |
| `tree-sitter-javascript` | 0.25.0 | JS grammar (also covers JSX) | Official tree-sitter JS grammar; also parses `.js` and `.jsx`; required for PARSE-02 |
| `tree-sitter-typescript` | 0.23.2 | TypeScript + TSX grammars | Official tree-sitter TS grammar; ships TWO dialects: `typescript` and `tsx`; required for `.ts` and `.tsx` files |
| `pathspec` | 1.0.4 | gitignore-style path matching | Industry standard for git wildmatch pattern matching in Python; v1.0.4 released Jan 27, 2026; supports Python 3.9–3.14; `GitIgnoreSpec` replicates git's exact edge-case behavior |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pathlib` (stdlib) | built-in | File walking and path operations | Always — use `Path.rglob()` to enumerate files, `Path.suffix` for extension checks, `Path.match()` for sensitive file deny-list |
| `ast.get_docstring()` (stdlib) | built-in | Extract docstring from AST node | Called on every `FunctionDef`, `AsyncFunctionDef`, `ClassDef` node to populate `CodeChunk.docstring` |
| `ast.get_source_segment()` (stdlib) | built-in | Extract raw source text for a node | Needed to populate `CodeChunk.content` without manually slicing the source file by line numbers |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `tree-sitter` (Python) | `@typescript-eslint/parser` (Node.js) | Node.js parser requires a Node runtime subprocess — adds complexity, cross-platform fragility, and a runtime dependency not in this stack |
| `tree-sitter` | `esprima`, `acorn`, `chevrotain` | All JS-only (no TypeScript); or require running in Node.js |
| `pathspec` | `gitignore` (PyPI) | `gitignore` package is less maintained; `pathspec` is the de-facto standard used by pip, poetry, and black |
| `pathspec` | Manual `.gitignore` line parsing + `fnmatch` | `fnmatch` doesn't implement git's wildmatch spec (e.g., `**` pattern, negation with `!`, directory-only patterns with trailing `/`) — will produce false negatives on real `.gitignore` files |

**Installation:**
```bash
uv add tree-sitter==0.25.2 tree-sitter-javascript==0.25.0 tree-sitter-typescript==0.23.2 pathspec==1.0.4
```

---

## Architecture Patterns

### Recommended Module Structure

```
src/docgen/
├── models.py           # CodeChunk dataclass (already exists from Phase 1)
├── parser/
│   ├── __init__.py     # Exports: parse_file(), parse_directory()
│   ├── filter.py       # gitignore + sensitive file exclusion (runs FIRST)
│   ├── python_parser.py  # ast-based Python chunker
│   └── js_parser.py    # tree-sitter JS/TS/TSX chunker
```

The `filter.py` module is a gate: every file path passes through it before any language parser sees it. Both the Python and JS parsers are pure functions: `parse_file(path: Path, source: str) -> list[CodeChunk]`. The `parse_directory()` function in `__init__.py` owns the walk + filter + dispatch loop.

### Pattern 1: File Filter (PRIV-01 + PARSE-04)

**What:** A single `should_parse(path: Path, gitignore_spec: PathSpec) -> bool` function applied before any parsing. Returns `False` for gitignored files and for files matching the sensitive-file deny list.
**When to use:** Called on every file discovered during directory walk, before reading the file content.

```python
# Source: https://pypi.org/project/pathspec/ + project PITFALLS.md
import pathspec
from pathlib import Path

# Sensitive file deny-list — checked BEFORE gitignore (fail-safe order)
SENSITIVE_PATTERNS = [
    "**/.env",
    "**/.env.*",
    "**/*.key",
    "**/*.pem",
    "**/*.pfx",
    "**/*.p12",
    "**/credentials*",
    "**/secrets*",
    "**/*_secret*",
    "**/config/production*",
    "**/*.keystore",
]

def build_gitignore_spec(repo_root: Path) -> pathspec.PathSpec:
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])
    lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)

def is_sensitive(path: Path) -> bool:
    """Returns True if file matches any sensitive pattern — must be excluded."""
    for pattern in SENSITIVE_PATTERNS:
        if path.match(pattern):
            return True
    return False

def should_parse(path: Path, repo_root: Path, spec: pathspec.PathSpec) -> bool:
    """Returns True only if file is safe to parse."""
    if is_sensitive(path):
        return False
    relative = path.relative_to(repo_root)
    if spec.match_file(str(relative)):
        return False
    return True
```

**Critical ordering:** Sensitive file check runs first, before gitignore check. A `.env` file not in `.gitignore` is still blocked.

### Pattern 2: Python Parser (PARSE-01 + PARSE-03)

**What:** Use `ast.NodeVisitor` to walk the AST and emit one `CodeChunk` per `FunctionDef`, `AsyncFunctionDef`, and `ClassDef` node.
**When to use:** For every `.py` file that passes the filter.

```python
# Source: https://docs.python.org/3/library/ast.html
import ast
from pathlib import Path
from docgen.models import CodeChunk

class _ChunkVisitor(ast.NodeVisitor):
    def __init__(self, source_lines: list[str], file_path: str, parent: str | None = None):
        self.source_lines = source_lines
        self.file_path = file_path
        self.parent = parent
        self.chunks: list[CodeChunk] = []

    def _extract_content(self, node: ast.AST) -> str:
        # ast nodes have lineno (1-based) and end_lineno
        return "\n".join(self.source_lines[node.lineno - 1 : node.end_lineno])

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.chunks.append(CodeChunk(
            file_path=self.file_path,
            language="python",
            chunk_type="function",
            name=node.name,
            content=self._extract_content(node),
            start_line=node.lineno,
            end_line=node.end_lineno,
            docstring=ast.get_docstring(node),
            parent=self.parent,
        ))
        # Visit nested defs — pass current name as parent
        nested = _ChunkVisitor(self.source_lines, self.file_path, parent=node.name)
        nested.generic_visit(node)
        self.chunks.extend(nested.chunks)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        # Identical to FunctionDef handling
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.chunks.append(CodeChunk(
            file_path=self.file_path,
            language="python",
            chunk_type="class",
            name=node.name,
            content=self._extract_content(node),
            start_line=node.lineno,
            end_line=node.end_lineno,
            docstring=ast.get_docstring(node),
            parent=self.parent,
        ))
        # Visit class methods with class name as parent
        nested = _ChunkVisitor(self.source_lines, self.file_path, parent=node.name)
        nested.generic_visit(node)
        self.chunks.extend(nested.chunks)

def parse_python(path: Path, source: str) -> list[CodeChunk]:
    tree = ast.parse(source, filename=str(path))
    source_lines = source.splitlines()
    visitor = _ChunkVisitor(source_lines, str(path))
    visitor.visit(tree)
    return visitor.chunks
```

**Key detail:** `ast.NodeVisitor.generic_visit(node)` must be called to recurse into children. NOT calling it means nested functions inside classes are silently skipped. The pattern above handles nesting by creating a new `_ChunkVisitor` for each level to track the `parent` field correctly.

### Pattern 3: JS/TS Parser (PARSE-02 + PARSE-03) — Current API (v0.22+)

**What:** Use `tree-sitter` with grammar capsule API (the v0.22+ pattern). One parser instance per language, reused across files.
**When to use:** For `.js`, `.ts`, `.tsx` files.

```python
# Source: https://dev.to/shrsv/diving-into-tree-sitter-parsing-code-with-python-like-a-pro-17h8
# and: https://github.com/tree-sitter/py-tree-sitter/issues/280
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser
from pathlib import Path
from docgen.models import CodeChunk

# Language objects — created ONCE at module level (expensive to instantiate)
JS_LANGUAGE = Language(tsjs.language())
TS_LANGUAGE = Language(tsts.language_typescript())
TSX_LANGUAGE = Language(tsts.language_tsx())

# Parsers — created ONCE at module level
_js_parser = Parser(JS_LANGUAGE)
_ts_parser = Parser(TS_LANGUAGE)
_tsx_parser = Parser(TSX_LANGUAGE)

# tree-sitter query for JS/TS function and class extraction
# Node type names verified against tree-sitter-javascript grammar
_JS_TS_QUERY_SRC = """
(function_declaration
  name: (identifier) @name) @chunk

(function_expression
  name: (identifier) @name) @chunk

(arrow_function) @chunk

(class_declaration
  name: (identifier) @name) @chunk

(method_definition
  name: (property_identifier) @name) @chunk
"""

def parse_js_ts(path: Path, source: str) -> list[CodeChunk]:
    suffix = path.suffix.lower()
    if suffix == ".tsx":
        parser, language, lang_name = _tsx_parser, TSX_LANGUAGE, "typescript"
    elif suffix == ".ts":
        parser, language, lang_name = _ts_parser, TS_LANGUAGE, "typescript"
    else:
        parser, language, lang_name = _js_parser, JS_LANGUAGE, "javascript"

    tree = parser.parse(bytes(source, "utf8"))
    query = language.query(_JS_TS_QUERY_SRC)
    captures = query.captures(tree.root_node)

    chunks: list[CodeChunk] = []
    source_lines = source.splitlines()

    for capture_name, nodes in captures.items():
        if capture_name != "chunk":
            continue
        for node in nodes:
            # Get the name: look for a "name" child capture on the same node
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode("utf8") if name_node else "<anonymous>"
            chunk_type = "function" if "function" in node.type or node.type == "arrow_function" else "class"
            start_line = node.start_point[0] + 1  # tree-sitter is 0-indexed
            end_line = node.end_point[0] + 1
            content = "\n".join(source_lines[start_line - 1 : end_line])
            chunks.append(CodeChunk(
                file_path=str(path),
                language=lang_name,
                chunk_type=chunk_type,
                name=name,
                content=content,
                start_line=start_line,
                end_line=end_line,
                docstring=None,  # JSDoc extraction is out of scope for Phase 2
                parent=None,
            ))
    return chunks
```

**WARNING:** The query `captures()` return type changed in v0.22+. It now returns `dict[str, list[Node]]` — not a list of `(node, name)` tuples. Code using the old `for node, name in captures` tuple-unpacking pattern will fail with a `TypeError`.

### Pattern 4: Directory Walk + Dispatch

```python
from pathlib import Path
from docgen.parser.filter import build_gitignore_spec, should_parse
from docgen.parser.python_parser import parse_python
from docgen.parser.js_parser import parse_js_ts
from docgen.models import CodeChunk

PARSEABLE_EXTENSIONS = {".py", ".js", ".ts", ".tsx"}

def parse_directory(repo_root: Path) -> list[CodeChunk]:
    spec = build_gitignore_spec(repo_root)
    chunks: list[CodeChunk] = []
    excluded: list[Path] = []

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in PARSEABLE_EXTENSIONS:
            continue
        if not should_parse(path, repo_root, spec):
            excluded.append(path)
            continue

        source = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".py":
            chunks.extend(parse_python(path, source))
        else:
            chunks.extend(parse_js_ts(path, source))

    return chunks
```

### Anti-Patterns to Avoid

- **Parsing before filtering:** Never call `ast.parse()` or `parser.parse()` on a file before it passes `should_parse()`. Sensitive file content must never enter memory in parsed form.
- **Re-instantiating `Language()` and `Parser()` per file:** `Language(grammar.language())` involves C extension overhead. Instantiate once at module level.
- **Using the old `parser.set_language(lang)` pattern:** `set_language()` was deprecated in favor of passing `language` to the `Parser()` constructor in v0.22+. The old call may still work in some versions but is not the authoritative API.
- **Old `Language(path_to_so, 'language_name')` pattern:** This used compiled `.so` files and is fully obsolete. The pre-compiled grammar packages (`tree-sitter-javascript` etc.) replace this entirely.
- **`for node, name in captures.items()`:** This is the old API. Current API returns `dict[str, list[Node]]` — iterate `captures.items()` as `for capture_name, nodes in captures.items()`.
- **Assuming `ast.NodeVisitor` recurses automatically:** It does NOT. You must call `self.generic_visit(node)` explicitly to descend into child nodes. Omitting this means only top-level functions are found (nested functions inside classes are silently lost).
- **Using `pathlib.Path.match()` alone for gitignore:** `Path.match()` does not implement git's wildmatch spec (`**` anchoring, negation `!` patterns). Use `pathspec` for `.gitignore` — use `Path.match()` only for the simple deny-list patterns.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| gitignore pattern matching | Custom glob/fnmatch rules | `pathspec.PathSpec.from_lines("gitwildmatch", ...)` | git's wildmatch spec has edge cases: `**` anchoring, trailing `/` for dirs, `!` negation — `fnmatch` misses all of these |
| JS/TS parser | Regex-based function/class extraction | `tree-sitter-javascript` + `tree-sitter-typescript` | Regex fails on: template literals containing function keywords, nested destructuring, multiline arrow functions, method shorthand, computed property names |
| Python docstring extraction | Manual string slicing after `def` | `ast.get_docstring(node)` | Handles all quote styles (`"""`, `'''`, concatenated strings), returns `None` cleanly when absent |
| Tree walking for Python | Manual `ast.walk()` with `isinstance` checks | `ast.NodeVisitor` with `visit_FunctionDef` etc. | `NodeVisitor` provides correct recursion control, handles missing fields gracefully, is the idiomatic pattern |
| JS/TS line number extraction | Counting `\n` characters in source text | `node.start_point[0]` / `node.end_point[0]` | tree-sitter provides O(1) line/column access per node, 0-indexed; add 1 for 1-based line numbers |

**Key insight:** Both parsing backends (stdlib `ast` and tree-sitter) already do the hard work of syntax-aware boundary detection. The implementation is primarily about knowing the right API calls — not about writing parsing logic.

---

## Common Pitfalls

### Pitfall 1: tree-sitter API Version Mismatch (v0.21 vs v0.22+)

**What goes wrong:** Code written for tree-sitter ≤0.21 using `Language(tspython.language())` where `.language()` returned an integer, or `parser.set_language(lang)`, fails with `TypeError` or produces no results on v0.22+.
**Why it happens:** tree-sitter v0.22 changed `language()` to return a capsule object instead of an integer; v0.23 removed `parser.set_language()` as the primary API; v0.23 also changed `query.captures()` return type from `list[tuple[Node, str]]` to `dict[str, list[Node]]`.
**How to avoid:** Pin to `tree-sitter>=0.22` and use only: `Language(grammar.language())`, `Parser(language)`, `query.captures()` returning `dict`.
**Warning signs:** `TypeError: argument 1 must be int, not capsule` on Language instantiation; empty captures dict when nodes should exist.

**Confirmed breaking change source:** https://github.com/tree-sitter/tree-sitter-python/issues/280

### Pitfall 2: ast.NodeVisitor Not Recursing into Nested Nodes

**What goes wrong:** A `visit_ClassDef` method finds the class but not the methods inside it, because `generic_visit(node)` is never called.
**Why it happens:** `NodeVisitor.visit_Foo()` does not automatically recurse. Returning without calling `generic_visit()` terminates traversal at that node.
**How to avoid:** Always call `self.generic_visit(node)` at the end of every `visit_*` method, OR explicitly create a new visitor for nested traversal (the recommended approach for tracking `parent` correctly).
**Warning signs:** `CodeChunk` list has class chunks but no method chunks; success criterion "at least one CodeChunk per function" fails on methods inside classes.

### Pitfall 3: 0-indexed vs 1-indexed Line Numbers

**What goes wrong:** tree-sitter uses 0-indexed line numbers (`node.start_point[0]`). The `CodeChunk` contract uses 1-indexed lines (matching the line numbers users see in editors). Storing tree-sitter raw values off by one.
**Why it happens:** tree-sitter's coordinate system is `(row, column)` with row=0 being the first line. Python `ast` nodes use 1-indexed `lineno`.
**How to avoid:** Always add 1 to tree-sitter line numbers: `start_line = node.start_point[0] + 1`.
**Warning signs:** Tests comparing chunk line numbers to `grep -n` output are always off by one.

### Pitfall 4: Sensitive File Check After Reading File Content

**What goes wrong:** File is opened and read into memory before the sensitive file check runs. The content (including secrets) is in Python memory and could end up in logs, error messages, or downstream processing.
**Why it happens:** Developer checks file extension first (is it `.py`?), reads source, then checks if it's sensitive.
**How to avoid:** Apply `should_parse()` on the `Path` object **before** any `path.read_text()` call. The filter operates on path metadata only — no file content needed.
**Warning signs:** Code flow reads file before calling `is_sensitive()`.

### Pitfall 5: Missing TSX Grammar (using TS grammar for .tsx files)

**What goes wrong:** `.tsx` files parsed with the TypeScript grammar (not the TSX grammar) fail to parse JSX syntax and produce an empty or malformed tree.
**Why it happens:** `tree-sitter-typescript` ships two grammars: `language_typescript()` and `language_tsx()`. They are distinct. JSX syntax is only valid in the TSX grammar.
**How to avoid:** Dispatch on extension: `.ts` → `tsts.language_typescript()`, `.tsx` → `tsts.language_tsx()`.
**Warning signs:** `.tsx` files produce zero chunks; `tree.root_node.has_error` is True on TSX files parsed with TS grammar.

### Pitfall 6: pathspec Relative Path Requirement

**What goes wrong:** `spec.match_file()` receives an absolute path (`/home/user/project/src/foo.py`) but `.gitignore` patterns are relative to the repo root. The match always returns `False` — nothing is filtered.
**Why it happens:** pathspec's `match_file()` expects a path relative to the repo root (same reference frame as `.gitignore`).
**How to avoid:** Always pass `str(path.relative_to(repo_root))` to `spec.match_file()`.
**Warning signs:** Files listed in `.gitignore` still appear in parsed output.

---

## Code Examples

Verified patterns from official sources:

### tree-sitter Language + Parser Initialization (v0.22+ API)

```python
# Source: https://dev.to/shrsv/diving-into-tree-sitter-parsing-code-with-python-like-a-pro-17h8
# Confirmed: tree-sitter 0.25.2 + tree-sitter-python issue #280
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser

JS_LANGUAGE = Language(tsjs.language())          # capsule API, not integer
TS_LANGUAGE = Language(tsts.language_typescript())
TSX_LANGUAGE = Language(tsts.language_tsx())

js_parser = Parser(JS_LANGUAGE)   # language passed to constructor
ts_parser = Parser(TS_LANGUAGE)
tsx_parser = Parser(TSX_LANGUAGE)
```

### tree-sitter Parse and Query

```python
# Source: https://dev.to/shrsv/diving-into-tree-sitter-parsing-code-with-python-like-a-pro-17h8
tree = js_parser.parse(bytes(source_code, "utf8"))

query = JS_LANGUAGE.query("""
  (function_declaration name: (identifier) @name) @chunk
  (class_declaration name: (identifier) @name) @chunk
""")

# v0.22+ API: returns dict[str, list[Node]]
captures = query.captures(tree.root_node)
for capture_name, nodes in captures.items():
    for node in nodes:
        print(node.type, node.start_point, node.end_point)
        # start_point = (row_0indexed, col); add 1 for 1-based line number
```

### Python ast Parse and Walk

```python
# Source: https://docs.python.org/3/library/ast.html
import ast

source = Path("example.py").read_text(encoding="utf-8")
tree = ast.parse(source, filename="example.py")

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        print(node.name, node.lineno, node.end_lineno)
        print(ast.get_docstring(node))  # None if no docstring
    elif isinstance(node, ast.ClassDef):
        print(node.name, node.lineno, node.end_lineno)
```

### pathspec gitignore Matching

```python
# Source: https://pypi.org/project/pathspec/ (v1.0.4, Jan 2026)
import pathspec
from pathlib import Path

repo_root = Path("/path/to/project")
gitignore_text = (repo_root / ".gitignore").read_text(encoding="utf-8")

spec = pathspec.PathSpec.from_lines("gitwildmatch", gitignore_text.splitlines())

# Must use relative path — relative to the repo root
relative = path.relative_to(repo_root)
is_ignored = spec.match_file(str(relative))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Language(grammar.language())` returns int | `Language(grammar.language())` returns capsule | tree-sitter v0.22 (2024) | Must use `Parser(language)` constructor, not `parser.set_language()` |
| `query.captures()` returns `list[tuple[Node, str]]` | `query.captures()` returns `dict[str, list[Node]]` | tree-sitter v0.22 (2024) | Iteration pattern changed completely |
| `Language('path/to/file.so', 'language_name')` | Pre-compiled grammar packages on PyPI | tree-sitter v0.20+ | No C compilation step; `pip install tree-sitter-javascript` is all that's needed |
| Separate `parser.set_language(lang)` call | Language passed to `Parser(language)` constructor | tree-sitter v0.22 (2024) | Single constructor call replaces two-step init |
| `tree-sitter-languages` bundle (grantjenks) | Individual grammar packages per language | Grammar packages now on PyPI | No need for the monolithic bundle; install only what you need |

**Deprecated/outdated:**
- `Language(path, name)` with `.so` file path: Fully obsolete. Use pre-compiled grammar packages.
- `parser.set_language()`: Deprecated in v0.22, removed or unreliable in v0.25.
- `captures()` tuple iteration: Broken since v0.22; use dict iteration.
- `tree-sitter==0.21.x` with old grammar versions: Do not mix versions; the grammar package version must be compatible with the `tree-sitter` core version.

---

## Open Questions

1. **tree-sitter-typescript grammar function for `language_typescript()` and `language_tsx()`**
   - What we know: `tree-sitter-typescript` ships two grammars; the PyPI page confirms this. The function names `language_typescript()` and `language_tsx()` are used in community examples.
   - What's unclear: Exact function names exported by `tree_sitter_typescript` module at v0.23.2 (could be `language()`, `language_typescript()`, `language_tsx()` or another naming scheme).
   - Recommendation: At implementation time, run `import tree_sitter_typescript as tsts; print(dir(tsts))` to confirm exact exported function names before writing parser code. Expect `language_typescript` and `language_tsx` but verify.

2. **Arrow function name extraction**
   - What we know: `arrow_function` nodes in tree-sitter often have no `name` field — they are assigned to a variable via `variable_declarator`.
   - What's unclear: Whether to (a) skip anonymous arrow functions, (b) extract the variable name from the parent `variable_declarator` node, or (c) emit them as `<anonymous>`.
   - Recommendation: For Phase 2, emit as `<anonymous>` or skip if no name can be extracted from parent. Named arrow functions assigned to `const foo = () => {}` should try parent lookup. This decision affects Success Criterion 2 only if the test file uses arrow functions as the primary pattern.

3. **Nested class/method chunk strategy**
   - What we know: The `CodeChunk.parent` field exists. Both Python methods inside classes and JS class methods need `parent` set.
   - What's unclear: Whether Phase 2 should emit BOTH the whole class as a chunk AND each method as a separate chunk (with `parent` set), or only one of these.
   - Recommendation: Emit both — the whole class chunk (for overview embeddings) and each method chunk (for fine-grained retrieval). This matches the Success Criteria ("at least one CodeChunk per function AND class").

---

## Sources

### Primary (HIGH confidence)
- https://pypi.org/project/tree-sitter/ — Latest version 0.25.2, Python >=3.10, MIT license
- https://tree-sitter.github.io/py-tree-sitter/ — Official docs, v0.25.2 API, `Parser`, `Language`, `Query`, `QueryCursor`, `TreeCursor` classes
- https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.Parser.html — `Parser(language, ...)` constructor, `parse(source, encoding='utf8')` signature
- https://pypi.org/project/tree-sitter-javascript/ — v0.25.0, Sep 1 2025, Python >=3.10
- https://pypi.org/project/tree-sitter-typescript/ — v0.23.2, Nov 11 2024, Python >=3.9
- https://pypi.org/project/pathspec/ — v1.0.4, Jan 27 2026, Python 3.9–3.14
- https://docs.python.org/3/library/ast.html — `FunctionDef`, `ClassDef`, `get_docstring()`, `get_source_segment()`, `lineno`, `end_lineno`, `NodeVisitor`

### Secondary (MEDIUM confidence)
- https://dev.to/shrsv/diving-into-tree-sitter-parsing-code-with-python-like-a-pro-17h8 — Current API pattern `Language(tspython.language())` + `Parser(PY_LANGUAGE)`; query captures usage
- https://github.com/tree-sitter/tree-sitter-python/issues/280 — Confirmed v0.23.0 breaking change: `Language()` now accepts capsule not integer; `Parser.parse()` changed; captures return type changed
- https://waylonwalker.com/gitignore-python/ — pathspec `PathSpec.from_lines("gitwildmatch", ...)` + relative path requirement pattern

### Tertiary (LOW confidence)
- Community examples for tree-sitter JS/TS node type names (`function_declaration`, `arrow_function`, `class_declaration`, `method_definition`) — **verify against grammar's `node-types.json`** at https://github.com/tree-sitter/tree-sitter-javascript before relying on these in query strings

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions pulled from PyPI directly (tree-sitter 0.25.2, tree-sitter-javascript 0.25.0, tree-sitter-typescript 0.23.2, pathspec 1.0.4 all verified)
- Architecture: HIGH — filter-first pattern is non-negotiable per PITFALLS.md; module structure follows established Python packaging conventions
- tree-sitter API: HIGH — v0.22+ breaking changes confirmed via official issue tracker; current constructor pattern verified via official docs and community article
- Python ast patterns: HIGH — stdlib, documented API, unchanged across Python 3.10+
- JS/TS node type names: MEDIUM — verified against community sources but not against grammar's `node-types.json` directly; validate at implementation time

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (tree-sitter grammar packages could release; check PyPI before pinning exact versions)
