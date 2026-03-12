# API Documentation for `src.docgen.llm.deepseek`

## Class `DeepSeekProvider`

```python
class DeepSeekProvider(BaseLLMProvider)
```

DeepSeek Provider using the OpenAI-compatible SDK.

### Attributes

-   `BASE_URL`:  Base URL for the DeepSeek API.  Value: `"https://api.deepseek.com"`
-   `DEFAULT_MODEL`: Default model name. Value: `"deepseek-chat"`
-   `ENV_KEY`: Environment variable key for the DeepSeek API key. Value: `"DEEPSEEK_API_KEY"`
-   `max_context_chars`: Maximum context characters. Value: `64000`

### `__init__`

```python
def __init__(self, model: str | None = None)
```

Initializes the DeepSeek provider.  Retrieves the API key from the environment variables `DEEPSEEK_API_KEY` or `DOCGEN_API_KEY`.

**Parameters:**

*   `model`: (Optional) The model to use. Defaults to the value of the `DOCGEN_MODEL` environment variable, or `"deepseek-chat"` if not set.

**Raises:**

*   `SystemExit`: If the API key is not found in the environment variables.

### `generate`

```python
def generate(self, system: str, user: str) -> str
```

Generates text using the DeepSeek API.

**Parameters:**

*   `system`: System-level instruction (e.g., "You are a tech doc generator").
*   `user`: User-level content (e.g., code context + generation request).

**Returns:**

*   Generated text as a plain string.
