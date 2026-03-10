# Research: Phase 3 - Ingest Pipeline

## Objective
Verify the requirements and technical approach for embedding code chunks locally and persisting them in ChromaDB.

## Technical Findings

### ChromaDB 0.5.x API
- Standard usage now requires `PersistentClient`.
- Collection creation: `client.get_or_create_collection(name="docgen", embedding_function=...)`.
- Data insertion: `collection.add(ids=..., documents=..., metadatas=...)`.

### Local Embeddings
- `fastembed` is preferred over `sentence-transformers` for CLI tools because it has fewer dependencies and is highly optimized for CPU.
- Supported models: `BAAI/bge-small-en-v1.5` (very lightweight and effective for code/text).

### Hash-based Skipping (Incremental Indexing)
- Store a hash of each `CodeChunk.content` in the metadata.
- Before embedding, check if the file/chunk already exists with the same hash.
- If hash matches, skip embedding and insertion.

### Locking Mechanism
- Use a simple file lock (e.g., `.chroma/lock`) to prevent concurrent writes from different CLI instances.

## Risks & Mitigations
- **Binary Bloat**: `fastembed` downloads models on first use. We should ensure the user is notified during the first `docgen index` run.
- **Corrupt DB**: Ensure graceful shutdown and file locking.
