from fastembed import TextEmbedding
from rich.console import Console


class Embedder:
    """Wrapper for fastembed TextEmbedding with local ONNX execution."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self._console = Console(stderr=True)
        
        # Notify user as download can be ~50MB on first run
        self._console.print(
            f"[dim]Loading embedding model: {model_name} (first run may download files)...[/dim]"
        )
        
        # TextEmbedding handles caching and local loading
        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of strings to embed.
            batch_size: Processing batch size (CPU optimized).
            
        Returns:
            List of float lists representing embeddings.
        """
        if not texts:
            return []
            
        # .embed returns a generator of numpy arrays
        raw_embeddings = self._model.embed(texts, batch_size=batch_size)
        
        # Convert numpy arrays to lists
        return [emb.tolist() for emb in raw_embeddings]

    @property
    def dimension(self) -> int:
        """Return the vector dimension (384 for bge-small)."""
        return 384
