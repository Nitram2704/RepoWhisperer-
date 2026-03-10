# Roadmap: DocGen CLI

## Overview

DocGen CLI is built as a strict pipeline: raw source files flow through a parser, into a vector store, through retrieval and LLM generation, and finally into written Markdown files. The roadmap mirrors that pipeline — each phase delivers one complete, independently testable pipeline stage, with security enforcement (secret file exclusion, API key safety) built into the earliest possible phase. Phase 6 wires the full pipeline end-to-end and validates the core value proposition: one command, accurate docs, local execution only.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - CLI scaffold, three-command structure, config loading, data contracts
- [ ] **Phase 2: Parser** - AST-aware code extraction for Python and JS/TS with sensitive file exclusion
- [ ] **Phase 3: Ingest Pipeline** - Chunker, local embedder, and vector store wired end-to-end
- [ ] **Phase 4: LLM Client** - Pluggable LLM providers with rate-limit handling and prompt templates
- [ ] **Phase 5: Output and Integration** - Writer, README/API doc generation, full pipeline wired

## Phase Details

### Phase 1: Foundation
**Goal**: Developer can invoke docgen commands and load configuration securely
**Depends on**: Nothing (first phase)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, PRIV-02
**Success Criteria** (what must be TRUE):
  1. Running `docgen --help` displays available commands (run, index, generate) without error
  2. Running `docgen run <path>` with a missing API key fails with a clear human-readable error, not a stack trace
  3. API key is loaded from an environment variable or config file and never appears in logs or output
  4. A progress indicator (spinner or bar) is visible during any operation that takes more than one second
  5. Running `docgen index <path>` and `docgen generate` as separate commands does not crash (stubs accepted at this stage)
**Plans**: TBD

Plans:
- [ ] 01-01: TBD

---

### Phase 2: Parser
**Goal**: DocGen can extract structured code chunks from Python and JS/TS files, with all sensitive files blocked before any data leaves the filesystem
**Depends on**: Phase 1
**Requirements**: PARSE-01, PARSE-02, PARSE-03, PARSE-04, PRIV-01
**Success Criteria** (what must be TRUE):
  1. Parser produces at least one `CodeChunk` per function and class in a sample Python file, never splitting mid-syntax
  2. Parser produces at least one `CodeChunk` per function and class in a sample JS/TS file, never splitting mid-syntax
  3. A repo containing `.env`, `*.key`, or `*.pem` files produces zero chunks from those files
  4. Files listed in `.gitignore` are never parsed or chunked
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

---

### Phase 3: Ingest Pipeline
**Goal**: Parsed code chunks are embedded locally and persisted in ChromaDB, making the index queryable for generation
**Depends on**: Phase 2
**Requirements**: (Infrastructure phase — no standalone v1 requirements; enables Phase 4 and Phase 5 integration)
**Success Criteria** (what must be TRUE):
  1. Running `docgen index <path>` on a sample project populates `.chroma/` with queryable entries
  2. Running `docgen index <path>` twice on the same unchanged repo does not re-embed files that have not changed (hash-based skip)
  3. A second concurrent invocation of `docgen index` fails with a clear lock error rather than corrupting the vector store
  4. No source code file contents are sent to any external service during the indexing step
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

---

### Phase 4: LLM Client
**Goal**: DocGen can generate raw Markdown documentation by querying an LLM provider with retrieved code context
**Depends on**: Phase 3
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06
**Success Criteria** (what must be TRUE):
  1. Setting `DOCGEN_PROVIDER=gemini` causes the tool to use Google Gemini for generation; setting `DOCGEN_PROVIDER=groq` causes it to use Groq/Llama 3
  2. Setting `DOCGEN_PROVIDER=openrouter` or `DOCGEN_PROVIDER=deepseek` causes the tool to use those providers without code changes
  3. When an LLM provider returns a 429 response, the tool automatically retries with exponential backoff and does not crash or produce partial output
  4. The active provider and model can be set via an environment variable or config file without editing source code
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

---

### Phase 5: Output and Integration
**Goal**: Running one command on a real repo produces a README.md and per-module API docs in under two minutes
**Depends on**: Phase 4
**Requirements**: OUT-01, OUT-02, OUT-03
**Success Criteria** (what must be TRUE):
  1. Running `docgen run <path>` writes a `README.md` summarizing the project to the output directory
  2. Running `docgen run <path>` writes one Markdown API reference file per module into the output directory
  3. The output directory defaults to `/docs` but can be overridden with a flag or config option
  4. Running `docgen run <path>` on a 50-file Python or JS/TS project completes in under 2 minutes on a standard developer laptop
  5. No source files are modified; all output is written only to the designated docs directory
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/TBD | Not started | - |
| 2. Parser | 0/TBD | Not started | - |
| 3. Ingest Pipeline | 0/TBD | Not started | - |
| 4. LLM Client | 0/TBD | Not started | - |
| 5. Output and Integration | 0/TBD | Not started | - |
