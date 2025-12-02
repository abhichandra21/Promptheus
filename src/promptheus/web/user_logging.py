"""User action logging for Cloudflare-authenticated users."""
import logging
from typing import Optional, Dict, Any
from fastapi import Request
from datetime import datetime


# Create a dedicated logger for user actions
user_action_logger = logging.getLogger("promptheus.user_actions")


def get_cloudflare_user_email(request: Request) -> Optional[str]:
    """
    Extract the authenticated user's email from Cloudflare Access headers.

    Cloudflare Access adds the following headers when a user is authenticated:
    - Cf-Access-Authenticated-User-Email: The email of the authenticated user
    - Cf-Access-Jwt-Assertion: JWT token with user details

    Args:
        request: The FastAPI request object

    Returns:
        The user's email address if found, otherwise None
    """
    # Try the standard Cloudflare Access header first
    user_email = request.headers.get("Cf-Access-Authenticated-User-Email")

    if not user_email:
        # Try alternative header names (case-insensitive)
        for header_name in request.headers:
            if header_name.lower() == "cf-access-authenticated-user-email":
                user_email = request.headers.get(header_name)
                break

    return user_email


def log_user_action(
    request: Request,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error: Optional[str] = None
) -> None:
    """
    Log a user action with Cloudflare authentication information.

    Args:
        request: The FastAPI request object
        action: Description of the action (e.g., "prompt_submit", "history_delete")
        details: Optional dictionary with additional action details
        success: Whether the action was successful
        error: Error message if the action failed
    """
    user_email = get_cloudflare_user_email(request)

    # Build the log message
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user_email or "unknown",
        "action": action,
        "path": request.url.path,
        "method": request.method,
        "success": success,
        "ip_address": request.client.host if request.client else "unknown",
    }

    # Add optional details
    if details:
        log_data["details"] = details

    # Add error if present
    if error:
        log_data["error"] = error

    # Log at appropriate level
    if success:
        user_action_logger.info(
            f"User action: {action} | User: {user_email or 'unknown'} | "
            f"Path: {request.url.path} | Success: {success}",
            extra=log_data
        )
    else:
        user_action_logger.warning(
            f"User action failed: {action} | User: {user_email or 'unknown'} | "
            f"Path: {request.url.path} | Error: {error}",
            extra=log_data
        )


def get_user_context(request: Request) -> Dict[str, Any]:
    """
    Get user context information for logging.

    Args:
        request: The FastAPI request object

    Returns:
        Dictionary with user context information
    """
    user_email = get_cloudflare_user_email(request)

    return {
        "user_email": user_email,
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("User-Agent", "unknown"),
        "cloudflare_authenticated": user_email is not None,
    }
