import asyncio
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from aiolimiter import AsyncLimiter

from docgen.llm.context import generate_docs
from docgen.models import CodeChunk
from docgen.store import VectorRepository

# Default safe limits
RPM_BY_PROVIDER = {
    "gemini": 9,      
    "groq": 28,       
    "openrouter": 10,
    "deepseek": 10
}

def file_path_to_module_name(file_path: str, root: str) -> str:
    """Converts file path to dotted module name (e.g. docgen.parser)."""
    p = Path(file_path).resolve()
    r = Path(root).resolve()
    
    try:
        relative = p.relative_to(r)
    except ValueError:
        # Fallback if outside root
        return p.stem
        
    parts = list(relative.with_suffix("").parts)
    
    # Handle __init__.py
    if parts and parts[-1] == "__init__":
        parts.pop()
        
    if not parts:
        return p.stem
        
    return ".".join(parts)

def group_chunks_by_module(chunks: List[CodeChunk], root: str) -> Dict[str, List[CodeChunk]]:
    """Groups chunks by their dotted module name."""
    groups = defaultdict(list)
    for chunk in chunks:
        mod_name = file_path_to_module_name(chunk.file_path, root)
        groups[mod_name].append(chunk)
    return dict(groups)

async def generate_all_docs(
    module_groups: Dict[str, List[CodeChunk]],
    repo: VectorRepository,
    provider,
    provider_name: str = "gemini",
    output_dir: Path = None,
    upserted_files: List[str] = None,
    on_progress = None
) -> Tuple[str, Dict[str, str]]:
    """Orchestrates concurrent, rate-limited LLM generation with incremental skip."""
    rpm = RPM_BY_PROVIDER.get(provider_name, 10)
    limiter = AsyncLimiter(max_rate=rpm, time_period=60)
    
    # Identify which modules actually need update
    # If upserted_files is None, we assume everything needs update (e.g. forced generate)
    # If a module contains ANY file that was upserted, it needs update.
    modules_to_gen = []
    skipped_count = 0
    
    for mod_name, chunks in module_groups.items():
        # Check if any chunk's file was modified
        needs_update = True
        if upserted_files is not None:
            mod_files = {c.file_path for c in chunks}
            # If no files in this module were upserted, check if doc already exists
            if not (mod_files & set(upserted_files)):
                doc_path = output_dir / "api" / f"{mod_name}.md" if output_dir else None
                if doc_path and doc_path.exists():
                    needs_update = False
        
        if needs_update:
            modules_to_gen.append(mod_name)
        else:
            skipped_count += 1
            if on_progress: on_progress()

    # README generation (always update README as it summarizes the whole project)
    async with limiter:
        readme_text = await asyncio.to_thread(
            generate_docs,
            "Generate a comprehensive README.md for this project. Summarize its purpose, modules, and usage.",
            repo,
            provider
        )
    if on_progress:
        on_progress()

    # Module generation
    module_docs: Dict[str, str] = {}
    
    async def generate_one(mod_name: str) -> Tuple[str, str]:
        async with limiter:
            prompt = f"Generate API documentation for the module '{mod_name}'. Document its classes and functions."
            text = await asyncio.to_thread(
                generate_docs, prompt, repo, provider
            )
        if on_progress:
            on_progress()
        return mod_name, text

    tasks = [generate_one(name) for name in modules_to_gen]
    
    # Run in parallel
    if tasks:
        results = await asyncio.gather(*tasks)
        for mod_name, text in results:
            # If the result contains multiple modules (batching), we'd need to split.
            # For v1, we focus on 1:1 mapping but optimized for RPM.
            # To truly batch, we'd need the LLM to return a JSON or clear separators.
            # Given the complexity of splitting LLM responses reliably without structured output,
            # we will stick to 1:1 but use a higher RPM limit for Gemini if we detect batching is possible?
            # No, let's implement true batching by requesting a combined response.
            module_docs[mod_name] = text
        
    return readme_text, module_docs

def batch_modules(module_groups: Dict[str, List[CodeChunk]], char_limit: int = 40000) -> List[List[str]]:
    """Groups module names into batches to minimize LLM calls.
    
    Logic: Same directory + total chars < char_limit.
    """
    # For v1, we will keep it simple and skip complex batching if it risks output quality.
    # However, to meet the < 2min requirement for 50 files on Gemini (10 RPM), 
    # we MUST batch. 
    
    batches = []
    current_batch = []
    current_chars = 0
    
    # Sort modules by directory depth to keep related ones together
    sorted_mods = sorted(module_groups.keys())
    
    for mod in sorted_mods:
        mod_chars = sum(len(c.content) for c in module_groups[mod])
        
        if current_batch and (current_chars + mod_chars > char_limit):
            batches.append(current_batch)
            current_batch = [mod]
            current_chars = mod_chars
        else:
            current_batch.append(mod)
            current_chars += mod_chars
            
    if current_batch:
        batches.append(current_batch)
        
    return batches
