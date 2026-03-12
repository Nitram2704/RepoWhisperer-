# PLAN: LLM Generation Refinement (Phase 4)

This plan refines the existing Phase 4 implementation to ensure high-quality documentation and robust handling of free-tier constraints.

## Phase -1: Context Check
- **Phase 3** is complete (Vector Store works).
- **Phase 4** plans 04-01 and 04-02 exist but lack "Global Context" and explicit CLI wiring for `docgen generate`.
- **Constraint**: Free-tier RPM/RPD limits are tight.

## Phase 0: Socratic Gate
1. **Fallback Priority**: If Gemini (1500 RPD) hits a limit, do we want to prompt the user for a second key, or just fail gracefully?
2. **Context Window**: Should we target 8K tokens (safe for all models) or leverage Gemini's 1M window for larger "Global Context"?

## Phase 1: Structured Implementation

### 1.1: Provider Resilience (`src/docgen/llm/`)
- [ ] **Task 1**: Implement `tenacity` retry logic with specific exception mapping for each provider (OpenAI vs Gemini).
- [ ] **Task 2**: Add `model_max_tokens` to provider config to prevent context overflows.

### 1.2: Context Assembly Refinement (`src/docgen/llm/context.py`)
- [ ] **Task 3**: Implement "Skeleton Retrieval": Extract a list of all files and top-level class/function names to include in the README prompt.
- [ ] **Task 4**: Add a `token_counter` helper to ensure we don't send malformed requests to providers with small windows (Groq).

### 1.3: CLI Wiring (`src/docgen/main.py`)
- [ ] **Task 5**: Wire the `generate` command to call `generate_docs`.

## Phase 2: Verification Plan

### Automated Tests
- `uv run pytest tests/test_providers.py` (Mocked API responses).
- `uv run pytest tests/test_context.py` (Verify prompt formatting with large contexts).

### Manual Verification
- `docgen generate <path>` on a sample repo with `DOCGEN_PROVIDER=gemini`.
- Verify that `README.md` includes information from files that weren't "most similar" but are key to the project.
