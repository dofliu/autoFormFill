"""
Email Draft Generator — RAG-powered email drafting with streaming.

Orchestrates: multi-collection search → prompt building → LLM streaming.
Yields SSE-formatted events for the router to wrap in StreamingResponse.
"""

import logging
from collections.abc import AsyncIterator

from app.schemas.chat import SourceChunk
from app.services.sse_pipeline import (
    format_context_default,
    rag_sse_stream,
    StreamConfig,
)

logger = logging.getLogger(__name__)

EMAIL_SYSTEM_PROMPT = """\
You are a professional email writer for an academic and research context.
Write an email draft based on the provided context documents.

Rules:
1. ONLY use information present in the provided context.
2. Address the recipient by name with appropriate formality.
3. Match the requested tone: {tone}.
4. Include specific details from context (projects, papers, findings) when relevant.
5. Write in the language matching the user's purpose description.
6. If context is insufficient for a detail, mark it with [需補充].
7. Structure: greeting → body → closing → signature placeholder "[Your Name]".

Recipient: {recipient_name} <{recipient_email}>
Subject hint: {subject_hint}

Retrieved context:
{context}"""


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def build_email_prompt(
    recipient_name: str,
    recipient_email: str,
    subject_hint: str | None,
    purpose: str,
    tone: str,
    context_chunks: list[SourceChunk],
) -> str:
    """Build the complete prompt for email draft generation."""
    context = format_context_default(context_chunks)

    system = EMAIL_SYSTEM_PROMPT.format(
        tone=tone,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        subject_hint=subject_hint or "(not specified)",
        context=context,
    )

    return f"{system}\n\nUser request: {purpose}\n\nDraft email:"


# ---------------------------------------------------------------------------
# Streaming orchestrator
# ---------------------------------------------------------------------------

async def email_draft_stream(
    recipient_name: str,
    recipient_email: str,
    purpose: str,
    subject_hint: str | None = None,
    tone: str = "professional",
    collections: list[str] | None = None,
    n_results: int = 5,
) -> AsyncIterator[str]:
    """Main email draft orchestrator: search → build prompt → stream LLM.

    Yields SSE-formatted strings (``data: {json}\\n\\n``).
    """
    search_query = f"{recipient_name} {purpose}"

    def _build(sources: list[SourceChunk]) -> str:
        return build_email_prompt(
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            subject_hint=subject_hint,
            purpose=purpose,
            tone=tone,
            context_chunks=sources,
        )

    async for event in rag_sse_stream(
        search_query=search_query,
        build_prompt=_build,
        config=StreamConfig(temperature=0.4, max_tokens=2048),
        collections=collections,
        n_results=n_results,
    ):
        yield event
