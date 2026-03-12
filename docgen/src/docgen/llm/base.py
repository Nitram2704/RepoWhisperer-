from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers."""
    max_context_chars: int = 32000  # Default safe limit

    @abstractmethod
    def generate(self, system: str, user: str) -> str:
        """Generate text from a system prompt and user message.

        Args:
            system: System-level instruction (e.g., "You are a tech doc generator").
            user: User-level content (e.g., code context + generation request).

        Returns:
            Generated text as a plain string.
        """
        pass
