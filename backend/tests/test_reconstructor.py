from __future__ import annotations

import pytest

from app.models import EncodeConfig
from app.services.encoder import encode
from app.services.exporter import build_xlsx
from app.services.reconstructor import reconstruct_from_excel
from app.services.validator import validate_roundtrip
from tests.conftest import tiny_doc_bytes, tiny_docx_bytes, tiny_pdf_bytes


@pytest.mark.parametrize(
    ("filename", "maker"),
    [
        ("sample.doc", tiny_doc_bytes),
        ("sample.docx", tiny_docx_bytes),
        ("sample.pdf", tiny_pdf_bytes),
    ],
)
def test_reconstruct_from_xlsx_roundtrip(filename: str, maker) -> None:
    content = maker(b"hello-dna-storage-content-12345")
    config = EncodeConfig(compression=True, ecc=True, fragment_length=150)
    result = encode(content, config, filename=filename)
    roundtrip = validate_roundtrip(content, result.fragments, result.decode_metadata)
    assert roundtrip.result == "PASS"

    xlsx_bytes = build_xlsx(result, roundtrip)
    recon = reconstruct_from_excel(xlsx_bytes, filename=f"export_{filename}.xlsx")

    assert recon.reconstructed_bytes == content
    assert recon.filename == filename
    assert recon.size == len(content)
    assert recon.sha256 == roundtrip.sha256_original
    assert recon.sha256_matched is True
    assert recon.fragment_count == result.stats.fragment_count


def test_reconstruct_without_compression() -> None:
    content = tiny_doc_bytes(b"uncompressed-doc-content")
    config = EncodeConfig(compression=False, ecc=False, fragment_length=100)
    result = encode(content, config, filename="uncompressed.doc")
    roundtrip = validate_roundtrip(content, result.fragments, result.decode_metadata)
    assert roundtrip.result == "PASS"

    xlsx_bytes = build_xlsx(result, roundtrip)
    recon = reconstruct_from_excel(xlsx_bytes, filename="export_uncompressed.xlsx")

    assert recon.reconstructed_bytes == content
    assert recon.filename == "uncompressed.doc"
    assert recon.sha256_matched is True


def test_reconstruct_invalid_excel() -> None:
    with pytest.raises(ValueError, match="Invalid XLSX|Unsupported format"):
        reconstruct_from_excel(b"PK\x03\x04corrupted_zip_data", "test.xlsx")

    with pytest.raises(ValueError, match="Empty file"):
        reconstruct_from_excel(b"", "test.xlsx")
