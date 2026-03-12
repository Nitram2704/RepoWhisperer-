```markdown
## API Documentation for `src.docgen.writer`

This module provides functions for writing the generated documentation to files.

### `write_docs` function

```python
def write_docs(
    readme_md: str, 
    module_docs: Dict[str, str], 
    all_module_names: List[str],
    output_dir: Path, 
    project_dir: Path
) -> List[Path]:
```

Orchestrates the writing of all documentation files.

**Parameters:**

-   `readme_md` (`str`): The content of the README file.
-   `module_docs` (`Dict[str, str]`): A dictionary mapping module names to their documentation content.
-   `all_module_names` (`List[str]`): A list of all module names in the project.
-   `output_dir` (`Path`): The directory where the documentation files should be written.
-   `project_dir` (`Path`): The root directory of the project.

**Returns:**

`List[Path]`: A list of the paths to the written documentation files.

### `generate_module_map` function

```python
def generate_module_map(module_names: List[str]) -> str:
```

Generates a Markdown table of contents for README.md.

**Parameters:**

-   `module_names` (`List[str]`): A list of module names.

**Returns:**

`str`: A Markdown string representing the module map.  Returns an empty string if `module_names` is empty.
```