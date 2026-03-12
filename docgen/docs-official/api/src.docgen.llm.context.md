```markdown
## `src.docgen.llm.context`

### `generate_docs(query: str, repo: VectorRepository, provider: Optional[BaseLLMProvider] = None, n_chunks: int = 15, include_skeleton: bool = True) -> str`

Retrieves context and generates documentation via LLM.

**Args:**

-   `query`: What to generate (e.g. 'Generate README').
-   `repo`: The vector repository to query. Type is assumed to be `VectorRepository` but the code does not define it.
-   `provider`: Active LLM provider.  If `None`, it obtains a provider using `docgen.llm.get_provider()`.
-   `n_chunks`: Number of relevant code chunks to retrieve.
-   `include_skeleton`: Whether to include project-wide structure in the prompt.

**Returns:**

-   Generated text as a plain string.

**Details:**

1.  Retrieves relevant code chunks from the vector repository based on the `query`.
2.  Optionally includes a project skeleton (list of file paths) in the prompt. If `include_skeleton` is True, it extracts file paths from retrieved code chunks.
3.  Formats a user prompt using `format_user_prompt` (not defined in the provided code).
4.  Generates documentation using the LLM provider's `generate` method, passing a `SYSTEM_PROMPT` (not defined in the provided code) and the formatted user prompt.
```