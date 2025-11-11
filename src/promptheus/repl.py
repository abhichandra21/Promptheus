"""
Backward compatibility module for REPL functionality.

This module re-exports all public APIs from the new repl package structure
to maintain backward compatibility with existing imports.
"""

# Re-export all public APIs from the new modular structure
from .repl.session import interactive_mode
from .repl.commands import handle_session_command as handle_repl_command
from .repl.history_view import display_history
from .repl.completer import CommandCompleter

# Also re-export any utility functions that might be imported
from .repl.commands import (
    show_help,
    show_about,
    show_bug_report,
    show_status,
    reload_provider_instance,
)

# Use shared copy_to_clipboard function from utils
from promptheus.utils import copy_to_clipboard
from .repl.session import format_toolbar_text, create_bottom_toolbar
from promptheus.history import get_history

# Re-export types for compatibility
from .repl.session import MessageSink, ProcessPromptFn

__all__ = [
    # Main public APIs
    "interactive_mode",
    "handle_repl_command",
    "display_history",
    "get_history",

    # Completer
    "CommandCompleter",

    # Utility functions (might be imported directly)
    "copy_to_clipboard",
    "show_help",
    "show_about",
    "show_bug_report",
    "show_status",
    "reload_provider_instance",
    "format_toolbar_text",
    "create_bottom_toolbar",

    # Type aliases
    "MessageSink",
    "ProcessPromptFn",
]