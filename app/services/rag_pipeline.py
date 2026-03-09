from app.llm.factory import get_llm_adapter
from app.services.document_service import search_documents

GENERATION_PROMPT = """Based on the following academic documents, generate content for
the form field "{field_name}".

Retrieved context:
{context}

Constraints:
- Maximum length: {max_length} characters
- Language: {language}
- Format: {format_hint}

Rules:
1. ONLY use information present in the provided context.
2. If the context is insufficient to answer, output EXACTLY: [需人工補充]
3. Do NOT fabricate names, dates, numbers, or citations.
4. Be concise and directly address what the field asks for.

Generate the field content:"""


async def generate_field_content(
    field_name: str,
    search_query: str,
    collection_name: str = "academic_papers",
    max_length: int = 1000,
    language: str = "zh-TW",
    format_hint: str = "paragraph",
) -> tuple[str, float]:
    """Retrieve relevant chunks and generate content for a form field.

    Returns (generated_text, confidence_score).
    """
    # Step 1: Retrieve relevant document chunks
    results = await search_documents(search_query, collection_name, n_results=5)

    if not results:
        return "[需人工補充]", 0.0

    context_chunks = [r["text"] for r in results]
    context = "\n---\n".join(context_chunks)

    # Step 2: Check if context is too thin
    total_context_len = sum(len(c) for c in context_chunks)
    if total_context_len < 50:
        return "[需人工補充]", 0.0

    # Step 3: Generate content
    prompt = GENERATION_PROMPT.format(
        field_name=field_name,
        context=context,
        max_length=max_length,
        language=language,
        format_hint=format_hint,
    )

    adapter = get_llm_adapter()
    generated = await adapter.generate_text(prompt, temperature=0.3)

    # Step 4: Self-correction — enforce length constraint
    if len(generated) > max_length:
        shorten_prompt = (
            f"Shorten the following text to under {max_length} characters "
            f"while preserving key information. Language: {language}\n\n{generated}"
        )
        generated = await adapter.generate_text(shorten_prompt, temperature=0.1)

    # Step 5: Hallucination guard — basic check
    generated = _hallucination_check(generated, context_chunks)

    confidence = min(0.9, 0.5 + 0.1 * len(results))
    return generated, confidence


def _hallucination_check(generated: str, source_chunks: list[str]) -> str:
    """Basic hallucination guard: if sources are empty or too short, reject."""
    if not source_chunks:
        return "[需人工補充]"
    if all(len(c.strip()) < 20 for c in source_chunks):
        return "[需人工補充]"
    return generated
