"""Decode BYTE2DNA-POC-1 fragments back to original bytes."""

from __future__ import annotations

import struct
import zlib

from app.constants import ENCODING_VERSION, INDEX_BYTES, INNER_MAGIC, VARIANT_HEADER_NT
from app.models import DecodeMetadata, Fragment
from app.services.dna import decode_variant_header, dna_to_bytes, xor_bytes
from app.services.ecc import decode_ecc
from app.services.fragmenter import payload_capacity


class DecodingError(ValueError):
    """Raised when DNA fragments cannot be reconstructed into bytes."""


def _as_sequences(fragments: list[str] | list[Fragment]) -> list[str]:
    sequences: list[str] = []
    for item in fragments:
        if isinstance(item, str):
            sequences.append(item)
        else:
            sequences.append(item.sequence)
    return sequences


def _parse_fragment(sequence: str, metadata: DecodeMetadata) -> tuple[int, bytes]:
    if len(sequence) != metadata.fragment_length:
        raise DecodingError("Decoding failed")
    try:
        variant = decode_variant_header(sequence[: metadata.variant_header_nt])
    except ValueError as exc:
        raise DecodingError("Decoding failed") from exc

    body_bytes_len = INDEX_BYTES + metadata.payload_capacity + (
        metadata.ecc_nsym if metadata.ecc else 0
    )
    body_nt = body_bytes_len * 4
    start = metadata.variant_header_nt
    body_dna = sequence[start : start + body_nt]
    scrambled = dna_to_bytes(body_dna)
    if len(scrambled) != body_bytes_len:
        raise DecodingError("Decoding failed")
    record = xor_bytes(scrambled, variant)
    try:
        plain = decode_ecc(record, metadata.ecc)
    except ValueError as exc:
        raise DecodingError("Decoding failed") from exc
    if len(plain) < INDEX_BYTES + metadata.payload_capacity:
        raise DecodingError("Decoding failed")
    index = int.from_bytes(plain[:INDEX_BYTES], "big")
    chunk = plain[INDEX_BYTES : INDEX_BYTES + metadata.payload_capacity]
    return index, chunk


def _parse_inner_payload(packed: bytes, expected_compression: bool) -> bytes:
    header_size = 4 + 1 + 4 + 4
    if len(packed) < header_size or packed[:4] != INNER_MAGIC:
        raise DecodingError("Decoding failed")
    flags, original_size, data_size = struct.unpack(">BII", packed[4:13])
    compressed = bool(flags & 1)
    if compressed != expected_compression:
        raise DecodingError("Decoding failed")
    data = packed[13 : 13 + data_size]
    if len(data) != data_size:
        raise DecodingError("Decoding failed")
    payload = zlib.decompress(data) if compressed else data
    if original_size != len(payload):
        raise DecodingError("Decoding failed")
    return payload


def decode(fragments: list[str] | list[Fragment], metadata: DecodeMetadata) -> bytes:
    """Reconstruct original bytes from DNA sequences and decode metadata only."""
    if metadata.encoding_version != ENCODING_VERSION:
        raise DecodingError("Decoding failed")
    if metadata.payload_capacity != payload_capacity(metadata.fragment_length, metadata.ecc):
        raise DecodingError("Decoding failed")
    if metadata.variant_header_nt != VARIANT_HEADER_NT:
        raise DecodingError("Decoding failed")

    sequences = _as_sequences(fragments)
    if not sequences:
        raise DecodingError("Decoding failed")

    by_index: dict[int, bytes] = {}
    for sequence in sequences:
        index, chunk = _parse_fragment(sequence, metadata)
        if index in by_index and by_index[index] != chunk:
            raise DecodingError("Decoding failed")
        by_index[index] = chunk

    expected = list(range(max(by_index) + 1))
    if sorted(by_index) != expected:
        raise DecodingError("Decoding failed")

    packed = b"".join(by_index[i] for i in expected)
    return _parse_inner_payload(packed, metadata.compression)
