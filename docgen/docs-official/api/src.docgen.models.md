# API Documentation for `src.docgen.models`

Since there is no explicit `models.py` file, I will generate the documentation based on the data models (`CodeChunk`) used in other modules, specifically the `src.docgen.parser.python_parser` module.

## Data Models

### CodeChunk

The `CodeChunk` data model is implicitly used within the `src.docgen.parser.python_parser` module (specifically in the `_ChunkVisitor` class). It represents a code snippet extracted from a file.  While the code doesn't explicitly define a class named `CodeChunk`, it's structure can be inferred from its usage.

**Fields (Inferred):**

*   `file_path`: `str` - The path to the file containing the code chunk.
*   `language`: `str` - The programming language of the code chunk (e.g., "python").
*   `chunk_type`: `str` - The type of code chunk (e.g., "function", "class").
*   `name`: `str` - The name of the code chunk (e.g., the function or class name).
*   `content`: `str` - The actual code content of the chunk.
*   `start_line`: `int` - The starting line number of the code chunk in the file.
*   `end_line`: `int` - The ending line number of the code chunk in the file.
*   `docstring`: `str` (Optional) - The docstring associated with the code chunk, if any.
*   `parent`: `str` (Optional) - The name of the parent element (e.g., the class name if the chunk is a method).

**Usage Example:**

```python
chunk = CodeChunk(
    file_path="example.py",
    language="python",
    chunk_type="function",
    name="my_function",
    content="def my_function():\n  pass",
    start_line=1,
    end_line=2,
    docstring="A simple function",
    parent=None
)
```

**Note:**

The `CodeChunk` is implicitly constructed within the `_ChunkVisitor` class. The exact method of instantiation and the presence of a formal class definition are not available in the provided code snippets. This documentation infers the existence and structure of `CodeChunk` from its context within the parser.
