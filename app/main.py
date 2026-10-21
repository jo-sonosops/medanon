"""medanon: a small DICOM de-identification API for a DevOps lab."""

from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import deid
from app.metrics import ELEMENTS_CHANGED, FILES, LATENCY, REQUESTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("medanon")

APP_VERSION = os.getenv("APP_VERSION", "dev")
DEFAULT_SALT = "change-me"

Upload = Annotated[UploadFile, File()]


def max_bytes() -> int:
    return int(os.getenv("MEDANON_MAX_BYTES", str(20 * 1024 * 1024)))


def salt() -> str:
    return os.getenv("MEDANON_SALT", DEFAULT_SALT)


def chaos_error_rate() -> float:
    return float(os.getenv("MEDANON_CHAOS_ERROR_RATE", "0"))


def chaos_latency_ms() -> int:
    return int(os.getenv("MEDANON_CHAOS_LATENCY_MS", "0"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    if salt() == DEFAULT_SALT:
        log.warning("MEDANON_SALT is not set, using the default. Fine for local dev only.")
    log.info("medanon %s starting", APP_VERSION)
    yield


app = FastAPI(title="medanon", version=APP_VERSION, lifespan=lifespan)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        template = route.path if route is not None else "unmatched"
        REQUESTS.labels(request.method, template, str(status)).inc()
        LATENCY.labels(request.method, template).observe(time.perf_counter() - start)


async def read_upload(file: UploadFile) -> bytes:
    limit = max_bytes()
    data = await file.read(limit + 1)
    if len(data) > limit:
        FILES.labels("too_large").inc()
        raise HTTPException(status_code=413, detail=f"file larger than {limit} bytes")
    return data


async def apply_chaos() -> None:
    """Fault injection for monitoring drills. Off unless the env vars are set."""
    if chaos_latency_ms() > 0:
        await asyncio.sleep(chaos_latency_ms() / 1000)
    if random.random() < chaos_error_rate():
        FILES.labels("error").inc()
        raise HTTPException(status_code=500, detail="injected failure (chaos drill)")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict:
    return {"version": APP_VERSION}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/inspect")
async def inspect(file: Upload) -> dict:
    data = await read_upload(file)
    try:
        report = deid.inspect(data)
    except deid.NotDicomError as exc:
        FILES.labels("rejected").inc()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return report


@app.post("/v1/deidentify")
async def deidentify(file: Upload) -> Response:
    data = await read_upload(file)
    await apply_chaos()
    try:
        result = deid.deidentify(data, salt())
    except deid.NotDicomError as exc:
        FILES.labels("rejected").inc()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    FILES.labels("ok").inc()
    ELEMENTS_CHANGED.inc(len(result.changed))
    # Log counts only. Never log values or the upload filename: both can carry PHI.
    log.info(
        "deidentified file: %d elements changed, %d private tags removed",
        len(result.changed),
        result.private_tags_removed,
    )
    return Response(
        content=result.data,
        media_type="application/dicom",
        headers={
            "X-Medanon-Elements-Changed": str(len(result.changed)),
            "X-Medanon-Private-Tags-Removed": str(result.private_tags_removed),
        },
    )
