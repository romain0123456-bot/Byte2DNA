"""FastAPI application for the Byte2DNA POC."""

from __future__ import annotations

import json
import tempfile
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
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
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:3001",
        "http://localhost:3001",
        "http://127.0.0.1:3002",
        "http://localhost:3002",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

_CACHE: OrderedDict[str, tuple[EncodingResult, RoundtripResult]] = OrderedDict()
_LOCK = Lock()
EXPORT_CACHE_DIR = Path(tempfile.gettempdir()) / "byte2dna_exports"
EXPORT_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _store(result: EncodingResult, roundtrip: RoundtripResult) -> str:
    result_id = uuid4().hex
    with _LOCK:
        _CACHE[result_id] = (result, roundtrip)
        while len(_CACHE) > RESULT_CACHE_LIMIT:
            _CACHE.popitem(last=False)
    return result_id


def _persist_export_to_disk(result_id: str, result: EncodingResult, roundtrip: RoundtripResult) -> None:
    try:
        payload = build_xlsx(result, roundtrip)
        fname = export_filename(result.file.original_filename)
        file_path = EXPORT_CACHE_DIR / f"{result_id}.xlsx"
        meta_path = EXPORT_CACHE_DIR / f"{result_id}.json"
        file_path.write_bytes(payload)
        meta_path.write_text(
            json.dumps({
                "filename": fname,
                "original_filename": result.file.original_filename,
                "roundtrip": roundtrip.result,
            }),
            encoding="utf-8",
        )
    except Exception:
        pass


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
    background_tasks: BackgroundTasks,
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
    if export_allowed:
        background_tasks.add_task(_persist_export_to_disk, result_id, result, roundtrip)

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


def _build_export_response(result_id: str, is_head: bool = False) -> Response:
    file_path = EXPORT_CACHE_DIR / f"{result_id}.xlsx"
    meta_path = EXPORT_CACHE_DIR / f"{result_id}.json"

    payload: bytes | None = None
    filename: str | None = None

    if file_path.is_file():
        try:
            payload = file_path.read_bytes()
            if meta_path.is_file():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                filename = meta.get("filename")
        except Exception:
            payload = None

    if payload is None:
        result, roundtrip = _load(result_id)
        if roundtrip.result != "PASS":
            raise HTTPException(status_code=400, detail="Export disabled: round-trip failed")
        try:
            payload = build_xlsx(result, roundtrip)
        except Exception as exc:  # noqa: BLE001 — convert to a clean API error
            raise HTTPException(status_code=500, detail="Export failed") from exc
        filename = export_filename(result.file.original_filename)
        try:
            file_path.write_bytes(payload)
            meta_path.write_text(
                json.dumps({
                    "filename": filename,
                    "original_filename": result.file.original_filename,
                    "roundtrip": roundtrip.result,
                }),
                encoding="utf-8",
            )
        except Exception:
            pass

    if not filename:
        filename = f"byte2dna_export_{result_id[:8]}.xlsx"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
        "Content-Length": str(len(payload)),
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return Response(
        content=b"" if is_head else payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.api_route("/api/export", methods=["GET", "HEAD"])
def export_xlsx_get(request: Request, result_id: str) -> Response:
    return _build_export_response(result_id, is_head=(request.method == "HEAD"))


@app.post("/api/export")
def export_xlsx(body: ExportRequest) -> Response:
    return _build_export_response(body.result_id)
