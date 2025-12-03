"""
Utility helpers shared across Promptheus modules.
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Iterable, Optional, TYPE_CHECKING

from promptheus.logging_config import setup_logging

if TYPE_CHECKING:
    from fastapi import Request

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


def get_user_email(request: "Request") -> str:
    """
    Extract user email from Cloudflare Access headers or future auth methods.

    Returns the authenticated user's email, or "unknown" if not authenticated.
    """
    # Option 1: Try specific email header first (correct case)
    user_email = request.headers.get("CF-Access-Authenticated-User-Email")

    if not user_email:
        # Option 2: Try case-insensitive search for safety
        for header_name in request.headers:
            if header_name.lower() == "cf-access-authenticated-user-email":
                user_email = request.headers.get(header_name)
                break

    # Option 3: Fallback to subject if no email (contains provider:identifier format)
    if not user_email:
        subject = request.headers.get("CF-Access-Subject")
        if subject and "@" in subject:  # If subject looks like an email
            user_email = subject

    # Future: Add custom auth extraction here
    # if not user_email and hasattr(request.state, "user"):
    #     user_email = request.state.user.email

    return user_email or "unknown"


def get_device_category(request: "Request") -> str:
    """
    Extract basic device category from User-Agent header for privacy-safe logging.

    Returns: "mobile", "tablet", "desktop", or "unknown".
    Only extracts category, NOT detailed fingerprinting information.
    """
    user_agent = request.headers.get("User-Agent", "").lower()

    if not user_agent:
        return "unknown"

    # Privacy-safe: Only detect basic device category
    # Avoid detailed fingerprinting, browser versions, or specific models

    # Mobile indicators (check first for specificity)
    mobile_indicators = ["mobile", "iphone", "ipod", "windows phone", "android"]

    # Tablet indicators (checked after confirming not mobile)
    tablet_indicators = ["ipad", "tablet", "kindle", "silk", "tab", "nexus", "sm-t", "gt-"]

    # Check for tablet-specific patterns first
    # iPads and explicit tablet indicators
    if "ipad" in user_agent or "tablet" in user_agent:
        return "tablet"

    # Android tablets (Android without "mobile")
    if "android" in user_agent and "mobile" not in user_agent:
        return "tablet"

    # Check for mobile indicators
    if any(indicator in user_agent for indicator in mobile_indicators):
        return "mobile"

    # Fallback to desktop for any other User-Agent
    return "desktop"
