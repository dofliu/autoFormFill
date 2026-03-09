import asyncio
import uuid

import fitz  # PyMuPDF
import pdfplumber
from docx import Document as DocxDocument

from app.llm.factory import get_llm_adapter
from app.schemas.document import DocumentMetadataInput, DocumentUploadResponse
from app.utils.chunker import chunk_text
from app.vector_store import get_collection


def extract_text_from_docx(file_path: str) -> str:
    """Extract all text from a .docx file."""
    doc = DocxDocument(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    # Also extract from tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    paragraphs.append(cell.text.strip())
    return "\n".join(paragraphs)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF using pdfplumber (better for tables) with PyMuPDF fallback."""
    texts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
    except Exception:
        # Fallback to PyMuPDF
        doc = fitz.open(file_path)
        for page in doc:
            texts.append(page.get_text())
        doc.close()
    return "\n".join(texts)


def extract_text(file_path: str, file_type: str) -> str:
    """Extract text based on file type."""
    if file_type == "docx":
        return extract_text_from_docx(file_path)
    elif file_type == "pdf":
        return extract_text_from_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def _build_metadata(meta: DocumentMetadataInput) -> dict:
    """Build ChromaDB-compatible metadata dict (string values only)."""
    result = {"title": meta.title, "doc_type": meta.doc_type}
    if meta.authors:
        result["authors"] = meta.authors
    if meta.publish_year:
        result["publish_year"] = str(meta.publish_year)
    if meta.keywords:
        result["keywords"] = meta.keywords
    if meta.project_name:
        result["project_name"] = meta.project_name
    if meta.funding_agency:
        result["funding_agency"] = meta.funding_agency
    if meta.execution_period:
        result["execution_period"] = meta.execution_period
    if meta.tech_stack:
        result["tech_stack"] = meta.tech_stack
    return result


async def embed_and_store(
    file_path: str, file_type: str, metadata: DocumentMetadataInput
) -> DocumentUploadResponse:
    """Extract text, chunk, embed, and store in ChromaDB."""
    text = extract_text(file_path, file_type)
    if not text.strip():
        raise ValueError("No text could be extracted from the document.")

    chunks = chunk_text(text)
    doc_id = uuid.uuid4().hex

    # Get embeddings via LLM adapter
    adapter = get_llm_adapter()
    embeddings = await asyncio.to_thread(adapter.embed_batch, chunks)

    # Determine collection
    collection_name = (
        "academic_papers" if metadata.doc_type == "paper" else "research_projects"
    )
    collection = get_collection(collection_name)

    # Store in ChromaDB
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    meta_dict = _build_metadata(metadata)
    metadatas = [meta_dict for _ in chunks]

    await asyncio.to_thread(
        collection.add,
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return DocumentUploadResponse(
        doc_id=doc_id,
        collection=collection_name,
        chunks_count=len(chunks),
        metadata=meta_dict,
    )


async def search_documents(
    query: str, collection_name: str, n_results: int = 5
) -> list[dict]:
    """Search ChromaDB for relevant document chunks."""
    adapter = get_llm_adapter()
    query_embedding = await asyncio.to_thread(adapter.embed_text, query)

    collection = get_collection(collection_name)
    results = await asyncio.to_thread(
        collection.query,
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    items = []
    if results and results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            items.append(
                {
                    "doc_id": doc_id,
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results["distances"] else None,
                }
            )
    return items
