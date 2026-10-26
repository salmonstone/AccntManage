from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])

LOG_FILE = Path("logs/app.log")
MAX_LOG_LINES = 500


@router.get("/logs", response_class=PlainTextResponse)
async def get_logs(
    tail: int = Query(100, ge=1, le=MAX_LOG_LINES),
):
    if not LOG_FILE.exists():
        return "No log file found."
    lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-tail:])


@router.get("/system")
async def system_info():
    import psutil  # type: ignore[import-not-found]
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage(".").percent,
    }
