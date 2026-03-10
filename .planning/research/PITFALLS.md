# Domain Pitfalls

**Domain:** Local RAG-based CLI documentation generator (Python, ChromaDB, Gemini/Groq free tier)
**Researched:** 2026-03-10
**Confidence note:** All findings sourced from training knowledge (cutoff August 2025). No external verification was available during this research session (WebSearch, WebFetch, and Read tools were denied). Mark all claims LOW-to-MEDIUM confidence and validate against current official docs before acting on them.

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or make the tool unusable.

---

### Pitfall 1: Treating Free-Tier Rate Limits as a Network Error

**What goes wrong:**
Gemini free tier (as of mid-2025: ~60 RPM, 1M TPM for Flash; Groq free tier: ~30 RPM, ~14,400 RPD for Llama models) returns HTTP 429 responses. If the pipeline catches 429s under a generic `requests.exceptions.RequestException` or swallows them silently, the tool either crashes mid-run on large repos or — worse — returns empty/truncated documentation with no user-visible error.

**Why it happens:**
Developers prototype on small repos (5-10 files) where rate limits are never hit, then ship to real-world repos (50-200 files) where sequential API calls saturate the RPM limit within the first minute.

**Consequences:**
- Silent data loss: some files get documented, others don't, output looks complete
- Unrecoverable runs: no checkpoint means starting over from scratch
- User distrust: the tool "works sometimes" with no explanation

**Prevention:**
- Implement explicit 429 detection separate from other HTTP errors
- Use exponential backoff with jitter: first retry after 2s, then 4s, 8s, cap at 60s
- Add a `--dry-run` flag that counts estimated API calls before executing
- Batch files into chunks sized to stay under RPM; insert deliberate `time.sleep()` between batches
- Log every API call with timestamp so users can audit what was skipped

**Detection (warning signs):**
- Output markdown files that are shorter than expected
- Log lines showing "retrying..." without eventual success
- Runtime that's suspiciously fast for a large repo (means calls are failing early)

**Phase to address:** Core LLM integration phase (before any large-scale testing)

---

### Pitfall 2: ChromaDB Persistent Client Corruption on Concurrent Access

**What goes wrong:**
ChromaDB's `PersistentClient` (SQLite + on-disk index) does not support multiple simultaneous writers. If a user runs two instances of the CLI in the same project directory, or if the process is killed mid-write (Ctrl+C during embedding), the SQLite WAL file or HNSW index files can be left in a corrupt state. Subsequent runs fail with cryptic errors like `sqlite3.DatabaseError: database disk image is malformed` or HNSW deserialization failures.

**Why it happens:**
CLI tools often get run in parallel by developers (multiple terminal tabs). SQLite's default journal mode does not prevent this. ChromaDB does not implement advisory locking at the application layer.

**Consequences:**
- `.chroma/` directory requires manual deletion and full re-index
- Users lose cached embeddings and must re-embed the entire codebase (costs API quota / time)
- Error messages are ChromaDB-internal and unhelpful to end users

**Prevention:**
- Write a lockfile (e.g., `.chroma/gsd.lock`) on startup using `fcntl.flock` (Unix) or `msvcrt.locking` (Windows), release on exit via `atexit`
- Wrap all ChromaDB writes in try/except, catch `Exception`, and on failure: (1) log the raw error, (2) attempt graceful close, (3) surface a human-readable message: "Index may be corrupted. Run `gsd reset` to rebuild."
- Implement a `gsd reset` subcommand that wipes `.chroma/` and re-indexes
- Validate the ChromaDB collection on startup with a cheap `.count()` call; if it throws, auto-reset

**Detection (warning signs):**
- `sqlite3.DatabaseError` in tracebacks
- `.chroma/` directory size that is 0 bytes or unexpectedly small
- Collection `.count()` returning 0 after a previously successful index

**Phase to address:** Storage layer / ChromaDB integration phase

---

### Pitfall 3: Naively Chunking Source Code by Character Count

**What goes wrong:**
Splitting code files into fixed-size character or token chunks (e.g., every 512 tokens) without respecting syntax boundaries destroys semantic coherence. A chunk may contain half a class definition, or split a function docstring from its signature. The embeddings for these chunks are semantically misleading, and retrieved context passed to the LLM generates wrong or hallucinated documentation.

**Why it happens:**
Character-count chunking is the default example in most RAG tutorials (LangChain, LlamaIndex). It works for prose but is incorrect for code.

**Consequences:**
- LLM receives truncated function signatures without bodies
- Generated docstrings reference parameters that don't exist in the chunk
- README summaries misrepresent what a module does because the retrieved chunk was the tail of an unrelated function

**Prevention:**
- Use AST-aware chunking: for Python use the `ast` module to extract top-level functions and classes as the minimum chunk unit; for JS/TS use `tree-sitter` or `@typescript-eslint/parser`
- Chunk boundary = one complete function, class, or export declaration
- If a single function exceeds the context window, split at the method level (not character level)
- Include the parent class name and module path as metadata on every chunk for retrieval context

**Detection (warning signs):**
- Generated docs reference method names that don't exist in the source
- Embeddings of two syntactically-distinct functions return high cosine similarity
- Chunk inspection shows chunks starting mid-line or ending with unterminated strings

**Phase to address:** Codebase scanning / chunking phase (before embedding)

---

### Pitfall 4: Embedding the Entire Codebase on Every Run

**What goes wrong:**
Without an incremental indexing strategy, every `gsd generate` call re-embeds all files, even unchanged ones. On a 50-file repo with an embedding API (or a local sentence-transformers model), this adds 10-60 seconds of pure overhead and burns free-tier quota unnecessarily.

**Why it happens:**
Incremental indexing requires comparing file state to stored state, which developers defer as "optimization" and then never revisit.

**Consequences:**
- 50-file target (< 2 min) becomes impossible if embedding overhead alone is 60s
- Free-tier embedding API quota exhausted on re-runs
- Users abandon the tool because it feels slow

**Prevention:**
- Store a content hash (SHA-256 of file content, not mtime) alongside each ChromaDB chunk's metadata
- On each run, compute current file hashes, diff against stored hashes, only re-embed changed or new files
- Delete ChromaDB documents for files that no longer exist (stale document cleanup)
- Store hash map in a simple JSON sidecar file (`.chroma/file_hashes.json`) for fast lookup without querying ChromaDB

**Detection (warning signs):**
- Run time does not decrease on second consecutive run with no file changes
- Embedding API call count equals total file count on every run
- ChromaDB collection grows unboundedly on repeated runs (stale documents accumulating)

**Phase to address:** Codebase scanning / incremental indexing phase

---

### Pitfall 5: Leaking Secrets or Private Files into the Vector Store

**What goes wrong:**
The tool scans "all Python and JS/TS files" but codebases routinely contain `.env` files loaded with Python (`python-dotenv`), config files with hardcoded credentials, migration scripts with connection strings, or test fixtures with real API keys. If these are embedded and stored in ChromaDB, the chunks are also passed as context to external LLM APIs (Gemini, Groq), exfiltrating secrets to third-party servers.

**Why it happens:**
Developers assume secret files are in non-code locations, but secrets in Python/JS source are common (especially in solo/personal repos, the exact target audience of this tool).

**Consequences:**
- API keys sent to Google/Groq servers in prompt context
- Secrets embedded in `.chroma/` on-disk index (readable by any process)
- Privacy-first positioning of the tool is violated

**Prevention:**
- Maintain a default exclusion list: `**/.env`, `**/secrets.*`, `**/*_secret*`, `**/credentials*`, `**/*.pem`, `**/*.key`, `**/config/production.*`
- Respect `.gitignore` patterns by default — files ignored by git are almost certainly not meant for documentation
- Before embedding any chunk, run a regex pass for high-entropy strings (potential secrets): flag and skip if detected
- Add a `--exclude` CLI flag for user-specified additional patterns
- Display a summary of excluded files at the end of each run so users can verify

**Detection (warning signs):**
- `.env` or `secrets.py` appearing in the list of indexed files
- Chunks containing strings matching `sk-`, `AIza`, `ghp_`, or other known API key prefixes
- Users reporting that generated docs contain their database passwords

**Phase to address:** Codebase scanning phase (first pass — before any embedding or API calls)

---

## Moderate Pitfalls

---

### Pitfall 6: LLM Context Window Overflow Silently Truncating Input

**What goes wrong:**
Gemini Flash 1.5 has a large context window (1M tokens) but Groq-hosted models (Llama 3 8B/70B) have 8K-32K token limits. Passing all retrieved chunks for a large module without checking total token count causes the API to either silently truncate input or return a 400 error. The generated doc is then based on partial context.

**Prevention:**
- Count tokens before each API call (use `tiktoken` or the model's tokenizer)
- Set a hard cap (e.g., 6,000 tokens for retrieved context on 8K models)
- If retrieved context exceeds the cap, rank chunks by relevance score and drop the lowest-scoring ones
- Log when truncation occurs so the user knows the doc may be incomplete

**Phase to address:** LLM integration phase

---

### Pitfall 7: Hardcoding the Embedding Model Without Versioning

**What goes wrong:**
ChromaDB's default embedding function (`all-MiniLM-L6-v2` via `sentence-transformers`) or a specific API embedding model is used to build the index. If the embedding model changes between tool versions (or the user switches from local to API embeddings), the existing index contains vectors from a different embedding space. Queries against the mismatched index return semantically wrong results without any error.

**Prevention:**
- Store the embedding model name and version in ChromaDB collection metadata
- On startup, compare stored model ID to the configured model ID; if they differ, warn and offer to re-index
- Never silently query a mismatched index

**Phase to address:** Storage layer / ChromaDB integration phase

---

### Pitfall 8: Generating Documentation Without a Determinism Strategy

**What goes wrong:**
LLM outputs are non-deterministic at `temperature > 0`. Every `gsd generate` run produces different markdown even for unchanged code. This makes diffs noisy, breaks CI checks that compare doc output, and makes users distrust the tool ("why did the README change?").

**Prevention:**
- Set `temperature=0` (or the minimum supported value) for all documentation generation calls
- Use `seed` parameter if the API supports it (Groq supports it; Gemini support varies — verify at integration time)
- Cache LLM outputs keyed by (file hash + prompt template hash); reuse cached output when neither changes

**Phase to address:** LLM integration phase

---

### Pitfall 9: CLI Argument Design That Breaks Scriptability

**What goes wrong:**
A CLI tool designed for interactive use (prompts for confirmation, uses color/ANSI output unconditionally, prints progress bars to stdout) breaks when used in scripts, CI, or piped commands. A `gsd generate | tee output.log` silently captures ANSI escape codes as garbage.

**Prevention:**
- Detect TTY: `sys.stdout.isatty()` — use rich/colorama only when true
- All user-facing output (progress, warnings, confirmations) goes to stderr; generated content goes to stdout or specified file
- Add `--quiet` flag to suppress all non-error output
- Never prompt for interactive confirmation in non-TTY mode; default to safe behavior instead
- Exit codes must be meaningful: 0 = success, 1 = partial failure (some files skipped), 2 = fatal error

**Phase to address:** CLI design phase (establish convention early — hard to retrofit)

---

### Pitfall 10: Ignoring Windows Path and Encoding Differences

**What goes wrong:**
Python path handling with forward slashes, `os.path.join` vs `pathlib`, and hardcoded `\n` newlines cause bugs on Windows. ChromaDB document IDs derived from file paths using `/` separators fail to match on Windows where paths use `\`. File reading without explicit `encoding='utf-8'` fails on Windows where the default is `cp1252`.

**Prevention:**
- Use `pathlib.Path` exclusively for all file operations — never string concatenation for paths
- Normalize all paths used as ChromaDB document IDs: `str(path.as_posix())` for cross-platform consistency
- Always open files with `encoding='utf-8', errors='replace'` — source code is almost always UTF-8
- Test on Windows from phase 1, not as a post-ship afterthought (this is a single-developer desktop tool)

**Phase to address:** Codebase scanning phase (establish convention before it spreads)

---

### Pitfall 11: RAG Retrieval Returning Irrelevant Chunks for Documentation

**What goes wrong:**
Standard RAG uses embedding similarity to retrieve context. For documentation generation, the query is often the function/class name itself, and the top-k results may include unrelated functions from other files that happen to use similar vocabulary (e.g., two files both having a `parse()` function). The LLM then generates documentation that conflates the two.

**Prevention:**
- For documentation generation (as opposed to Q&A), prefer direct retrieval over similarity search: retrieve the specific file's chunks by metadata filter (`where={"source_file": target_file}`) rather than by vector similarity
- Use vector similarity only for cross-reference context ("what other modules use this function?")
- Add a `source_file` and `symbol_name` metadata field to every ChromaDB document at index time

**Phase to address:** LLM integration / documentation generation phase

---

## Minor Pitfalls

---

### Pitfall 12: Verbose Stack Traces Exposed to End Users

**What goes wrong:**
Python exceptions with full tracebacks are printed to the terminal. For a CLI tool aimed at individual developers, this is alarming and unhelpful. Users file "bug reports" that are actually expected API failures (e.g., quota exceeded).

**Prevention:**
- Wrap the top-level CLI entrypoint in a try/except that catches known error types and prints friendly messages
- Use `--debug` flag to re-raise with full traceback for developers
- Log full tracebacks to a `~/.gsd/logs/` file silently, mention the log path in error messages

**Phase to address:** CLI design phase

---

### Pitfall 13: ChromaDB Collection Bloat from Deleted Files

**What goes wrong:**
When source files are deleted or renamed, their chunks remain in ChromaDB indefinitely. The collection grows, queries include stale context, and generated docs reference functions that no longer exist.

**Prevention:**
- On each run, compare the set of source files on disk to the set of `source_file` metadata values in ChromaDB
- Delete documents where `source_file` no longer exists on disk
- This is a one-liner with ChromaDB's `.delete(where={"source_file": stale_path})` — implement it from day one

**Phase to address:** Codebase scanning / incremental indexing phase

---

### Pitfall 14: Prompt Template Drift Producing Inconsistent Doc Formats

**What goes wrong:**
As the project evolves, prompt templates get tweaked for individual edge cases (large files, files with no docstrings, test files). Over time, different files get documented with different prompt versions, producing inconsistent markdown structure (some READMEs have an "Examples" section, others don't).

**Prevention:**
- Store prompt templates as versioned files, not inline strings
- Hash the prompt template alongside the file hash in the cache key (see Pitfall 8)
- When the prompt template version changes, invalidate the cache for all affected files and re-generate
- Define a documentation schema (what sections every output must have) and validate LLM output against it

**Phase to address:** LLM integration phase

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Codebase scanning setup | Secrets leaking into index (Pitfall 5) | Implement exclusion list and `.gitignore` respect before writing a single embedding |
| AST parsing for Python/JS | Naively chunking by character count (Pitfall 3) | Use `ast` module from day one; add `tree-sitter` for JS/TS |
| ChromaDB integration | Concurrent access corruption (Pitfall 2) | Implement lockfile and `gsd reset` command in same phase |
| ChromaDB integration | Embedding model version mismatch (Pitfall 7) | Store model ID in collection metadata immediately |
| Incremental indexing | Full re-embed on every run (Pitfall 4) | SHA-256 hash map is 1 day of work, implement before performance testing |
| LLM API integration | Rate limit silent failures (Pitfall 1) | 429 handling must be in place before any multi-file testing |
| LLM API integration | Context window overflow (Pitfall 6) | Token counting wrapper before any large-repo tests |
| LLM API integration | Non-deterministic output (Pitfall 8) | Set temperature=0 from first integration, not as a later "fix" |
| Documentation generation | Wrong retrieval strategy (Pitfall 11) | Use metadata-filtered retrieval for file-level docs, not similarity search |
| CLI design | Windows path bugs (Pitfall 10) | Use `pathlib.Path` from the first line of scanning code |
| CLI design | Scriptability breakage (Pitfall 9) | TTY detection and stderr/stdout split in initial CLI scaffold |
| First release | Stack traces exposed to users (Pitfall 12) | Top-level error handler before any user testing |

---

## Confidence Assessment

| Pitfall Area | Confidence | Basis |
|---|---|---|
| Free-tier rate limit behavior (Pitfall 1) | MEDIUM | Training data on Gemini/Groq limits; limits change frequently — verify against current docs |
| ChromaDB concurrent access (Pitfall 2) | MEDIUM | Training data on SQLite WAL behavior and ChromaDB internals; verify with current ChromaDB changelog |
| AST-aware chunking necessity (Pitfall 3) | HIGH | Well-established in RAG literature; code chunking failure modes are consistent across sources |
| Incremental indexing impact (Pitfall 4) | HIGH | Basic performance math; not source-dependent |
| Secret leakage via file scanning (Pitfall 5) | HIGH | Fundamental security concern, not version-dependent |
| Context window overflow (Pitfall 6) | MEDIUM | Model context limits as of mid-2025; verify current Groq model limits |
| Embedding model versioning (Pitfall 7) | HIGH | Vector space incompatibility is a mathematical property, not version-dependent |
| LLM non-determinism (Pitfall 8) | HIGH | Temperature parameter behavior is well-established |
| CLI scriptability design (Pitfall 9) | HIGH | Unix convention; not version-dependent |
| Windows path encoding (Pitfall 10) | HIGH | Python behavior is well-established |
| Retrieval strategy for docs (Pitfall 11) | HIGH | RAG design principle; not version-dependent |
| Stack trace UX (Pitfall 12) | HIGH | Python CLI best practice; not version-dependent |
| ChromaDB collection bloat (Pitfall 13) | HIGH | ChromaDB delete API has been stable |
| Prompt template drift (Pitfall 14) | HIGH | Software engineering principle; not version-dependent |

---

## Sources

All findings from training knowledge (cutoff August 2025). No external sources were accessible during this session.

**Recommended verification before acting on MEDIUM-confidence claims:**
- Gemini free tier limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Groq rate limits: https://console.groq.com/docs/rate-limits
- ChromaDB persistent client docs: https://docs.trychroma.com/docs/run-chroma/persistent-client
- ChromaDB metadata filtering: https://docs.trychroma.com/docs/querying-collections/metadata-filtering
- ChromaDB changelog for concurrent access fixes: https://github.com/chroma-core/chroma/releases
