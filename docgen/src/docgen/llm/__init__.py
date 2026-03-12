"""LLM provider package. Use get_provider() to get the active provider."""
import os
from docgen.llm.base import BaseLLMProvider

def get_provider(provider_name: str | None = None, model: str | None = None) -> BaseLLMProvider:
    """Return an LLM provider instance based on config.

    Priority:
    1. provider_name / model arguments
    2. DOCGEN_PROVIDER / DOCGEN_MODEL env vars
    3. Defaults: "gemini" 
    """
    from docgen.llm.gemini import GeminiProvider
    from docgen.llm.groq import GroqProvider
    from docgen.llm.openrouter import OpenRouterProvider
    from docgen.llm.deepseek import DeepSeekProvider

    providers = {
        "gemini": GeminiProvider,
        "groq": GroqProvider,
        "openrouter": OpenRouterProvider,
        "deepseek": DeepSeekProvider,
    }

    name = (provider_name or os.getenv("DOCGEN_PROVIDER", "gemini")).lower().strip()
    if name not in providers:
        valid = ", ".join(sorted(providers.keys()))
        raise SystemExit(f"Unknown DOCGEN_PROVIDER='{name}'. Valid options: {valid}")
    
    return providers[name](model=model)

__all__ = ["get_provider", "BaseLLMProvider"]
