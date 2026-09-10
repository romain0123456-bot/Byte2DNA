"""Round-trip validation: DNA fragments must reconstruct the original bytes."""

from __future__ import annotations

import random

from app.models import DecodeMetadata, Fragment, RoundtripResult
from app.services.decoder import DecodingError, decode
from app.services.dna import sha256_hex


def validate_roundtrip(
    original: bytes,
    fragments: list[Fragment],
    metadata: DecodeMetadata,
    *,
    shuffle: bool = True,
) -> RoundtripResult:
    """Decode from DNA sequences only. Never returns the original buffer as-is."""
    original_hash = sha256_hex(original)
    sequences = [fragment.sequence for fragment in fragments]
    if shuffle:
        sequences = list(sequences)
        random.Random(2026).shuffle(sequences)

    try:
        reconstructed = decode(sequences, metadata)
    except DecodingError as exc:
        return RoundtripResult(
            result="FAIL",
            sha256_original=original_hash,
            sha256_reconstructed=None,
            reconstructed_size=None,
            message=str(exc) or "Round-trip failed",
            bit_identical=False,
        )

    reconstructed_hash = sha256_hex(reconstructed)
    identical = reconstructed == original and reconstructed_hash == original_hash
    if identical:
        return RoundtripResult(
            result="PASS",
            sha256_original=original_hash,
            sha256_reconstructed=reconstructed_hash,
            reconstructed_size=len(reconstructed),
            message="Fichier reconstruit bit-à-bit",
            bit_identical=True,
        )
    return RoundtripResult(
        result="FAIL",
        sha256_original=original_hash,
        sha256_reconstructed=reconstructed_hash,
        reconstructed_size=len(reconstructed),
        message="Round-trip failed",
        bit_identical=False,
    )
