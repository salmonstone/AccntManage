from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

from backend.app.core.config import settings

_REDACT_PATTERN = re.compile(
    r"(password|secret|token|auth|key|credential|refresh_token|access_token)"
    r"\s*[=:]\s*\S+",
    re.IGNORECASE,
)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        return _REDACT_PATTERN.sub(r"\1=***REDACTED***", msg)


def setup_logging() -> None:
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = RedactingFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(correlation_id)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        defaults={"correlation_id": "-"},
    )

    file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    root.addHandler(file_handler)
    root.addHandler(console_handler)
