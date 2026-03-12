from pathlib import Path
from typing import Optional

import typer
from filelock import Timeout

from docgen.embedder import Embedder
from docgen.parser import parse_directory
from docgen.store import VectorRepository
from docgen.ui import spinner


def run_ingest(repo_path: str, chroma_dir: Optional[str] = None) -> dict:
    """Orchestrate the full parse -> embed -> store pipeline.
    
    Args:
        repo_path: Absolute path to the repository root.
        chroma_dir: Optional path for ChromaDB storage.
        
    Returns:
        Summary dictionary of the ingestion results.
    """
    repo_root = Path(repo_path).resolve()
    if not repo_root.is_dir():
        typer.secho(f"Error: {repo_path} is not a valid directory.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Use repo root for .chroma storage if not specified
    db_path = chroma_dir or str(repo_root / ".chroma")

    try:
        # 1. Parse
        with spinner(f"Scanning {repo_root.name}..."):
            chunks = parse_directory(repo_root)
        
        if not chunks:
            typer.echo("No parseable files found matching supported extensions.")
            return {"parsed": 0, "skipped": 0, "upserted": 0}

        # 2. Embed (Lazy init model here)
        with spinner(f"Computing embeddings for {len(chunks)} chunks..."):
            embedder = Embedder()
            texts = [chunk.content for chunk in chunks]
            embeddings = embedder.embed(texts)

        # 3. Store
        with spinner("Updating vector database..."):
            try:
                store = VectorRepository(chroma_dir=db_path)
                results = store.upsert_chunks(chunks, embeddings)
            except Timeout:
                typer.secho(
                    "\nError: Another docgen process holds the lock on the vector store.",
                    fg=typer.colors.RED,
                    err=True
                )
                raise typer.Exit(code=1)

        # Final Report
        typer.echo(
            f"Successfully indexed project: "
            f"{results['upserted']} new/changed, {results['skipped']} unchanged."
        )
        
        return {
            "parsed": len(chunks),
            "skipped": results["skipped"],
            "upserted": results["upserted"],
            "upserted_files": results.get("upserted_files", [])
        }

    except Exception as e:
        typer.secho(f"\nIngestion failed: {str(e)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
