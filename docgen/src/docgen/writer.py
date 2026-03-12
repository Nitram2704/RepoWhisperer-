import os
from pathlib import Path
from typing import Dict, List

def validate_output_dir(output_dir: Path, project_dir: Path) -> None:
    """Refuses to write if output_dir is identical to project_dir.
    
    Allows writing to subdirectories (e.g., ./docs).
    """
    out = output_dir.resolve()
    proj = project_dir.resolve()
    
    if out == proj:
        raise ValueError(
            f"Destructive output detected! Output directory '{out}' matches project root. "
            "DocGen refuses to overwrite your source files. Please specify a subdirectory like --output-dir docs"
        )

def safe_write(output_dir: Path, rel_path: str, content: str) -> Path:
    """Writes content to output_dir / rel_path with traversal protection."""
    out_file = (output_dir / rel_path).resolve()
    
    # Ensure it's inside the output_dir
    if not out_file.is_relative_to(output_dir.resolve()):
        raise ValueError(f"Path traversal attempt blocked: {rel_path}")
        
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(content, encoding="utf-8")
    return out_file

def generate_module_map(module_names: List[str]) -> str:
    """Generates a Markdown table of contents for README.md."""
    if not module_names:
        return ""
        
    lines = [
        "## API Reference",
        "",
        "| Module | Description |",
        "| :--- | :--- |"
    ]
    
    for module_name in sorted(module_names):
        link = f"./api/{module_name}.md"
        lines.append(f"| [{module_name}]({link}) | API documentation |")
        
    return "\n".join(lines)

def write_docs(
    readme_md: str, 
    module_docs: Dict[str, str], 
    all_module_names: List[str],
    output_dir: Path, 
    project_dir: Path
) -> List[Path]:
    """Orchestrates the writing of all documentation files."""
    validate_output_dir(output_dir, project_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    written_paths = []
    
    # 1. Enrich/Replace README with Module Map
    module_map = generate_module_map(all_module_names)
    full_readme = readme_md
    
    # If LLM generated its own (likely broken) API Reference, replace it.
    # Otherwise, append it.
    if "## API Reference" in full_readme:
        parts = full_readme.split("## API Reference", 1)
        full_readme = parts[0] + module_map
    else:
        full_readme += f"\n\n{module_map}"
    
    # 2. Write README.md
    written_paths.append(safe_write(output_dir, "README.md", full_readme))
    
    # 3. Write individual module docs
    for module_name, content in module_docs.items():
        filename = f"api/{module_name}.md"
        written_paths.append(safe_write(output_dir, filename, content))
        
    return written_paths
