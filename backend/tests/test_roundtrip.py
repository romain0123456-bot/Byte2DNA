"""Critical round-trip tests: original bytes must be reconstructed from DNA only."""

from __future__ import annotations

import hashlib
import json
import random

import pytest

from app.models import DecodeMetadata, EncodeConfig, EncodingResult
from app.services.codec import decode, encode
from app.services.dna import sha256_hex


def _assert_no_original_payload(result: EncodingResult, original: bytes) -> None:
    dumped = result.model_dump()
    assert "original_bytes" not in dumped
    assert original not in [result.file.sha256_original.encode(), b""]


def _decode_from_serialized(result: EncodingResult) -> bytes:
    """Simulate a decoder that only sees DNA strings + JSON metadata."""
    sequences = [fragment.sequence for fragment in result.fragments]
    random.Random(7).shuffle(sequences)
    metadata = DecodeMetadata.model_validate(
        json.loads(result.decode_metadata.model_dump_json())
    )
    return decode(sequences, metadata)


@pytest.mark.parametrize("length", [1, 2, 3, 7, 8, 15, 16, 31, 64, 100, 255, 1024, 4096])
def test_padding_roundtrip(length: int) -> None:
    original = bytes((i * 17 + 3) % 256 for i in range(length))
    result = encode(original, EncodeConfig(), filename="pad.bin")
    reconstructed = _decode_from_serialized(result)
    assert reconstructed == original
    assert sha256_hex(reconstructed) == sha256_hex(original)


@pytest.mark.parametrize("compression", [True, False])
def test_compression_roundtrip(compression: bool) -> None:
    original = (b"PDF-like-repeat-" * 80) + bytes(range(128))
    result = encode(
        original,
        EncodeConfig(compression=compression),
        filename="comp.bin",
    )
    reconstructed = _decode_from_serialized(result)
    assert reconstructed == original
    assert result.stats.compression is compression
    if compression:
        assert result.stats.compressed_size <= result.stats.original_size


@pytest.mark.parametrize("fragment_length", [100, 150, 200])
def test_fragment_lengths(fragment_length: int) -> None:
    original = bytes(range(256)) * 4
    result = encode(
        original,
        EncodeConfig(fragment_length=fragment_length, ecc=True),
        filename="frag.bin",
    )
    assert all(len(f.sequence) == fragment_length for f in result.fragments)
    assert _decode_from_serialized(result) == original


@pytest.mark.parametrize("ecc", [True, False])
def test_ecc_roundtrip(ecc: bool) -> None:
    original = b"ecc-payload-" + bytes(range(200))
    result = encode(original, EncodeConfig(ecc=ecc), filename="ecc.bin")
    assert all(fragment.ecc is ecc for fragment in result.fragments)
    assert _decode_from_serialized(result) == original


def test_shuffle_index_reconstruction() -> None:
    original = b"index-order-must-not-matter" + bytes(range(50))
    result = encode(original, EncodeConfig(fragment_length=100), filename="idx.bin")
    ids = [f.fragment_id for f in result.fragments]
    assert ids == [f"DNA{i:06d}" for i in range(1, len(ids) + 1)]
    sequences = [f.sequence for f in result.fragments]
    random.shuffle(sequences)
    assert decode(sequences, result.decode_metadata) == original


def test_anti_fake_roundtrip_discards_original() -> None:
    original = hashlib.sha256(b"seed-for-unique-bytes").digest() * 20 + b"tail"
    original_hash = sha256_hex(original)
    result = encode(original, EncodeConfig(), filename="anti.bin")
    _assert_no_original_payload(result, original)

    sequences_only = [fragment.sequence for fragment in result.fragments]
    metadata_only = result.decode_metadata.model_copy(deep=True)
    del original
    del result

    reconstructed = decode(sequences_only, metadata_only)
    assert reconstructed == hashlib.sha256(b"seed-for-unique-bytes").digest() * 20 + b"tail"
    assert sha256_hex(reconstructed) == original_hash


def test_sha256_matches() -> None:
    original = b"\x00\x01\x02" + bytes(range(90))
    result = encode(original, EncodeConfig(), filename="hash.bin")
    reconstructed = decode([f.sequence for f in result.fragments], result.decode_metadata)
    assert sha256_hex(original) == result.file.sha256_original
    assert sha256_hex(original) == sha256_hex(reconstructed)
