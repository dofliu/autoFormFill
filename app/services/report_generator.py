"""Report generation service — structured report from knowledge base via SSE streaming."""

import logging
from collections.abc import AsyncIterator

from app.llm.factory import get_llm_adapter
from app.schemas.chat import SourceChunk
from app.services.chat_service import _sse, search_all_collections

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default section outlines per report type
# ---------------------------------------------------------------------------

DEFAULT_SECTIONS: dict[str, list[str]] = {
    "summary": [
        "摘要 (Abstract)",
        "重點發現 (Key Findings)",
        "結論與建議 (Conclusions & Recommendations)",
    ],
    "detailed": [
        "摘要 (Abstract)",
        "背景與動機 (Background & Motivation)",
        "方法 (Methods)",
        "結果 (Results)",
        "討論 (Discussion)",
        "結論 (Conclusions)",
        "參考資料 (References)",
    ],
    "executive": [
        "執行摘要 (Executive Summary)",
        "關鍵指標 (Key Metrics)",
        "分析 (Analysis)",
        "建議行動 (Recommended Actions)",
    ],
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

REPORT_SYSTEM_PROMPT = """\
You are an expert report writer specializing in academic and research contexts.
Generate a well-structured report based on the provided context documents.

Rules:
1. ONLY use information present in the provided context documents.
2. Follow the specified outline structure exactly, using Markdown headings (##).
3. Write in the specified language: {language}.
4. Tailor the depth and style for the target audience: {audience}.
5. If the context does not contain enough information for a section, write "[需補充]" as a placeholder.
6. Use specific data, names, and findings from the context — do not fabricate.
7. Maintain a {tone} tone throughout the report.
8. For "References" sections, only cite sources mentioned in the provided context.

Report topic: {topic}

Outline:
{outline}

Retrieved context:
{context}"""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

AUDIENCE_TONE: dict[str, str] = {
    "academic": "formal and scholarly",
    "business": "professional and concise",
    "general": "accessible and clear",
}


def build_report_prompt(
    topic: str,
    report_type: str,
    target_audience: str,
    sections: list[str] | None,
    language: str,
    context_chunks: list[SourceChunk],
) -> str:
    """Assemble the full LLM prompt for report generation."""
    # Determine sections
    outline_sections = sections or DEFAULT_SECTIONS.get(report_type, DEFAULT_SECTIONS["summary"])
    outline = "\n".join(f"- {s}" for s in outline_sections)

    # Format context
    if context_chunks:
        ctx_parts = []
        for i, src in enumerate(context_chunks, 1):
            collection = src.collection
            title = src.metadata.get("title", "Unknown")
            ctx_parts.append(f"[Source {i} | {collection} | {title}]\n{src.text}")
        context = "\n\n".join(ctx_parts)
    else:
        context = "(No context documents found — mark all sections as [需補充])"

    tone = AUDIENCE_TONE.get(target_audience, "formal and scholarly")

    return REPORT_SYSTEM_PROMPT.format(
        language=language,
        audience=target_audience,
        tone=tone,
        topic=topic,
        outline=outline,
        context=context,
    )


# ---------------------------------------------------------------------------
# Streaming orchestrator
# ---------------------------------------------------------------------------

async def report_stream(
    topic: str,
    report_type: str = "summary",
    target_audience: str = "academic",
    sections: list[str] | None = None,
    language: str = "zh-TW",
    collections: list[str] | None = None,
    n_results: int = 8,
) -> AsyncIterator[str]:
    """Generate a structured report via RAG + SSE streaming.

    Yields SSE-formatted strings:
    - ``{"type": "sources", "sources": [...]}``
    - ``{"type": "chunk", "content": "..."}``
    - ``{"type": "done"}`` or ``{"type": "error", "message": "..."}``
    """
    # 1. Search knowledge base
    search_query = topic
    sources = await search_all_collections(search_query, collections, n_results)

    # 2. Emit sources
    sources_data = [s.model_dump() for s in sources]
    yield _sse({"type": "sources", "sources": sources_data})

    # 3. Build prompt
    prompt = build_report_prompt(
        topic=topic,
        report_type=report_type,
        target_audience=target_audience,
        sections=sections,
        language=language,
        context_chunks=sources,
    )

    # 4. Stream LLM response
    adapter = get_llm_adapter()
    try:
        async for chunk in adapter.generate_text_stream(
            prompt, temperature=0.3, max_tokens=4096
        ):
            yield _sse({"type": "chunk", "content": chunk})
    except Exception as e:
        logger.error("Report generation LLM streaming failed: %s", e)
        yield _sse({"type": "error", "message": str(e)})
        return

    # 5. Done
    yield _sse({"type": "done"})
