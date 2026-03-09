"""
Email Draft Generator — RAG-powered email drafting with streaming.

Orchestrates: multi-collection search → prompt building → LLM streaming.
Yields SSE-formatted events for the router to wrap in StreamingResponse.

Reuses ``search_all_collections`` and ``_sse`` from the chat service.
"""
import logging
from collections.abc import AsyncIterator

from app.llm.factory import get_llm_adapter
from app.schemas.chat import SourceChunk
from app.services.chat_service import _sse, search_all_collections

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
    # 1. Search knowledge base for relevant context
    search_query = f"{recipient_name} {purpose}"
    sources = await search_all_collections(search_query, collections, n_results)

    # 2. Emit sources event
    sources_data = [s.model_dump() for s in sources]
    yield _sse({"type": "sources", "sources": sources_data})

    # 3. Build prompt
    prompt = build_email_prompt(
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        subject_hint=subject_hint,
        purpose=purpose,
        tone=tone,
        context_chunks=sources,
    )

    # 4. Stream LLM response
    adapter = get_llm_adapter()
    try:
        async for chunk in adapter.generate_text_stream(
            prompt, temperature=0.4, max_tokens=2048
        ):
            yield _sse({"type": "chunk", "content": chunk})
    except Exception as e:
        logger.error(f"Email draft LLM streaming failed: {e}")
        yield _sse({"type": "error", "message": str(e)})
        return

    # 5. Done signal
    yield _sse({"type": "done"})
