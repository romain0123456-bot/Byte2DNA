"""Upload validation: extension, size, emptiness. Binary-only, no parsing."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

from app.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES

PDF_MAGIC = b"%PDF"
DOCX_MAGIC = b"PK"


class UploadError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sanitize_filename(name: str) -> str:
    base = Path(name or "upload").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return cleaned or "upload.bin"


def validate_upload(filename: str, content: bytes, content_type: str | None = None) -> str:
    if not content:
        raise UploadError("Empty file", "Empty file")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise UploadError("File too large", "File too large")

    safe_name = sanitize_filename(filename)
    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadError("Unsupported file type", "Unsupported file type")

    mime = (content_type or "").split(";")[0].strip().lower()
    if extension == ".pdf":
        if not content.startswith(PDF_MAGIC):
            raise UploadError("Unsupported file type", "Unsupported file type")
        if mime and mime not in {"application/pdf", "application/octet-stream"}:
            raise UploadError("Unsupported file type", "Unsupported file type")
    elif extension == ".docx":
        if not content.startswith(DOCX_MAGIC):
            raise UploadError("Unsupported file type", "Unsupported file type")
        if mime and mime not in {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
            "application/zip",
        }:
            raise UploadError("Unsupported file type", "Unsupported file type")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise UploadError("Unsupported file type", "Unsupported file type")
        except UploadError:
            raise
        except Exception as exc:
            raise UploadError("Unsupported file type", "Unsupported file type") from exc
    return safe_name
