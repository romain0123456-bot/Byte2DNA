"""Encode raw bytes into indexed DNA fragments (BYTE2DNA-POC-1)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from app.constants import (
    BASE_TO_BITS,
    ECC_NSYM,
    ENCODING_VERSION,
    INDEX_BYTES,
    INNER_MAGIC,
    MAX_VARIANTS,
    VARIANT_HEADER_NT,
)
from app.models import (
    DecodeMetadata,
    EncodeConfig,
    EncodingResult,
    EncodingStats,
    FileInfo,
    Fragment,
)
from app.services.constraints import classify_status, constraint_score, gc_percent, max_homopolymer
from app.services.dna import bytes_to_dna, encode_variant_header, sha256_hex, xor_bytes
from app.services.ecc import encode_ecc
from app.services.fragmenter import payload_capacity, split_payload


def _fragment_id(index: int) -> str:
    return f"DNA{index + 1:06d}"


def _inner_payload(data: bytes, compression: bool) -> tuple[bytes, int]:
    payload_data = zlib.compress(data) if compression else data
    header = INNER_MAGIC + struct.pack(">BII", 1 if compression else 0, len(data), len(payload_data))
    return header + payload_data, len(payload_data)


def _build_body_bytes(index: int, chunk: bytes, ecc: bool) -> bytes:
    record = index.to_bytes(INDEX_BYTES, "big") + chunk
    return encode_ecc(record, ecc)


def _pad_sequence(sequence: str, target: int, variant: int) -> str:
    if len(sequence) > target:
        raise ValueError("Encoding failed")
    filler_bases = "ACGT"
    while len(sequence) < target:
        sequence += filler_bases[(len(sequence) + variant) % 4]
    return sequence


def _build_sequence(index: int, chunk: bytes, variant: int, config: EncodeConfig) -> str:
    header = encode_variant_header(variant)
    body = xor_bytes(_build_body_bytes(index, chunk, config.ecc), variant)
    return _pad_sequence(header + bytes_to_dna(body), config.fragment_length, variant)


def _select_variant(index: int, chunk: bytes, config: EncodeConfig) -> tuple[str, int, str]:
    best: tuple[tuple[int, float], str, int, str] | None = None
    for variant in range(MAX_VARIANTS):
        sequence = _build_sequence(index, chunk, variant, config)
        gc = gc_percent(sequence)
        hp = max_homopolymer(sequence)
        status = classify_status(gc, hp, config)
        score = constraint_score(gc, hp, config)
        candidate = (score, sequence, variant, status)
        if best is None or candidate[0] < best[0]:
            best = candidate
        if status == "VALID":
            return sequence, variant, status
    assert best is not None
    return best[1], best[2], best[3]


def encode(data: bytes, config: EncodeConfig, filename: str = "payload.bin") -> EncodingResult:
    """Convert original bytes into DNA fragments. Does not keep a copy of `data`."""
    if not data:
        raise ValueError("Empty file")

    path = Path(filename)
    extension = path.suffix.lower()
    original_size = len(data)
    sha256_original = sha256_hex(data)

    packed, compressed_size = _inner_payload(data, config.compression)
    capacity = payload_capacity(config.fragment_length, config.ecc)
    chunks = split_payload(packed, capacity)

    fragments: list[Fragment] = []
    for index, chunk in enumerate(chunks):
        sequence, variant, status = _select_variant(index, chunk, config)
        fragments.append(
            Fragment(
                fragment_id=_fragment_id(index),
                index=index,
                sequence=sequence,
                length_nt=len(sequence),
                gc_percent=gc_percent(sequence),
                max_homopolymer=max_homopolymer(sequence),
                encoding_variant=variant,
                ecc=config.ecc,
                status=status,  # type: ignore[arg-type]
            )
        )

    gc_values = [f.gc_percent for f in fragments]
    ratio = (compressed_size / original_size) if original_size else 1.0
    stats = EncodingStats(
        fragment_count=len(fragments),
        total_nucleotides=sum(f.length_nt for f in fragments),
        gc_average=round(sum(gc_values) / len(gc_values), 4),
        gc_min_observed=round(min(gc_values), 4),
        gc_max_observed=round(max(gc_values), 4),
        max_homopolymer_observed=max(f.max_homopolymer for f in fragments),
        original_size=original_size,
        compressed_size=compressed_size,
        compression_ratio=round(ratio, 4),
        compression=config.compression,
        fragments_valid=sum(1 for f in fragments if f.status == "VALID"),
        fragments_warning=sum(1 for f in fragments if f.status == "WARNING"),
        fragments_invalid=sum(1 for f in fragments if f.status == "INVALID"),
        payload_capacity=capacity,
    )

    decode_metadata = DecodeMetadata(
        encoding_version=ENCODING_VERSION,
        compression=config.compression,
        ecc=config.ecc,
        ecc_nsym=ECC_NSYM if config.ecc else 0,
        fragment_length=config.fragment_length,
        payload_capacity=capacity,
        variant_header_nt=VARIANT_HEADER_NT,
        index_bytes=INDEX_BYTES,
        base_mapping=dict(BASE_TO_BITS),
    )

    return EncodingResult(
        encoding_version=ENCODING_VERSION,
        config=config,
        file=FileInfo(
            original_filename=path.name,
            original_extension=extension.lstrip("."),
            original_size=original_size,
            sha256_original=sha256_original,
        ),
        stats=stats,
        fragments=fragments,
        decode_metadata=decode_metadata,
    )
