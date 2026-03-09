from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate free-form text response."""
        ...

    @abstractmethod
    async def generate_json(self, prompt: str, schema: dict | None = None) -> dict | list:
        """Generate structured JSON output."""
        ...

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for a single text."""
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts."""
        ...
