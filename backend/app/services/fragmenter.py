"""Split a payload into fixed-size chunks for DNA fragments."""

from __future__ import annotations

from app.constants import ECC_NSYM, INDEX_BYTES, VARIANT_HEADER_NT


def payload_capacity(fragment_length: int, ecc: bool) -> int:
    """Number of payload bytes stored in one fragment (excluding index and ECC)."""
    available_nt = fragment_length - VARIANT_HEADER_NT
    available_bytes = available_nt // 4
    nsym = ECC_NSYM if ecc else 0
    capacity = available_bytes - INDEX_BYTES - nsym
    if capacity < 1:
        raise ValueError("fragment_length is too small for the chosen ECC setting")
    return capacity


def split_payload(payload: bytes, capacity: int) -> list[bytes]:
    if capacity < 1:
        raise ValueError("payload capacity must be at least 1 byte")
    if not payload:
        return [b"\x00" * capacity]
    chunks: list[bytes] = []
    for offset in range(0, len(payload), capacity):
        chunk = payload[offset : offset + capacity]
        if len(chunk) < capacity:
            chunk = chunk + b"\x00" * (capacity - len(chunk))
        chunks.append(chunk)
    return chunks
