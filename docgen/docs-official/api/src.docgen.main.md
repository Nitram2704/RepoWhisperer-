# API Documentation for `src.docgen.main`

## Functions

### `generate`

```python
def generate(path: str = typer.Argument(..., help="Path to the repository"), output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="Where to save documentation"))
```

**(Re)Generate documentation from an existing index.**

This function regenerates documentation for a project based on an existing index. It uses a vector repository to retrieve file paths, generates documentation using an LLM provider, and writes the generated documentation to files.

**Parameters:**

-   `path` (*str*): Path to the repository. This is a required argument.
-   `output_dir` (*Optional[str]*): Where to save documentation. If not provided, defaults to a "docs" directory within the repository.

**Raises:**

-   `typer.Exit`: If no index is found (meaning `docgen run` hasn't been executed).

**Example Usage:**

```bash
docgen generate /path/to/your/repo --output-dir /path/to/output
```
