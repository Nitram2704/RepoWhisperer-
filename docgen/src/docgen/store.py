import hashlib
from pathlib import Path
from typing import Optional

import chromadb
from chromadb import PersistentClient
from filelock import FileLock, Timeout

from docgen.models import CodeChunk


def _chunk_hash(chunk: CodeChunk) -> str:
    """SHA-256 of relative path + name + content for deterministic dedup.
    
    Using relative path ensures reproducibility across different environments.
    """
    # Note: caller should ensure file_path is relative to repo_root
    payload = f"{chunk.file_path}::{chunk.name}::{chunk.content}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class VectorRepository:
    """Wraps ChromaDB with file locking and hash-based deduplication."""

    def __init__(self, chroma_dir: str = ".chroma"):
        self._chroma_dir = Path(chroma_dir)
        self._chroma_dir.mkdir(parents=True, exist_ok=True)
        
        # Lock file prevents concurrent write corruption
        self._lock_path = self._chroma_dir / "docgen.lock"
        self._lock = FileLock(str(self._lock_path), timeout=5)
        
        # Initialize PersistentClient with telemetry disabled
        from chromadb.config import Settings
        self._client = PersistentClient(
            path=str(self._chroma_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection. Plan 02 provides embeddings externally.
        self._collection = self._client.get_or_create_collection(
            name="docgen",
            metadata={"hnsw:space": "cosine"}
        )

    def upsert_chunks(self, chunks: list[CodeChunk], embeddings: list[list[float]]) -> dict:
        """Upsert chunks into ChromaDB, skipping those with identical content hashes.
        
        Args:
            chunks: List of CodeChunk instances.
            embeddings: Corresponding embeddings from the Embedder.
            
        Returns:
            Summary dict with total, skipped, and upserted counts.
        """
        if not chunks:
            return {"total": 0, "skipped": 0, "upserted": 0}

        with self._lock:
            # Stable IDs based on path and name
            stable_ids = [f"{c.file_path}::{c.name}" for c in chunks]
            computed_hashes = [_chunk_hash(c) for c in chunks]
            
            # Batch check for existing entries
            existing = self._collection.get(ids=stable_ids, include=["metadatas"])
            # Map ID -> Metadata hash
            id_to_old_hash = {
                id_: meta.get("content_hash") 
                for id_, meta in zip(existing["ids"], existing["metadatas"])
                if meta
            }
            
            to_upsert_ids = []
            to_upsert_docs = []
            to_upsert_embs = []
            to_upsert_metas = []
            
            skipped = 0
            
            for i, chunk in enumerate(chunks):
                id_ = stable_ids[i]
                new_hash = computed_hashes[i]
                old_hash = id_to_old_hash.get(id_)
                
                # Deduplication check: skip if hash is unchanged
                if old_hash == new_hash:
                    skipped += 1
                    continue
                
                to_upsert_ids.append(id_)
                to_upsert_docs.append(chunk.content)
                to_upsert_embs.append(embeddings[i])
                
                # Metadata must be simple types
                meta = {
                    "file_path": str(chunk.file_path),
                    "language": chunk.language,
                    "chunk_type": chunk.chunk_type,
                    "name": chunk.name,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "docstring": chunk.docstring or "",
                    "parent": chunk.parent or "",
                    "content_hash": new_hash
                }
                to_upsert_metas.append(meta)

            if to_upsert_ids:
                self._collection.upsert(
                    ids=to_upsert_ids,
                    documents=to_upsert_docs,
                    embeddings=to_upsert_embs,
                    metadatas=to_upsert_metas
                )

            upserted_files = set()
            for id_ in to_upsert_ids:
                # Extract file path from ID (path::name)
                upserted_files.add(id_.split("::")[0])

            return {
                "total": len(chunks),
                "skipped": skipped,
                "upserted": len(to_upsert_ids),
                "upserted_files": list(upserted_files)
            }

    def query(self, text: Optional[str] = None, embedding: Optional[list[float]] = None, n_results: int = 5) -> dict:
        """Query the collection for relevant chunks."""
        if embedding:
            return self._collection.query(query_embeddings=[embedding], n_results=n_results)
        elif text:
            return self._collection.query(query_texts=[text], n_results=n_results)
        return {}

    def count(self) -> int:
        """Return the number of entries in the collection."""
        return self._collection.count()

    def clear(self) -> None:
        """Wipe the collection and recreate it."""
        with self._lock:
            self._client.delete_collection("docgen")
            self._collection = self._client.get_or_create_collection(name="docgen")

    def list_files(self) -> list[str]:
        """Return unique file_path values stored in the collection.
        
        Used to reconstruct the module list without re-parsing.
        """
        if self.count() == 0:
            return []
            
        # Get all metadatas to extract file paths
        results = self._collection.get(include=["metadatas"])
        seen = set()
        files = []
        for meta in results.get("metadatas", []):
            if not meta: continue
            fp = meta.get("file_path")
            if fp and fp not in seen:
                seen.add(fp)
                files.append(fp)
        return files
