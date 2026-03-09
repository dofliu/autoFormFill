def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    separator: str = "\n",
) -> list[str]:
    """Split text into overlapping chunks by paragraph boundaries."""
    if not text.strip():
        return []
    if len(text) <= chunk_size:
        return [text.strip()]

    paragraphs = text.split(separator)
    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 1 > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Keep overlap from end of current chunk
            if overlap > 0:
                current_chunk = current_chunk[-overlap:] + separator + para
            else:
                current_chunk = para
        else:
            current_chunk = (current_chunk + separator + para) if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks
