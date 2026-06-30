"""
TCAI structured logging — unified logging via stdlib logging module.

Replaces all sys.stderr.write() and print() calls with proper loggers.
Provides dual output: console (stderr) for development + JSONL file for production.

Usage:
    from tcai.gateway.logging_setup import get_logger
    logger = get_logger(__name__)
    logger.info("Session started", extra={"session_id": sid})
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from . import paths

# China Standard Time (UTC+8)
TZ_CN = timezone(timedelta(hours=8))

# Module-level logger cache
_loggers: dict[str, logging.Logger] = {}

# Has setup been called?
_setup_done: bool = False


class JsonlFormatter(logging.Formatter):
    """Format log records as JSONL (one JSON object per line)."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(TZ_CN).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }

        # Include session_id if present in extra
        if hasattr(record, "session_id"):
            entry["session_id"] = record.session_id

        # Include the formatted message
        entry["message"] = record.getMessage()

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])

        # Include any extra fields
        for key in dir(record):
            if key not in {
                "message", "session_id", "args", "asctime", "created",
                "exc_info", "exc_text", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "msg", "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName",
            }:
                value = getattr(record, key, None)
                if value is not None and not key.startswith("_") and not callable(value):
                    entry[key] = value

        return json.dumps(entry, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable format for stderr output."""

    def __init__(self) -> None:
        super().__init__(
            fmt="[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(
    *,
    console_level: int = logging.WARNING,
    file_level: int = logging.DEBUG,
    jsonl_path: Path | None = None,
) -> None:
    """Initialize logging system.

    Must be called once at application startup.
    Subsequent calls are no-ops.

    Args:
        console_level: Minimum level for stderr output.
        file_level: Minimum level for JSONL file output.
        jsonl_path: Path to JSONL log file. Defaults to work/tcai.log.
    """
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # === Console handler (stderr) ===
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(console_level)
    console.setFormatter(ConsoleFormatter())
    root.addHandler(console)

    # === JSONL file handler ===
    if jsonl_path is None:
        jsonl_path = paths.WORK_DIR / "tcai.log"

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        jsonl_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(JsonlFormatter())
    root.addHandler(file_handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name.

    Returns a cached logger instance. Use __name__ as the argument.

    Args:
        name: Typically __name__ from the calling module.

    Returns:
        Configured logger instance.
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]


def log_security_event(
    logger: logging.Logger,
    level: int,
    message: str,
    *,
    session_id: str = "",
    tool: str = "",
    verdict: str = "",
    reason: str = "",
    **kwargs: Any,
) -> None:
    """Log a security-relevant event with structured context.

    Args:
        logger: Logger instance from get_logger().
        level: Logging level (e.g., logging.WARNING).
        message: Human-readable description.
        session_id: Session identifier.
        tool: Tool name that triggered the event.
        verdict: Security verdict (safe/risky/blocked).
        reason: Reason for the verdict.
        **kwargs: Additional fields to include in JSONL output.
    """
    extra: dict[str, Any] = {
        "session_id": session_id,
        "tool": tool,
        "verdict": verdict,
        "reason": reason,
        **kwargs,
    }
    logger.log(level, message, extra=extra)
