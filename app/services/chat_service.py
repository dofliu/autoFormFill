"""
Chat Service — RAG-powered knowledge QA with streaming.

Orchestrates: multi-collection search → prompt building → LLM streaming.
Yields SSE-formatted events for the router to wrap in StreamingResponse.
"""
import asyncio
import json
import logging
from collections.abc import AsyncIterator

from app.config import settings
from app.llm.factory import get_llm_adapter
from app.schemas.chat import ChatMessage, SourceChunk
from app.services.document_service import search_documents
from app.vector_store import COLLECTIONS

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
# Multi-collection search
# ---------------------------------------------------------------------------

async def search_all_collections(
    query: str,
    collections: list[str] | None = None,
    n_results: int = 5,
) -> list[SourceChunk]:
    """Search across multiple ChromaDB collections in parallel.

    Returns the top *n_results* chunks sorted by ascending distance.
    """
    target = collections or COLLECTIONS

    tasks = [
        search_documents(query, col, n_results=n_results)
        for col in target
    ]
    results_per_col = await asyncio.gather(*tasks, return_exceptions=True)

    all_sources: list[SourceChunk] = []
    for col_name, results in zip(target, results_per_col):
        if isinstance(results, Exception):
            logger.warning(f"Search failed for collection '{col_name}': {results}")
            continue
        for item in results:
            all_sources.append(
                SourceChunk(
                    text=item["text"],
                    metadata=item.get("metadata", {}),
                    distance=item.get("distance"),
                    collection=col_name,
                )
            )

    # Sort by distance (lower = more relevant)
    all_sources.sort(
        key=lambda s: s.distance if s.distance is not None else float("inf")
    )
    return all_sources[:n_results]


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
    # Format retrieved context
    context_parts: list[str] = []
    for i, chunk in enumerate(context_chunks, 1):
        meta_str = ", ".join(
            f"{k}: {v}" for k, v in chunk.metadata.items() if v
        )
        header = f"[Source {i}] ({chunk.collection}"
        if meta_str:
            header += f", {meta_str}"
        header += ")"
        context_parts.append(f"{header}\n{chunk.text}")

    context = "\n---\n".join(context_parts) if context_parts else "(No relevant documents found)"
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
) -> AsyncIterator[str]:
    """Main chat orchestrator: search → build prompt → stream LLM response.

    Yields SSE-formatted strings (``data: {json}\\n\\n``).
    """
    # 1. Search knowledge base
    sources = await search_all_collections(message, collections, n_results)

    # 2. Emit sources event
    sources_data = [s.model_dump() for s in sources]
    yield _sse({"type": "sources", "sources": sources_data})

    # 3. Build prompt
    max_rounds = settings.chat_context_rounds
    prompt = build_chat_prompt(message, sources, history, max_rounds)

    # 4. Stream LLM response
    adapter = get_llm_adapter()
    try:
        async for chunk in adapter.generate_text_stream(
            prompt, temperature=0.3, max_tokens=2048
        ):
            yield _sse({"type": "chunk", "content": chunk})
    except Exception as e:
        logger.error(f"Chat LLM streaming failed: {e}")
        yield _sse({"type": "error", "message": str(e)})
        return

    # 5. Done signal
    yield _sse({"type": "done"})


def _sse(data: dict) -> str:
    """Format a dict as an SSE event line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
