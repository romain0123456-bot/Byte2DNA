"""Sprint 2: deterministic byte-preservation tests (current codec API only)."""

from __future__ import annotations

import hashlib
import random

import pytest

from app.models import EncodeConfig
from app.services.codec import decode, encode
from app.services.dna import sha256_hex


def _roundtrip(data: bytes, config: EncodeConfig | None = None) -> bytes:
    result = encode(data, config or EncodeConfig(), filename="payload.bin")
    sequences = [f.sequence for f in result.fragments]
    random.Random(1).shuffle(sequences)
    out = decode(sequences, result.decode_metadata)
    assert result.file.sha256_original == hashlib.sha256(data).hexdigest()
    return out


def test_empty_payload_rejected_by_contract() -> None:
    with pytest.raises(ValueError, match="Empty file"):
        encode(b"", EncodeConfig(), filename="empty.bin")


@pytest.mark.parametrize("byte", [0x00, 0xFF])
@pytest.mark.parametrize("length", [1, 17, 1000])
def test_extreme_single_byte_values(byte: int, length: int) -> None:
    data = bytes([byte]) * length
    out = _roundtrip(data)
    assert out == data
    assert sha256_hex(out) == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("compression", [False, True])
@pytest.mark.parametrize("ecc", [False, True])
def test_all_256_byte_values(compression: bool, ecc: bool) -> None:
    data = bytes(range(256)) + bytes(reversed(range(256)))
    out = _roundtrip(data, EncodeConfig(compression=compression, ecc=ecc))
    assert out == data
    assert hashlib.sha256(out).digest() == hashlib.sha256(data).digest()


def test_alternating_extreme_bytes() -> None:
    data = b"\x00\xff" * 500 + b"\xff\x00" * 500
    assert _roundtrip(data) == data


@pytest.mark.parametrize("compression", [False, True])
def test_repetitive_data(compression: bool) -> None:
    data = b"ACGT" * 2000 + b"\x00" * 3000 + b"abc" * 777
    assert _roundtrip(data, EncodeConfig(compression=compression)) == data


def test_seeded_random_binary_sha256_identical() -> None:
    data = random.Random(20240601).randbytes(5000)
    out = _roundtrip(data)
    assert out == data
    assert sha256_hex(out) == sha256_hex(data)
