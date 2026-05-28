"""Structured JSON logging configuration for RMIAS.

Call configure_logging() once at application startup (in lifespan).
Every log record is emitted as a single JSON line with ts, level, logger, msg.
"""

from __future__ import annotations

import json
import logging
import time


class _JsonFormatter(logging.Formatter):
    """Format each log record as a compact JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        obj: dict[str, object] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "service": "rmias",
            "msg": record.getMessage(),
        }
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Replace root logger handlers with a single JSON stream handler."""
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Quieten chatty third-party loggers that add noise in production
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
