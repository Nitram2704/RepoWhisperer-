```markdown
## Module `src.docgen.writer`

### `write_docs` function

```python
def write_docs(
    readme_md: str, 
    module_docs: Dict[str, str], 
    output_dir: Path, 
    project_dir: Path
) -> List[Path]
```

Orchestrates the writing of all documentation files.

**Parameters:**

-   `readme_md` (str): The content of the README file.
-   `module_docs` (Dict[str, str]): A dictionary mapping module names to their documentation content.
-   `output_dir` (Path): The directory where the documentation files will be written.
-   `project_dir` (Path): The root directory of the project.

**Returns:**

-   List[Path]: A list of paths to the written documentation files.

### `generate_module_map` function

```python
def generate_module_map(module_docs: Dict[str, str]) -> str
```

Generates a Markdown table of contents for README.md.

**Parameters:**

-   `module_docs` (Dict[str, str]): A dictionary mapping module names to their documentation content.

**Returns:**

-   str: A Markdown string representing the module map.
```