from app.config import settings
from app.llm.base import LLMAdapter

_adapter_instance: LLMAdapter | None = None


def get_llm_adapter() -> LLMAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        if settings.llm_provider == "gemini":
            from app.llm.gemini_adapter import GeminiAdapter

            _adapter_instance = GeminiAdapter()
        else:
            raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
    return _adapter_instance
