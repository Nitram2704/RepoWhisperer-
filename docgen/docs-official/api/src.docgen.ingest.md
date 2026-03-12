```markdown
## Module: src.docgen.ingest

### `run_ingest(repo_path: str, chroma_dir: Optional[str] = None) -> dict`

Orchestrates the full parse -> embed -> store pipeline.

**Args:**

-   `repo_path`: Absolute path to the repository root.
-   `chroma_dir`: Optional path for ChromaDB storage.

**Returns:**

Summary dictionary of the ingestion results, containing:

-   `parsed`: The number of files parsed.
-   `skipped`: The number of unchanged chunks skipped.
-   `upserted`: The number of new or changed chunks upserted.
-   `upserted_files`: A list of files that were upserted.

**Raises:**

-   `typer.Exit`: If the repository path is invalid or if another docgen process holds a lock on the vector store.
```