"""Inverse reconstruction: restore original document bytes from an Excel workbook."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.decoder import DecodingError, decode
from app.services.dna import sha256_hex
from app.services.excel_reader import (
    ExcelParseError,
    build_decode_metadata_from_dict,
    extract_sequences_and_metadata,
)


@dataclass
class ReconstructResult:
    reconstructed_bytes: bytes
    filename: str
    size: int
    sha256: str
    sha256_original: str | None
    sha256_matched: bool | None
    fragment_count: int
    compression: bool
    ecc: bool


def reconstruct_from_excel(content: bytes, filename: str = "export.xlsx") -> ReconstructResult:
    """Parse an Excel file (XLSX or XLS), decode sequences, and reconstruct the original document."""
    sequences, meta_dict = extract_sequences_and_metadata(content, filename)
    metadata, orig_name, sha_orig = build_decode_metadata_from_dict(meta_dict, sequences)

    try:
        reconstructed = decode(sequences, metadata)
    except DecodingError as exc:
        raise ValueError("Decoding failed: could not reconstruct file from DNA sequences") from exc

    current_sha256 = sha256_hex(reconstructed)
    sha_matched = (current_sha256 == sha_orig) if sha_orig else None

    return ReconstructResult(
        reconstructed_bytes=reconstructed,
        filename=orig_name,
        size=len(reconstructed),
        sha256=current_sha256,
        sha256_original=sha_orig,
        sha256_matched=sha_matched,
        fragment_count=len(sequences),
        compression=metadata.compression,
        ecc=metadata.ecc,
    )
