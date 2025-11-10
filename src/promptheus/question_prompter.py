"""Question prompter abstraction for interactive and non-interactive modes."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import questionary

from promptheus.io_context import IOContext, MessageSink


class QuestionPrompter(ABC):
    """Abstract interface for prompting users with questions."""

    @abstractmethod
    def prompt_confirmation(self, message: str, default: bool = True) -> bool:
        """
        Ask a yes/no question.

        Args:
            message: The question to ask
            default: Default answer if user just presses enter

        Returns:
            True for yes, False for no

        Raises:
            EOFError: If stdin is not interactive
        """
        pass

    @abstractmethod
    def prompt_radio(self, message: str, choices: List[str]) -> str:
        """
        Ask user to select one option from a list.

        Args:
            message: The question to ask
            choices: List of options to choose from

        Returns:
            Selected option

        Raises:
            EOFError: If stdin is not interactive
        """
        pass

    @abstractmethod
    def prompt_checkbox(self, message: str, choices: List[str]) -> List[str]:
        """
        Ask user to select multiple options from a list.

        Args:
            message: The question to ask
            choices: List of options to choose from

        Returns:
            List of selected options

        Raises:
            EOFError: If stdin is not interactive
        """
        pass

    @abstractmethod
    def prompt_text(self, message: str, default: str = "") -> str:
        """
        Ask user for text input.

        Args:
            message: The question to ask
            default: Default value if user just presses enter

        Returns:
            User's text input

        Raises:
            EOFError: If stdin is not interactive
        """
        pass


class RichPrompter(QuestionPrompter):
    """
    Interactive prompter using questionary for rich TTY experience.

    Uses arrow keys, colored output, and interactive menus.
    Requires both stdin and stdout to be TTYs.
    """

    def prompt_confirmation(self, message: str, default: bool = True) -> bool:
        answer = questionary.confirm(message, default=default).ask()
        if answer is None:
            raise KeyboardInterrupt("User cancelled")
        return answer

    def prompt_radio(self, message: str, choices: List[str]) -> str:
        answer = questionary.select(message, choices=choices).ask()
        if answer is None:
            raise KeyboardInterrupt("User cancelled")
        return answer

    def prompt_checkbox(self, message: str, choices: List[str]) -> List[str]:
        answer = questionary.checkbox(message, choices=choices).ask()
        if answer is None:
            raise KeyboardInterrupt("User cancelled")
        return answer

    def prompt_text(self, message: str, default: str = "") -> str:
        answer = questionary.text(message, default=default).ask()
        if answer is None:
            raise KeyboardInterrupt("User cancelled")
        return answer.strip()


class StdioPrompter(QuestionPrompter):
    """
    Simple prompter using stderr/input() for when stdout is piped.

    All prompts written to stderr, reads from stdin.
    Works when stdin is TTY but stdout is not.
    """

    def __init__(self, notify: MessageSink):
        """
        Initialize stdio prompter.

        Args:
            notify: Function to write messages to stderr
        """
        self.notify = notify

    def prompt_confirmation(self, message: str, default: bool = True) -> bool:
        default_str = "Y/n" if default else "y/N"
        sys.stderr.write(f"\n{message} ({default_str}): ")
        sys.stderr.flush()
        try:
            response = input().strip().lower()
        except EOFError:
            raise EOFError("stdin is not interactive")

        if not response:
            return default
        return response in ('y', 'yes')

    def prompt_radio(self, message: str, choices: List[str]) -> str:
        sys.stderr.write(f"\n{message}\n")
        for i, choice in enumerate(choices, 1):
            sys.stderr.write(f"  {i}. {choice}\n")
        sys.stderr.write(f"Choice [1-{len(choices)}]: ")
        sys.stderr.flush()

        while True:
            try:
                user_input = input().strip()
            except EOFError:
                raise EOFError("stdin is not interactive")

            try:
                idx = int(user_input) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
                else:
                    sys.stderr.write(f"Invalid choice. Please enter 1-{len(choices)}: ")
                    sys.stderr.flush()
            except ValueError:
                sys.stderr.write("Invalid input. Please enter a number: ")
                sys.stderr.flush()

    def prompt_checkbox(self, message: str, choices: List[str]) -> List[str]:
        sys.stderr.write(f"\n{message} (comma-separated numbers)\n")
        for i, choice in enumerate(choices, 1):
            sys.stderr.write(f"  {i}. {choice}\n")
        sys.stderr.write(f"Choices [1-{len(choices)}]: ")
        sys.stderr.flush()

        while True:
            try:
                user_input = input().strip()
            except EOFError:
                raise EOFError("stdin is not interactive")

            if not user_input:
                return []

            try:
                indices = [int(c.strip()) - 1 for c in user_input.split(',') if c.strip()]
                selected = [choices[i] for i in indices if 0 <= i < len(choices)]
                if selected or not user_input:
                    return selected
                else:
                    sys.stderr.write("Invalid choices. Please try again: ")
                    sys.stderr.flush()
            except ValueError:
                sys.stderr.write("Invalid input. Please enter comma-separated numbers: ")
                sys.stderr.flush()

    def prompt_text(self, message: str, default: str = "") -> str:
        default_str = f" [{default}]" if default else ""
        sys.stderr.write(f"\n{message}{default_str}: ")
        sys.stderr.flush()

        try:
            answer = input().strip()
        except EOFError:
            raise EOFError("stdin is not interactive")

        if not answer and default:
            return str(default)
        return answer


def create_prompter(io: IOContext) -> QuestionPrompter:
    """
    Factory function to create appropriate prompter based on I/O context.

    Args:
        io: I/O context with TTY state

    Returns:
        RichPrompter if fully interactive, StdioPrompter otherwise
    """
    if io.is_fully_interactive:
        return RichPrompter()
    else:
        return StdioPrompter(io.notify)
