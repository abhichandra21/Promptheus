"""
Central logging configuration for Promptheus.

Provides structured logging setup with support for JSON formatting and
environment-driven configuration.
"""

from __future__ import annotations

import json
import logging
import os
from logging import Handler
from typing import Optional

from promptheus.constants import PROMPTHEUS_DEBUG_ENV


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = record.stack_info
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(default_level: int = logging.WARNING) -> None:
    """
    Configure root logging based on environment flags.

    By default, logging is suppressed for end users (only WARNING and above).
    Logs only go to console if PROMPTHEUS_DEBUG is enabled or a log file is specified.

    Environment variables:
      - PROMPTHEUS_DEBUG: enable DEBUG level logging to console
      - PROMPTHEUS_LOG_LEVEL: override log level (INFO, WARNING, etc.)
      - PROMPTHEUS_LOG_FORMAT: "json" for JSON, otherwise format string
      - PROMPTHEUS_LOG_FILE: path to a log file (optional)
    """
    debug_flag = os.getenv(PROMPTHEUS_DEBUG_ENV, "").lower()
    is_debug = debug_flag in {"1", "true", "yes", "on"}

    # Default to WARNING for production, DEBUG if explicitly enabled
    level = logging.DEBUG if is_debug else default_level

    env_level = os.getenv("PROMPTHEUS_LOG_LEVEL")
    if env_level:
        try:
            level = getattr(logging, env_level.upper())
        except AttributeError:
            pass

    raw_format = os.getenv("PROMPTHEUS_LOG_FORMAT", "%(asctime)s %(levelname)s [%(name)s] %(message)s")
    use_json = raw_format.lower() == "json"

    log_file = os.getenv("PROMPTHEUS_LOG_FILE")

    # Only add handlers if debug mode is on OR log file is specified
    # This prevents ugly logging to console for normal users
    if not logging.getLogger().handlers:
        handlers: Optional[list[Handler]] = None

        if log_file:
            # Log to file
            handlers = [logging.FileHandler(log_file)]
        elif is_debug:
            # Log to console only if debug is explicitly enabled
            handlers = [logging.StreamHandler()]
        else:
            # No console logging for normal users - use NullHandler
            handlers = [logging.NullHandler()]

        logging.basicConfig(level=level, handlers=handlers)
        for handler in logging.getLogger().handlers:
            if use_json:
                handler.setFormatter(JsonFormatter())
            else:
                handler.setFormatter(logging.Formatter(raw_format))
    else:
        logging.getLogger().setLevel(level)
        for handler in logging.getLogger().handlers:
            handler.setLevel(level)
            if use_json:
                handler.setFormatter(JsonFormatter())
