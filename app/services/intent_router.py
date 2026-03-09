import json
import logging

from app.llm.factory import get_llm_adapter
from app.schemas.form import FieldRoutingResult, FormField

logger = logging.getLogger(__name__)

ROUTING_PROMPT = """You are a field classifier for an academic form-filling system.

Given form fields, classify each one into a data source:

- SQL_DB: Maps to a user profile field (name, title, email, department, university, phone, address)
  or education/experience record. Provide the exact sql_target as "table.column".
  Available columns in user_profiles: name_zh, name_en, title, department, university, email, phone_office, address
  Available columns in education_experiences: organization, role_degree, start_date, end_date

- VECTOR_DB: Requires retrieval from academic papers or research projects
  (e.g., research summary, publication list, project description, technical expertise).
  Provide a search_query in the language matching the field context.

- SKIP: Cannot be auto-filled (signatures, stamps, dates-to-be-determined, checkboxes).

Form fields to classify:
{fields_json}

Respond as a JSON array. Each element must have:
- field_name (string)
- data_source ("SQL_DB" | "VECTOR_DB" | "SKIP")
- sql_target (string or null)
- search_query (string or null)
- confidence (float 0.0-1.0)
"""


async def route_fields(
    fields: list[FormField],
    entity_attribute_names: list[str] | None = None,
) -> list[FieldRoutingResult]:
    """Use LLM to classify each form field into its data source.

    Args:
        fields: Form fields to classify.
        entity_attribute_names: If provided, injects available entity attribute
            keys into the prompt so the router can map fields to ``entities.<key>``.
    """
    if not fields:
        return []

    fields_json = json.dumps(
        [f.model_dump() for f in fields], ensure_ascii=False, indent=2
    )
    prompt = ROUTING_PROMPT.format(fields_json=fields_json)

    # Inject entity attributes into prompt when available
    if entity_attribute_names:
        entity_hint = (
            "\n  Available entity attributes (use sql_target = \"entities.<key>\"): "
            + ", ".join(entity_attribute_names)
        )
        prompt = prompt.replace(
            "  Available columns in education_experiences:",
            entity_hint + "\n  Available columns in education_experiences:",
        )

    adapter = get_llm_adapter()
    try:
        result = await adapter.generate_json(prompt)
    except Exception as e:
        logger.warning(
            "Intent routing LLM call failed: %s. Falling back to SKIP for all %d fields.",
            e, len(fields),
        )
        return [
            FieldRoutingResult(
                field_name=f.field_name,
                data_source="SKIP",
                confidence=0.0,
            )
            for f in fields
        ]

    routing_results = []
    for item in result:
        routing_results.append(
            FieldRoutingResult(
                field_name=item.get("field_name", ""),
                data_source=item.get("data_source", "SKIP"),
                sql_target=item.get("sql_target"),
                search_query=item.get("search_query"),
                confidence=item.get("confidence", 0.5),
            )
        )
    return routing_results
