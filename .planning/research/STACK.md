# Technology Stack

**Project:** CLI Documentation Generator (RAG-based)
**Researched:** 2026-03-10
**Research method:** Training knowledge (cutoff August 2025). Live source verification was unavailable during this session (WebSearch, WebFetch, Bash denied). All confidence levels reflect this constraint. Versions should be re-validated before pinning in requirements.txt.

---

## Recommended Stack

### Core Framework / CLI Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11+ | Runtime | 3.11 delivers 10–60% speed improvements over 3.10 via the "Faster CPython" project; 3.12 adds further gains. Broadly available, all key libraries support it. |
| Typer | ~0.12 | CLI framework | Built on Click but leverages Python type hints for zero-boilerplate argument parsing. Produces `--help` output automatically. Preferred over raw Click for new projects because it eliminates manual `@click.argument` decorators while remaining Click-compatible under the hood. |
| Rich | ~13.x | Terminal output | Typer integrates Rich natively for progress bars, colored output, and tables — critical for a tool that processes 50 files and needs real-time feedback without extra wiring. |

**Confidence:** MEDIUM — versions based on training data (Aug 2025). Typer 0.12 was current at cutoff; Rich 13.x was stable. Re-verify on PyPI before pinning.

---

### Embedding / Vector Store Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| ChromaDB | ~0.5.x | Local vector database | The de-facto standard for local-first RAG. Stores embeddings + metadata on disk (SQLite + DuckDB backend), zero external services, pip-installable. Fits the privacy-first constraint perfectly. Alternative (FAISS) lacks metadata filtering; Qdrant requires a running server. |
| sentence-transformers | ~2.7.x | Local embedding model | Provides `all-MiniLM-L6-v2` (fast, 384-dim, 80 MB) and `all-mpnet-base-v2` (better quality, slower). Running embeddings locally means zero API cost and no code leaves the machine. For 50 files this is fast enough on CPU. |

**Confidence:** MEDIUM — ChromaDB 0.5.x introduced a breaking API change from 0.4.x (the `Client` → `PersistentClient` migration). Confirm the exact current version on PyPI; do not assume 0.4.x APIs still apply.

---

### RAG Orchestration Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| LangChain Core | ~0.2.x / 0.3.x | RAG pipeline orchestration | Provides `RecursiveCharacterTextSplitter` (the right splitter for code), document loaders, and retrieval chains. The ecosystem has stabilised around the `langchain-core` + provider-specific package split. |
| langchain-community | ~0.2.x | Document loaders | Contains `TextLoader`, `DirectoryLoader`, and language-aware loaders for Python/JS/TS. Avoids writing custom file-walking code. |

**Confidence:** LOW-MEDIUM — LangChain versioning was in flux through 2024 (0.1 → 0.2 → 0.3). The recommended pattern at cutoff was to use `langchain-core` + thin provider packages rather than the monolithic `langchain` package. Verify the current stable release before using. If LangChain feels heavyweight, see the "Lean Alternative" note below.

**Lean Alternative:** Skip LangChain entirely. Use `chromadb` directly + `sentence-transformers` + a custom 50-line retrieval loop. This is viable for a single-domain tool and avoids LangChain's dependency footprint (~50 transitive packages). Recommend LangChain only if the roadmap plans to add multiple retrieval strategies or swap vector stores later.

---

### LLM API Clients

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| google-generativeai | ~0.7.x | Gemini API client | Official Google SDK. Gemini 1.5 Flash is the recommended free-tier model: 1M token context window (handles large code chunks), 15 requests/min free tier. Substantially more capable than older models. |
| groq | ~0.9.x | Groq/Llama 3 API client | Official Groq SDK. Llama 3 70B on Groq's free tier (14,400 tokens/min) is fast and high quality. Groq's LPU inference makes it noticeably faster than comparable free-tier options. Use as fallback or primary depending on project preference. |

**Confidence:** MEDIUM — Both SDKs were stable at training cutoff. Free-tier limits are subject to change; check current Groq and Google AI Studio docs before committing to rate-limit handling logic.

---

### Code Parsing Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| tree-sitter | ~0.22.x | Language-aware code parsing | Parses Python and JS/TS into ASTs. Enables chunking at function/class boundaries rather than fixed character windows — critical for RAG quality. Fixed-size chunks split docstrings from function signatures, producing bad embeddings. |
| tree-sitter-python | ~0.21.x | Python grammar | Required alongside `tree-sitter` for Python AST parsing. |
| tree-sitter-javascript | ~0.21.x | JS/TS grammar | Required for JS and TypeScript (TS uses the JS grammar with `tsx` support). |

**Confidence:** MEDIUM — tree-sitter Python bindings have been stable. The exact grammar package versions must match the tree-sitter core version; check the tree-sitter GitHub release matrix.

**Simpler Alternative:** Use Python's built-in `ast` module for Python files + regex for JS/TS. Lower quality chunking but zero extra dependencies. Acceptable for an MVP, replace with tree-sitter in a later phase.

---

### Output / Markdown Generation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Jinja2 | ~3.1.x | Markdown template rendering | The LLM generates raw content; Jinja2 assembles it into structured README + API doc templates. Separates prompt engineering from output formatting. Avoids f-string spaghetti for multi-section docs. |
| pathlib (stdlib) | built-in | File I/O | Standard library `pathlib.Path` is sufficient for all file reading/writing. No extra dependency needed. |

**Confidence:** HIGH — Jinja2 3.x has been stable for years. pathlib is stdlib.

---

### Project / Dependency Management

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| uv | ~0.4.x | Package manager + virtualenv | Replaces pip + virtualenv. Written in Rust, resolves dependencies 10–100x faster. The 2025 community default for new Python projects. Produces a `pyproject.toml`-based setup compatible with PEP 517/518/660. |
| pyproject.toml | — | Project metadata | PEP 621 standard. Replaces `setup.py` + `requirements.txt`. Works with uv, pip, and all modern tooling. |

**Confidence:** MEDIUM — uv was rapidly gaining adoption through 2024-2025. Verify the current stable version; the API stabilised around 0.2.x but has continued evolving.

---

### Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | ~8.x | Test runner | Standard. Supports `tmp_path` fixtures for testing file-output CLIs without touching real directories. |
| pytest-mock | ~3.x | Mocking LLM API calls | Essential — tests must not make real API calls. Mock `google-generativeai` and `groq` responses to test the pipeline without network or token cost. |
| typer.testing | built-in | CLI integration testing | Typer ships a `CliRunner` (wrapping Click's) for end-to-end CLI tests without subprocess overhead. |

**Confidence:** HIGH — pytest 8.x and pytest-mock 3.x were stable at cutoff.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| CLI framework | Typer | Click (raw), argparse | Click works but requires manual type wiring; argparse is verbose and lacks auto-help richness. Typer produces a better DX in less code. |
| Vector DB | ChromaDB | FAISS, Qdrant, Weaviate | FAISS is a library (no persistence without custom code, no metadata queries). Qdrant/Weaviate require a running server — violates local-only constraint. |
| Embeddings | sentence-transformers (local) | OpenAI text-embedding-ada-002 | OpenAI embeddings send code to the cloud — violates privacy-first constraint and incurs cost. |
| RAG orchestration | LangChain-core | LlamaIndex, Haystack | LlamaIndex is excellent but heavier for a single-domain tool; Haystack is enterprise-oriented. LangChain's splitters + retriever API are the lightest fit here. Custom loop is the lightest of all. |
| Package manager | uv | poetry, pip-tools | poetry is mature but slower; pip-tools doesn't manage virtualenvs. uv does both faster. |
| LLM provider | Gemini Flash + Groq/Llama 3 | OpenAI GPT-4o, Anthropic Claude | Both have no free tier for API usage at meaningful scale. The constraint is free-tier. |
| Code chunking | tree-sitter | Fixed-size + overlap, ast module | Fixed-size chunking splits across semantic boundaries, degrading RAG retrieval quality. tree-sitter is the correct tool; stdlib `ast` is the acceptable MVP fallback. |

---

## Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project and virtualenv
uv init docgen
cd docgen
uv venv

# Core dependencies
uv add typer rich chromadb sentence-transformers
uv add langchain-core langchain-community
uv add google-generativeai groq
uv add jinja2

# Code parsing (install after verifying version matrix)
uv add tree-sitter tree-sitter-python tree-sitter-javascript

# Dev dependencies
uv add --dev pytest pytest-mock
```

```toml
# pyproject.toml (key fields)
[project]
name = "docgen"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
docgen = "docgen.cli:app"
```

---

## Performance Notes (50 files < 2 minutes constraint)

- **Embedding bottleneck:** `all-MiniLM-L6-v2` on CPU embeds ~500 tokens/sec. A 50-file repo at ~200 tokens/file = 10,000 tokens — takes ~20 seconds. Well within budget.
- **LLM bottleneck:** Gemini Flash at 15 req/min free tier means max 15 LLM calls in 60 seconds. Design the pipeline to batch context into as few calls as possible (e.g., one README call, one per-module API doc call). Groq's free tier is higher throughput but has daily token limits.
- **ChromaDB write speed:** Local persist mode writes to SQLite; 50 files embed and store in under 5 seconds.
- **Recommendation:** Profile the LLM call count first — it will be the binding constraint, not embedding or vector search.

---

## Confidence Assessment Summary

| Component | Confidence | Reason |
|-----------|------------|--------|
| Python 3.11+, Typer, Rich | MEDIUM | Stable at cutoff; verify Typer version |
| ChromaDB | MEDIUM | 0.4.x → 0.5.x API break; verify current version |
| sentence-transformers | MEDIUM | Stable at cutoff; model names unlikely to change |
| LangChain | LOW-MEDIUM | Version flux through 2024; verify current stable release |
| google-generativeai + Gemini Flash | MEDIUM | SDK stable; free-tier limits subject to change |
| groq SDK + Llama 3 | MEDIUM | SDK stable; free-tier limits subject to change |
| tree-sitter bindings | MEDIUM | Version matrix coupling requires manual check |
| Jinja2, pytest | HIGH | Long-stable libraries |
| uv | MEDIUM | Rapidly evolving; verify current version |

---

## Sources

All recommendations based on training knowledge (cutoff August 2025). Live source verification was unavailable during this research session. The following official sources MUST be checked before finalising version pins:

- ChromaDB docs and migration guide: https://docs.trychroma.com/
- sentence-transformers models: https://www.sbert.net/docs/pretrained_models.html
- LangChain current release: https://python.langchain.com/docs/
- Google Generative AI SDK: https://ai.google.dev/gemini-api/docs
- Groq API docs and free tier: https://console.groq.com/docs/
- tree-sitter Python bindings: https://github.com/tree-sitter/py-tree-sitter
- uv documentation: https://docs.astral.sh/uv/
- Typer docs: https://typer.tiangolo.com/
