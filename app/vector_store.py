import chromadb

from app.config import settings

_chroma_client: chromadb.ClientAPI | None = None

COLLECTIONS = ["academic_papers", "research_projects"]


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _chroma_client


def get_collection(name: str) -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(name=name)


def init_vector_store() -> None:
    """Ensure all collections exist at startup."""
    client = get_chroma_client()
    for name in COLLECTIONS:
        client.get_or_create_collection(name=name)
