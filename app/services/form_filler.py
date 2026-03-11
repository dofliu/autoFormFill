import os
import shutil
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.form import FieldFillResult, FormFillResponse
from app.services import document_generator, entity_service, form_parser, user_service
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

    # Step 2: Load entity attribute names for routing prompt
    entity_attr_names = await entity_service.get_entity_attribute_names(db, user_id)

    # Step 3: Route fields to data sources via LLM
    routing = await route_fields(fields, entity_attribute_names=entity_attr_names or None)

    # Step 4: Fetch data for each field
    user = await user_service.get_user(db, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found.")

    # Merge entity attributes into a flat lookup dict
    entities = await entity_service.list_entities(db, user_id)
    entity_attrs = _merge_entity_attributes(entities)

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
            value = _get_sql_value(user, route.sql_target, entity_attrs)
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
                user_id=user_id,
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

    # Step 5: Save a persistent copy of the blank template so that
    # submit_form_with_overrides can re-generate the document later
    # (the upload temp file is deleted by the router after this call returns).
    ext = os.path.splitext(file_path)[1]
    template_copy_name = f"tpl_{uuid.uuid4().hex[:8]}{ext}"
    template_copy_path = os.path.join(settings.output_dir, template_copy_name)
    shutil.copy2(file_path, template_copy_path)

    # Step 6: Generate filled document
    output_path = document_generator.generate_filled_document(
        file_path, file_type, fill_data
    )

    fields_filled = sum(1 for r in results if r.source != "skip")
    fields_skipped = sum(1 for r in results if r.source == "skip")

    # Create job record (persisted to database)
    job_data = {
        "filename": original_filename,
        "template_filename": os.path.basename(file_path),
        "template_path": template_copy_path,
        "user_id": user_id,
        "fields": [r.dict() for r in results],
        "fill_data": fill_data,
        "output_path": output_path,
        "field_overrides": field_overrides or {},
    }

    job_id = await job_store.create_job(job_data, db)

    return FormFillResponse(
        job_id=job_id,
        filename=os.path.basename(output_path),
        fields_filled=fields_filled,
        fields_skipped=fields_skipped,
        results=results,
        output_path=output_path,
    )


def _merge_entity_attributes(entities) -> dict[str, str]:
    """Flatten all entity attributes into one dict.

    Most recently updated entity wins on key conflict (entities are already
    sorted by updated_at desc from the service layer).
    """
    merged: dict[str, str] = {}
    # Iterate in reverse so that the most recently updated entity overwrites
    for entity in reversed(entities):
        merged.update(entity.attributes)
    return merged


def _get_sql_value(user, sql_target: str, entity_attrs: dict[str, str] | None = None) -> str:
    """Extract a value from user profile or entity attributes.

    sql_target formats:
    - ``user_profiles.name_zh`` → UserProfile attribute
    - ``entities.key``          → entity attribute lookup
    """
    parts = sql_target.split(".")
    table = parts[0] if len(parts) >= 2 else ""
    column = parts[-1] if len(parts) >= 2 else parts[0]

    # Entity attributes
    if table == "entities":
        if entity_attrs:
            value = entity_attrs.get(column)
            if value is not None:
                return str(value)
        return "[需人工補充]"

    # UserProfile attributes (default path)
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
    job = await job_store.get_job(job_id, db)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    # Use the persistent template copy saved at fill time.
    # Fall back to the legacy uploads path for jobs created before this fix.
    template_path = job.get("template_path")
    if not template_path or not os.path.exists(template_path):
        legacy_path = os.path.join("data", "uploads", job["template_filename"])
        if os.path.exists(legacy_path):
            template_path = legacy_path
        else:
            raise ValueError(
                f"Template file not found for job {job_id}. "
                "Please re-upload and re-fill the form."
            )

    # Merge existing overrides with the new ones
    existing_overrides = job.get("field_overrides", {})
    all_overrides = {**existing_overrides, **field_overrides}

    return await fill_form(
        file_path=template_path,
        file_type=os.path.splitext(job["template_filename"])[1].lstrip("."),
        original_filename=job["filename"],
        user_id=job["user_id"],
        db=db,
        field_overrides=all_overrides,
    )
