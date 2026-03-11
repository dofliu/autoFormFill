from pydantic import BaseModel


class ReportRequest(BaseModel):
    """Request body for POST /api/v1/report/generate."""

    topic: str
    report_type: str = "summary"  # "summary" | "detailed" | "executive"
    target_audience: str = "academic"  # "academic" | "business" | "general"
    sections: list[str] | None = None  # Custom outline; None = use default for report_type
    language: str = "zh-TW"  # "zh-TW" | "en"
    collections: list[str] | None = None
    n_results: int = 8  # Reports need more context than chat/email
    user_id: int | None = None  # fallback when AUTH_ENABLED=False
