import os
import uuid
from pathlib import Path

from fastapi import UploadFile


async def save_upload_file(upload_file: UploadFile, upload_dir: str) -> str:
    """Save an UploadFile to disk with a unique name. Returns the file path."""
    ext = Path(upload_file.filename or "file").suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, unique_name)
    content = await upload_file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def detect_file_type(filename: str) -> str:
    """Return 'docx', 'pdf', or 'unknown' based on file extension."""
    ext = Path(filename).suffix.lower()
    return {".docx": "docx", ".pdf": "pdf"}.get(ext, "unknown")
