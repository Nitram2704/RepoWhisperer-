# PLAN: Phase 3 Execution Audit

Detailed audit and refinement plan for the Ingest Pipeline (Phase 3). This plan ensures the transition from Phase 2 (Parser) to Phase 4 (Generation) is robust and efficient.

## Phase -1: Context Check
- **User Goal**: Deeply review and verify Phase 3 plans (`03-01` and `03-02`).
- **Dependencies**: Parser (Phase 2) must be verified (Completed).
- **Environment**: Python 3.10+, `uv` for package management.

## Phase 0: Socratic Gate
1. **Deduplication Range**: Should we allow forced re-indexing (e.g., a `--force` flag) in case of metadata corruption?
2. **Metadata Scope**: Do we need to store the `parent` relationship in ChromaDB to enable "Class-aware" retrieval in Phase 4?
3. **Storage Path**: Should the `.chroma/` directory be configurable via CLI, or strictly relative to the repo root?

## Phase 1: Technical Audit & Verification
- [ ] **ChromaDB API Check**: Verify that `PersistentClient` is the current standard for 0.5.x and that `get_or_create_collection` handles threading correctly with the proposed `filelock`.
- [ ] **Hash Robustness**: Ensure the SHA-256 calculation includes the relative path (not absolute) to prevent cross-environment cache misses.
- [ ] **Model Selection**: Confirm `BAAI/bge-small-en-v1.5` is compatible with the `fastembed` v0.4.x API.

## Phase 2: Refined Implementation Steps

### 2.1: Vector Storage Layer (Refinement of 03-01)
- **Component**: `src/docgen/store.py`
- **Action**: Implement `VectorRepository` with:
    - Thread-safe `PersistentClient`.
    - Batch-lookup of IDs before embedding.
    - Explicit `docgen.lock` handling with clear error messages.

### 2.2: Ingest & Embedding (Refinement of 03-02)
- **Component**: `src/docgen/embedder.py`, `src/docgen/ingest.py`
- **Action**:
    - Build `Embedder` wrapper with `fastembed`.
    - Orchestrate `run_ingest` with `rich.progress` to show status across 3 stages: Parse -> Embed -> Store.

## Phase 3: Verification Plan

### Automated Verification
- **Unit Tests**:
    - `test_store_dedup`: Verify that identical content is not stored twice.
    - `test_store_locking`: Simulate concurrent writes and catch `Timeout`.
- **Integration Test**:
    - Run `docgen index` on a sample repo with 5 files.
    - Verify `.chroma/` persistence and content queryability.

### Manual Verification
- Index the `docgen` repo itself.
- Delete one file, re-index, and verify the count decreases (or stale entry handling).
- Disconnect internet and verify embedding still works (Local ONNX check).
