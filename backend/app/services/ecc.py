"""Reed-Solomon helpers. Isolated so the base round-trip never depends on ECC."""

from __future__ import annotations

from reedsolo import RSCodec, ReedSolomonError

from app.constants import ECC_NSYM


class EccError(ValueError):
    """Raised when ECC encoding or decoding fails."""


def encode_ecc(data: bytes, enabled: bool) -> bytes:
    if not enabled:
        return data
    return bytes(RSCodec(ECC_NSYM).encode(data))


def decode_ecc(data: bytes, enabled: bool) -> bytes:
    if not enabled:
        return data
    try:
        decoded = RSCodec(ECC_NSYM).decode(data)[0]
    except ReedSolomonError as exc:
        raise EccError("Decoding failed") from exc
    return bytes(decoded)
