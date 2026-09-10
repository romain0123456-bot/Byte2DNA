"""Low-level DNA mapping, hashing and keystream helpers."""

from __future__ import annotations

import hashlib

from app.constants import BASE_TO_BITS, BITS_TO_BASE, ENCODING_VERSION, VARIANT_HEADER_NT


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bytes_to_dna(data: bytes) -> str:
    """Map each byte to four bases using 00=A, 01=C, 10=G, 11=T."""
    parts: list[str] = []
    for byte in data:
        for shift in (6, 4, 2, 0):
            parts.append(BITS_TO_BASE[f"{(byte >> shift) & 0b11:02b}"])
    return "".join(parts)


def dna_to_bytes(sequence: str) -> bytes:
    """Inverse of bytes_to_dna. Trailing incomplete bases are ignored."""
    if not sequence:
        return b""
    usable = len(sequence) - (len(sequence) % 4)
    out = bytearray()
    for i in range(0, usable, 4):
        bits = "".join(BASE_TO_BITS[base] for base in sequence[i : i + 4])
        out.append(int(bits, 2))
    return bytes(out)


def keystream(variant: int, length: int) -> bytes:
    """Deterministic SHA-256 counter keystream bound to BYTE2DNA-POC-1."""
    if length <= 0:
        return b""
    out = bytearray()
    counter = 0
    prefix = ENCODING_VERSION.encode("ascii") + variant.to_bytes(4, "big")
    while len(out) < length:
        block = hashlib.sha256(prefix + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def xor_bytes(data: bytes, variant: int) -> bytes:
    stream = keystream(variant, len(data))
    return bytes(a ^ b for a, b in zip(data, stream))


def encode_variant_header(variant: int) -> str:
    """Encode 0..255 as 8 nt: even positions C/G, odd positions A/T.

    Guarantees GC = 50% and max homopolymer = 1 for the header itself.
    """
    if not 0 <= variant < 256:
        raise ValueError("variant must be in 0..255")
    bases: list[str] = []
    for i in range(VARIANT_HEADER_NT):
        bit = (variant >> (VARIANT_HEADER_NT - 1 - i)) & 1
        if i % 2 == 0:
            bases.append("C" if bit == 0 else "G")
        else:
            bases.append("A" if bit == 0 else "T")
    return "".join(bases)


def decode_variant_header(header: str) -> int:
    if len(header) < VARIANT_HEADER_NT:
        raise ValueError("variant header too short")
    value = 0
    for i, base in enumerate(header[:VARIANT_HEADER_NT]):
        if i % 2 == 0:
            if base not in ("C", "G"):
                raise ValueError("invalid variant header base")
            bit = 0 if base == "C" else 1
        else:
            if base not in ("A", "T"):
                raise ValueError("invalid variant header base")
            bit = 0 if base == "A" else 1
        value = (value << 1) | bit
    return value
