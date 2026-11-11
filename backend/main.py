"""Career Stat Card API."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

import analyzer  # noqa: E402
from analyzer import MAX_JOB_CHARS, AnalysisError, analyze_resume  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("career_stat_card.api")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "8"))
RATE_LIMIT_WINDOW_S = int(os.getenv("RATE_LIMIT_WINDOW_S", "600"))

DEFAULT_ORIGINS = "https://unnamed-catalyst.github.io,http://localhost:5173,http://localhost:4173"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()]

app = FastAPI(title="Career Stat Card API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class RateLimiter:
    """Sliding-window limit per client IP (in memory; fine for one instance)."""

    def __init__(self, limit: int, window_s: int):
        self.limit, self.window_s = limit, window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int:
        """0 if the request is allowed (and records it), else seconds to wait."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_s:
                hits.popleft()
            if len(hits) >= self.limit:
                return int(self.window_s - (now - hits[0])) + 1
            hits.append(now)
            return 0


limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_S)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _error(status: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message, "code": code}, headers=headers)


def _probe_loop() -> None:
    """Find a usable (free) model at startup, then re-check hourly."""
    while True:
        try:
            analyzer.probe_models()
        except Exception:
            log.exception("Model probe failed")
        time.sleep(analyzer.PROBE_INTERVAL_S)


@app.on_event("startup")
def _start_probe() -> None:
    # The page pings /health on load, which wakes a sleeping server; the probe
    # then usually finds a working model before the user clicks Generate.
    if os.getenv("DISABLE_MODEL_PROBE") != "1":
        threading.Thread(target=_probe_loop, name="model-probe", daemon=True).start()


@app.get("/health")
def health():
    """Cheap endpoint the frontend calls on page load to wake the server."""
    return {"status": "ok", "model": analyzer.current_model()}


@app.post("/analyze")
def analyze(request: Request, file: UploadFile = File(...), job_description: str = Form("")):
    started = time.perf_counter()

    is_pdf = (file.content_type or "").lower() in ("application/pdf", "application/x-pdf") or (
        file.filename or ""
    ).lower().endswith(".pdf")
    if not is_pdf:
        return _error(400, "not_pdf", "Please upload your resume as a PDF file.")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return _error(413, "too_large", "That PDF is over 5 MB. Please upload a smaller file.")
    if not data.startswith(b"%PDF"):
        return _error(400, "not_pdf", "That file does not look like a PDF.")
    if len(job_description) > MAX_JOB_CHARS:
        job_description = job_description[:MAX_JOB_CHARS]

    wait = limiter.retry_after(_client_ip(request))
    if wait:
        return _error(
            429,
            "rate_limited",
            f"You've made a lot of cards in a short time. Please try again in {max(1, wait // 60)} min.",
            {"Retry-After": str(wait)},
        )

    try:
        card = analyze_resume(data, job_description)
    except AnalysisError as exc:
        log.warning("analyze failed code=%s ms=%d", exc.code, (time.perf_counter() - started) * 1000)
        return _error(exc.status, exc.code, exc.message)
    except Exception:
        log.exception("Unexpected error")
        return _error(500, "internal", "Something went wrong on our side. Please try again.")

    log.info(
        "analyze ok model=%s attempts=%d ms=%d overall=%d",
        card.meta.model,
        card.meta.attempts,
        card.meta.latency_ms,
        card.overall,
    )
    return card.model_dump()
