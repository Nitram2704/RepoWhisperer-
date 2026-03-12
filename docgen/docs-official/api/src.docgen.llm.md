```markdown
## `docgen.llm` Module

This module provides abstractions and implementations for interacting with Large Language Models (LLMs) to generate documentation.

### Submodules
- [docgen.llm.base](./llm.base.md)
- [docgen.llm.context](./llm.context.md)
- [docgen.llm.gemini](./llm.gemini.md)

## `docgen.llm.base`

### `BaseLLMProvider` (class)

```python
class BaseLLMProvider(ABC):
    max_context_chars: int = 32000

    @abstractmethod
    def generate(self, system: str, user: str) -> str:
        pass
```

Abstract base class for all LLM providers.

*   **`max_context_chars`**:  The maximum number of characters allowed in the context window. Defaults to 32000.

#### `generate` (method)

```python
def generate(self, system: str, user: str) -> str:
```

Generate text from a system prompt and user message. This method must be implemented by subclasses.

*   **Args:**
    *   `system` (`str`): System-level instruction (e.g., "You are a tech doc generator").
    *   `user` (`str`): User-level content (e.g., code context + generation request).
*   **Returns:**
    *   `str`: Generated text as a plain string.

## `docgen.llm.context`

### `generate_docs` (function)

```python
def generate_docs(
    query: str, 
    repo: VectorRepository, 
    provider: Optional[BaseLLMProvider] = None,
    n_chunks: int = 15,
    include_skeleton: bool = True
) -> str:
```

Retrieves context and generates documentation via LLM.

*   **Args:**
    *   `query` (`str`): What to generate (e.g. 'Generate README').
    *   `repo` (`VectorRepository`): The vector repository to query.  It's unclear how this class is defined.
    *   `provider` (`Optional[BaseLLMProvider]`, defaults to `None`): Active LLM provider.  If `None`, it attempts to get a provider using `docgen.llm.get_provider()`.
    *   `n_chunks` (`int`, defaults to `15`): Number of relevant code chunks to retrieve.
    *   `include_skeleton` (`bool`, defaults to `True`): Whether to include project-wide structure in the prompt.
*   **Returns:**
    *   `str`: The generated documentation.

## `docgen.llm.gemini`

### `generate` (function)

```python
def generate(self, system: str, user: str) -> str:
```

```
    def generate(self, system: str, user: str) -> str:
        # Latest SDK uses config for system instruction
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user,
            config={"system_instruction": system}
        )
        return response.text
```

No class definition was provided for the `gemini` module.  The `generate` function uses `self.client` and `self.model_name`, suggesting it's part of a class, but the class itself is not defined in the given code.

*   **Args:**
    *   `system` (`str`): System-level instruction.
    *   `user` (`str`): User-level content.
*   **Returns:**
    *   `str`: The generated text from the Gemini model.
