"""
Shared SSE streaming pipeline — reusable RAG-to-SSE infrastructure.

Provides:
- ``_sse()`` — format a dict as an SSE event line
- ``search_all_collections()`` — multi-collection parallel search
- ``format_context_default()`` / ``format_context_report()`` — context formatters
- ``StreamConfig`` — LLM parameter dataclass
- ``rag_sse_stream()`` — the shared search → sources → prompt → stream → done pipeline
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from app.llm.factory import get_llm_adapter
from app.schemas.chat import SourceChunk
from app.services.document_service import search_documents
from app.vector_store import COLLECTIONS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SSE formatting
# ---------------------------------------------------------------------------

def _sse(data: dict) -> str:
    """Format a dict as an SSE event line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


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
            logger.warning("Search failed for collection '%s': %s", col_name, results)
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
# Context formatters
# ---------------------------------------------------------------------------

def format_context_default(
    chunks: list[SourceChunk],
    empty_message: str = "(No relevant documents found)",
) -> str:
    """Format source chunks for chat/email prompts.

    Style: ``[Source i] (collection, key: value, ...)``
    """
    if not chunks:
        return empty_message

    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        meta_str = ", ".join(
            f"{k}: {v}" for k, v in chunk.metadata.items() if v
        )
        header = f"[Source {i}] ({chunk.collection}"
        if meta_str:
            header += f", {meta_str}"
        header += ")"
        parts.append(f"{header}\n{chunk.text}")

    return "\n---\n".join(parts)


def format_context_report(
    chunks: list[SourceChunk],
    empty_message: str = "(No context documents found — mark all sections as [需補充])",
) -> str:
    """Format source chunks for report prompts.

    Style: ``[Source i | collection | title]``
    """
    if not chunks:
        return empty_message

    parts: list[str] = []
    for i, src in enumerate(chunks, 1):
        title = src.metadata.get("title", "Unknown")
        parts.append(f"[Source {i} | {src.collection} | {title}]\n{src.text}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Streaming pipeline
# ---------------------------------------------------------------------------

@dataclass
class StreamConfig:
    """LLM parameters for a streaming pipeline."""
    temperature: float = 0.3
    max_tokens: int = 2048


async def rag_sse_stream(
    search_query: str,
    build_prompt: Callable[[list[SourceChunk]], str],
    config: StreamConfig = StreamConfig(),
    collections: list[str] | None = None,
    n_results: int = 5,
) -> AsyncIterator[str]:
    """Shared RAG-to-SSE streaming pipeline.

    1. Search knowledge base across collections
    2. Emit ``sources`` SSE event
    3. Build prompt via caller-provided callback
    4. Stream LLM response as ``chunk`` events
    5. Emit ``done`` (or ``error`` on failure)

    Args:
        search_query: The query string for multi-collection search.
        build_prompt: Callable that receives search results and returns the
                      complete LLM prompt string.
        config: LLM streaming parameters (temperature, max_tokens).
        collections: Which ChromaDB collections to search (None = all).
        n_results: Number of search results to retrieve.

    Yields:
        SSE-formatted strings: sources → chunk(s) → done/error.
    """
    # 1. Search knowledge base
    sources = await search_all_collections(search_query, collections, n_results)

    # 2. Emit sources event
    sources_data = [s.model_dump() for s in sources]
    yield _sse({"type": "sources", "sources": sources_data})

    # 3. Build prompt using caller's builder
    prompt = build_prompt(sources)

    # 4. Stream LLM response
    adapter = get_llm_adapter()
    try:
        async for chunk in adapter.generate_text_stream(
            prompt, temperature=config.temperature, max_tokens=config.max_tokens
        ):
            yield _sse({"type": "chunk", "content": chunk})
    except Exception as e:
        logger.error("LLM streaming failed: %s", e)
        yield _sse({"type": "error", "message": str(e)})
        return

    # 5. Done signal
    yield _sse({"type": "done"})
