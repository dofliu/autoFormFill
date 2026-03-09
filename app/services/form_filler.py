import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.form import FieldFillResult, FormFillResponse
from app.services import document_generator, form_parser, user_service
from app.services.intent_router import route_fields
from app.services.rag_pipeline import generate_field_content
from app.job_store import job_store


async def fill_form(
    file_path: str,
    file_type: str,
    original_filename: str,
    user_id: int,
    db: AsyncSession,
    field_overrides: dict[str, str] | None = None,
) -> FormFillResponse:
    """Full pipeline: parse → route → retrieve/query → generate → fill document."""

    # Step 1: Parse form fields
    fields = form_parser.parse_form(file_path, file_type)
    if not fields:
        raise ValueError("No fillable fields detected in the document.")

    # Step 2: Route fields to data sources via LLM
    routing = await route_fields(fields)

    # Step 3: Fetch data for each field
    user = await user_service.get_user(db, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found.")

    fill_data: dict[str, str] = {}
    results: list[FieldFillResult] = []

    for route in routing:
        field_name = route.field_name

        # Check for manual overrides first
        if field_overrides and field_name in field_overrides:
            fill_data[field_name] = field_overrides[field_name]
            results.append(
                FieldFillResult(
                    field_name=field_name,
                    value=field_overrides[field_name],
                    source="override",
                )
            )
            continue

        if route.data_source == "SQL_DB" and route.sql_target:
            value = _get_sql_value(user, route.sql_target)
            fill_data[field_name] = value
            results.append(
                FieldFillResult(
                    field_name=field_name,
                    value=value,
                    source="sql",
                    confidence=route.confidence,
                )
            )

        elif route.data_source == "VECTOR_DB" and route.search_query:
            generated, confidence = await generate_field_content(
                field_name=field_name,
                search_query=route.search_query,
            )
            fill_data[field_name] = generated
            results.append(
                FieldFillResult(
                    field_name=field_name,
                    value=generated,
                    source="rag",
                    confidence=confidence,
                )
            )

        else:
            fill_data[field_name] = "[需人工補充]"
            results.append(
                FieldFillResult(
                    field_name=field_name,
                    value="[需人工補充]",
                    source="skip",
                    confidence=0.0,
                )
            )

    # Step 4: Generate filled document
    output_path = document_generator.generate_filled_document(
        file_path, file_type, fill_data
    )

    fields_filled = sum(1 for r in results if r.source != "skip")
    fields_skipped = sum(1 for r in results if r.source == "skip")

    # Create job record
    job_data = {
        "filename": original_filename,
        "template_filename": os.path.basename(file_path),
        "user_id": user_id,
        "fields": [r.dict() for r in results],
        "fill_data": fill_data,
        "output_path": output_path,
        "field_overrides": field_overrides or {}
    }
    
    job_id = job_store.create_job(job_data)

    return FormFillResponse(
        job_id=job_id,
        filename=os.path.basename(output_path),
        fields_filled=fields_filled,
        fields_skipped=fields_skipped,
        results=results,
        output_path=output_path,
    )


def _get_sql_value(user, sql_target: str) -> str:
    """Extract a value from the user profile based on sql_target like 'user_profiles.name_zh'."""
    parts = sql_target.split(".")
    column = parts[-1] if len(parts) >= 2 else parts[0]

    # Map column names to UserProfile attributes
    value = getattr(user, column, None)
    if value is None:
        return "[需人工補充]"
    return str(value)


async def submit_form_with_overrides(
    job_id: str,
    field_overrides: dict[str, str],
    db: AsyncSession,
) -> FormFillResponse:
    """Regenerate form with new field overrides."""
    job = job_store.get_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # Get the original template file path
    template_filename = job["template_filename"]
    template_path = os.path.join("data", "uploads", template_filename)
    
    if not os.path.exists(template_path):
        raise ValueError(f"Template file not found: {template_path}")
    
    # Run fill_form again with new overrides
    # Merge existing overrides with new ones
    existing_overrides = job.get("field_overrides", {})
    all_overrides = {**existing_overrides, **field_overrides}
    
    return await fill_form(
        file_path=template_path,
        file_type=os.path.splitext(template_filename)[1].lstrip('.'),
        original_filename=job["filename"],
        user_id=job["user_id"],
        db=db,
        field_overrides=all_overrides,
    )
