"""FastAPI application for the Byte2DNA POC."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from app.constants import (
    APPLICATION_NAME,
    ENCODING_VERSION,
    MAX_FILE_SIZE_BYTES,
    PROFILE_NAME,
    RESULT_CACHE_LIMIT,
)
from app.models import ApiEncodeResponse, EncodeConfig, EncodingResult, ExportRequest, RoundtripResult
from app.services.encoder import encode
from app.services.exporter import build_xlsx, export_filename
from app.services.files import UploadError, validate_upload
from app.services.validator import validate_roundtrip

app = FastAPI(title=APPLICATION_NAME, version=ENCODING_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_CACHE: OrderedDict[str, tuple[EncodingResult, RoundtripResult]] = OrderedDict()
_LOCK = Lock()


def _store(result: EncodingResult, roundtrip: RoundtripResult) -> str:
    result_id = uuid4().hex
    with _LOCK:
        _CACHE[result_id] = (result, roundtrip)
        while len(_CACHE) > RESULT_CACHE_LIMIT:
            _CACHE.popitem(last=False)
    return result_id


def _load(result_id: str) -> tuple[EncodingResult, RoundtripResult]:
    with _LOCK:
        stored = _CACHE.get(result_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Export failed")
    return stored


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "on", "yes"}


@app.exception_handler(UploadError)
async def upload_error_handler(_, exc: UploadError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": exc.code, "detail": exc.detail})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/encode", response_model=ApiEncodeResponse)
async def encode_file(
    file: UploadFile = File(...),
    compression: str = Form("true"),
    include_sha256_export: str = Form("true"),
    ecc: str = Form("true"),
    fragment_length: int = Form(150),
    gc_min: float = Form(40),
    gc_max: float = Form(60),
    homopolymer_max: int = Form(3),
) -> ApiEncodeResponse:
    raw = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(raw) > MAX_FILE_SIZE_BYTES:
        raise UploadError("File too large", "File too large")
    filename = validate_upload(file.filename or "upload.bin", raw, file.content_type)

    try:
        config = EncodeConfig(
            compression=_parse_bool(compression),
            include_sha256_export=_parse_bool(include_sha256_export),
            ecc=_parse_bool(ecc),
            fragment_length=fragment_length,
            gc_min=gc_min,
            gc_max=gc_max,
            homopolymer_max=homopolymer_max,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="Encoding failed") from exc

    try:
        result = encode(raw, config, filename=filename)
        roundtrip = validate_roundtrip(raw, result.fragments, result.decode_metadata)
    except ValueError as exc:
        message = str(exc) if str(exc) in {"Encoding failed", "Empty file"} else "Encoding failed"
        raise HTTPException(status_code=400, detail=message) from exc
    finally:
        raw = b""

    result_id = _store(result, roundtrip)
    review = result.stats.fragments_warning > 0 or result.stats.fragments_invalid > 0
    export_allowed = roundtrip.result == "PASS"
    export_warning = None
    if export_allowed and review:
        export_warning = "Séquences nécessitant une revue avant synthèse"
    if not export_allowed:
        export_warning = "EXPORT DISABLED"

    return ApiEncodeResponse(
        encoding_version=ENCODING_VERSION,
        result_id=result_id,
        file=result.file,
        stats=result.stats,
        roundtrip=roundtrip,
        fragments_preview=result.fragments[:40],
        fragment_count=result.stats.fragment_count,
        synthesis_review_required=review,
        export_allowed=export_allowed,
        export_warning=export_warning,
        qc_message=(
            "ENCODING VALID"
            if result.stats.fragments_invalid == 0
            else "ENCODING COMPLETE — SOME FRAGMENTS INVALID"
        )
        + (
            " / SYNTHESIS CONSTRAINTS PASS"
            if not review
            else " / SYNTHESIS CONSTRAINTS NEED REVIEW"
        ),
        profile=PROFILE_NAME,
    )


@app.post("/api/export")
def export_xlsx(body: ExportRequest) -> Response:
    result, roundtrip = _load(body.result_id)
    if roundtrip.result != "PASS":
        raise HTTPException(status_code=400, detail="Export disabled: round-trip failed")
    try:
        payload = build_xlsx(result, roundtrip)
    except Exception as exc:  # noqa: BLE001 — convert to a clean API error
        raise HTTPException(status_code=500, detail="Export failed") from exc
    filename = export_filename(result.file.original_filename)
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
