# DocGen CLI

## What This Is

A local CLI tool that scans a code repository and auto-generates README and per-module API documentation as Markdown files. It uses RAG (Retrieval-Augmented Generation) to embed and query code, then calls a free-tier LLM API (Google Gemini or Groq/Llama 3) to produce human-readable docs. Designed for individual developers documenting their own projects.

## Core Value

A developer runs one command and gets accurate, up-to-date README and API docs written to their repo — without sending their full codebase to a cloud service.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can run a CLI command targeting a local repo path and receive generated docs
- [ ] Tool parses Python (.py) and JavaScript/TypeScript (.js/.ts/.tsx) source files
- [ ] Tool generates README.md summarizing the project
- [ ] Tool generates per-module API reference docs as Markdown files in a /docs folder
- [ ] Tool uses RAG: embeds code chunks into ChromaDB, queries relevant context for generation
- [ ] LLM provider is configurable — supports Google Gemini and Groq (Llama 3)
- [ ] API key is stored securely (env variable or local config file, never hardcoded)
- [ ] Sensitive files are excluded from processing (e.g. .env, secrets, credentials)
- [ ] Tool processes 50 files in under 2 minutes on a standard developer machine

### Out of Scope

- Cloud hosting or SaaS version — local execution only, privacy constraint
- Training or fine-tuning models — inference only
- Inline comment injection into source files — output is separate Markdown only
- Real-time / watch mode — single-run CLI, no file watcher
- Java/Kotlin or other languages in v1 — Python and JS/TS first

## Context

- **Architecture:** Single executable CLI, monolithic but internally modular (parser, embedder, retriever, generator, writer modules). Designed for future extensibility.
- **Vector DB:** ChromaDB (embedded, no server required) — chosen for native embedding support and local-only operation.
- **LLM APIs:** Google Gemini free tier and Groq free tier (Llama 3). User configures which provider via env var or config.
- **Privacy:** Codebase stays local. Only chunked context (not full files) is sent to LLM API for generation. Sensitive file patterns (.env, *.key, *.pem, etc.) are blocklisted.
- **Performance target:** 50 files documented in under 2 minutes.

## Constraints

- **Execution:** Local only — no cloud infrastructure, no Docker required
- **LLM cost:** Free-tier APIs only — must respect rate limits, minimize token usage
- **Vector DB:** Open-source embedded DB — ChromaDB (no paid services)
- **Data privacy:** Sensitive files must never be processed or sent to external APIs
- **Performance:** 50 files < 2 minutes on a typical developer laptop

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Monolithic CLI with modular internals | Single-user local tool; simpler for MVP, modular for future extension | — Pending |
| ChromaDB for vector storage | Embedded, open-source, designed for embeddings, easy local setup | — Pending |
| Pluggable LLM provider (Gemini + Groq) | Free-tier constraint; user may prefer one over the other | — Pending |
| RAG over full-file prompting | Stays within free-tier token limits; improves relevance of generated docs | — Pending |
| Output as separate Markdown files | Non-destructive; doesn't modify source code | — Pending |

---
*Last updated: 2026-03-10 after initialization*
