"""Prompt templates and formatting utilities."""

SYSTEM_PROMPT = """You are a technical documentation generator. You receive code snippets from a software project and produce clear, accurate Markdown documentation.

Rules:
- Write documentation based ONLY on the code provided. Do not invent features or APIs not present in the code.
- Use proper Markdown formatting: headings, code blocks with language tags, bullet lists.
- For README generation: include a project summary, installation section (if inferable), and usage examples derived from the code.
- For API documentation: document each function/class with its signature, parameters, return type, and a brief description.
- If the code is insufficient to document something fully, state what is unclear rather than guessing.
- Keep language concise and developer-focused. No marketing fluff.
"""

def format_user_prompt(query: str, code_chunks: list[dict], skeleton: list[str] | None = None, char_limit: int = 32000) -> str:
    """Formats the user message with optional project skeleton.
    
    Args:
        query: User's documentation request (e.g., "Generate README").
        code_chunks: List of dictionaries with 'content', 'file_path', 'name', 'chunk_type'.
        skeleton: List of strings (paths/names) representing the project structure.
        char_limit: Max characters before truncation.
    """
    lines = [f"## Task\n{query}\n"]
    
    if skeleton:
        lines.append("## Project Structure (Skeleton)")
        for item in skeleton:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Code Context")
    for chunk in code_chunks:
        lines.append(f"### {chunk['file_path']} -- {chunk['name']} ({chunk['chunk_type']})")
        lang = chunk.get('language', '')
        lines.append(f"```{lang}\n{chunk['content']}\n```\n")

    full_prompt = "\n".join(lines)
    
    if len(full_prompt) > char_limit:
        return full_prompt[:char_limit] + f"\n\n(Context truncated at {char_limit} chars)"
    
    return full_prompt
