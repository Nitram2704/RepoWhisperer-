# Architecture Patterns

**Domain:** Local RAG-based CLI documentation generator (Python)
**Researched:** 2026-03-10
**Confidence:** MEDIUM (training knowledge; WebSearch and official docs unavailable in this session)

---

## Recommended Architecture

A pipeline architecture with six discrete stages. Each stage has a single responsibility, communicates only with adjacent stages via well-defined data contracts, and can be developed and tested independently.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                          │
│                    (click / argparse)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ command + config
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Orchestrator                                │
│           (coordinates pipeline stages, owns config)            │
└──────┬──────────────┬───────────────┬───────────────┬───────────┘
       │              │               │               │
       ▼              │               │               │
┌─────────────┐       │               │               │
│   Parser    │       │               │               │
│  (Python +  │       │               │               │
│   JS/TS     │       │               │               │
│   AST)      │       │               │               │
└──────┬──────┘       │               │               │
       │ CodeChunks   │               │               │
       ▼              │               │               │
┌─────────────┐       │               │               │
│  Chunker /  │       │               │               │
│  Splitter   │       │               │               │
│ (semantic   │       │               │               │
│  units)     │       │               │               │
└──────┬──────┘       │               │               │
       │ Chunks[]     │               │               │
       ▼              │               │               │
┌─────────────┐       │               │               │
│  Embedder   │◄──────┘               │               │
│ (local or   │  (called on ingest    │               │
│  API)       │   AND on queries)     │               │
└──────┬──────┘                       │               │
       │ Vectors                      │               │
       ▼                              │               │
┌─────────────┐                       │               │
│  VectorDB   │◄──────────────────────┘               │
│ (ChromaDB   │  (query at doc-gen time)               │
│  embedded)  │                                       │
└──────┬──────┘                                       │
       │ TopK Chunks (context)                        │
       ▼                                              │
┌─────────────┐                                       │
│  LLM Client │◄─────────────────────────────────────┘
│ (Gemini /   │  (prompt templates + retrieved context)
│  Groq API)  │
└──────┬──────┘
       │ Generated text
       ▼
┌─────────────┐
│   Writer    │
│ (README.md, │
│  /docs/*.md)│
└─────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Inputs | Outputs | Communicates With |
|-----------|---------------|--------|---------|-------------------|
| **CLI Entry** | Parse CLI args, validate flags, route to commands | sys.argv | Config object, command signal | Orchestrator only |
| **Orchestrator** | Coordinate pipeline, hold config, manage run modes (index / generate / full) | Config | Nothing directly; calls components | All components |
| **Parser** | Walk file tree, parse Python (ast module) and JS/TS (tree-sitter or regex fallback), extract functions/classes/modules with signatures and docstrings | File paths | `CodeChunk[]` structs | Chunker |
| **Chunker** | Assign chunk IDs, attach metadata (file, language, type, line range), enforce max-token limits, handle overlap for large functions | `CodeChunk[]` | `IndexableChunk[]` (id, text, metadata) | Embedder, VectorDB |
| **Embedder** | Convert text to float vectors via local model (sentence-transformers) or API (Gemini embeddings); must be deterministic for same input | `str[]` | `float[][]` | VectorDB (write), Orchestrator (query path) |
| **VectorDB** | Persist and query embeddings; collection-per-project or single collection with metadata filters | Vectors + metadata | TopK `IndexableChunk[]` by cosine similarity | Embedder (write), LLM Client (read) |
| **LLM Client** | Build prompt from template + retrieved context; call Gemini or Groq REST API; handle retries and rate limits | Context chunks + prompt template | Raw generated markdown text | Writer |
| **Writer** | Normalise LLM output, write `README.md` and `docs/<module>.md`; create `/docs` if absent; never overwrite without flag | Raw markdown | Files on disk | CLI (reports paths) |

**Hard boundaries:**
- Parser never calls Embedder or VectorDB directly.
- LLM Client never reads files directly — it only sees retrieved chunk text.
- Writer never calls the LLM — it receives final text.
- VectorDB is accessed only through a thin repository interface, not imported directly by Parser or Writer.

---

## Data Flow

### Ingest Path (index command)

```
File tree on disk
  → Parser          extracts CodeChunks (text + metadata per function/class)
  → Chunker         normalises chunks, enforces token limits, assigns IDs
  → Embedder        converts chunk text to vectors (batch)
  → VectorDB        upserts vectors + metadata; persists to .chroma/ directory
```

This path is run once (or incrementally on file changes). It is the "build index" step.

### Generation Path (generate command)

```
User prompt / per-module query string
  → Embedder        embeds the query string into a vector
  → VectorDB        retrieves TopK most similar chunks (cosine similarity)
  → LLM Client      builds prompt: system instructions + retrieved chunks + "write docs for X"
  → Writer          receives markdown, writes README.md + docs/<module>.md
```

### Full Pipeline (default command)

Ingest path runs first, then generation path runs immediately after. The VectorDB acts as the handoff point between the two sub-pipelines.

### Config / State Flow

```
CLI Entry
  → Config struct (file path, model choice, output dir, chunk size, top-k)
  → Orchestrator holds Config for full run
  → Each component receives only the slice of Config it needs
```

---

## Patterns to Follow

### Pattern 1: Thin Repository Over VectorDB

**What:** Wrap ChromaDB behind a `VectorRepository` interface with methods `upsert(chunks)`, `query(vector, k)`, `delete_collection()`. No component except VectorRepository imports `chromadb` directly.

**When:** Always — this is the main seam for testing and for swapping ChromaDB if needed.

**Example:**
```python
class VectorRepository:
    def __init__(self, persist_path: str, collection_name: str): ...
    def upsert(self, chunks: list[IndexableChunk]) -> None: ...
    def query(self, vector: list[float], k: int) -> list[IndexableChunk]: ...
    def collection_exists(self) -> bool: ...
```

### Pattern 2: CodeChunk as Central Data Contract

**What:** Define a `CodeChunk` dataclass early (Phase 1). Every component after the Parser speaks in `CodeChunk` or `IndexableChunk` terms. This prevents string-passing across boundaries.

**When:** Define before writing Parser or Chunker.

**Example:**
```python
@dataclass
class CodeChunk:
    id: str          # deterministic hash of file+name+type
    text: str        # raw source text of the unit
    language: str    # "python" | "javascript" | "typescript"
    chunk_type: str  # "function" | "class" | "module"
    file_path: str
    start_line: int
    end_line: int
    metadata: dict   # arbitrary extra fields for VectorDB filter
```

### Pattern 3: Prompt Template Files (not hardcoded strings)

**What:** Keep LLM prompts in `/prompts/*.txt` or `/prompts/*.jinja2` files, loaded at runtime. The LLM Client reads the template and formats it with retrieved context.

**When:** From the start — prompt engineering is iterative and should not require code changes.

### Pattern 4: Two-Phase CLI Commands

**What:** Expose three commands: `index` (ingest only), `generate` (query + write, requires existing index), `run` (index then generate). This allows re-generating docs without re-indexing.

**When:** Structure CLI this way from Phase 1 even if initially only `run` is wired up.

### Pattern 5: Batch Embedding with Configurable Batch Size

**What:** Never embed one chunk at a time. The Embedder accepts `list[str]` and calls the model once per batch (default 32). This is the main lever for hitting the 50 files / 2 minutes performance target.

**When:** Implement from the start in the Embedder.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic Pipeline Function

**What:** A single `generate_docs(project_path)` function that contains all logic inline.

**Why bad:** Impossible to unit-test individual stages. Prompt changes require touching parsing logic. Performance profiling is impossible at the component level.

**Instead:** Each stage is a class or module with a single public method. The Orchestrator calls them in sequence.

### Anti-Pattern 2: Embedding at Parse Time

**What:** Calling the embedding model inside the Parser or Chunker loop as each chunk is created.

**Why bad:** Parser becomes network/GPU-dependent. Breaks the ingest/generate separation. Slower due to missing batching.

**Instead:** Parser and Chunker produce `CodeChunk[]` (pure data). Embedder receives the full list and batches.

### Anti-Pattern 3: Storing Raw Source in VectorDB as the Only Copy

**What:** Relying on ChromaDB document storage as the sole source of the original chunk text.

**Why bad:** ChromaDB's document retrieval is not guaranteed to be lossless for very large texts, and the DB is a cache not a source of truth.

**Instead:** Store chunk text in ChromaDB for retrieval convenience, but the Parser can always re-derive it from source files. Treat the VectorDB as a queryable index, not the primary data store.

### Anti-Pattern 4: One LLM Call Per File

**What:** Calling the LLM once for each source file to generate that file's documentation.

**Why bad:** For 50 files this is 50 sequential API calls, easily exceeding 2 minutes and burning free-tier quota.

**Instead:** At generation time, batch per-module queries. Where the LLM context window permits, combine related modules. Use per-function retrieval only for targeted API doc sections.

### Anti-Pattern 5: Hardcoded Model Names

**What:** `model = "gemini-1.5-flash"` or `model = "llama3-70b-8192"` scattered across LLM Client code.

**Why bad:** Free-tier model names change frequently (Groq in particular rotates available models). A single version bump breaks the tool.

**Instead:** Model names come from Config, which reads from a config file or env var with a documented default. One change point.

---

## Scalability Considerations

| Concern | At 10 files | At 50 files (target) | At 500 files |
|---------|-------------|----------------------|--------------|
| Parse time | <5s (negligible) | <30s (Python ast is fast) | May need parallel file walking |
| Embedding time | <10s | <60s with batch_size=32 | Needs async batching or local GPU |
| VectorDB write | Instant | <5s | ChromaDB embedded handles ~1M vectors fine |
| VectorDB query | <100ms | <100ms (unchanged) | <100ms (HNSW index) |
| LLM calls | 1-3 calls | 5-15 calls | May exceed free-tier rate limits |
| Memory | <200MB | <400MB | May need streaming chunker |
| Output size | Small | Manageable | Needs output pagination / index page |

For the 50-file target, the bottleneck is LLM API calls. ChromaDB and the embedding step are not the constraint at this scale.

---

## Suggested Build Order

The component dependency graph drives this order. Each phase produces something testable before the next begins.

```
Phase 1: Data contracts + CLI skeleton
  - Define CodeChunk and IndexableChunk dataclasses
  - Set up CLI entry point with index / generate / run commands (stubs)
  - Set up Config struct and config file loading
  - Deliverable: `docgen --help` works; config loads

Phase 2: Parser
  - Python parser (ast module — stdlib, no dependency)
  - JS/TS parser (tree-sitter-python + tree-sitter-javascript bindings, or regex MVP)
  - Unit tests with fixture files
  - Deliverable: parser outputs CodeChunk[] for sample projects

Phase 3: Chunker + VectorRepository (ChromaDB)
  - Chunker normalises CodeChunk[], enforces token limits
  - VectorRepository wraps ChromaDB; upsert + query
  - Integration test: index a small project, verify chunks persisted
  - Deliverable: `docgen index .` populates .chroma/

Phase 4: Embedder
  - Integrate sentence-transformers (local) or Gemini Embeddings API
  - Batch embedding implementation
  - Wire into ingest path: Chunker → Embedder → VectorRepository
  - Deliverable: full ingest path working end-to-end

Phase 5: LLM Client + Prompt Templates
  - Gemini or Groq client with retry logic
  - Prompt templates for README and per-module docs
  - Wire query path: query → Embedder → VectorRepository → LLM Client
  - Deliverable: LLM returns raw markdown given a module query

Phase 6: Writer + full pipeline
  - Writer outputs README.md and docs/<module>.md
  - Wire full run: index → generate → write
  - Performance test against 50-file project
  - Deliverable: `docgen run .` produces /docs in <2 min

Phase 7: Polish
  - Progress indicators (tqdm or rich)
  - Incremental indexing (skip unchanged files by hash)
  - Error handling and user-friendly messages
  - Deliverable: production-ready CLI
```

**Key dependency rule:** The VectorRepository interface must exist before the Embedder is wired (Phase 3 before Phase 4). The LLM Client is completely independent of the Parser — it only needs retrieved text, so it can be developed in parallel with Phases 2-4 once the CodeChunk contract is defined.

---

## Component Communication Summary

```
CLI Entry        →  Orchestrator         (Config + command)
Orchestrator     →  Parser               (file paths)
Parser           →  Chunker              (CodeChunk[])
Chunker          →  Embedder             (text[] for batching)
Embedder         →  VectorRepository     (vectors + metadata)
Orchestrator     →  Embedder             (query text at generate time)
Embedder         →  VectorRepository     (query vector)
VectorRepository →  LLM Client           (TopK IndexableChunk[])
LLM Client       →  Writer               (raw markdown string)
Writer           →  Disk                 (README.md, docs/*.md)
```

No component skips a stage. No component communicates backwards up the pipeline.

---

## Sources

- Training knowledge: Python `ast` module (stdlib, stable since Python 3.8)
- Training knowledge: ChromaDB embedded mode architecture (HNSW index, SQLite persistence)
- Training knowledge: sentence-transformers batching patterns
- Training knowledge: RAG pipeline design patterns (retrieval-augmented generation literature)
- Training knowledge: tree-sitter Python bindings for JS/TS parsing
- **Note:** WebSearch was unavailable in this session. All findings are from training data (knowledge cutoff August 2025). Confidence is MEDIUM. Verify ChromaDB API surface and Groq/Gemini model name availability before implementation.
