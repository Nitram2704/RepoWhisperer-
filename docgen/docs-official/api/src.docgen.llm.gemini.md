```markdown
## API Documentation for `src.docgen.llm.gemini`

This module provides functionality for generating documentation using the Gemini language model.

### Functions

#### `generate(self, system: str, user: str) -> str`

```python
def generate(self, system: str, user: str) -> str
```

Generates text using the Gemini language model based on a system instruction and a user prompt.

**Parameters:**

-   `system` (str): System-level instruction (e.g., "You are a tech doc generator").
-   `user` (str): User-level content (e.g., code context + generation request).

**Returns:**

-   `str`: The generated text from the Gemini model. The exact return type and structure depend on the Gemini API response.
```
