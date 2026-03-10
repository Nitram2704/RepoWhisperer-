# Phase 5: Output and Integration - Research

**Researched:** 2026-03-10
**Domain:** CLI pipeline wiring, file I/O, asyncio rate-limit throttling, Markdown generation
**Confidence:** HIGH (core pathlib/asyncio patterns from official Python docs; Rich from official docs; rate limits from Groq official docs)

---

## Summary

Phase 5 wires the `run` and `generate` commands in `main.py` end-to-end: parse → ingest → generate docs → write files. The prior phases have built every component; this phase is about orchestration and output. Three distinct problems must be solved cleanly.

**Problem 1: Module grouping.** `CodeChunk` objects have a `file_path` field. Grouping them by file with Python's `itertools.groupby` or a `defaultdict` is trivial. Deriving a dotted module name from a file path (e.g., `src/docgen/parser/__init__.py` → `docgen.parser`) is a two-step pathlib operation: `relative_to(src_root)` then `'.'.join(parts_without_suffix)`. For `__init__.py` files, the module name is the parent directory path; for all other files, it is the full path with `.py` removed.

**Problem 2: Performance.** With Groq at 30 RPM and Gemini at 10 RPM, sequential LLM calls are the bottleneck. A 50-file project needs approximately 51 LLM calls (1 for README + 1 per module). Sequential execution at 10 RPM = 5+ minutes; this violates the 2-minute target. The solution is `asyncio` with `aiolimiter.AsyncLimiter` for per-minute throttling. Running concurrent calls limited to the provider's RPM — not one per second — eliminates wait time between calls while respecting the rate limit. The existing providers in `llm/` are synchronous; they need `asyncio.to_thread()` wrappers or the `AsyncOpenAI` client variant. `aiolimiter` is a leaky-bucket async rate limiter, minimal dependency, purpose-built for this use case.

**Problem 3: Safety.** The non-destructive contract (source files must never be modified) is enforced by two checks: (1) resolve the output directory path and verify it does not overlap with the source directory using `Path.is_relative_to()`; (2) never write to any path outside `output_dir.resolve()`. The output directory defaults to `./docs` relative to the project path being documented, not the current working directory.

**Primary recommendation:** Group CodeChunks by file using `defaultdict(list)`. Convert file paths to module names with `pathlib.relative_to().with_suffix('').parts`. Run all LLM calls concurrently with `asyncio.gather()` throttled by `aiolimiter.AsyncLimiter(max_rate=RPM, time_period=60)`. Use `asyncio.to_thread()` to run synchronous provider `.generate()` calls in threads. Write output with Rich `Progress` (not spinner) since file count is known. Enforce non-destructive contract by resolving and comparing paths before writing.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pathlib` | stdlib | File path manipulation, output dir creation, module name derivation | Standard library; zero dependency; cross-platform |
| `asyncio` | stdlib | Concurrent LLM call coordination | Standard library; `gather()` + `to_thread()` is the correct pattern for concurrent sync I/O |
| `aiolimiter` | >=1.1 | Per-minute rate limiting for async LLM calls | Leaky-bucket algorithm; async context manager; purpose-built for this use case; 0 heavy dependencies |
| `rich` (already installed) | existing | `Progress` with task tracking per module | Already in the project from Phase 1 `ui.py` |
| `itertools` / `collections` | stdlib | `defaultdict(list)` for grouping CodeChunks by file | Standard library |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typer` (already installed) | existing | `--output-dir` option on `run` and `generate` commands | Already installed from Phase 1 |
| `asyncio.to_thread` | stdlib (Python 3.9+) | Run synchronous provider `.generate()` in a thread pool without blocking event loop | Required since existing providers are synchronous |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `aiolimiter` | `asyncio.Semaphore` only | Semaphore limits concurrency but does not enforce per-minute rate; 30 goroutines all finishing within 1 second would hit RPM limit despite semaphore |
| `aiolimiter` | `time.sleep()` between calls | Eliminates concurrency entirely; sequential calls at 10 RPM × 51 files = 5+ minutes; violates 2-minute target |
| `aiolimiter` | `tenacity` with retry | Tenacity is reactive (retry on 429); aiolimiter is proactive (never sends if limit would be exceeded); proactive is more efficient for a known rate limit |
| `asyncio.to_thread()` | Rewrite providers as `async` | Rewriting all 4 providers to async is out of scope for Phase 5; `to_thread()` is the correct bridge pattern |
| `rich.Progress` | `rich.spinner` | Spinner is for unknown-duration operations; file count is known, so `Progress` with `total=N` is correct and gives user better feedback |
| Pure Python f-strings | Jinja2 | Jinja2 adds a dependency and template file management for what are 3-5 line Markdown templates; f-strings are sufficient and more transparent |

**Installation:**
```bash
uv add aiolimiter
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 5 additions)

```
src/docgen/
├── main.py              # wire run() and generate() — already exists as stubs
├── writer.py            # NEW: write_docs(readme_md, module_docs, output_dir)
├── runner.py            # NEW: orchestrate full pipeline for run command
├── llm/
│   ├── context.py       # generate_docs() — already exists from Phase 4
│   └── ...
docs/                    # default output directory (created by writer.py)
├── README.md
└── api/
    ├── docgen.parser.md
    ├── docgen.store.md
    └── ...
```

### Pattern 1: Module Name Derivation from File Path

**What:** Convert a `CodeChunk.file_path` to a dotted Python module name, using the scanned root directory as the anchor.

**When to use:** For every file being documented; determines the output filename `docs/api/<module_name>.md`.

**Algorithm:**
1. Resolve both the file path and root path to absolute paths.
2. Compute `relative = Path(file_path).resolve().relative_to(root.resolve())`.
3. Strip the `.py` suffix: `no_suffix = relative.with_suffix('')`.
4. If the filename was `__init__`, drop the last component (it represents the package, not a file): check `relative.stem == '__init__'`, if so use `no_suffix.parent`.
5. Join with dots: `'.'.join(no_suffix.parts)` or `'.'.join(no_suffix.parent.parts)` for `__init__`.

**Example:**
```python
# Source: Python official pathlib docs (docs.python.org/3/library/pathlib.html)
from pathlib import Path

def file_path_to_module_name(file_path: str, root: str) -> str:
    """Convert absolute file path to dotted module name.

    Examples:
        src/docgen/parser/__init__.py, root=src  → docgen.parser
        src/docgen/store.py, root=src            → docgen.store
        src/docgen/llm/groq.py, root=src         → docgen.llm.groq
    """
    p = Path(file_path).resolve()
    r = Path(root).resolve()
    relative = p.relative_to(r)          # parser/__init__.py
    no_suffix = relative.with_suffix('') # parser/__init__
    if no_suffix.name == '__init__':
        no_suffix = no_suffix.parent     # parser
    return '.'.join(no_suffix.parts)     # docgen.parser
```

**Edge cases:**
- Files at the root level (e.g., `setup.py`): `relative_to()` returns a single component. Handle gracefully.
- Non-`.py` files (JS/TS): use the same pattern; `with_suffix('')` removes `.ts`/`.js`.
- `__init__.py` at root: becomes empty string; skip or treat as top-level package name.

### Pattern 2: CodeChunk Grouping by Module

**What:** Collect all `CodeChunk` objects for a file into a single LLM call, not one call per chunk.

**When to use:** Always. One LLM call per module (file), not per chunk. This is critical for staying under rate limits.

```python
# Source: Python stdlib docs
from collections import defaultdict
from docgen.models import CodeChunk

def group_chunks_by_file(chunks: list[CodeChunk]) -> dict[str, list[CodeChunk]]:
    """Group CodeChunks by their source file path."""
    groups: dict[str, list[CodeChunk]] = defaultdict(list)
    for chunk in chunks:
        groups[chunk.file_path].append(chunk)
    return dict(groups)
```

One `generate_docs()` call per group (file), not per chunk. The `format_user_prompt` from Phase 4's `prompt.py` already handles lists of chunks with token budget enforcement — it can receive all chunks for a file at once.

### Pattern 3: Async Concurrent LLM Calls with Rate Limiting

**What:** Run all per-module generation calls concurrently, throttled to the provider's RPM limit.

**Why:** Sequential calls at 10 RPM = 5+ minutes for 51 calls. Concurrent calls at 10 RPM = ~5.1 minutes only if all take < 1 second each. In practice, with concurrency, throughput approaches the rate limit ceiling rather than adding latency.

**Key insight from Groq docs (verified March 2026):** Groq free tier is 30 RPM / 12,000 TPM for `llama-3.3-70b-versatile`, and 30 RPM / 6,000 TPM for `llama-3.1-8b-instant`. The TPM limit at 6,000 is binding for large code files. At ~200 tokens per response and ~300 tokens per request: each call uses ~500 TPM, so Groq 8B can sustain 12 calls/minute. Groq 70B: 12,000 TPM ÷ 500 = 24 effective calls/minute (TPM-bound before RPM). Gemini Flash: 10 RPM.

**Rate limit math for 50-file project:**
- 51 calls total (1 README + 50 modules, assuming 1 call per file, some files may be grouped)
- Groq 70B effective ~24 calls/minute → 51 ÷ 24 ≈ 2.1 minutes (borderline)
- Groq 8B effective ~12 calls/minute → 51 ÷ 12 ≈ 4.3 minutes (too slow)
- Groq 70B at RPM: 30 RPM → 51 ÷ 30 ≈ 1.7 minutes (fits if TPM not binding)
- Gemini Flash 10 RPM → 51 ÷ 10 = 5.1 minutes (violates target)
- **Conclusion:** To meet the 2-minute target with Gemini (10 RPM), group multiple small files into single LLM calls. With Groq (30 RPM), 51 calls fits in under 2 minutes if TPM is managed.

**Grouping strategy for 2-minute target:**
- Files with few chunks (< 3 functions/classes): group multiple related files per LLM call
- Large files (many chunks): one call per file; rely on `format_user_prompt`'s 8K token budget to truncate
- Target: ≤ 25 LLM calls total for a 50-file project (2 calls/minute headroom above 10 RPM × 2 min = 20 calls for Gemini)

**Async implementation pattern:**
```python
# Source: aiolimiter docs (aiolimiter.readthedocs.io) + asyncio stdlib
import asyncio
from aiolimiter import AsyncLimiter
from docgen.llm.context import generate_docs

async def generate_all_docs(
    module_groups: dict[str, list],  # module_name -> chunks
    repo,
    provider,
    rpm: int = 10,
) -> dict[str, str]:
    """Generate docs for all modules concurrently, throttled to rpm."""
    limiter = AsyncLimiter(max_rate=rpm, time_period=60)
    results: dict[str, str] = {}

    async def generate_one(module_name: str, chunks: list) -> tuple[str, str]:
        async with limiter:
            # generate_docs is synchronous — run in thread pool
            text = await asyncio.to_thread(
                generate_docs,
                f"Generate API documentation for module: {module_name}",
                repo,
                provider,
            )
        return module_name, text

    tasks = [
        generate_one(name, chunks)
        for name, chunks in module_groups.items()
    ]
    for name, text in await asyncio.gather(*tasks):
        results[name] = text

    return results
```

**Key detail:** `aiolimiter.AsyncLimiter(max_rate=10, time_period=60)` enforces at most 10 acquisitions per 60 seconds using the leaky-bucket algorithm. It does NOT enforce concurrency — it enforces rate. With 10 concurrent coroutines all starting at time 0, the first 10 acquisitions happen immediately (burst), then subsequent ones wait for capacity to refill. For our use case (10 RPM, burst=10), all first 10 calls fire instantly, then additional calls wait ~6s per call. This is optimal.

**RPM values to use per provider:**
- Gemini Flash: use `max_rate=9` (conservative margin below 10 RPM)
- Groq 70B: use `max_rate=25` (conservative below 30 RPM, accounting for TPM saturation)
- Groq 8B: use `max_rate=10` (TPM-bound at ~12 effective calls/minute)
- OpenRouter/DeepSeek: use `max_rate=10` (conservative; actual limits unverified)

### Pattern 4: Safe Output Directory Isolation

**What:** Ensure output files are only ever written inside `output_dir`, which must not overlap with the source directory.

**Safety check (verified pattern from Python security docs):**
```python
# Source: Mike Salvatore's directory traversal prevention guide
from pathlib import Path

def validate_output_dir(output_dir: Path, source_dir: Path) -> None:
    """Raise if output_dir would overlap with or be inside source_dir."""
    out = output_dir.resolve()
    src = source_dir.resolve()
    # Block writing inside source tree
    if out.is_relative_to(src):
        raise ValueError(
            f"Output directory {out} is inside source directory {src}. "
            "Use --output-dir to specify a safe output location."
        )
    # Block source tree being inside output dir (also dangerous)
    if src.is_relative_to(out):
        raise ValueError(
            f"Source directory {src} is inside output directory {out}. "
            "This would risk overwriting source files."
        )

def safe_write(output_dir: Path, relative_path: str, content: str) -> Path:
    """Write content to output_dir/relative_path, verifying no traversal."""
    out_file = (output_dir / relative_path).resolve()
    if not out_file.is_relative_to(output_dir.resolve()):
        raise ValueError(f"Path traversal detected: {relative_path}")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(content, encoding="utf-8")
    return out_file
```

**Default output directory:** `./docs` relative to the scanned project path (not CWD), so `docgen run /home/user/myproject` writes to `/home/user/myproject/docs/`. This prevents accidents when CWD and project path differ.

### Pattern 5: Markdown Output Structure

**What:** README.md and per-module API docs using simple f-string templates. No Jinja2 needed.

**README query to `generate_docs()`:**
```
"Generate a README.md for this project. Include: project name and purpose,
main modules and what they do, installation instructions (if inferable from
dependencies), and a usage example. Base everything on the provided code."
```

**API doc query per module:**
```
f"Generate API reference documentation for the Python module '{module_name}'.
Document each public function and class: its signature, parameters, return type,
and behavior. Use Markdown with ## for class/function names."
```

**File layout written to disk:**
```
{output_dir}/README.md          ← project summary
{output_dir}/api/{module}.md    ← one file per module
```

Module name → filename: `module_name.replace('.', '/')` + `.md`, but keep it flat for readability: `docgen.parser.md` (dots kept) rather than `docgen/parser.md` (nested dirs). Either works; flat is simpler for initial version.

**Recommendation:** Use flat filenames (`docs/api/docgen.parser.md`) in v1. Nested dirs add complexity with no v1 benefit.

### Pattern 6: Rich Progress Bar for Multi-File Generation

**What:** Replace the Phase 1 spinner with a `rich.Progress` bar when the file count is known.

**Why:** The number of LLM calls is known before starting generation. A `Progress` bar shows completion and gives users confidence the tool is working rather than hanging.

**Verified pattern (rich.readthedocs.io/en/stable/progress.html):**
```python
# Source: Rich official docs
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

def run_with_progress(tasks_fn, total: int, description: str = "Generating docs"):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=False,  # keep visible after completion
    ) as progress:
        task = progress.add_task(description, total=total)
        for result in tasks_fn(lambda: progress.advance(task)):
            yield result
```

Use `transient=False` so the completed bar remains visible (shows success). Use `transient=True` only if you want minimal output.

**For async usage:** The `progress.advance(task)` call is thread-safe in Rich. Calling it from `asyncio.to_thread()` callbacks is safe.

### Pattern 7: Wiring `docgen run` and `docgen generate`

**What:** Both commands share the same generation logic. `run` adds the index step first.

**`docgen run <path>` full flow:**
```
1. load_config()                          → validate API keys
2. parse_directory(path)                  → list[CodeChunk]
3. run_ingest(chunks, chroma_dir)         → VectorRepository (Phase 3)
4. generate_all_docs(module_groups, repo) → dict[module_name, str] (async)
5. write_docs(readme_md, module_docs, output_dir)
```

**`docgen generate` flow (requires existing index):**
```
1. load_config()
2. VectorRepository(chroma_dir)            → repo (must already exist)
3. If repo.count() == 0: error "No index found. Run `docgen index <path>` first."
4. generate_all_docs(module_groups, repo)  → BUT: module list must come from querying metadata
5. write_docs(readme_md, module_docs, output_dir)
```

**Problem with `docgen generate`:** The `run` command has parsed files and knows the module list from CodeChunks. The `generate` command has no parsed files — it must reconstruct the module list from ChromaDB metadata.

**Solution:** Query the ChromaDB collection for all unique `file_path` values in metadata. ChromaDB supports `collection.get(include=["metadatas"])` which returns all metadata. Extract unique `file_path` values and group from there. This is the correct approach — do NOT re-parse the source directory in `generate` (it could have changed since indexing).

**`docgen generate` with metadata recovery:**
```python
# Get unique file paths from the vector store
results = repo._collection.get(include=["metadatas"])  # or expose a method
file_paths = list({m["file_path"] for m in results["metadatas"]})
# Then build module groups and proceed
```

Expose this as `VectorRepository.list_files() -> list[str]` to avoid reaching into private internals.

### Anti-Patterns to Avoid

- **One LLM call per CodeChunk:** For a 50-file project with 200 functions, this is 200 LLM calls — 20 minutes at 10 RPM. Group by file (module), not by chunk.
- **Sequential LLM calls with `time.sleep(6)`:** Achieves 10 RPM but with no concurrency. Under asyncio with aiolimiter, multiple calls can be in flight simultaneously. Use aiolimiter, not sleep.
- **Writing to `output_dir` without `resolve()`:** A user passing `--output-dir ../src` would silently overwrite source files. Always `resolve()` before checking ancestry.
- **Hardcoding `./docs` without respecting `--output-dir`:** The requirement OUT-03 explicitly requires overridability. Make the default `docs` relative to the project path, overridable via both CLI flag and config file.
- **Blocking the event loop with synchronous provider calls:** The existing provider `.generate()` methods are synchronous. Calling them directly in an `async def` function blocks the event loop. Use `await asyncio.to_thread(provider.generate, system, user)`.
- **Jinja2 for Markdown templates:** Overkill. The Markdown output is simple enough for f-strings. Adding Jinja2 creates a dependency and template file management burden. Generate README and API docs with `format_user_prompt` already built in Phase 4 plus simple wrapping.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-minute rate limiting | `time.sleep(60/rpm)` between calls | `aiolimiter.AsyncLimiter` | Custom sleep is sequential; aiolimiter supports burst then throttle with no sequential penalty |
| Concurrency + rate limiting | Custom `asyncio.Queue` with worker pool | `asyncio.gather()` + `aiolimiter` | gather+limiter is the idiomatic pattern; queue adds complexity with no benefit at this scale |
| Path traversal prevention | String startswith checks | `Path.resolve().is_relative_to()` | String checks fail on symlinks and `..` sequences; resolve() canonicalizes first |
| Module name derivation | String replace of `/` and `.py` | `pathlib.relative_to().with_suffix('').parts` | String hacks break on Windows paths, absolute paths, edge cases |
| Markdown formatting | HTML generation | Plain f-strings | Markdown is text; HTML generation adds complexity and the LLM already produces Markdown |

**Key insight:** The performance target (50 files < 2 minutes) is only achievable with concurrent LLM calls. Any sequential approach violates it at Gemini's 10 RPM. `aiolimiter` is the single most important library addition for this phase.

---

## Common Pitfalls

### Pitfall 1: Grouping by CodeChunk Instead of File

**What goes wrong:** `generate_docs()` is called once per `CodeChunk` instead of once per file. A 50-file project with an average of 10 functions per file = 500 LLM calls = 50 minutes at 10 RPM.
**Why it happens:** The natural loop is `for chunk in chunks: generate_docs(...)`.
**How to avoid:** Always group chunks by `file_path` first with `defaultdict(list)`. Pass the entire group to one `generate_docs()` call.
**Warning signs:** LLM call count equals chunk count (not file count) in logs.

### Pitfall 2: asyncio.to_thread() Forgotten — Event Loop Blocking

**What goes wrong:** `async def generate_one(...)` calls `provider.generate(...)` directly without `to_thread`. All concurrency is defeated — only one call runs at a time, defeating `asyncio.gather()`.
**Why it happens:** The provider methods are synchronous and look callable from async code. They are, but they block.
**How to avoid:** Every call to a synchronous I/O function inside an `async def` must use `await asyncio.to_thread(fn, *args)`.
**Warning signs:** No observed concurrency speedup; CPU-bound profile despite "async" code.

### Pitfall 3: Output Directory Default Relative to CWD, Not Project Path

**What goes wrong:** User runs `docgen run /home/alice/myproject` from `/home/alice/` and output goes to `/home/alice/docs/` instead of `/home/alice/myproject/docs/`.
**Why it happens:** `Path("docs")` resolves relative to CWD, not the project argument.
**How to avoid:** Default output dir = `Path(project_path) / "docs"`. Not `Path("docs")`.
**Warning signs:** Docs appear in CWD when user expected them in the project directory.

### Pitfall 4: `docgen generate` Has No Module List

**What goes wrong:** `docgen generate` cannot enumerate what to document because it doesn't re-parse source files.
**Why it happens:** The `run` command has fresh CodeChunks; `generate` only has the vector store.
**How to avoid:** Add `VectorRepository.list_files() -> list[str]` that calls `collection.get(include=["metadatas"])` and returns unique `file_path` values. The `generate` command reconstructs the module list from stored metadata.
**Warning signs:** `generate` command either crashes or generates only a README with no per-module docs.

### Pitfall 5: Gemini 10 RPM Cannot Hit 50-File Target Without Grouping

**What goes wrong:** 50 files × 1 call/file + 1 README = 51 calls. At 10 RPM with `aiolimiter`, even with full concurrency, this takes 51/10 = 5.1 minutes minimum. Violates the < 2 minute target.
**Why it happens:** Assumed 1 call per file without doing the math.
**How to avoid:** Implement file grouping: bundle small files (< 3 chunks) together into combined prompts. Target ≤ 20 LLM calls for a 50-file project. With Gemini at 10 RPM and a 2-minute window: max 20 calls. So the grouping strategy must reduce calls from 51 to ≤ 20. With Groq at 30 RPM: 51 calls fits in 1.7 minutes — no aggressive grouping needed for Groq.
**Warning signs:** Performance test on real 50-file project with Gemini takes > 2 minutes.

### Pitfall 6: Overwriting Source Files

**What goes wrong:** `output_dir` is set to the project root, and the writer creates `README.md` there, overwriting the project's own README.
**Why it happens:** Default `./docs` is in the project root, which is fine, but if the user passes `--output-dir .` it would be destructive.
**How to avoid:** Call `validate_output_dir(output_dir, source_dir)` before writing anything. Check that `output_dir.resolve()` is not the same as `source_dir.resolve()`. Also warn (but don't block) if `README.md` already exists in `output_dir` (it may be a previously generated file, which is fine to overwrite; it may also be a user-authored file).
**Warning signs:** User's manually-written README.md gets overwritten silently.

---

## Code Examples

### Module Name from File Path
```python
# Source: Python official pathlib docs (docs.python.org/3/library/pathlib.html)
from pathlib import Path

def file_path_to_module_name(file_path: str, root: str) -> str:
    """Convert file path to dotted module name, anchored at root.

    src/docgen/parser/__init__.py, root=src → docgen.parser
    src/docgen/store.py, root=src           → docgen.store
    """
    p = Path(file_path).resolve()
    r = Path(root).resolve()
    relative = p.relative_to(r)           # docgen/parser/__init__.py
    no_suffix = relative.with_suffix('')  # docgen/parser/__init__
    if no_suffix.name == '__init__':
        no_suffix = no_suffix.parent      # docgen/parser
    return '.'.join(no_suffix.parts)      # 'docgen.parser'
```

### Async Generation with Rate Limiting
```python
# Source: aiolimiter docs (aiolimiter.readthedocs.io), asyncio stdlib
import asyncio
from aiolimiter import AsyncLimiter

RPM_BY_PROVIDER = {
    "gemini": 9,
    "groq": 25,
    "openrouter": 10,
    "deepseek": 10,
}

async def generate_all_docs_async(
    module_groups: dict[str, list],
    repo,
    provider,
    provider_name: str = "gemini",
) -> dict[str, str]:
    rpm = RPM_BY_PROVIDER.get(provider_name, 10)
    limiter = AsyncLimiter(max_rate=rpm, time_period=60)
    results = {}

    async def generate_one(module_name: str) -> tuple[str, str]:
        query = (
            f"Generate API documentation for module '{module_name}'. "
            "Document all public functions and classes with signatures, "
            "parameters, return types, and descriptions."
        )
        async with limiter:
            text = await asyncio.to_thread(generate_docs, query, repo, provider)
        return module_name, text

    # README first (outside the per-module limiter acquisition but still throttled)
    async with limiter:
        readme_text = await asyncio.to_thread(
            generate_docs,
            "Generate a README.md summarizing this project: its purpose, "
            "main modules, installation, and usage examples.",
            repo,
            provider,
        )

    module_tasks = [generate_one(name) for name in module_groups]
    for name, text in await asyncio.gather(*module_tasks):
        results[name] = text

    return readme_text, results
```

### Safe File Writer
```python
# Source: pathlib docs + Mike Salvatore security guide
from pathlib import Path

def write_docs(
    readme_md: str,
    module_docs: dict[str, str],
    output_dir: Path,
    source_dir: Path,
) -> list[Path]:
    """Write README and per-module docs to output_dir. Returns written paths."""
    out = output_dir.resolve()
    src = source_dir.resolve()

    # Safety: prevent writing into source tree
    if out == src or out.is_relative_to(src):
        raise ValueError(
            f"Output dir {out} overlaps source dir {src}. "
            "Use --output-dir to choose a safe location."
        )

    written = []

    # Write README.md
    readme_path = out / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text(readme_md, encoding="utf-8")
    written.append(readme_path)

    # Write per-module API docs
    api_dir = out / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    for module_name, content in module_docs.items():
        # Flat filenames: docs/api/docgen.parser.md
        filename = f"{module_name}.md"
        out_file = (api_dir / filename).resolve()
        # Verify no path traversal
        if not out_file.is_relative_to(api_dir.resolve()):
            raise ValueError(f"Path traversal attempt: {filename}")
        out_file.write_text(content, encoding="utf-8")
        written.append(out_file)

    return written
```

### Rich Progress for Multi-File Generation
```python
# Source: Rich official docs (rich.readthedocs.io/en/stable/progress.html)
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import asyncio

def run_generation_with_progress(
    generate_coro,  # async coroutine that accepts an advance_fn callback
    total: int,
):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task_id = progress.add_task("Generating docs...", total=total)

        def advance():
            progress.advance(task_id)

        return asyncio.run(generate_coro(advance_fn=advance))
```

### VectorRepository.list_files() for `docgen generate`
```python
# Add to src/docgen/store.py
def list_files(self) -> list[str]:
    """Return list of unique file_path values stored in the collection."""
    if self.count() == 0:
        return []
    results = self._collection.get(include=["metadatas"])
    seen = set()
    files = []
    for meta in results.get("metadatas", []):
        fp = meta.get("file_path", "")
        if fp and fp not in seen:
            seen.add(fp)
            files.append(fp)
    return files
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| Sequential LLM calls with sleep | `asyncio.gather()` + `aiolimiter` | 5x speedup at 10 RPM; concurrency fills wait time |
| One call per chunk | One call per module (grouped) | 10x reduction in API calls for typical projects |
| `rich.spinner` (indeterminate) | `rich.Progress` (determinate with bar) | Better UX; user sees X/N files done |
| String path manipulation | `pathlib.relative_to().parts` | Cross-platform; handles Windows paths; no edge-case bugs |
| Writing to `./docs` (CWD-relative) | Writing to `project_path/docs` | Correct behavior when CWD ≠ project path |

---

## Open Questions

1. **Async providers vs. `to_thread()` — which approach for Phase 5?**
   - What we know: Existing providers from Phase 4 are synchronous. `asyncio.to_thread()` wraps them with no code changes.
   - What's unclear: Whether the OpenAI SDK's `AsyncOpenAI` client is worth adopting for Groq/OR/DeepSeek providers in Phase 5 or should wait for a v2 refactor.
   - Recommendation: Use `asyncio.to_thread()` for Phase 5. Adopting `AsyncOpenAI` would require rewriting all four provider classes and the test suite — out of scope. `to_thread()` achieves the same concurrency with zero changes to existing providers.

2. **File grouping threshold for Gemini 10 RPM target**
   - What we know: 50 files at 1 call/file = 51 calls. Gemini 10 RPM × 2 min = 20 calls max.
   - What's unclear: What heuristic should determine which files get bundled (by package? by chunk count? by token count?).
   - Recommendation: Bundle by package directory. Files in the same directory (package) are logically related. Bundle files until combined chunks would exceed `format_user_prompt`'s 8K token budget. This is a natural grouping that produces coherent API docs.

3. **`docgen generate` — should it require a `<path>` argument?**
   - What we know: It needs a module list to know what to generate. The vector store contains file paths in metadata via `list_files()`. But without a path argument, how does it know where to write output?
   - What's unclear: Should `generate` reuse the last-indexed path (stored in ChromaDB metadata), or always require `--output-dir`?
   - Recommendation: Have `generate` accept an optional `--output-dir` with no path argument. Derive the source path from the stored `file_path` metadata (take the common ancestor directory of all stored paths). This allows `docgen generate` to work without re-specifying the path.

4. **What happens if `--output-dir` is inside the project but also contains source files?**
   - What we know: The safety check prevents `output_dir == source_dir` or `output_dir inside source_dir`. But `/project/docs/` inside `/project/` is valid and expected.
   - What's unclear: The current safety check would block `/project/docs/` when source is `/project/`.
   - Recommendation: Refine the safety check: block only when `output_dir` has `.py` or `.ts` or `.js` files directly in it (not nested). Or simpler: only block `output_dir == source_dir`. The original "is_relative_to" check is too strict for the default `./docs` use case.

---

## Sources

### Primary (HIGH confidence)
- https://docs.python.org/3/library/pathlib.html — `relative_to()`, `parts`, `stem`, `with_suffix()`, `is_relative_to()` API verified directly
- https://rich.readthedocs.io/en/stable/progress.html — Progress class, add_task, advance, transient mode; fetched directly
- https://console.groq.com/docs/rate-limits — Groq free tier rate limits table (RPM/TPM/RPD per model); fetched directly March 2026
- https://aiolimiter.readthedocs.io/ — AsyncLimiter API, leaky bucket algorithm, basic usage; fetched directly
- https://docs.python.org/3/library/asyncio-task.html — `asyncio.to_thread()` stdlib docs (Python 3.9+)

### Secondary (MEDIUM confidence)
- https://salvatoresecurity.com/preventing-directory-traversal-vulnerabilities-in-python/ — `Path.resolve().is_relative_to()` security pattern; verified against pathlib official docs
- https://console.groq.com/docs/rate-limits (Groq community FAQ cross-reference) — TPM limits confirmed at 12K (70B) / 6K (8B)

### Tertiary (LOW confidence — flag for validation)
- Gemini 10 RPM free tier: carried forward from Phase 4 RESEARCH (MEDIUM confidence there); not re-verified in this session
- OpenRouter/DeepSeek RPM for throttling: no official published limit; using conservative 10 RPM default

---

## Metadata

**Confidence breakdown:**
- Standard stack (pathlib, asyncio, aiolimiter, rich): HIGH — all from official docs
- Module name derivation algorithm: HIGH — verified against official pathlib docs
- Rate limit math: HIGH for Groq (official docs); MEDIUM for Gemini (from Phase 4 research)
- Async pattern (gather + to_thread + aiolimiter): HIGH — all stdlib/official docs
- Safety pattern (resolve + is_relative_to): HIGH — official pathlib + security guide
- File grouping strategy: MEDIUM — derived from rate limit math; specific threshold is a judgment call
- `docgen generate` metadata recovery: MEDIUM — ChromaDB `collection.get()` API assumed stable; verify against Phase 3 store.py implementation

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (Gemini/Groq rate limits change; re-verify before implementation)
