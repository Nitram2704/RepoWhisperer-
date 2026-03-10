# Feature Landscape

**Domain:** CLI code documentation generator (RAG-based, local-first, AI-generated Markdown)
**Researched:** 2026-03-10
**Confidence note:** Research tools (WebSearch, WebFetch) were unavailable in this session. All findings are based on trained knowledge (cutoff August 2025) of Sphinx, JSDoc, Dokka, Mintlify, Docsify, TypeDoc, pydoc-markdown, and AI doc tools (Mintlify Scraper, Swimm, CodeSee, Docify). Confidence levels reflect this. For competitive positioning, verify with current tool changelogs before roadmap phase 2+.

---

## Table Stakes

Features users expect from any serious documentation generator. Missing = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-file repository scan | Every doc tool scans a directory, not one file at a time | Low | Walk directory tree, respect .gitignore patterns |
| README.md generation | The single most-requested output; absence is a dealbreaker | Medium | Needs project-level summary: what it is, how to install, usage example |
| Per-module / per-file API docs | Sphinx, JSDoc, TypeDoc all do this; users expect module-scoped output | Medium | One .md per source file or logical module in /docs |
| Structured Markdown output | Output must be valid, readable Markdown — not raw prose blobs | Low | Headers, code blocks, parameter tables are expected format |
| Sensitive file exclusion | .env, *.key, secrets — users won't trust any tool that risks leaking these | Low | Blocklist of filename patterns; must run before any embedding or LLM call |
| Configurable LLM provider | Single hard-wired provider is a hard blocker for many users | Low | env var or config file; at minimum two providers (Gemini + Groq) |
| CLI entry point with path argument | `docgen ./my-project` — one-command UX is the whole value prop | Low | argparse or Typer; must accept path and produce output without further prompts |
| Progress feedback during run | Silent 2-minute runs feel broken; users kill the process | Low | Per-file progress bar or step log (e.g. tqdm or rich) |
| Idempotent / safe output | Never modify source files; output only in /docs | Low | Non-destructive is a hard user trust requirement |
| Python + JS/TS language support | Target users have polyglot repos; single-language tools feel limited | Medium | AST-level parsing preferred over regex for accuracy |

**Confidence:** HIGH — these features appear consistently across Sphinx, JSDoc, TypeDoc, pydoc-markdown, and user expectations in community discussions I was trained on.

---

## Differentiators

Features that make this tool stand out. Not universally expected, but create meaningful competitive advantage for the RAG-based, privacy-first positioning.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| RAG-based context selection | Avoids sending entire codebase to LLM; respects free-tier token limits and privacy | High | Core architectural differentiator; ChromaDB embedding + semantic retrieval per-module |
| Privacy-first local execution | No cloud service, no account, no telemetry — developer owns their data | Low | Framing and marketing; enforced by architecture (local ChromaDB, no server required) |
| Free-tier LLM routing | Works with $0/month spend (Gemini free, Groq free) — unlike GitHub Copilot Workspace or Mintlify AI | Medium | Rate-limit awareness (retry with backoff); configurable provider fallback |
| Incremental / smart re-generation | Only regenerate docs for files changed since last run | High | Requires storing file hash → ChromaDB collection metadata; reduces LLM calls dramatically |
| Doc quality scoring / stale detection | Flag docs that are likely out of date (source changed, doc not regenerated) | Medium | Compare embedding similarity of current code vs stored doc content |
| Cross-file relationship summary | "This module is used by X, Y, Z" — inferred from import graph, not just comments | High | Build import dependency graph; enrich LLM prompt with caller/callee context |
| Configurable output templates | Let users customize README structure (badges, contributing section, license section) | Medium | Jinja2 template system; ship sensible defaults |
| Provider fallback chain | If Gemini fails or hits rate limit, automatically retry with Groq | Medium | Increases reliability without requiring manual intervention |
| Verbose / debug mode | Show which chunks were retrieved, what prompt was sent — essential for power users who want to audit output | Low | --verbose flag; log retrieved context and prompt to stderr |
| `.docgenignore` support | Explicit user control over what to exclude beyond the default blocklist | Low | gitignore-style pattern file; maps to user expectation from other tools |

**Confidence:** MEDIUM — RAG-based doc generation is an emerging pattern (Swimm, Docify, Mintlify AI Writer exist as of mid-2025). Incremental generation and cross-file relationship analysis are differentiated relative to those tools based on training data; verify against current Mintlify/Swimm feature sets before finalizing positioning.

---

## Anti-Features

Features to deliberately NOT build — they would increase scope, undermine the tool's positioning, or pull toward a different product entirely.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Inline comment injection | Modifies source files — breaks user trust, violates non-destructive contract, and is reversible only with git | Output external Markdown only; never touch source |
| Web UI or dashboard | Contradicts CLI/local-first positioning; massive scope increase | Keep it a CLI; if a web view is wanted, open the /docs folder in a browser |
| Cloud sync or hosted docs | Violates privacy-first constraint; becomes a SaaS product, not a dev tool | Let users push /docs to GitHub Pages themselves |
| Training or fine-tuning models | Inference only; training requires cloud infra, GPUs, and data pipelines | Use free-tier inference APIs as designed |
| Real-time watch mode | File watcher + incremental re-generation adds significant complexity; v1 is not ready for it | Single-run CLI; watch mode is a v2+ feature if validated |
| Java/Kotlin/Go/Rust parsers | Language surface area multiplies maintenance; Python + JS/TS covers most individual developers | Explicitly document supported languages; design parser interface to be extensible |
| GUI installer or .exe bundling | Adds packaging complexity for no developer-experience gain; target users are comfortable with `pip install` | Ship as a PyPI package |
| Paid API enforcement | Users chose this tool to avoid cost; any path that requires a paid key kills adoption | Document free-tier setup clearly; never default to a model that requires billing |
| Semantic versioning of generated docs | Auto-versioning docs from git tags adds significant complexity and is not core value | Let users manage versioning via git |
| Chat / Q&A interface over codebase | Different product (code assistant) — competes with Cursor, Copilot, not documentation tools | Stay in document generation lane |

**Confidence:** HIGH — these are well-understood scope boundaries derived from the stated constraints in PROJECT.md and from observing where documentation tools get overextended.

---

## Feature Dependencies

```
CLI entry point (--path, --provider flags)
  └── File scanner (walk repo)
        └── Sensitive file filter (MUST run first, before any processing)
              └── Language parser (Python AST / JS/TS AST)
                    └── Code chunker (split into embeddable units)
                          └── ChromaDB embedder (store chunks + metadata)
                                └── RAG retriever (query relevant chunks per module)
                                      └── LLM generator (prompt + chunks → Markdown)
                                            └── Markdown writer (/docs output)
                                                  └── Progress feedback (wraps all steps)

Configurable LLM provider
  └── Provider fallback chain (optional, adds retry logic on top)

Incremental re-generation
  └── File hash storage (requires ChromaDB metadata or sidecar file)
  └── ChromaDB embedder (re-use existing embeddings for unchanged files)

Cross-file relationship summary
  └── Language parser (must extract import statements)
  └── Import graph builder (new component, not in MVP pipeline)
  └── RAG retriever (enriched prompt)

Configurable output templates
  └── Markdown writer (Jinja2 layer on top of base writer)

Doc quality scoring / stale detection
  └── ChromaDB embedder (existing doc embedding must be stored)
  └── Code chunker (current source embedding must be computable)
```

---

## MVP Recommendation

The MVP must prove the core value prop: **one command → accurate, readable docs from any local Python/JS repo, free, private.**

**Prioritize (MVP):**
1. CLI entry point with --path and --provider flags
2. File scanner + sensitive file filter
3. Python + JS/TS AST parser (basic: functions, classes, docstrings/JSDoc comments)
4. Code chunker + ChromaDB embedder
5. RAG retriever (per-module context selection)
6. LLM generator for README + per-module API docs (Gemini + Groq)
7. Markdown writer to /docs
8. Progress feedback (tqdm or rich)
9. .docgenignore support

**Defer (post-MVP, validate demand first):**
- Incremental re-generation: High value but high complexity; requires hash storage design. Add in phase 2.
- Cross-file relationship summary: High complexity; requires import graph. Add only if users report docs feel context-free.
- Provider fallback chain: Medium complexity; adds reliability but isn't a day-one need.
- Configurable output templates: Nice-to-have; default template covers 80% of users. Phase 2.
- Doc quality scoring / stale detection: Clever feature but users must first experience the tool generating docs before they'll care about staleness.

**Never build (anti-features above):** Inline injection, web UI, cloud sync, watch mode in v1, non-Python/JS languages in v1.

---

## Competitive Positioning Summary

| Tool | Generation Method | Privacy | Cost | Output |
|------|------------------|---------|------|--------|
| Sphinx | Docstring extraction | Local | Free | HTML/PDF |
| JSDoc / TypeDoc | Comment extraction | Local | Free | HTML/JSON |
| pydoc-markdown | Docstring extraction | Local | Free | Markdown |
| Mintlify | AI-assisted, cloud | Cloud | Paid tier | Hosted docs |
| Swimm | AI doc sync, cloud | Cloud | Paid tier | In-repo + portal |
| **DocGen CLI (this)** | **RAG + free LLM** | **Local** | **Free** | **Markdown** |

The gap this fills: Sphinx/JSDoc require well-commented code; Mintlify/Swimm require cloud and payment. DocGen CLI generates useful docs even from poorly-commented code and runs entirely locally for free.

**Confidence:** MEDIUM — Mintlify and Swimm pricing/feature tiers may have changed since August 2025; verify before using in marketing copy.

---

## Sources

- Training knowledge of Sphinx 7.x, JSDoc 4.x, TypeDoc 0.25.x, pydoc-markdown 4.x, Mintlify, Swimm, Docify, CodeSee (as of August 2025 cutoff)
- PROJECT.md at C:/Users/marti/Visual/Documentacion/.planning/PROJECT.md (authoritative for this project's constraints)
- Note: WebSearch and WebFetch were unavailable during this session. WebSearch verification recommended for Mintlify AI Writer, Swimm, and any new entrants before phase 2 competitive analysis.
