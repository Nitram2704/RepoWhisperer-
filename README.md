# Documentation Generator

This project aims to automate the generation of documentation from code, leveraging LLMs for content creation. It parses code files, extracts relevant information, and uses a language model to generate documentation in Markdown format.

## Modules

- **docgen.embedder:** Handles the embedding of text using `fastembed` for semantic search.
- **docgen.llm:** Contains modules for interacting with different Large Language Models (LLMs):
    - **docgen.llm.base:** Defines the base class for LLM providers.
    - **docgen.llm.context:**  Handles context retrieval and documentation generation.
    - **docgen.llm.deepseek:** Integrates with the DeepSeek LLM API.
    - **docgen.llm.gemini:** Integrates with the Gemini LLM API.
    - **docgen.llm.prompt:**  Formats prompts for the LLMs, including project structure and code snippets.
- **docgen.parser:** Contains code parsers:
    - **docgen.parser.python_parser:** Parses Python code to extract functions and classes.
- **docgen.store:** Manages the vector store for storing and querying code embeddings.
- **docgen.writer:**  Writes the generated documentation to files.

## Installation

While a detailed installation guide isn't available in the provided code, the following steps can be inferred:

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install dependencies:**  (Requires inspection of `requirements.txt` or similar for full list)
    It's very likely you'll need to install `fastembed` and `openai`.

    ```bash
    pip install fastembed openai
    ```

3.  **Set up API keys:**
    - For DeepSeek, set the `DEEPSEEK_API_KEY` or `DOCGEN_API_KEY` environment variable.  You can obtain one at https://platform.deepseek.com/

    ```bash
    export DEEPSEEK_API_KEY="YOUR_API_KEY"
    ```
    - For Gemini, API key setup is likely also required, but specific environment variables are unclear from the code.

## Usage

The primary entry point for generating documentation appears to be through the `docgen.llm.context.generate_docs` function. Here's an example usage scenario:

```python
from docgen.llm.context import generate_docs
from docgen.store import VectorRepository  # Assuming this is how VectorRepository is used
from pathlib import Path

# Initialize the vector repository (implementation details omitted)
repo = VectorRepository() # Requires initialization with data

# Generate a README
readme_content = generate_docs(
    query="Generate README",
    repo=repo,
    include_skeleton=True
)

print(readme_content)

# Write documentation to files using docgen.writer.write_docs
from docgen.writer import write_docs
from pathlib import Path

# Example usage:
readme_md = "This is a sample README."
module_docs = {"module1": "Documentation for module1", "module2": "Documentation for module2"}
all_module_names = ["module1", "module2"]
output_dir = Path("./output")
project_dir = Path(".")  # Current directory

written_paths = write_docs(readme_md, module_docs, all_module_names, output_dir, project_dir)

for path in written_paths:
    print(f"Wrote documentation to: {path}")
```

## API Reference

| Module | Description |
| :--- | :--- |
| [llm_test](./api/llm_test.md) | API documentation |
| [src.docgen.config](./api/src.docgen.config.md) | API documentation |
| [src.docgen.embedder](./api/src.docgen.embedder.md) | API documentation |
| [src.docgen.ingest](./api/src.docgen.ingest.md) | API documentation |
| [src.docgen.llm](./api/src.docgen.llm.md) | API documentation |
| [src.docgen.llm.base](./api/src.docgen.llm.base.md) | API documentation |
| [src.docgen.llm.context](./api/src.docgen.llm.context.md) | API documentation |
| [src.docgen.llm.deepseek](./api/src.docgen.llm.deepseek.md) | API documentation |
| [src.docgen.llm.gemini](./api/src.docgen.llm.gemini.md) | API documentation |
| [src.docgen.llm.groq](./api/src.docgen.llm.groq.md) | API documentation |
| [src.docgen.llm.openrouter](./api/src.docgen.llm.openrouter.md) | API documentation |
| [src.docgen.llm.prompt](./api/src.docgen.llm.prompt.md) | API documentation |
| [src.docgen.main](./api/src.docgen.main.md) | API documentation |
| [src.docgen.models](./api/src.docgen.models.md) | API documentation |
| [src.docgen.parser](./api/src.docgen.parser.md) | API documentation |
| [src.docgen.parser.filter](./api/src.docgen.parser.filter.md) | API documentation |
| [src.docgen.parser.js_parser](./api/src.docgen.parser.js_parser.md) | API documentation |
| [src.docgen.parser.python_parser](./api/src.docgen.parser.python_parser.md) | API documentation |
| [src.docgen.runner](./api/src.docgen.runner.md) | API documentation |
| [src.docgen.store](./api/src.docgen.store.md) | API documentation |
| [src.docgen.ui](./api/src.docgen.ui.md) | API documentation |
| [src.docgen.writer](./api/src.docgen.writer.md) | API documentation |
| [tests.test_runner](./api/tests.test_runner.md) | API documentation |
| [tests.test_writer](./api/tests.test_writer.md) | API documentation |