from pydantic import BaseModel


class FormField(BaseModel):
    field_name: str
    field_label: str | None = None
    field_type: str  # "template_var" | "table_cell" | "pdf_widget" | "llm_detected"
    location: str | None = None


class FormParseResponse(BaseModel):
    filename: str
    file_type: str
    fields: list[FormField]
    total_fields: int


class FieldRoutingResult(BaseModel):
    field_name: str
    data_source: str  # "SQL_DB" | "VECTOR_DB" | "SKIP"
    sql_target: str | None = None
    search_query: str | None = None
    confidence: float = 0.0


class FormFillRequest(BaseModel):
    user_id: int
    field_overrides: dict[str, str] | None = None


class FieldFillResult(BaseModel):
    field_name: str
    value: str
    source: str  # "sql", "rag", "override", "skip"
    confidence: float = 1.0


class FormFillResponse(BaseModel):
    job_id: str
    filename: str
    fields_filled: int
    fields_skipped: int
    results: list[FieldFillResult]
    output_path: str


class FormPreviewResponse(BaseModel):
    job_id: str
    filename: str
    template_filename: str
    fields: list[FieldFillResult]
    created_at: str


class FormSubmitRequest(BaseModel):
    job_id: str
    field_overrides: dict[str, str]
