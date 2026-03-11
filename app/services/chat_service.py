"""
Chat Service — RAG-powered knowledge QA with streaming.

Orchestrates: multi-collection search → prompt building → LLM streaming.
Yields SSE-formatted events for the router to wrap in StreamingResponse.
"""

import logging
from collections.abc import AsyncIterator

from app.config import settings
from app.schemas.chat import ChatMessage, SourceChunk
from app.services.sse_pipeline import (
    _sse,                        # noqa: F401 — re-export for backward compat
    format_context_default,
    rag_sse_stream,
    search_all_collections,      # noqa: F401 — re-export for backward compat
    StreamConfig,
)

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """\
You are a knowledgeable research assistant. Answer the user's question \
based on the provided context documents.

Rules:
1. ONLY use information present in the provided context.
2. If the context is insufficient, say so clearly — do NOT fabricate information.
3. Cite your sources by referring to the document titles or metadata when available.
4. Answer in the same language as the user's question.
5. Be concise but thorough.

Retrieved context:
{context}"""


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def build_chat_prompt(
    message: str,
    context_chunks: list[SourceChunk],
    history: list[ChatMessage],
    max_history_rounds: int = 5,
) -> str:
    """Build a complete prompt: system instructions + context + history + user message."""
    context = format_context_default(context_chunks)
    system = CHAT_SYSTEM_PROMPT.format(context=context)

    # Format conversation history (last N rounds)
    trimmed = history[-(max_history_rounds * 2):]
    history_text = ""
    if trimmed:
        lines = []
        for msg in trimmed:
            prefix = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{prefix}: {msg.content}")
        history_text = "\nPrevious conversation:\n" + "\n".join(lines) + "\n"

    return f"{system}\n{history_text}\nUser: {message}\nAssistant:"


# ---------------------------------------------------------------------------
# Streaming orchestrator
# ---------------------------------------------------------------------------

async def chat_stream(
    message: str,
    history: list[ChatMessage],
    collections: list[str] | None = None,
    n_results: int = 5,
    user_id: int | None = None,
) -> AsyncIterator[str]:
    """Main chat orchestrator: search → build prompt → stream LLM response.

    Args:
        user_id: Filter search results by owner — ``None`` = no filtering.

    Yields SSE-formatted strings (``data: {json}\\n\\n``).
    """
    max_rounds = settings.chat_context_rounds

    def _build(sources: list[SourceChunk]) -> str:
        return build_chat_prompt(message, sources, history, max_rounds)

    async for event in rag_sse_stream(
        search_query=message,
        build_prompt=_build,
        config=StreamConfig(temperature=0.3, max_tokens=2048),
        collections=collections,
        n_results=n_results,
        user_id=user_id,
    ):
        yield event
