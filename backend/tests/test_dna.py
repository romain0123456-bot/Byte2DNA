import pytest

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


def test_dna_to_bytes_strict_length_and_bases() -> None:
    # ACGT -> PASS
    assert dna_to_bytes("ACGT") == bytes([0b00011011])

    # ACG -> FAIL (len % 4 != 0)
    with pytest.raises(ValueError, match="multiple of 4"):
        dna_to_bytes("ACG")

    # ACGX -> FAIL (invalid base X, not KeyError)
    with pytest.raises(ValueError, match="Invalid DNA base"):
        try:
            dna_to_bytes("ACGX")
        except KeyError:
            pytest.fail("KeyError should not leak from dna_to_bytes")

    # NNNN -> FAIL (invalid base N, not KeyError)
    with pytest.raises(ValueError, match="Invalid DNA base"):
        try:
            dna_to_bytes("NNNN")
        except KeyError:
            pytest.fail("KeyError should not leak from dna_to_bytes")


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
