"""Pydantic models shared by the codec and the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.constants import (
    ALLOWED_FRAGMENT_LENGTHS,
    DEFAULT_COMPRESSION,
    DEFAULT_ECC,
    DEFAULT_FRAGMENT_LENGTH,
    DEFAULT_GC_MAX,
    DEFAULT_GC_MIN,
    DEFAULT_HOMOPOLYMER_MAX,
    DEFAULT_INCLUDE_SHA256_EXPORT,
    ECC_NSYM,
    ENCODING_VERSION,
)


FragmentStatus = Literal["VALID", "WARNING", "INVALID"]
RoundtripStatus = Literal["PASS", "FAIL"]


class EncodeConfig(BaseModel):
    compression: bool = DEFAULT_COMPRESSION
    include_sha256_export: bool = DEFAULT_INCLUDE_SHA256_EXPORT
    ecc: bool = DEFAULT_ECC
    fragment_length: int = DEFAULT_FRAGMENT_LENGTH
    gc_min: float = DEFAULT_GC_MIN
    gc_max: float = DEFAULT_GC_MAX
    homopolymer_max: int = DEFAULT_HOMOPOLYMER_MAX

    @field_validator("fragment_length")
    @classmethod
    def validate_fragment_length(cls, value: int) -> int:
        if value not in ALLOWED_FRAGMENT_LENGTHS:
            raise ValueError(
                f"fragment_length must be one of {ALLOWED_FRAGMENT_LENGTHS}"
            )
        return value

    @field_validator("homopolymer_max")
    @classmethod
    def validate_homopolymer(cls, value: int) -> int:
        if value < 1 or value > 10:
            raise ValueError("homopolymer_max must be between 1 and 10")
        return value

    @field_validator("gc_max")
    @classmethod
    def validate_gc_range(cls, value: float, info) -> float:  # type: ignore[no-untyped-def]
        gc_min = info.data.get("gc_min", DEFAULT_GC_MIN)
        if not 0 <= gc_min <= 100 or not 0 <= value <= 100:
            raise ValueError("GC bounds must be between 0 and 100")
        if value < gc_min:
            raise ValueError("gc_max must be greater than or equal to gc_min")
        return value


class Fragment(BaseModel):
    fragment_id: str
    index: int
    sequence: str
    length_nt: int
    gc_percent: float
    max_homopolymer: int
    encoding_variant: int
    ecc: bool
    status: FragmentStatus


class DecodeMetadata(BaseModel):
    """Minimum information required to reconstruct bytes from DNA fragments."""

    encoding_version: str = ENCODING_VERSION
    compression: bool
    ecc: bool
    ecc_nsym: int = ECC_NSYM
    fragment_length: int
    payload_capacity: int
    variant_header_nt: int
    index_bytes: int
    base_mapping: dict[str, str]


class FileInfo(BaseModel):
    original_filename: str
    original_extension: str
    original_size: int
    sha256_original: str


class EncodingStats(BaseModel):
    fragment_count: int
    total_nucleotides: int
    gc_average: float
    gc_min_observed: float
    gc_max_observed: float
    max_homopolymer_observed: int
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression: bool
    fragments_valid: int
    fragments_warning: int
    fragments_invalid: int
    payload_capacity: int


class RoundtripResult(BaseModel):
    result: RoundtripStatus
    sha256_original: str
    sha256_reconstructed: str | None = None
    reconstructed_size: int | None = None
    message: str
    bit_identical: bool = False


class EncodingResult(BaseModel):
    encoding_version: str = ENCODING_VERSION
    config: EncodeConfig
    file: FileInfo
    stats: EncodingStats
    fragments: list[Fragment]
    decode_metadata: DecodeMetadata
    # Intentionally no original_bytes field.


class ApiEncodeResponse(BaseModel):
    encoding_version: str
    result_id: str
    file: FileInfo
    stats: EncodingStats
    roundtrip: RoundtripResult
    fragments_preview: list[Fragment]
    fragment_count: int
    synthesis_review_required: bool
    export_allowed: bool
    export_warning: str | None = None
    qc_message: str
    profile: str = "Generic POC"


class ExportRequest(BaseModel):
    result_id: str = Field(min_length=8)


class ErrorBody(BaseModel):
    error: str
    detail: str
