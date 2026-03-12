```markdown
## docgen.llm.openrouter

### OpenRouterProvider (class)
```python
class OpenRouterProvider(BaseLLMProvider):
    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
    ENV_KEY = "OPENROUTER_API_KEY"
    max_context_chars = 32000

    def __init__(self, model: str | None = None):
        ...
    
    @openai_retry
    def generate(self, system: str, user: str) -> str:
        ...
```
OpenRouter Provider using the OpenAI-compatible SDK.

*   **BASE_URL**: Base URL for the OpenRouter API.
*   **DEFAULT_MODEL**: Default model to use if none is specified.
*   **ENV_KEY**: Environment variable key for the OpenRouter API key.
*   **max_context_chars**: Maximum number of characters allowed in the context.

#### `__init__(self, model: str | None = None)`
```python
def __init__(self, model: str | None = None)
```
Initializes the OpenRouterProvider with an optional model.  If no model is provided, it defaults to the value of the `DOCGEN_MODEL` environment variable or the `DEFAULT_MODEL` attribute. The API key is retrieved from the `OPENROUTER_API_KEY` or `DOCGEN_API_KEY` environment variables.

*   **Parameters:**
    *   `model` (`str | None`): The model to use for generation.

*   **Raises:**
    *   `SystemExit`: If the `OPENROUTER_API_KEY` or `DOCGEN_API_KEY` environment variable is not set.

#### `generate(self, system: str, user: str) -> str`
```python
def generate(self, system: str, user: str) -> str
```
Generates text using the OpenRouter API.

*   **Parameters:**
    *   `system` (`str`): System-level instructions for the model.
    *   `user` (`str`): User-provided content to generate from.

*   **Returns:**
    *   `str`: The generated text.
