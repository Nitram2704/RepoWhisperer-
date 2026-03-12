```markdown
## API Documentation for `src.docgen.runner`

This module does not explicitly define any classes or functions. However, it is used in other modules. The documentation below is based on how it is used.

### Functions used in `src.docgen.main`

*   **`file_path_to_module_name(file_path, root)`**

    This function is used to convert a file path to a module name. The exact implementation is not available in the provided code.
    From `test_runner.py`:
    ```python
    def test_file_path_to_module_name():
        root = "C:/repo"
        assert file_path_to_module_name("C:/repo/src/docgen/main.py", root) == "src.docgen.main"
        assert file_path_to_module_name("C:/repo/src/docgen/__init__.py", root) == "src.docgen"
        assert file_path_to_module_name("C:/repo/README.md", root) == "README"
    ```
    Based on the test, the function likely:
    *   Removes the `root` prefix from `file_path`.
    *   Replaces path separators with dots.
    *   Removes the `.py` extension.
    *   Returns `"README"` for `README.md` files.

*   **`generate_all_docs(module_groups, repo, provider, provider_name, output_dir, upserted_files, on_progress)`**

    This is an `async` function that generates documentation for all modules. The exact implementation is not available in the provided code.

    Parameters:
        *   `module_groups`:  A dictionary mapping module names to a list of code chunks.
        *   `repo`: A `VectorRepository` instance.
        *   `provider`: An LLM provider (e.g., Gemini).
        *   `provider_name`: The name of the LLM provider.
        *   `output_dir`: The output directory for the generated documentation.
        *   `upserted_files`: A list of files that were upserted during the ingest phase.
        *   `on_progress`: A callback function to update the progress bar.
    Returns:
        *   `readme_md`: String containing the generated README.md content.
        *   `module_docs`: A dictionary mapping module names to their documentation content.

*   **`group_chunks_by_module(chunks, root)`**

    This function groups code chunks by module. The exact implementation is not available in the provided code.

    Parameters:
        * `chunks`: list of `CodeChunk` objects.
        * `root`: The root path of the repository.

    Returns:
        * A dictionary where keys are module names and values are lists of `CodeChunk` objects belonging to that module.
```