import os
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

from docgen.config import load_config
from docgen.ui import spinner

app = typer.Typer(
    help="Generate documentation for your codebase.",
    pretty_exceptions_show_locals=False,
)
console = Console()


@app.command()
def run(
    path: str = typer.Argument(..., help="Path to the repository to index and document"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="Where to save documentation"),
):
    """Index a repository and generate full documentation."""
    from docgen.config import load_config
    from docgen.ingest import run_ingest
    from docgen.parser import parse_directory
    from docgen.runner import group_chunks_by_module, generate_all_docs
    from docgen.writer import write_docs
    from docgen.store import VectorRepository
    from docgen.llm import get_provider
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.table import Table
    import asyncio

    # 1. Config & Paths
    load_config()
    repo_path = Path(path).resolve()
    out_path = Path(output_dir).resolve() if output_dir else repo_path / "docs"

    # 2. Ingest
    ingest_result = run_ingest(str(repo_path))
    
    # 3. Prepare Generation
    with spinner("Analyzing project structure..."):
        chunks = parse_directory(repo_path)
        module_groups = group_chunks_by_module(chunks, str(repo_path))
        repo = VectorRepository(chroma_dir=str(repo_path / ".chroma"))
        provider_name = os.getenv("DOCGEN_PROVIDER", "gemini")
        provider = get_provider(provider_name)
    
    # 4. Generate with Progress
    total_tasks = len(module_groups) + 1 # +1 for README
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task_id = progress.add_task("Generating documentation...", total=total_tasks)
        
        readme_md, module_docs = asyncio.run(
            generate_all_docs(
                module_groups, 
                repo, 
                provider, 
                provider_name,
                output_dir=out_path,
                upserted_files=ingest_result["upserted_files"],
                on_progress=lambda: progress.advance(task_id)
            )
        )

    # 5. Write
    written = write_docs(readme_md, module_docs, list(module_groups.keys()), out_path, repo_path)
    
    # 6. Report
    table = Table(title="DocGen Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Phase", style="cyan")
    table.add_column("Result", style="green")
    
    table.add_row("Ingestion", f"{ingest_result['upserted']} updated, {ingest_result['skipped']} skipped")
    table.add_row("Generation", f"{len(module_docs)} modules ready")
    table.add_row("Files Written", f"{len(written)} Markdown files")
    table.add_row("Output Dir", str(out_path))
    
    console.print("\n")
    console.print(table)


@app.command()
def generate(
    path: str = typer.Argument(..., help="Path to the repository"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="Where to save documentation"),
):
    """(Re)Generate documentation from an existing index."""
    from docgen.config import load_config
    from docgen.runner import file_path_to_module_name, generate_all_docs
    from docgen.writer import write_docs
    from docgen.store import VectorRepository
    from docgen.llm import get_provider
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    import asyncio

    load_config()
    repo_path = Path(path).resolve()
    out_path = Path(output_dir).resolve() if output_dir else repo_path / "docs"
    
    repo = VectorRepository(chroma_dir=str(repo_path / ".chroma"))
    if repo.count() == 0:
        typer.secho("Error: No index found. Please run 'docgen run' first.", fg=typer.colors.RED)
        raise typer.Exit(1)
        
    with spinner("Recovering modules from index..."):
        file_paths = repo.list_files()
        module_groups = {file_path_to_module_name(fp, str(repo_path)): [] for fp in file_paths}
    
    provider_name = os.getenv("DOCGEN_PROVIDER", "gemini")
    provider = get_provider(provider_name)
    
    total_tasks = len(module_groups) + 1
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task_id = progress.add_task("Regenerating docs...", total=total_tasks)
        
        # In 'generate' mode, force update by passing upserted_files=None
        readme_md, module_docs = asyncio.run(
            generate_all_docs(
                module_groups, 
                repo, 
                provider, 
                provider_name,
                on_progress=lambda: progress.advance(task_id)
            )
        )

    written = write_docs(readme_md, module_docs, out_path, repo_path)
    typer.secho(f"\nSuccess! {len(written)} files generated in {out_path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
