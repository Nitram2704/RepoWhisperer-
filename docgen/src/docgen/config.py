import os

import typer
from dotenv import load_dotenv
from rich.console import Console

_error = Console(stderr=True)


def load_config() -> dict:
    """Load configuration from environment variables or .env file.

    Returns a dict with the API key. Exits with code 1 and a styled
    error message on stderr if DOCGEN_API_KEY is not set.
    """
    load_dotenv()
    api_key = os.getenv("DOCGEN_API_KEY")
    if not api_key:
        _error.print(
            "[bold red]Error:[/bold red] DOCGEN_API_KEY environment variable is not set.\n"
            "Add it to your shell environment or create a .env file with:\n\n"
            "  DOCGEN_API_KEY=your-key-here"
        )
        raise typer.Exit(code=1)
    return {"api_key": api_key}
