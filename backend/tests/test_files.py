import io
import zipfile

import pytest

from app.services.files import UploadError, sanitize_filename, validate_upload
from tests.conftest import tiny_docx_bytes, tiny_pdf_bytes


def test_sanitize_filename_strips_paths() -> None:
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("rapport final.docx") == "rapport_final.docx"


def test_reject_empty() -> None:
    with pytest.raises(UploadError, match="Empty file"):
        validate_upload("a.pdf", b"")


def test_reject_too_large() -> None:
    with pytest.raises(UploadError, match="File too large"):
        validate_upload("a.pdf", b"%PDF" + b"x" * (5 * 1024 * 1024))


def test_reject_bad_extension() -> None:
    with pytest.raises(UploadError, match="Unsupported file type"):
        validate_upload("notes.txt", b"hello world")
    with pytest.raises(UploadError, match="Unsupported file type"):
        validate_upload("macro.docm", b"PK\x03\x04abcd")


def test_accept_pdf_and_docx_magic() -> None:
    pdf = tiny_pdf_bytes()
    docx = tiny_docx_bytes()
    assert validate_upload("doc.pdf", pdf, "application/pdf").endswith(".pdf")
    assert validate_upload("doc.docx", docx).endswith(".docx")


def test_reject_mismatched_magic() -> None:
    with pytest.raises(UploadError):
        validate_upload("fake.pdf", b"not-a-pdf")
    with pytest.raises(UploadError):
        validate_upload("fake.docx", b"not-a-zip")


def test_real_minimal_docx_container_pass() -> None:
    docx = tiny_docx_bytes()
    assert validate_upload("minimal.docx", docx) == "minimal.docx"


def test_zip_renamed_docx_without_word_document_xml_fail() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
    with pytest.raises(UploadError, match="Unsupported file type"):
        validate_upload("fake.docx", buf.getvalue())

    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w") as z:
        z.writestr("random.txt", "just a text file")
    with pytest.raises(UploadError, match="Unsupported file type"):
        validate_upload("arbitrary.docx", buf2.getvalue())


def test_invalid_pk_payload_fail() -> None:
    with pytest.raises(UploadError, match="Unsupported file type"):
        validate_upload("invalid_pk.docx", b"PK\x03\x04truncated-junk-pk-bytes")
