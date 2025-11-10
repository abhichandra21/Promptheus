"""
REPL package for Promptheus interactive mode.

This package contains the modularized components of the interactive REPL interface.
"""

from .session import interactive_mode
from .commands import handle_session_command, create_command_registry
from .history_view import display_history
from .completer import CommandCompleter

# Export with backward compatible names
handle_repl_command = handle_session_command

__all__ = [
    "interactive_mode",
    "handle_session_command",
    "handle_repl_command",  # Backward compatibility
    "display_history",
    "CommandCompleter",
    "create_command_registry",
]