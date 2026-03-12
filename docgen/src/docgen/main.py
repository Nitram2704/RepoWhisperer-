import typer

from docgen.config import load_config
from docgen.ui import spinner

app = typer.Typer(
    help="Generate documentation for your codebase.",
    pretty_exceptions_show_locals=False,
)


@app.command()
def run(path: str = typer.Argument(..., help="Path to source directory")):
    """Scan, embed, and generate docs in one step."""
    cfg = load_config()
    with spinner("Running full pipeline..."):
        pass
    typer.echo("Pipeline complete.")


@app.command()
def index(path: str = typer.Argument(..., help="Path to source directory")):
    """Build the vector index without generating docs."""
    with spinner("Indexing..."):
        pass
    typer.echo("Indexing complete.")


@app.command()
def generate():
    """Generate docs from an existing index."""
    cfg = load_config()
    with spinner("Generating documentation..."):
        pass
    typer.echo("Generation complete.")


if __name__ == "__main__":
    app()
