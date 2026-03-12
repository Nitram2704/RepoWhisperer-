```markdown
## `src.docgen.parser.filter`

### `build_gitignore_spec(repo_root: Path) -> pathspec.PathSpec`

Build a pathspec from the repository's .gitignore file if it exists.

**Parameters:**

-   `repo_root` (`Path`): The root directory of the repository.

**Returns:**

-   `pathspec.PathSpec`: A pathspec object representing the gitignore rules. Returns an empty pathspec if no .gitignore file is found.
```