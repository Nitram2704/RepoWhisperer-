import os
from openai import OpenAI
from docgen.llm.base import BaseLLMProvider
from docgen.llm.retry import openai_retry

class GroqProvider(BaseLLMProvider):
    """Groq Provider using the OpenAI-compatible SDK."""
    BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    ENV_KEY = "GROQ_API_KEY"
    max_context_chars = 32000  # Groq free tier safe limit

    def __init__(self, model: str | None = None):
        api_key = os.environ.get(self.ENV_KEY) or os.environ.get("DOCGEN_API_KEY")
        if not api_key:
            raise SystemExit(f"Missing {self.ENV_KEY} or DOCGEN_API_KEY environment variable. Get one at https://console.groq.com/")
        
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
