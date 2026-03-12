import pytest
from pathlib import Path
from docgen.writer import validate_output_dir, safe_write, generate_module_map

def test_validate_output_dir_prevents_overwrite(tmp_path):
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    
    # Should raise error if output_dir == project_dir
    with pytest.raises(ValueError, match="Destructive output detected"):
        validate_output_dir(project_dir, project_dir)
        
    # Should allow subdirectory
    validate_output_dir(project_dir / "docs", project_dir)

def test_safe_write_prevents_traversal(tmp_path):
    out_dir = tmp_path / "docs"
    out_dir.mkdir()
    
    # Valid write
    safe_write(out_dir, "test.md", "hello")
    assert (out_dir / "test.md").exists()
    
    # Traversal write
    with pytest.raises(ValueError, match="traversal attempt blocked"):
        safe_write(out_dir, "../secret.txt", "data")

def test_generate_module_map_sorting():
    docs = {"z_mod": "...", "a_mod": "...", "m_mod": "..."}
    map_str = generate_module_map(docs)
    
    assert "| [a_mod]" in map_str
    assert "| [m_mod]" in map_str
    assert "| [z_mod]" in map_str
    # Verify order
    lines = [l for l in map_str.splitlines() if "|" in l and "Module" not in l and "---" not in l]
    names = [l.split("[")[1].split("]")[0] for l in lines]
    assert names == ["a_mod", "m_mod", "z_mod"]
