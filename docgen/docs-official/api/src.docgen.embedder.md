# API Documentation for `src.docgen.embedder`

This module provides functionality for generating embeddings from text using the `fastembed` library.

## Class `Embedder`

```python
class Embedder:
```

Wrapper for `fastembed` TextEmbedding with local ONNX execution.

### `__init__(self, model_name: str = "BAAI/bge-small-en-v1.5")`

```python
def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
```

Initializes the `Embedder` with a specified model.  Downloads the model if it's the first time it's being used.

**Parameters:**

*   `model_name` (*str*, optional): The name of the embedding model to use. Defaults to `"BAAI/bge-small-en-v1.5"`.

### `embed(self, texts: list[str], batch_size: int = 32) -> list[list[float]]`

```python
def embed(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
```

Generates embeddings for a list of texts.

**Parameters:**

*   `texts` (*list[str]*): List of strings to embed.
*   `batch_size` (*int*, optional): Processing batch size (CPU optimized). Defaults to `32`.

**Returns:**

*   *list[list[float]]*: List of float lists representing embeddings.

### `dimension` property

```python
@property
def dimension(self) -> int:
```

Returns the vector dimension.

**Returns:**

*   *int*: The vector dimension (384 for bge-small).
