"""Shared binary fixtures. Files are synthetic; the codec is bytes-generic."""

from __future__ import annotations

import io
import zipfile


def tiny_pdf_bytes(payload: bytes = b"Byte2DNA pdf fixture") -> bytes:
    body = payload.decode("latin-1", errors="replace")
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 1 1]>>endobj\n"
        b"4 0 obj<</Length "
        + str(len(payload)).encode()
        + b">>stream\n"
        + payload
        + b"\nendstream\nendobj\n"
        b"trailer<</Root 1 0 R>>\n"
        b"%%EOF\n"
        + body.encode("latin-1", errors="replace")
    )


def tiny_docx_bytes(payload: bytes = b"Byte2DNA docx fixture") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        archive.writestr("word/document.xml", payload.decode("latin-1", errors="replace"))
    return buffer.getvalue()
