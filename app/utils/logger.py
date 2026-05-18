"""
Structured logging configuration for the Voice Agent system.
Uses Python's built-in logging with JSON-formatted output for production.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "call_id"):
            log_data["call_id"] = record.call_id
        if hasattr(record, "state"):
            log_data["state"] = record.state
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms

        if record.exc_info and record.exc_info[1]:
            log_data["exception"] = str(record.exc_info[1])

        return json.dumps(log_data)


class CallLogger:
    """
    Logger with call context.
    Usage:
        logger = CallLogger(call_id="abc-123")
        logger.info("Processing user input", state="COLLECTING")
    """

    def __init__(self, call_id: str = "system"):
        self._logger = logging.getLogger(f"voice_agent.{call_id}")
        self.call_id = call_id

    def _log(self, level: int, message: str, **kwargs):
        extra = {"call_id": self.call_id}
        extra.update(kwargs)
        self._logger.log(level, message, extra=extra)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)


def setup_logging(log_level: str = "INFO", json_format: bool = False):
    """Initialize logging for the application."""
    root_logger = logging.getLogger("voice_agent")
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(handler)
    return root_logger
