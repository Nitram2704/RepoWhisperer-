# Phase 1: Foundation - Research

**Researched:** 2026-03-10
**Domain:** Python CLI bootstrapping — Typer, Rich, uv, secure config loading
**Confidence:** HIGH

---

## Summary

Phase 1 establishes the skeleton of the `docgen` CLI: a working multi-command entry point, secure API key loading, and a visible progress indicator. The stack is fully decided (Typer + Rich + uv), so no alternatives need evaluating. All three libraries are mature and actively maintained as of early 2026.

The canonical pattern for this stack is: one `typer.Typer()` app in `main.py`, each command (`run`, `index`, `generate`) as a separate `@app.command()` decorated function, Rich's `Progress` with `SpinnerColumn` for indeterminate operations, and a dedicated `config.py` module that reads secrets from the environment and raises a clean `typer.Exit(code=1)` on missing keys — never logging the key value.

The single biggest risk in this phase is the `[project.scripts]` entry point requiring a build-system block in `pyproject.toml` and an explicit `uv tool install . -e` (or `uv pip install -e .`) step. Forgetting that step causes `docgen` not to exist as a shell command even after `uv sync`.

**Primary recommendation:** Bootstrap with `uv init --app --package docgen`, wire `[project.scripts]`, install with `uv tool install . -e`, then build commands one file at a time.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typer | 0.24.1 (Feb 2026) | CLI framework — commands, args, help, errors | Type-hint-driven, auto `--help`, built-in Rich integration |
| rich | bundled via typer | Styled terminal output, progress bars, spinners | De-facto Python terminal UI; Typer depends on it directly |
| python-dotenv | latest stable | Load `.env` file into environment at startup | Industry-standard secret injection for local dev |
| uv | latest stable | Package manager, venv, lockfile, project scaffold | Decided stack; replaces pip+venv entirely |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich.console.Console | (via rich) | Styled stderr output for errors | Every user-facing error message |
| rich.progress.Progress | (via rich) | Indeterminate spinner for long ops | Any operation > 1 second |
| os (stdlib) | — | Read environment variables after dotenv load | Always prefer over direct os.environ[] access |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| typer | click (raw) | Click is Typer's foundation; Typer adds type hints, auto-help, Rich — no reason to drop down |
| python-dotenv | pydantic-settings | pydantic-settings is better for large apps; overkill for Phase 1 stubs |
| Rich Progress | yaspin, alive-progress | Rich is already a transitive dependency; adding another spinner library is waste |

**Installation:**
```bash
uv init --app --package docgen
uv add typer python-dotenv
```

---

## Architecture Patterns

### Recommended Project Structure

```
docgen/
├── pyproject.toml          # [project.scripts] docgen = "docgen.main:app"
├── src/
│   └── docgen/
│       ├── __init__.py
│       ├── main.py         # typer.Typer() app, @app.command() for run/index/generate
│       ├── config.py       # load_dotenv(), os.getenv(), fail-fast on missing keys
│       └── ui.py           # Rich Console, spinner/progress helpers
```

`uv init --app --package` scaffolds `src/` layout by default. Use it.

### Pattern 1: Multi-Command Typer App

**What:** One root `Typer()` instance with three `@app.command()` functions. Each command is a stub in Phase 1 but has the right signature.
**When to use:** Whenever the CLI has multiple distinct top-level verbs.

```python
# Source: https://typer.tiangolo.com/tutorial/commands/
import typer

app = typer.Typer(help="Generate documentation for your codebase.")

@app.command()
def run(path: str = typer.Argument(..., help="Path to source directory")):
    """Scan, embed, and generate docs in one step."""
    ...

@app.command()
def index(path: str = typer.Argument(..., help="Path to source directory")):
    """Build the vector index without generating docs."""
    ...

@app.command()
def generate():
    """Generate docs from an existing index."""
    ...

if __name__ == "__main__":
    app()
```

### Pattern 2: Secure Config Loading (Fail-Fast)

**What:** Centralised `config.py` that loads `.env` once, reads API key, and raises a clean error if absent. Never logs the key.
**When to use:** At the top of any command that needs the API key.

```python
# config.py
import os
from dotenv import load_dotenv
from rich.console import Console

error_console = Console(stderr=True, style="bold red")

def load_config() -> dict:
    load_dotenv()  # no-op if .env absent; env vars from shell still work
    api_key = os.getenv("DOCGEN_API_KEY")
    if not api_key:
        error_console.print(
            "[bold red]Error:[/bold red] DOCGEN_API_KEY is not set.\n"
            "Set it in your environment or in a .env file."
        )
        raise typer.Exit(code=1)
    return {"api_key": api_key}
```

Key rules:
- `load_dotenv()` must be called before `os.getenv()`.
- Use `os.getenv()` (returns `None` on miss) not `os.environ[]` (raises `KeyError`).
- Never `print(api_key)` or `console.log(api_key)` anywhere.
- `.env` must be in `.gitignore`.

### Pattern 3: Indeterminate Spinner for Unknown Duration

**What:** Rich `Progress` with `SpinnerColumn` and `total=None` shows a pulsing animation when the operation duration is unknown.
**When to use:** Any operation > 1 second where total work units are unknown (indexing, embedding, API calls).

```python
# Source: https://rich.readthedocs.io/en/stable/progress.html
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    transient=True,    # clears the spinner from terminal on completion
) as progress:
    task = progress.add_task("Indexing files...", total=None)
    do_work()
    # spinner runs until context exits
```

For operations with a known total (e.g., iterating a file list):

```python
from rich.progress import track

for file in track(files, description="Processing files..."):
    process(file)
```

### Pattern 4: pyproject.toml Entry Point

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "docgen"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "typer>=0.24.1",
    "python-dotenv>=1.0",
]

[project.scripts]
docgen = "docgen.main:app"
```

Install for local dev:
```bash
uv tool install . -e       # makes `docgen` available in PATH
# OR for venv-scoped use:
uv pip install -e .
```

### Anti-Patterns to Avoid

- **Scattering `os.getenv()` in every command:** Call `load_config()` once per command entrypoint; never read raw env vars ad hoc.
- **Using `typer.echo()` for errors:** Use `Console(stderr=True)` so errors go to stderr and don't pollute stdout pipelines.
- **Calling `app.add_typer()`  for flat three-command CLIs:** `add_typer` is for nested command groups. Three flat commands on one `Typer()` is the right model here.
- **Using `pretty_exceptions_show_locals=True` in production:** It will print the API key value if it appears in a local variable during a traceback.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| `--help` text | Manual argument parsing / help strings | `typer` + docstrings | Typer auto-generates help from function signatures and docstrings |
| Progress spinner | `print(".", end="")` polling loop | `rich.progress.Progress` | Thread-safe, handles terminal resize, transient cleanup |
| .env file parsing | Manual `open(".env")` + split | `python-dotenv` | Handles quoting, comments, multi-line values, shell override precedence |
| Styled error output | `print(f"\033[31mError\033[0m ...")` | `rich.console.Console(stderr=True)` | Correct ANSI escape handling, Windows support, NO_COLOR env var |

**Key insight:** Every problem in this phase has an off-the-shelf solution in the already-committed stack. Writing any custom version wastes time and misses edge cases.

---

## Common Pitfalls

### Pitfall 1: `docgen` Command Not Found After `uv sync`

**What goes wrong:** Developer runs `uv sync`, then types `docgen` — shell reports command not found.
**Why it happens:** `uv sync` installs dependencies but does NOT install the project itself as a package. `[project.scripts]` entry points only activate after `uv pip install -e .` or `uv tool install . -e`.
**How to avoid:** Include `uv pip install -e .` as a one-time setup step in the project README (or Makefile target). Verify with `which docgen`.
**Warning signs:** `which docgen` returns nothing; `uv run docgen` works but bare `docgen` does not.

### Pitfall 2: API Key Leaking into Logs or Tracebacks

**What goes wrong:** An exception occurs while the API key is in a local variable scope. `pretty_exceptions_show_locals=True` (or a debug print) exposes the value.
**Why it happens:** Typer's default in older versions was to show locals; default changed in 0.23.0. Developer enabling debug mode re-enables it.
**How to avoid:** Never store the raw key outside `config.py`. Delete or overwrite it after passing to the LLM client constructor. Keep `pretty_exceptions_show_locals` at its default (`False`).
**Warning signs:** Running `TYPER_STANDARD_TRACEBACK=1 docgen run .` shows API key in output.

### Pitfall 3: Multiple Commands, Missing `invoke_without_command`

**What goes wrong:** Running `docgen` (no subcommand) prints `Missing command.` instead of `--help`.
**Why it happens:** Multi-command Typer apps require a subcommand by default.
**How to avoid:** Either add `invoke_without_command=True` plus a callback that prints help, or accept the default behavior since `docgen --help` still works.
**Warning signs:** `docgen` alone exits with non-zero and `Missing command.` instead of a help screen.

### Pitfall 4: `.env` Committed to Git

**What goes wrong:** API key is pushed to remote repository.
**Why it happens:** Developer forgets to add `.env` to `.gitignore` before `git add .`.
**How to avoid:** `uv init` generates a `.gitignore` — verify `.env` is in it before the first commit. Use `git secrets` or a pre-commit hook as a safety net.
**Warning signs:** `git status` shows `.env` as untracked (not ignored).

### Pitfall 5: `typer.progressbar()` Instead of Rich Progress

**What goes wrong:** Developer uses `typer.progressbar()` for spinner, but it requires a known total and shows a bar — not a spinner for unknown-duration tasks.
**Why it happens:** `typer.progressbar()` appears in Typer docs as the "built-in" option.
**How to avoid:** Use `rich.progress.Progress` with `total=None` for indeterminate operations. `typer.progressbar()` is a fallback for simple iteration over a known-length sequence.

---

## Code Examples

Verified patterns from official sources:

### Complete main.py Skeleton

```python
# Source: https://typer.tiangolo.com/tutorial/commands/
import typer
from docgen.config import load_config
from docgen.ui import spinner

app = typer.Typer(
    help="Generate documentation for your codebase.",
    pretty_exceptions_show_locals=False,  # never expose secrets in tracebacks
)

@app.command()
def run(path: str = typer.Argument(..., help="Path to source directory")):
    """Scan, embed, and generate docs in one step."""
    cfg = load_config()
    with spinner("Running full pipeline..."):
        pass  # Phase 1 stub

@app.command()
def index(path: str = typer.Argument(..., help="Path to source directory")):
    """Build the vector index without generating docs."""
    with spinner("Indexing..."):
        pass  # Phase 1 stub

@app.command()
def generate():
    """Generate docs from an existing index."""
    with spinner("Generating..."):
        pass  # Phase 1 stub

if __name__ == "__main__":
    app()
```

### ui.py Spinner Helper

```python
# Source: https://rich.readthedocs.io/en/stable/progress.html
from contextlib import contextmanager
from rich.progress import Progress, SpinnerColumn, TextColumn

@contextmanager
def spinner(description: str):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description, total=None)
        yield
```

### config.py Clean Error on Missing Key

```python
import os
import typer
from dotenv import load_dotenv
from rich.console import Console

_error = Console(stderr=True)

def load_config() -> dict:
    load_dotenv()
    api_key = os.getenv("DOCGEN_API_KEY")
    if not api_key:
        _error.print(
            "[bold red]Error:[/bold red] DOCGEN_API_KEY environment variable is not set.\n"
            "Add it to your shell environment or create a .env file with:\n\n"
            "  DOCGEN_API_KEY=your-key-here"
        )
        raise typer.Exit(code=1)
    return {"api_key": api_key}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `argparse` / `click` raw | `typer` with type hints | 2019+ (typer), mainstream 2023 | No manual `add_argument()` calls; type hints drive everything |
| `pip` + `setup.py` | `uv` + `pyproject.toml` | 2024-2025 (uv mainstream) | Single tool for venv, deps, lock, scripts |
| `pretty_exceptions_show_locals=True` default | `False` default (since Typer 0.23.0) | Typer 0.23.0 (2025) | Safe by default; enabling it in dev is explicit opt-in |
| Manual spinner loops | `rich.progress.Progress` with `total=None` | Rich ~12.x | Animated, thread-safe, no custom code |

**Deprecated/outdated:**
- `setup.py` + `setup.cfg`: Replaced by `pyproject.toml`. Do not use.
- `typer.progressbar()` for spinner use cases: Only use for known-length iteration; use Rich `Progress` for everything else.

---

## Open Questions

1. **Which environment variable name for the API key?**
   - What we know: Multiple LLM providers are planned (Gemini, Groq, OpenRouter, DeepSeek); each has its own key name.
   - What's unclear: Does `docgen` use a single `DOCGEN_API_KEY` that gets routed, or one var per provider?
   - Recommendation: Use a single `DOCGEN_API_KEY` in Phase 1 (stubs don't need a real key). Defer per-provider naming to the LLM integration phase.

2. **Config file format (beyond `.env`)?**
   - What we know: PRIV-02 says "env var or config file". A `.env` file satisfies this for Phase 1.
   - What's unclear: Whether a `~/.config/docgen/config.toml` or similar is also needed.
   - Recommendation: Implement `.env` only in Phase 1. Config file support is a later enhancement.

3. **`docgen --help` shows subcommand list vs. requires subcommand?**
   - What we know: Default multi-command Typer requires a subcommand; without one it prints `Missing command.`
   - What's unclear: Success Criterion 1 says `docgen --help` should work — that already works by default.
   - Recommendation: Verify `docgen --help` shows `run`, `index`, `generate` in output. No extra callback needed.

---

## Sources

### Primary (HIGH confidence)
- https://typer.tiangolo.com/ — Command structure, subcommands, `@app.command()`, `typer.Exit`, `typer.Abort`, `pretty_exceptions_*`, `typer.progressbar()`
- https://typer.tiangolo.com/tutorial/exceptions/ — Exception handling, `pretty_exceptions_show_locals`, security defaults
- https://typer.tiangolo.com/tutorial/terminating/ — `typer.Exit(code=1)`, `typer.Abort()`
- https://typer.tiangolo.com/tutorial/progressbar/ — Built-in progressbar vs Rich recommendation
- https://rich.readthedocs.io/en/stable/progress.html — `Progress`, `SpinnerColumn`, `track()`, `total=None` indeterminate
- https://rich.readthedocs.io/en/stable/console.html — `Console(stderr=True)`, markup, styled errors
- https://pypi.org/project/typer/ — Confirmed latest version: 0.24.1 (Feb 21, 2026), Python >=3.10
- https://docs.astral.sh/uv/concepts/projects/config/#entry-points — `[project.scripts]` syntax
- https://mathspp.com/blog/using-uv-to-build-and-install-python-cli-apps — `uv tool install . -e`, pitfall around config vs code changes

### Secondary (MEDIUM confidence)
- https://pypi.org/project/typer/ — Version 0.21.0 (Jan 6, 2026) / 0.20.x confirmed active maintenance in 2025-2026
- WebSearch: Typer 2026 best practices — `app.add_typer()` for nested groups, flat commands use `@app.command()` directly, `typer.Exit(code=1)` pattern
- WebSearch: python-dotenv + fail-fast pattern — `load_dotenv()` before `os.getenv()`, `os.getenv()` preferred over `os.environ[]`

### Tertiary (LOW confidence)
- None — all critical claims verified with primary sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions pulled from PyPI directly, library docs fetched
- Architecture: HIGH — patterns from official Typer and Rich docs with code examples
- Pitfalls: HIGH (Pitfall 1, 2, 4) / MEDIUM (Pitfall 3, 5) — 1, 2, 4 from official docs; 3, 5 from docs + community patterns

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable libraries; recheck if Typer releases 0.25+)
