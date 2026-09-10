from __future__ import annotations

from app.services.dna import (
    bytes_to_dna,
    decode_variant_header,
    dna_to_bytes,
    encode_variant_header,
    xor_bytes,
)


def test_bytes_dna_roundtrip() -> None:
    original = bytes(range(256)) + b"\x00\xffhello"
    assert dna_to_bytes(bytes_to_dna(original)) == original


def test_mapping_two_bits() -> None:
    # 00 A, 01 C, 10 G, 11 T  — byte 0b00011011 = 0x1B → ACGT
    assert bytes_to_dna(bytes([0b00011011])) == "ACGT"
    assert dna_to_bytes("ACGT") == bytes([0b00011011])


def test_variant_header_balanced_and_reversible() -> None:
    for variant in range(256):
        header = encode_variant_header(variant)
        assert len(header) == 8
        assert decode_variant_header(header) == variant
        gc = header.count("G") + header.count("C")
        assert gc == 4


def test_xor_is_involutive() -> None:
    data = b"payload-bytes-123"
    assert xor_bytes(xor_bytes(data, 42), 42) == data
