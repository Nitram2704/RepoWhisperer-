import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from docgen.runner import file_path_to_module_name, generate_all_docs
from docgen.models import CodeChunk

def test_file_path_to_module_name():
    root = "C:/repo"
    assert file_path_to_module_name("C:/repo/src/docgen/main.py", root) == "src.docgen.main"
    assert file_path_to_module_name("C:/repo/src/docgen/__init__.py", root) == "src.docgen"
    assert file_path_to_module_name("C:/repo/README.md", root) == "README"

@pytest.mark.asyncio
async def test_generate_all_docs_incremental_skip(tmp_path):
    repo = MagicMock()
    provider = MagicMock()
    # Mock generate_docs as a blocking call run via thread
    import docgen.runner
    from docgen.llm.context import generate_docs
    
    # We need to mock generate_docs in the runner's context
    with MagicMock() as mock_gen:
        mock_gen.return_value = "fake docs"
        
        module_groups = {
            "mod1": [CodeChunk(file_path="src/mod1.py", name="f1", content="code", language="python", chunk_type="func", start_line=1, end_line=10)],
            "mod2": [CodeChunk(file_path="src/mod2.py", name="f2", content="code2", language="python", chunk_type="func", start_line=1, end_line=10)]
        }
        
        # Scenario: mod1 is upserted, mod2 is NOT and mod2.md exists
        out_dir = tmp_path / "docs"
        api_dir = out_dir / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "mod2.md").write_text("old docs")
        
        # We need to monkeypatch generate_docs because runner calls it via asyncio.to_thread
        import docgen.runner
        original_gen = docgen.runner.generate_docs
        docgen.runner.generate_docs = MagicMock(return_value="new docs")
        
        try:
            readme, modules = await generate_all_docs(
                module_groups,
                repo,
                provider,
                provider_name="gemini",
                output_dir=out_dir,
                upserted_files=["src/mod1.py"]
            )
            
            # mod1 should be in modules, mod2 should NOT be in modules (skipped)
            assert "mod1" in modules
            assert "mod2" not in modules
            assert modules["mod1"] == "new docs"
            
        finally:
            docgen.runner.generate_docs = original_gen
