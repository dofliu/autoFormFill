from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_user
from app.models.user_profile import UserProfile
from app.schemas.report import ReportRequest
from app.services.report_generator import report_stream

router = APIRouter(prefix="/api/v1/report", tags=["Report"])


@router.post("/generate")
async def generate_report(
    request: ReportRequest,
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Generate a structured report from the knowledge base.

    Streams the response using Server-Sent Events (SSE).

    SSE event types:
    - ``sources``: Retrieved context chunks used for generation
    - ``chunk``: A text fragment of the generated report
    - ``done``: Report generation completed
    - ``error``: An error occurred during generation
    """
    # Resolve user_id: JWT token takes precedence, then request body fallback
    user_id = current_user.id if current_user else request.user_id

    return StreamingResponse(
        report_stream(
            topic=request.topic,
            report_type=request.report_type,
            target_audience=request.target_audience,
            sections=request.sections,
            language=request.language,
            collections=request.collections,
            n_results=request.n_results,
            user_id=user_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
