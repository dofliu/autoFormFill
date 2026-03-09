"""
Email Router — streaming email draft generation endpoint.

Uses Server-Sent Events (SSE) to stream RAG-powered email drafts
based on recipient info and purpose description.
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.email import EmailDraftRequest
from app.services.email_generator import email_draft_stream

router = APIRouter(prefix="/api/v1/email", tags=["Email"])


@router.post("/draft")
async def email_draft(request: EmailDraftRequest):
    """Generate an email draft from your knowledge base.

    Accepts recipient information, purpose description, and optional
    tone preference. Returns a streaming SSE response with retrieved
    sources and generated email draft chunks.

    SSE event types:
    - ``sources``: Retrieved document chunks from the knowledge base
    - ``chunk``: A text fragment of the generated email draft
    - ``done``: Stream completed successfully
    - ``error``: An error occurred during generation
    """
    return StreamingResponse(
        email_draft_stream(
            recipient_name=request.recipient_name,
            recipient_email=request.recipient_email,
            purpose=request.purpose,
            subject_hint=request.subject_hint,
            tone=request.tone,
            collections=request.collections,
            n_results=request.n_results,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
