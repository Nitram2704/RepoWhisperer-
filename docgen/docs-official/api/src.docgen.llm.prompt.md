```markdown
## `src.docgen.llm.prompt`

### `format_user_prompt(query: str, code_chunks: list[dict], skeleton: list[str] | None = None, char_limit: int = 32000) -> str`

Formats the user message with optional project skeleton.

**Args:**

-   `query`: User's documentation request (e.g., "Generate README").
-   `code_chunks`: List of dictionaries with 'content', 'file_path', 'name', 'chunk_type'.
-   `skeleton`: List of strings (paths/names) representing the project structure.
-   `char_limit`: Max characters before truncation.

**Returns:**

A string containing the formatted prompt, truncated if it exceeds the character limit. The return also includes a truncation message.
```
