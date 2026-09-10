"""Critical round-trip tests: original bytes must be reconstructed from DNA only."""

from __future__ import annotations

import hashlib
import json
import random

import pytest

from app.models import DecodeMetadata, EncodeConfig, EncodingResult
from app.services.codec import decode, encode
from app.services.decoder import DecodingError
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


def test_decode_metadata_strictness() -> None:
    original = b"strict-metadata-test-payload-12345"
    result = encode(original, EncodeConfig(ecc=True, compression=True), filename="test.bin")
    sequences = [f.sequence for f in result.fragments]
    valid_meta = result.decode_metadata

    # valid metadata -> PASS
    assert decode(sequences, valid_meta) == original

    # bad encoding_version -> FAIL
    bad_version = valid_meta.model_copy(update={"encoding_version": "INVALID-VERSION"})
    with pytest.raises(DecodingError, match="Decoding failed"):
        decode(sequences, bad_version)

    # bad variant_header_nt -> FAIL
    bad_vh = valid_meta.model_copy(update={"variant_header_nt": 12})
    with pytest.raises(DecodingError, match="Decoding failed"):
        decode(sequences, bad_vh)

    # bad index_bytes -> FAIL
    bad_idx = valid_meta.model_copy(update={"index_bytes": 2})
    with pytest.raises(DecodingError, match="Decoding failed"):
        decode(sequences, bad_idx)

    # bad ecc_nsym when ecc=True -> FAIL
    bad_ecc_sym = valid_meta.model_copy(update={"ecc_nsym": 4})
    with pytest.raises(DecodingError, match="Decoding failed"):
        decode(sequences, bad_ecc_sym)

    # ecc=False with valid ecc_nsym=0 -> PASS
    result_no_ecc = encode(original, EncodeConfig(ecc=False, compression=True), filename="test.bin")
    seqs_no_ecc = [f.sequence for f in result_no_ecc.fragments]
    meta_no_ecc = result_no_ecc.decode_metadata
    assert decode(seqs_no_ecc, meta_no_ecc) == original

    # ecc=False with bad ecc_nsym != 0 -> FAIL
    bad_no_ecc_sym = meta_no_ecc.model_copy(update={"ecc_nsym": 8})
    with pytest.raises(DecodingError, match="Decoding failed"):
        decode(seqs_no_ecc, bad_no_ecc_sym)


def test_decode_invalid_dna_sequence_rejected() -> None:
    original = b"dna-sequence-strictness-test"
    result = encode(original, EncodeConfig(), filename="dna.bin")
    seqs = [f.sequence for f in result.fragments]

    # Non-ACGT base in fragment
    bad_seqs_char = list(seqs)
    bad_seqs_char[0] = "X" + bad_seqs_char[0][1:]
    with pytest.raises(DecodingError, match="Decoding failed"):
        decode(bad_seqs_char, result.decode_metadata)

    # Bad base 'N'
    bad_seqs_n = list(seqs)
    bad_seqs_n[0] = bad_seqs_n[0][:-1] + "N"
    with pytest.raises(DecodingError, match="Decoding failed"):
        decode(bad_seqs_n, result.decode_metadata)

    # Truncated sequence (length not matching fragment_length)
    bad_seqs_len = list(seqs)
    bad_seqs_len[0] = bad_seqs_len[0][:-2]
    with pytest.raises(DecodingError, match="Decoding failed"):
        decode(bad_seqs_len, result.decode_metadata)


@pytest.mark.parametrize("size", [1, 17, 101, 513])
@pytest.mark.parametrize("compression", [True, False])
@pytest.mark.parametrize("ecc", [True, False])
@pytest.mark.parametrize("fragment_length", [100, 150, 200])
def test_last_fragment_padding_and_roundtrip(
    size: int,
    compression: bool,
    ecc: bool,
    fragment_length: int,
) -> None:
    original = bytes((i * 47 + 11) % 256 for i in range(size))
    config = EncodeConfig(
        compression=compression,
        ecc=ecc,
        fragment_length=fragment_length,
    )
    result = encode(original, config, filename="padding_test.bin")
    sequences = [f.sequence for f in result.fragments]
    reconstructed = decode(sequences, result.decode_metadata)
    assert reconstructed == original
    assert sha256_hex(reconstructed) == sha256_hex(original)
