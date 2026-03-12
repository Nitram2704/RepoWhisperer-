import os
from google import genai
from docgen.llm.base import BaseLLMProvider
from docgen.llm.retry import gemini_retry

class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider using the LATEST official 'google-genai' SDK."""
    DEFAULT_MODEL = "gemini-2.0-flash" # Current stable
    ENV_KEY = "GEMINI_API_KEY"
    max_context_chars = 1_000_000 * 4  # 1M tokens ~ 4M chars

    def __init__(self, model: str | None = None):
        api_key = os.environ.get(self.ENV_KEY) or os.environ.get("GOOGLE_API_KEY") or os.environ.get("DOCGEN_API_KEY")
        if not api_key:
            raise SystemExit(f"Missing {self.ENV_KEY}, GOOGLE_API_KEY or DOCGEN_API_KEY environment variable. Get one at https://aistudio.google.com/")
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = model or os.getenv("DOCGEN_MODEL", self.DEFAULT_MODEL)

    @gemini_retry
    def generate(self, system: str, user: str) -> str:
        # Latest SDK uses config for system instruction
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user,
            config={"system_instruction": system}
        )
        return response.text
