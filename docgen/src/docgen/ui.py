from contextlib import contextmanager

from rich.progress import Progress, SpinnerColumn, TextColumn


@contextmanager
def spinner(description: str):
    """Display an indeterminate spinner while work is being done.

    Usage::

        with spinner("Processing files..."):
            do_work()
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description, total=None)
        yield
