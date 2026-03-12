# API Documentation for `src.docgen.parser.js_parser`

## Functions

### `parse_js_ts(path: Path, source: str) -> list[CodeChunk]`

Parse JavaScript, TypeScript, or TSX files using Tree-Sitter.

**Parameters:**

-   `path` (`Path`): The path to the JavaScript/TypeScript file.
-   `source` (`str`): The source code of the file.

**Returns:**

`list[CodeChunk]`: A list of `CodeChunk` objects representing the extracted code elements (functions, classes, etc.).
