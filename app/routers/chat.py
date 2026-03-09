"""
Chat Router — streaming knowledge QA endpoint.

Uses Server-Sent Events (SSE) to stream RAG-powered answers
from the user's knowledge base.
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.services.chat_service import chat_stream

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.post("")
async def chat(request: ChatRequest):
    """Chat with your knowledge base.

    Accepts a user message and optional conversation history.
    Returns a streaming SSE response with retrieved sources and
    generated answer chunks.

    SSE event types:
    - ``sources``: Retrieved document chunks from the knowledge base
    - ``chunk``: A text fragment of the generated answer
    - ``done``: Stream completed successfully
    - ``error``: An error occurred during generation
    """
    return StreamingResponse(
        chat_stream(
            message=request.message,
            history=request.history,
            collections=request.collections,
            n_results=request.n_results,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
