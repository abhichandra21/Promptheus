"""I/O Context for managing terminal state and console routing."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable

from rich.console import Console

MessageSink = Callable[[str], None]


@dataclass
class IOContext:
    """
    Encapsulates all I/O state for the CLI application.

    This centralizes TTY detection, console routing, and mode flags
    so we don't have to thread multiple parameters everywhere.
    """

    # TTY detection
    stdin_is_tty: bool
    stdout_is_tty: bool

    # Consoles
    console_out: Console  # stdout - for payloads only
    console_err: Console  # stderr - for UI, errors, prompts

    # Notify function (always writes to stderr)
    notify: MessageSink

    # Mode flags
    quiet_output: bool
    plain_mode: bool

    @classmethod
    def create(cls, quiet_output_flag: bool = False, plain_mode: bool = False) -> IOContext:
        """
        Factory method to create IOContext from current terminal state.

        Args:
            quiet_output_flag: Force quiet mode even on TTY
            plain_mode: Use plain text instead of rich formatting

        Returns:
            Configured IOContext instance
        """
        stdin_is_tty = sys.stdin.isatty()
        stdout_is_tty = sys.stdout.isatty()

        # Auto-quiet when stdout is piped, or manual via flag
        quiet_output = (not stdout_is_tty) or quiet_output_flag

        # Create consoles
        console_out = Console(file=sys.stdout, color_system=None, force_terminal=False)
        console_err = Console(file=sys.stderr)

        # Notify always writes to stderr - errors must never be silenced
        notify: MessageSink = console_err.print

        return cls(
            stdin_is_tty=stdin_is_tty,
            stdout_is_tty=stdout_is_tty,
            console_out=console_out,
            console_err=console_err,
            notify=notify,
            quiet_output=quiet_output,
            plain_mode=plain_mode,
        )

    @property
    def is_fully_interactive(self) -> bool:
        """Both stdin and stdout are TTYs - can use full interactive UI."""
        return self.stdin_is_tty and self.stdout_is_tty

    @property
    def is_semi_interactive(self) -> bool:
        """stdin is TTY but stdout is not - can prompt but output is piped."""
        return self.stdin_is_tty and not self.stdout_is_tty

    @property
    def is_non_interactive(self) -> bool:
        """stdin is not a TTY - cannot ask questions."""
        return not self.stdin_is_tty
