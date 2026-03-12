# API Documentation for `src.docgen.parser.python_parser`

## Functions

### `parse_python`

```python
def parse_python(path: Path, source: str) -> list[CodeChunk]
```

Parse a Python source file and extract functions and classes as `CodeChunk` objects.

**Parameters:**

-   `path` (`Path`): The path to the Python file.
-   `source` (`str`): The source code of the Python file.

**Returns:**

-   `list[CodeChunk]`: A list of `CodeChunk` objects representing the functions and classes found in the file. Returns an empty list if a `SyntaxError` is encountered during parsing.

## Classes

### `_ChunkVisitor`

```python
class _ChunkVisitor(ast.NodeVisitor)
```

AST Visitor that extracts functions and classes into `CodeChunk` objects.

**Methods:**

#### `__init__`

```python
def __init__(self, source_lines: list[str], file_path: str, parent: Optional[str] = None)
```

Initializes the `_ChunkVisitor`.

**Parameters:**

-   `source_lines` (`list[str]`): A list of strings, where each string is a line of the source code.
-   `file_path` (`str`): The path to the file being visited.
-   `parent` (`Optional[str]`, default: `None`): The name of the parent node (e.g., class name for methods), or `None` if the node is at the top level.

#### `visit_FunctionDef`

```python
def visit_FunctionDef(self, node: ast.FunctionDef) -> None
```

Visits a function definition node in the AST and extracts it as a `CodeChunk`.  Also recursively visits any nested function definitions.

**Parameters:**

-   `node` (`ast.FunctionDef`): The function definition node.

#### `visit_AsyncFunctionDef`

```python
def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None
```

Visits an async function definition node in the AST and extracts it as a `CodeChunk`. Also recursively visits any nested function definitions.

**Parameters:**

-   `node` (`ast.AsyncFunctionDef`): The async function definition node.

#### `visit_ClassDef`

```python
def visit_ClassDef(self, node: ast.ClassDef) -> None
```

Visits a class definition node in the AST and extracts it as a `CodeChunk`. Also recursively visits any method definitions inside the class.

**Parameters:**

-   `node` (`ast.ClassDef`): The class definition node.

#### `_extract_content`

```python
def _extract_content(self, node: ast.AST) -> str
```

Extracts the source code content of a given AST node.

**Parameters:**

-   `node` (`ast.AST`): The AST node to extract the content from.

**Returns:**

-   `str`: The source code content of the node, as a single string with newlines.
