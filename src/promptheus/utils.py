"""
Utility helpers shared across Promptheus modules.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable, Optional

from promptheus.logging_config import setup_logging


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\-]{12,}")


def sanitize_error_message(message: str, max_length: int = 160) -> str:
    """
    Remove potentially sensitive substrings (API keys, tokens) and truncate
    overly long provider error messages before showing them to users.
    """
    if not message:
        return ""

    masked = TOKEN_PATTERN.sub("***", message)
    sanitized = " ".join(masked.split())
    if len(sanitized) > max_length:
        sanitized = sanitized[: max_length - 3] + "..."
    return sanitized


def configure_logging(default_level: int = logging.INFO) -> None:
    """Backward-compatible wrapper around logging_config.setup_logging."""
    setup_logging(default_level)


def collapse_whitespace(lines: Iterable[str]) -> str:
    """Join lines while stripping trailing whitespace."""
    return "\n".join(line.rstrip() for line in lines)
