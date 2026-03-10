# Requirements: DocGen CLI

**Defined:** 2026-03-10
**Core Value:** A developer runs one command and gets accurate, up-to-date README and API docs written to their repo — without sending their full codebase to a cloud service.

## v1 Requirements

### CLI

- [ ] **CLI-01**: User can run `docgen run <path>` to scan, embed, and generate docs in one command
- [ ] **CLI-02**: User can run `docgen index <path>` to build the vector index without generating docs
- [ ] **CLI-03**: User can run `docgen generate` to generate docs from an existing index
- [ ] **CLI-04**: User sees a progress bar/spinner during long operations

### Output

- [ ] **OUT-01**: Tool generates a README.md summarizing the project
- [ ] **OUT-02**: Tool generates per-module API reference docs as Markdown files
- [ ] **OUT-03**: User can configure the output directory (default: `/docs`)

### Parsing

- [ ] **PARSE-01**: Tool parses Python `.py` files using stdlib `ast`
- [ ] **PARSE-02**: Tool parses JavaScript/TypeScript `.js/.ts/.tsx` files using tree-sitter
- [ ] **PARSE-03**: Code is chunked by semantic units (function/class), not character count
- [ ] **PARSE-04**: Sensitive files (`.env`, `*.key`, `*.pem`, credentials) are excluded before embedding

### Privacy & Config

- [ ] **PRIV-01**: Tool respects `.gitignore` — gitignored files are never processed
- [ ] **PRIV-02**: API key is loaded from env var or config file, never hardcoded

### LLM

- [ ] **LLM-01**: Tool supports Google Gemini as an LLM provider
- [ ] **LLM-02**: Tool supports Groq (Llama 3) as an LLM provider
- [ ] **LLM-03**: Tool supports OpenRouter as an LLM provider
- [ ] **LLM-04**: Tool supports DeepSeek as an LLM provider
- [ ] **LLM-05**: Tool handles rate limits (429) with automatic retry/backoff
- [ ] **LLM-06**: LLM provider is configurable via env var or config file

## v2 Requirements

### Output

- **OUT-V2-01**: Incremental regeneration — only regenerate docs for files that changed (hash-based)
- **OUT-V2-02**: Cross-file relationship summary (import graph visualization)

### Privacy

- **PRIV-V2-01**: `.docgenignore` support — user-defined exclusion patterns

### Performance

- **PERF-V2-01**: Benchmark mode — measure and report indexing/generation time

## Out of Scope

| Feature | Reason |
|---------|--------|
| Inline comment injection into source files | Modifies source code — non-destructive contract must hold |
| Cloud hosting / SaaS version | Local execution only — privacy constraint |
| Watch mode / real-time re-generation | Out of scope for v1 single-run CLI |
| Mobile or web UI | CLI-first, no frontend |
| Training or fine-tuning models | Inference only |
| Java/Kotlin or other languages | Python + JS/TS first; expand in v2 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 1 | Pending |
| CLI-02 | Phase 1 | Pending |
| CLI-03 | Phase 1 | Pending |
| CLI-04 | Phase 1 | Pending |
| PRIV-02 | Phase 1 | Pending |
| PARSE-01 | Phase 2 | Pending |
| PARSE-02 | Phase 2 | Pending |
| PARSE-03 | Phase 2 | Pending |
| PARSE-04 | Phase 2 | Pending |
| PRIV-01 | Phase 2 | Pending |
| LLM-01 | Phase 4 | Pending |
| LLM-02 | Phase 4 | Pending |
| LLM-03 | Phase 4 | Pending |
| LLM-04 | Phase 4 | Pending |
| LLM-05 | Phase 4 | Pending |
| LLM-06 | Phase 4 | Pending |
| OUT-01 | Phase 5 | Pending |
| OUT-02 | Phase 5 | Pending |
| OUT-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-10*
*Last updated: 2026-03-10 after roadmap creation (phase assignments finalized)*
