import pytest
from unittest.mock import MagicMock, patch
from docgen.llm import get_provider
from docgen.llm.prompt import format_user_prompt

def test_provider_factory():
    # Mocking environment for test
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        provider = get_provider("gemini")
        assert provider.__class__.__name__ == "GeminiProvider"

def test_prompt_formatting():
    chunks = [
        {"file_path": "a.py", "name": "foo", "chunk_type": "function", "content": "def foo(): pass", "language": "python"}
    ]
    skeleton = ["a.py", "b.py"]
    prompt = format_user_prompt("Gen README", chunks, skeleton=skeleton)
    
    assert "Gen README" in prompt
    assert "Project Structure (Skeleton)" in prompt
    assert "- a.py" in prompt
    assert "- b.py" in prompt
    assert "def foo(): pass" in prompt

def test_dynamic_truncation():
    chunks = [{"file_path": "a.py", "name": "f", "chunk_type": "func", "content": "X" * 100}]
    # Strict limit
    prompt_small = format_user_prompt("Q", chunks, char_limit=50)
    assert "(Context truncated at 50 chars)" in prompt_small
    assert len(prompt_small) <= 50 + 50 # padding for truncation msg
    
    # Large limit
    prompt_large = format_user_prompt("Q", chunks, char_limit=1000)
    assert "X" * 100 in prompt_large
    assert "(Context truncated" not in prompt_large

def test_groq_init_fails_without_key():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit):
            get_provider("groq")
