from pydantic import BaseModel


class EmailDraftRequest(BaseModel):
    recipient_name: str
    recipient_email: str
    subject_hint: str | None = None
    purpose: str
    tone: str = "professional"  # "professional" | "friendly" | "formal"
    collections: list[str] | None = None
    n_results: int = 5
