from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from docgen.store import VectorRepository
    from docgen.llm.base import BaseLLMProvider

from docgen.llm.prompt import SYSTEM_PROMPT, format_user_prompt

def generate_docs(
    query: str, 
    repo: VectorRepository, 
    provider: Optional[BaseLLMProvider] = None,
    n_chunks: int = 15,
    include_skeleton: bool = True
) -> str:
    """Retrieves context and generates documentation via LLM.
    
    Args:
        query: What to generate (e.g. 'Generate README').
        repo: The vector repository to query.
        provider: Active LLM provider.
        n_chunks: Number of relevant code chunks to retrieve.
        include_skeleton: Whether to include project-wide structure in the prompt.
    """
    if provider is None:
        from docgen.llm import get_provider
        provider = get_provider()

    # 1. Retrieve relevant chunks
    results = repo.query(text=query, n_results=n_chunks)
    code_chunks = []
    if results and results.get("documents") and results["documents"][0]:
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            code_chunks.append({
                "content": doc,
                "file_path": meta.get("file_path", "unknown"),
                "name": meta.get("name", "unknown"),
                "chunk_type": meta.get("chunk_type", "unknown"),
                "language": meta.get("language", "unknown"),
            })

    # 2. Get Skeleton (Option B Brainstorm)
    skeleton = None
    if include_skeleton:
        # We can query with a generic term or just get recent items
        # To make it efficient, we use the already retrieved results 
        # or do a second query for 'project structure'.
        # For v1, let's just use the metadata from ALL stored IDs if the repo is small
        # or just deduplicate paths in current retrieved chunks.
        # Improvement: actually query for module docstrings.
        paths = {c["file_path"] for c in code_chunks}
        skeleton = sorted(list(paths))

    # 3. Format Prompt
    user_msg = format_user_prompt(
        query, 
        code_chunks, 
        skeleton=skeleton, 
        char_limit=provider.max_context_chars
    )

    # 4. Generate
    return provider.generate(SYSTEM_PROMPT, user_msg)
