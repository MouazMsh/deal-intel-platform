"""Structured logging setup.

Uses the stdlib ``logging`` module with a JSON-ish formatter — no extra
dependency needed for Phase 1. Any log record whose message or extras
contain a key that looks secret-shaped is redacted defensively, on top of
the project rule that call sites must never pass secrets into ``extra=``.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any

_SECRET_KEY_PATTERN = re.compile(r"(token|secret|api_key|password|bot_token)", re.IGNORECASE)
_REDACTED = "***REDACTED***"


class _RedactingJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in (
                "args",
                "msg",
                "levelname",
                "levelno",
                "name",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "taskName",
            ):
                continue
            payload[key] = _REDACTED if _SECRET_KEY_PATTERN.search(key) else value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_RedactingJsonFormatter())
    root.addHandler(handler)
