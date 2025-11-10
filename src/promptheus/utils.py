"""
Utility helpers shared across Promptheus modules.
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Iterable, Optional

from promptheus.logging_config import setup_logging

try:
    import pyperclip
except ImportError:
    pyperclip = None


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


def copy_to_clipboard(text: str, console, notify: Optional[Callable[[str], None]] = None) -> bool:
    """
    Copy text to clipboard.

    Returns True if successful, False otherwise.
    If notify is provided, will call it with status messages.
    """
    if pyperclip is None:
        msg = "[yellow]Warning: pyperclip not available - cannot copy to clipboard[/yellow]"
        if notify:
            notify(msg)
        else:
            console.print(msg)
        return False

    try:
        pyperclip.copy(text)
        msg = "[green]✓[/green] Copied to clipboard!"
        if notify:
            notify(msg)
        else:
            console.print(msg)
        return True
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        msg = f"[yellow]Warning: Failed to copy to clipboard: {sanitized}[/yellow]"
        if notify:
            notify(msg)
        else:
            console.print(msg)
        return False
