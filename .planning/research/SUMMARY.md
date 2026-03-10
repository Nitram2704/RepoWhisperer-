# Project Research Summary

**Project:** CLI Documentation Generator (RAG-based)
**Domain:** Local-first AI documentation generation CLI (Python, RAG pipeline, free-tier LLMs)
**Researched:** 2026-03-10
**Confidence:** MEDIUM

## Executive Summary

DocGen CLI is a local, privacy-first command-line tool that generates Markdown documentation from Python and JS/TS codebases using a RAG pipeline backed by ChromaDB and free-tier LLMs (Gemini Flash, Groq/Llama 3). This is a well-understood domain architecturally: the core pipeline follows the established ingest-then-retrieve-then-generate pattern used in RAG systems, and the individual components (Typer CLI, ChromaDB, sentence-transformers, Jinja2) are all mature, well-documented libraries. The novel aspect is applying RAG specifically to documentation generation rather than Q&A, which changes the retrieval strategy from similarity-based to metadata-filtered retrieval at the file-doc generation step.

The recommended approach is a strict pipeline architecture with six discrete stages (Parser, Chunker, Embedder, VectorDB, LLM Client, Writer), each communicating only through well-defined data contracts (`CodeChunk`, `IndexableChunk`). This separation is not optional: it is what makes the system testable (mock any single stage), maintainable (prompt changes don't touch parsing code), and performant (batch embedding becomes possible when the Embedder receives a full list rather than chunks one-by-one). LangChain can be used for its splitters and loaders but a lean alternative — direct ChromaDB + sentence-transformers + a 50-line retrieval loop — covers the MVP adequately and avoids ~50 transitive dependencies.

The top risks are operational, not architectural. Free-tier LLM rate limits (Gemini ~60 RPM, Groq ~30 RPM) will be the binding constraint on a 50-file repo and must be addressed with explicit 429 handling and exponential backoff before any multi-file testing begins. Naive character-count chunking destroys RAG quality for code and must be replaced by AST-aware chunking from day one using Python's `ast` module and tree-sitter for JS/TS. Secret file leakage into the vector store is the primary security concern and must be addressed before any embedding or API call is made. All other risks are mitigable with straightforward engineering patterns documented in PITFALLS.md.

---

## Key Findings

### Recommended Stack

The stack is centered on Python 3.11+ with Typer+Rich for CLI, ChromaDB for the local vector store, sentence-transformers (`all-MiniLM-L6-v2`) for local embeddings, and Jinja2 for output templating. LLM access uses the official `google-generativeai` and `groq` SDKs targeting free-tier models. uv replaces pip+virtualenv for dependency management. The stack is deliberately local-first: no component requires an external service to be running, and no source code leaves the machine during the embedding phase.

LangChain is listed as optional. If the roadmap stays single-domain (Python/JS/TS docs only, one retrieval strategy), a direct ChromaDB+sentence-transformers implementation is preferred to avoid LangChain's dependency weight and version instability. If future phases add multiple vector backends or retrieval strategies, LangChain provides the abstraction layer for that.

**Core technologies:**
- **Python 3.11+**: Runtime — 10-60% speed gains over 3.10; all target libraries support it
- **Typer + Rich**: CLI framework — type-hint-based argument parsing with native progress bar/color support
- **ChromaDB ~0.5.x**: Local vector database — disk-persistent, zero-server, pip-installable; only viable local-first option
- **sentence-transformers ~2.7.x**: Local embedding — `all-MiniLM-L6-v2` runs on CPU in <60s for a 50-file repo; no code leaves the machine
- **google-generativeai + groq SDKs**: LLM API clients — both have free tiers sufficient for the target scale
- **tree-sitter ~0.22.x**: AST-aware code parsing — required for semantic chunking; `ast` stdlib covers Python as an MVP fallback
- **Jinja2 ~3.1.x**: Output templating — separates prompt engineering from Markdown structure
- **uv ~0.4.x**: Package manager — 10-100x faster than pip; the 2025 community default for new Python projects
- **pytest 8.x + pytest-mock**: Testing — `typer.testing.CliRunner` enables end-to-end CLI tests without subprocess overhead

**Critical version note:** ChromaDB 0.5.x introduced a breaking `Client` → `PersistentClient` API change. Do not assume 0.4.x code applies. Verify the current version on PyPI before pinning.

### Expected Features

The feature landscape is well-defined. The core competitive position is: "generates useful docs from poorly-commented code, entirely locally, for free" — which neither the Sphinx/JSDoc family (requires good comments) nor Mintlify/Swimm (requires cloud and payment) delivers.

**Must have (table stakes):**
- CLI entry point with `--path` and `--provider` flags — the entire value prop is one-command UX
- Multi-file repository scan with sensitive file exclusion — must run before any embedding or API call
- Python + JS/TS AST parsing — polyglot repos are the norm for target users
- README.md generation — absence is a dealbreaker; most-requested output from any doc tool
- Per-module/per-file API docs in `/docs` — expected by users of Sphinx, JSDoc, TypeDoc
- Structured Markdown output (headers, code blocks, parameter tables) — not raw prose blobs
- Progress feedback — silent 2-minute runs feel broken; users kill the process
- Idempotent output — never modify source files; output only to `/docs`
- `.docgenignore` support — expected by users of other tools

**Should have (differentiators):**
- RAG-based context selection — avoids sending full codebase to LLM; protects free-tier quota and privacy
- Privacy-first local execution — enforced by architecture, not just marketing
- Free-tier LLM routing with provider fallback — if Gemini hits rate limit, retry with Groq
- Incremental re-generation (hash-based) — skip unchanged files; reduces LLM calls dramatically; critical for performance
- Verbose/debug mode (`--verbose`) — shows retrieved chunks and prompt; essential for power users
- Configurable output templates (Jinja2) — let users customize README structure

**Defer to v2+:**
- Cross-file relationship summary (import graph) — high complexity; validate demand first
- Doc quality scoring / stale detection — users must experience the tool before caring about staleness
- Real-time watch mode — significant complexity; single-run is sufficient for v1
- Provider fallback chain — adds reliability but is not a day-one need

**Anti-features (never build):**
- Inline comment injection into source files — violates non-destructive contract; destroys user trust
- Web UI, cloud sync, hosted docs — contradicts CLI/local-first positioning
- Languages beyond Python/JS/TS in v1 — multiplies maintenance; design parser interface to be extensible instead

### Architecture Approach

The architecture is a strict linear pipeline with an Orchestrator coordinating six discrete stages. The key design decision is the `CodeChunk` dataclass as the central data contract defined before any other component — every stage from Parser onward communicates in `CodeChunk` or `IndexableChunk` terms, preventing string-passing across boundaries. The VectorDB is always accessed through a thin `VectorRepository` interface; no component imports `chromadb` directly. This is the main seam for testing and for future backend swaps.

The pipeline splits naturally into two sub-pipelines: **Ingest** (Parser → Chunker → Embedder → VectorDB) and **Generate** (query → Embedder → VectorDB → LLM Client → Writer). The CLI exposes three commands — `index`, `generate`, and `run` (full pipeline) — even if only `run` is wired in the MVP, because retrofitting this structure later is expensive.

**Major components:**
1. **CLI Entry / Orchestrator** — parses args, builds Config, coordinates pipeline; Config is the only object that crosses all boundaries
2. **Parser** — walks file tree; extracts functions/classes/modules with signatures and docstrings using Python `ast` and tree-sitter for JS/TS
3. **Chunker** — normalises `CodeChunk[]`, enforces token limits, assigns deterministic IDs; produces `IndexableChunk[]` for embedding
4. **Embedder** — converts text to float vectors in batches (default batch_size=32); accepts `list[str]`, never one-at-a-time
5. **VectorRepository** — wraps ChromaDB; `upsert(chunks)`, `query(vector, k)`, `delete_collection()`; sole ChromaDB importer
6. **LLM Client** — builds prompts from Jinja2 templates + retrieved context; handles retries, rate limits, token counting
7. **Writer** — normalises LLM output; writes `README.md` and `docs/<module>.md`; never overwrites without flag

### Critical Pitfalls

Five pitfalls are rated Critical (cause rewrites, data loss, or make the tool unusable). Nine more are Moderate or Minor.

1. **Free-tier rate limit silent failures** — Implement explicit 429 detection separate from other HTTP errors; exponential backoff with jitter (2s → 4s → 8s, cap 60s); add `--dry-run` to count API calls before executing. Address before any multi-file testing.

2. **Naive character-count chunking** — Code chunked by fixed character windows produces semantically broken embeddings (docstrings separated from signatures, half-classes). Use Python `ast` module from day one; add tree-sitter for JS/TS. This is non-negotiable for RAG quality.

3. **Secret file leakage into vector store** — `.env`, `secrets.py`, config files with credentials get embedded and sent to Gemini/Groq servers, violating the privacy-first contract. Implement the exclusion blocklist and `.gitignore` respect before writing a single embedding. This is the first filter, not an afterthought.

4. **Full re-embedding on every run** — Without hash-based incremental indexing, every run embeds all 50 files. At ~20s embedding overhead per run, this accumulates quickly and may breach the 2-minute target after multiple runs. SHA-256 hash map in `.chroma/file_hashes.json` is ~1 day of work; implement before performance testing.

5. **ChromaDB concurrent access corruption** — Two CLI instances writing to the same `.chroma/` directory (or a Ctrl+C mid-write) can corrupt the SQLite WAL. Implement a lockfile on startup and a `reset` subcommand that wipes and re-indexes. Add startup validation with `.count()`.

**Moderate pitfalls to address per phase:**
- Context window overflow on Groq models (8K-32K limit) — token count before every API call
- Hardcoded embedding model name — store model ID in ChromaDB collection metadata; warn on mismatch
- Non-deterministic LLM output — set `temperature=0` from first integration
- Wrong retrieval strategy for docs — use metadata-filtered retrieval (`where={"source_file": target}`), not similarity search, for file-level documentation
- Windows path/encoding bugs — use `pathlib.Path` exclusively; `encoding='utf-8'` on all file opens

---

## Implications for Roadmap

Research across all four files converges on the same build order, driven by component dependencies. The `CodeChunk` dataclass must exist before the Parser, the VectorRepository interface before the Embedder, and secrets filtering before any data ever reaches the embedding step.

### Phase 1: Foundation — Data Contracts, CLI Scaffold, Config

**Rationale:** Everything downstream depends on the `CodeChunk` dataclass and the CLI/Config structure. Define these first so all subsequent phases build to a stable interface. Retrofitting these structures mid-project is the most expensive kind of rework. Also establish the three-command CLI structure (`index` / `generate` / `run`) even as stubs.
**Delivers:** `docgen --help` works; config loads from env/file; data contracts are frozen
**Addresses:** Table-stakes CLI entry point (FEATURES.md)
**Avoids:** Anti-Pattern 1 (monolithic pipeline function); Pitfall 9 (CLI scriptability — TTY detection and stderr/stdout split belong here)
**Stack used:** Typer, Rich, pyproject.toml, uv
**Research flag:** Standard patterns — no deeper research needed

### Phase 2: Parser — AST-Aware Code Extraction

**Rationale:** The Parser is the first real data producer. It must be correct before the Chunker or Embedder are built, because bad chunks propagate bad embeddings. Start with Python `ast` (stdlib, no dependency), then add tree-sitter for JS/TS. Unit test with fixture files before moving on.
**Delivers:** Parser outputs `CodeChunk[]` for sample Python and JS/TS projects; all chunks are function/class/module-scoped, never mid-syntax
**Addresses:** Python + JS/TS language support (FEATURES.md table stakes)
**Avoids:** Pitfall 3 (naive character-count chunking — AST-aware from day one); Pitfall 5 (sensitive file filter runs in this phase, before any embedding or API call)
**Stack used:** Python `ast` (stdlib), tree-sitter ~0.22.x, tree-sitter-python, tree-sitter-javascript
**Research flag:** Standard patterns for Python `ast`; tree-sitter Python bindings version matrix needs manual verification against the installed core version

### Phase 3: Storage Layer — Chunker + VectorRepository (ChromaDB)

**Rationale:** The Chunker and VectorRepository form the handoff between parsing and embedding. The `VectorRepository` interface must be defined and tested here (not in Phase 4) so the Embedder can be wired to a known interface. Implement lockfile, startup `.count()` validation, and `reset` subcommand in this phase.
**Delivers:** `docgen index .` populates `.chroma/`; chunks are persisted with metadata; lockfile prevents concurrent corruption
**Addresses:** Configurable output structure; metadata required for later incremental indexing
**Avoids:** Pitfall 2 (ChromaDB concurrent access corruption); Pitfall 7 (store embedding model ID in collection metadata now); Pitfall 13 (stale document cleanup on each run)
**Stack used:** ChromaDB ~0.5.x (`PersistentClient` API — not 0.4.x); pyproject.toml
**Research flag:** Needs verification — ChromaDB 0.5.x `PersistentClient` API surface must be confirmed before implementation; concurrent access and WAL behavior should be checked in the current changelog

### Phase 4: Embedder — Local Sentence-Transformers Integration

**Rationale:** With the VectorRepository interface defined, the Embedder can be wired without touching other components. Implement batch embedding (batch_size=32) from the start — single-item embedding is the performance anti-pattern. Wire the full ingest path (Chunker → Embedder → VectorRepository) and validate end-to-end.
**Delivers:** Full ingest path working; 50-file project indexed in <60s on CPU
**Addresses:** Privacy-first local execution (no embeddings leave the machine); performance target groundwork
**Avoids:** Anti-Pattern 2 (embedding at parse time); Pitfall 4 (SHA-256 hash map for incremental indexing — implement here alongside the embedder, not as a later optimization)
**Stack used:** sentence-transformers ~2.7.x (`all-MiniLM-L6-v2`); optionally Gemini Embeddings API as alternative
**Research flag:** Standard patterns — sentence-transformers batching is well-documented

### Phase 5: LLM Client + Prompt Templates

**Rationale:** The LLM Client is independent of the Parser and Embedder — it only needs retrieved text. However, it cannot be integration-tested until the VectorRepository is populated (Phase 3-4). Build the client with explicit 429 handling, exponential backoff, token counting, and `temperature=0` from the start. Keep all prompts in `/prompts/*.jinja2` files.
**Delivers:** LLM returns raw Markdown given a module query; rate limit handling proven on multi-file runs
**Addresses:** Configurable LLM provider (Gemini + Groq); free-tier LLM routing
**Avoids:** Pitfall 1 (rate limit silent failures — 429 detection must be in place before multi-file testing); Pitfall 6 (context window overflow — token counting wrapper before any large-repo tests); Pitfall 8 (non-determinism — temperature=0 from first integration); Pitfall 11 (wrong retrieval strategy — use metadata-filtered retrieval for file-level docs); Anti-Pattern 5 (hardcoded model names)
**Stack used:** google-generativeai ~0.7.x, groq ~0.9.x, Jinja2 ~3.1.x
**Research flag:** Needs verification — free-tier rate limits for both Gemini and Groq should be confirmed at current docs before implementing retry logic; Groq model name rotation is a known risk

### Phase 6: Writer + Full Pipeline Integration

**Rationale:** The Writer is the final stage and requires LLM output to exist. Wire the complete `run` command (index → generate → write) and performance-test against a real 50-file project. This phase proves the end-to-end value proposition.
**Delivers:** `docgen run .` produces `/docs/README.md` and `docs/<module>.md` files in <2 minutes for a 50-file project
**Addresses:** README.md generation; per-module API docs; structured Markdown output; idempotent/safe output (never modify source)
**Avoids:** Anti-Pattern 4 (one LLM call per file — batch related modules where context window permits)
**Stack used:** Jinja2 ~3.1.x, pathlib (stdlib)
**Research flag:** Standard patterns — Jinja2 templating is stable; Markdown output format is well-understood

### Phase 7: Polish — UX, Error Handling, Incremental Indexing

**Rationale:** Everything before this phase is functional. This phase makes the tool production-ready. Progress indicators, user-friendly error messages (no raw stack traces), `.docgenignore` support, and incremental indexing (if not already wired in Phase 4) belong here. Also add `--verbose`/`--debug` flags.
**Delivers:** Production-ready CLI; second run on unchanged repo completes in seconds; error messages are human-readable
**Addresses:** Progress feedback (FEATURES.md table stakes); `.docgenignore` support; verbose/debug mode (FEATURES.md differentiator); configurable output templates
**Avoids:** Pitfall 12 (stack traces exposed to users — top-level error handler); Pitfall 10 (Windows path/encoding — validate cross-platform before release); Pitfall 14 (prompt template drift — hash prompt template into cache key)
**Research flag:** Standard patterns — no deeper research needed

### Phase Ordering Rationale

- **Data contracts first (Phase 1):** `CodeChunk` is the lingua franca of the entire system. Defining it before writing any component prevents the most expensive refactor type.
- **Security before data (Phase 2):** The sensitive file exclusion filter is implemented in the Parser phase, which means it runs before any data ever reaches ChromaDB or an LLM API. This is a hard ordering requirement, not a preference.
- **VectorRepository interface before Embedder (Phase 3 before 4):** The Embedder writes to VectorRepository; if the interface is undefined, the Embedder's output contract is undefined. Build the seam before you build the component that crosses it.
- **LLM Client after ingest is proven (Phase 5 after 4):** Integration testing the LLM Client requires a populated index. Deferring it prevents testing against an empty or incorrect VectorDB.
- **Performance validation in Phase 6:** By the time the full pipeline is wired, all performance-critical components (batch embedding, token counting, LLM call batching) are already in place. The Phase 6 performance test is a validation, not a discovery.
- **Polish last (Phase 7):** Error handling and UX polish are safe to defer; the pipeline correctness and security properties are not.

### Research Flags

Phases needing deeper research during planning:
- **Phase 3 (ChromaDB storage):** The 0.4.x → 0.5.x API break (`Client` → `PersistentClient`) means code examples from tutorials may be wrong. Verify the current ChromaDB API surface and concurrent-access behavior in the current changelog before writing the VectorRepository implementation.
- **Phase 5 (LLM Client):** Free-tier rate limits for Gemini and Groq change frequently. The specific RPM/TPM numbers must be checked at current docs before implementing retry/backoff logic. Groq's available model names rotate and must be verified before hardcoding defaults.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Typer and pyproject.toml patterns are stable and well-documented.
- **Phase 2:** Python `ast` module is stdlib and has been stable since Python 3.8. Tree-sitter Python bindings are stable; only the version matrix against the core package needs a one-time check.
- **Phase 4:** sentence-transformers batching patterns are well-documented and stable.
- **Phase 6:** Jinja2 templating and pathlib file I/O are among the most stable Python libraries.
- **Phase 7:** CLI UX patterns (TTY detection, stderr/stdout split, exit codes) are Unix conventions, not library-dependent.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core libraries (Typer, Rich, Jinja2, pytest) are HIGH confidence. ChromaDB version and API surface need live verification (breaking change between 0.4.x and 0.5.x). LangChain is LOW-MEDIUM due to version flux — recommend avoiding it in MVP. sentence-transformers and tree-sitter are MEDIUM. |
| Features | HIGH | Table stakes are well-established from Sphinx/JSDoc/TypeDoc comparisons. Anti-features are clearly derived from stated project constraints. Differentiators are MEDIUM — verify Mintlify/Swimm current feature sets before finalizing competitive positioning. |
| Architecture | MEDIUM | Pipeline pattern and component boundaries are well-established in RAG literature. ChromaDB-specific patterns (PersistentClient, metadata filtering API) need live verification. Data contracts and component communication are HIGH confidence. |
| Pitfalls | HIGH | 10 of 14 pitfalls are HIGH confidence (mathematical/architectural/convention-based, not version-dependent). Rate limit specifics (Pitfall 1) and ChromaDB concurrent-access internals (Pitfall 2) are MEDIUM — validate against current docs. |

**Overall confidence:** MEDIUM-HIGH

Research is sufficient to begin roadmap creation and requirements definition. The two areas requiring live verification (ChromaDB 0.5.x API surface, current free-tier rate limits for Gemini/Groq) are scoped to specific implementation phases and do not block earlier phases.

### Gaps to Address

- **ChromaDB 0.5.x API surface:** The `PersistentClient` migration from 0.4.x must be confirmed at https://docs.trychroma.com/ before Phase 3 implementation. Do not write VectorRepository code against training-data examples without checking the current API.
- **Free-tier rate limits:** Gemini and Groq free-tier RPM/TPM limits must be checked at current docs before Phase 5 backoff logic is implemented. The numbers in PITFALLS.md are from mid-2025 training data and may have changed.
- **Groq model name availability:** Groq rotates available models. The specific model string (e.g., `llama3-70b-8192`) must be confirmed at https://console.groq.com/docs before being set as the default in Config.
- **LangChain version:** If the team decides to include LangChain despite the lean-alternative recommendation, verify the current stable release and the `langchain-core` + provider package split structure before including it.
- **tree-sitter version matrix:** The tree-sitter Python bindings version must match the core package version exactly. Check the release matrix at https://github.com/tree-sitter/py-tree-sitter before pinning versions.
- **Competitive positioning:** Mintlify and Swimm may have added local/free-tier options since August 2025. Verify before using the competitive comparison table in any user-facing materials.

---

## Sources

### Primary (HIGH confidence)
- Python `ast` module — stdlib documentation, stable since Python 3.8
- Jinja2 3.x — stable for multiple years; no version concerns
- pytest 8.x + pytest-mock 3.x — stable at research cutoff
- Unix CLI conventions (TTY detection, exit codes, stderr/stdout split) — platform standards

### Secondary (MEDIUM confidence)
- Training knowledge of ChromaDB ~0.5.x embedded mode, HNSW index, SQLite persistence (cutoff August 2025)
- Training knowledge of sentence-transformers 2.7.x, `all-MiniLM-L6-v2` model characteristics
- Training knowledge of Typer ~0.12, Rich ~13.x
- Training knowledge of Gemini Flash 1.5 context window (1M tokens), free-tier limits
- Training knowledge of Groq free-tier limits and Llama 3 70B availability
- Training knowledge of RAG pipeline design patterns and code chunking literature
- Training knowledge of Sphinx 7.x, JSDoc 4.x, TypeDoc 0.25.x, pydoc-markdown 4.x, Mintlify, Swimm

### Tertiary (LOW-MEDIUM confidence — verify before acting)
- LangChain ~0.2.x/0.3.x — version was in flux through 2024; verify current stable release at https://python.langchain.com/docs/
- Specific free-tier rate limit numbers for Gemini and Groq — subject to change; verify at https://ai.google.dev/gemini-api/docs/rate-limits and https://console.groq.com/docs/rate-limits
- ChromaDB concurrent access / WAL behavior specifics — verify at https://github.com/chroma-core/chroma/releases
- Mintlify and Swimm current feature tiers — may have changed since August 2025

**Note:** WebSearch, WebFetch, and Bash tools were unavailable during all four research sessions. All findings are from training knowledge (cutoff August 2025). Live verification at the URLs listed above is required for MEDIUM-confidence claims before implementation begins.

---
*Research completed: 2026-03-10*
*Ready for roadmap: yes*
