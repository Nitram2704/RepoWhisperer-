import os
from openai import OpenAI
from docgen.llm.base import BaseLLMProvider
from docgen.llm.retry import openai_retry

class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek Provider using the OpenAI-compatible SDK."""
    BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-chat"
    ENV_KEY = "DEEPSEEK_API_KEY"
    max_context_chars = 64000

    def __init__(self, model: str | None = None):
        api_key = os.environ.get(self.ENV_KEY) or os.environ.get("DOCGEN_API_KEY")
        if not api_key:
            raise SystemExit(f"Missing {self.ENV_KEY} or DOCGEN_API_KEY environment variable. Get one at https://platform.deepseek.com/")
        
        self.model = model or os.getenv("DOCGEN_MODEL", self.DEFAULT_MODEL)
        self._client = OpenAI(api_key=api_key, base_url=self.BASE_URL)

    @openai_retry
    def generate(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""
