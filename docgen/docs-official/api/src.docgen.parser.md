# API Documentation for `src.docgen.parser`

## `src.docgen.parser` Package

This module contains functions and classes for parsing source code files of different languages and extracting code chunks.

## Functions

### `parse_file(path: Path, source: str) -> list[CodeChunk]`

Dispatches a file to the correct parser based on its extension.

*   **Parameters:**
    *   `path` (`Path`): The path to the file.
    *   `source` (`str`): The content of the file.
*   **Returns:**
    *   `list[CodeChunk]`: A list of `CodeChunk` objects representing the extracted code elements, or an empty list if the file type is not supported.

### `build_gitignore_spec(repo_root: Path) -> pathspec.PathSpec`

Builds a pathspec from the repository's `.gitignore` file if it exists.

*   **Parameters:**
    *   `repo_root` (`Path`): The root directory of the repository.
*   **Returns:**
    *   `pathspec.PathSpec`: A `PathSpec` object representing the gitignore rules.  Returns an empty `PathSpec` if no `.gitignore` file is found.

### `parse_python(path: Path, source: str) -> list[CodeChunk]`

Parses a Python source file and extracts functions and classes as `CodeChunk` objects.

*   **Parameters:**
    *   `path` (`Path`): The path to the Python file.
    *   `source` (`str`): The content of the Python file.
*   **Returns:**
    *   `list[CodeChunk]`: A list of `CodeChunk` objects representing the extracted functions and classes. Returns an empty list if a syntax error is encountered.

### `parse_js_ts(path: Path, source: str) -> list[CodeChunk]`

Parses JavaScript, TypeScript, or TSX files using Tree-Sitter and extracts code chunks.

*   **Parameters:**
    *   `path` (`Path`): The path to the JavaScript/TypeScript file.
    *   `source` (`str`): The content of the JavaScript/TypeScript file.
*   **Returns:**
    *   `list[CodeChunk]`: A list of `CodeChunk` objects representing the extracted code elements.

## Classes

### `_ChunkVisitor(ast.NodeVisitor)`

AST Visitor that extracts functions and classes into `CodeChunk` objects.

*   **Inheritance:** `ast.NodeVisitor`

    *   **`__init__(self, source_lines: list[str], file_path: str, parent: Optional[str] = None)`**
        *   **Parameters:**
            *   `source_lines` (`list[str]`): A list of strings representing the lines of source code.
            *   `file_path` (`str`): The path to the file being parsed.
            *   `parent` (`Optional[str]`): The name of the parent element (e.g., class name for methods). Defaults to `None`.
        *   Initializes the visitor with the source code lines and file path.

    *   **`_extract_content(self, node: ast.AST) -> str`**
        *   **Parameters:**
            *   `node` (`ast.AST`): The AST node to extract content from.
        *   **Returns:**
            *   `str`: The source code content corresponding to the given AST node.
        *   Extracts the source code content from the given AST node based on its line numbers.

    *   **`visit_FunctionDef(self, node: ast.FunctionDef) -> None`**
        *   **Parameters:**
            *   `node` (`ast.FunctionDef`): The AST node representing a function definition.
        *   Extracts information from a function definition node and stores it as a `CodeChunk`. Also handles nested function definitions.

    *   **`visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None`**
        *   **Parameters:**
            *   `node` (`ast.AsyncFunctionDef`): The AST node representing an asynchronous function definition.
        *   Extracts information from an async function definition node and stores it as a `CodeChunk`. Also handles nested async function definitions.

    *   **`visit_ClassDef(self, node: ast.ClassDef) -> None`**
        *   **Parameters:**
            *   `node` (`ast.ClassDef`): The AST node representing a class definition.
        *   Extracts information from a class definition node and stores it as a `CodeChunk`. Also handles methods inside the class.
