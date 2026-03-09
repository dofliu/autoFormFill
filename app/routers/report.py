from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.report import ReportRequest
from app.services.report_generator import report_stream

router = APIRouter(prefix="/api/v1/report", tags=["Report"])


@router.post("/generate")
async def generate_report(request: ReportRequest):
    """Generate a structured report from the knowledge base.

    Streams the response using Server-Sent Events (SSE).

    SSE event types:
    - ``sources``: Retrieved context chunks used for generation
    - ``chunk``: A text fragment of the generated report
    - ``done``: Report generation completed
    - ``error``: An error occurred during generation
    """
    return StreamingResponse(
        report_stream(
            topic=request.topic,
            report_type=request.report_type,
            target_audience=request.target_audience,
            sections=request.sections,
            language=request.language,
            collections=request.collections,
            n_results=request.n_results,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
