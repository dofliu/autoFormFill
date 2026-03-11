"""Report generation service — structured report from knowledge base via SSE streaming."""

import logging
from collections.abc import AsyncIterator

from app.schemas.chat import SourceChunk
from app.services.sse_pipeline import (
    format_context_report,
    rag_sse_stream,
    StreamConfig,
)

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
    context = format_context_report(context_chunks)

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
    user_id: int | None = None,
) -> AsyncIterator[str]:
    """Generate a structured report via RAG + SSE streaming.

    Args:
        user_id: Filter search results by owner — ``None`` = no filtering.

    Yields SSE-formatted strings:
    - ``{"type": "sources", "sources": [...]}``
    - ``{"type": "chunk", "content": "..."}``
    - ``{"type": "done"}`` or ``{"type": "error", "message": "..."}``
    """

    def _build(sources: list[SourceChunk]) -> str:
        return build_report_prompt(
            topic=topic,
            report_type=report_type,
            target_audience=target_audience,
            sections=sections,
            language=language,
            context_chunks=sources,
        )

    async for event in rag_sse_stream(
        search_query=topic,
        build_prompt=_build,
        config=StreamConfig(temperature=0.3, max_tokens=4096),
        collections=collections,
        n_results=n_results,
        user_id=user_id,
    ):
        yield event
