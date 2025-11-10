"""Integration tests for IOContext and QuestionPrompter refactor."""

from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from promptheus.io_context import IOContext
from promptheus.question_prompter import (
    QuestionPrompter,
    RichPrompter,
    StdioPrompter,
    create_prompter,
)


class TestIOContext:
    """Test IOContext creation and properties."""

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=True)
    def test_create_fully_interactive(self, mock_stdout_tty, mock_stdin_tty):
        """Test IOContext creation when both stdin and stdout are TTYs."""
        io = IOContext.create()

        assert io.stdin_is_tty is True
        assert io.stdout_is_tty is True
        assert io.quiet_output is False
        assert io.is_fully_interactive is True
        assert io.is_semi_interactive is False
        assert io.is_non_interactive is False
        assert io.notify is not None
        assert io.console_out is not None
        assert io.console_err is not None

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=False)
    def test_create_semi_interactive(self, mock_stdout_tty, mock_stdin_tty):
        """Test IOContext creation when stdin is TTY but stdout is not (piped)."""
        io = IOContext.create()

        assert io.stdin_is_tty is True
        assert io.stdout_is_tty is False
        assert io.quiet_output is True  # Auto-quiet when stdout piped
        assert io.is_fully_interactive is False
        assert io.is_semi_interactive is True
        assert io.is_non_interactive is False

    @patch('sys.stdin.isatty', return_value=False)
    @patch('sys.stdout.isatty', return_value=True)
    def test_create_non_interactive(self, mock_stdout_tty, mock_stdin_tty):
        """Test IOContext creation when stdin is not a TTY (piped input)."""
        io = IOContext.create()

        assert io.stdin_is_tty is False
        assert io.stdout_is_tty is True
        assert io.quiet_output is False  # stdout is TTY, so not quiet
        assert io.is_fully_interactive is False
        assert io.is_semi_interactive is False
        assert io.is_non_interactive is True

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=True)
    def test_create_with_quiet_flag(self, mock_stdout_tty, mock_stdin_tty):
        """Test IOContext creation with explicit quiet mode flag (internal use)."""
        io = IOContext.create(quiet_output_flag=True)

        assert io.stdin_is_tty is True
        assert io.stdout_is_tty is True
        assert io.quiet_output is True  # Forced quiet via flag
        assert io.is_fully_interactive is True

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=True)
    def test_create_with_plain_mode(self, mock_stdout_tty, mock_stdin_tty):
        """Test IOContext creation with plain mode flag."""
        io = IOContext.create(plain_mode=True)

        assert io.plain_mode is True

    def test_notify_always_present(self):
        """Test that notify is always a callable, never None."""
        with patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=False):
            io = IOContext.create()

            # Notify should always be callable
            assert callable(io.notify)

            # Should not raise an exception
            io.notify("[red]Error: test[/red]")


class TestQuestionPrompter:
    """Test QuestionPrompter interface and implementations."""

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=True)
    def test_create_rich_prompter_for_fully_interactive(self, mock_stdout_tty, mock_stdin_tty):
        """Test that RichPrompter is created for fully interactive sessions."""
        io = IOContext.create()
        prompter = create_prompter(io)

        assert isinstance(prompter, RichPrompter)

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=False)
    def test_create_stdio_prompter_for_semi_interactive(self, mock_stdout_tty, mock_stdin_tty):
        """Test that StdioPrompter is created when stdout is piped."""
        io = IOContext.create()
        prompter = create_prompter(io)

        assert isinstance(prompter, StdioPrompter)

    @patch('sys.stdin.isatty', return_value=False)
    @patch('sys.stdout.isatty', return_value=True)
    def test_create_stdio_prompter_for_non_interactive(self, mock_stdout_tty, mock_stdin_tty):
        """Test that StdioPrompter is created when stdin is not interactive."""
        io = IOContext.create()
        prompter = create_prompter(io)

        assert isinstance(prompter, StdioPrompter)

    def test_rich_prompter_confirmation(self):
        """Test RichPrompter confirmation prompt."""
        prompter = RichPrompter()

        with patch('questionary.confirm') as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            result = prompter.prompt_confirmation("Test question?", default=True)

            assert result is True
            mock_confirm.assert_called_once_with("Test question?", default=True)

    def test_rich_prompter_radio(self):
        """Test RichPrompter radio selection."""
        prompter = RichPrompter()
        choices = ["Option 1", "Option 2", "Option 3"]

        with patch('questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = "Option 2"
            result = prompter.prompt_radio("Choose one:", choices)

            assert result == "Option 2"
            mock_select.assert_called_once_with("Choose one:", choices=choices)

    def test_rich_prompter_checkbox(self):
        """Test RichPrompter checkbox selection."""
        prompter = RichPrompter()
        choices = ["Option 1", "Option 2", "Option 3"]

        with patch('questionary.checkbox') as mock_checkbox:
            mock_checkbox.return_value.ask.return_value = ["Option 1", "Option 3"]
            result = prompter.prompt_checkbox("Choose multiple:", choices)

            assert result == ["Option 1", "Option 3"]
            mock_checkbox.assert_called_once_with("Choose multiple:", choices=choices)

    def test_rich_prompter_text(self):
        """Test RichPrompter text input."""
        prompter = RichPrompter()

        with patch('questionary.text') as mock_text:
            mock_text.return_value.ask.return_value = "User input"
            result = prompter.prompt_text("Enter text:", default="default")

            assert result == "User input"
            mock_text.assert_called_once_with("Enter text:", default="default")

    def test_stdio_prompter_confirmation_yes(self):
        """Test StdioPrompter confirmation with 'yes' response."""
        with patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=False):
            io = IOContext.create()
            prompter = StdioPrompter(io.notify)

            with patch('builtins.input', return_value='y'):
                result = prompter.prompt_confirmation("Proceed?", default=True)
                assert result is True

    def test_stdio_prompter_confirmation_no(self):
        """Test StdioPrompter confirmation with 'no' response."""
        with patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=False):
            io = IOContext.create()
            prompter = StdioPrompter(io.notify)

            with patch('builtins.input', return_value='n'):
                result = prompter.prompt_confirmation("Proceed?", default=True)
                assert result is False

    def test_stdio_prompter_confirmation_default(self):
        """Test StdioPrompter confirmation with empty response (uses default)."""
        with patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=False):
            io = IOContext.create()
            prompter = StdioPrompter(io.notify)

            with patch('builtins.input', return_value=''):
                result = prompter.prompt_confirmation("Proceed?", default=True)
                assert result is True

    def test_stdio_prompter_radio(self):
        """Test StdioPrompter radio selection."""
        with patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=False):
            io = IOContext.create()
            prompter = StdioPrompter(io.notify)
            choices = ["Option 1", "Option 2", "Option 3"]

            with patch('builtins.input', return_value='2'):
                result = prompter.prompt_radio("Choose:", choices)
                assert result == "Option 2"

    def test_stdio_prompter_checkbox(self):
        """Test StdioPrompter checkbox selection."""
        with patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=False):
            io = IOContext.create()
            prompter = StdioPrompter(io.notify)
            choices = ["Option 1", "Option 2", "Option 3"]

            with patch('builtins.input', return_value='1,3'):
                result = prompter.prompt_checkbox("Choose multiple:", choices)
                assert result == ["Option 1", "Option 3"]

    def test_stdio_prompter_text(self):
        """Test StdioPrompter text input."""
        with patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=False):
            io = IOContext.create()
            prompter = StdioPrompter(io.notify)

            with patch('builtins.input', return_value='User input'):
                result = prompter.prompt_text("Enter text:", default="default")
                assert result == "User input"

    def test_stdio_prompter_eoferror(self):
        """Test StdioPrompter raises EOFError when stdin is not interactive."""
        with patch('sys.stdin.isatty', return_value=True), \
             patch('sys.stdout.isatty', return_value=False):
            io = IOContext.create()
            prompter = StdioPrompter(io.notify)

            with patch('builtins.input', side_effect=EOFError):
                with pytest.raises(EOFError):
                    prompter.prompt_confirmation("Proceed?")


class TestIntegration:
    """Integration tests combining IOContext and QuestionPrompter."""

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=True)
    def test_fully_interactive_workflow(self, mock_stdout_tty, mock_stdin_tty):
        """Test complete workflow in fully interactive mode."""
        io = IOContext.create()
        prompter = create_prompter(io)

        # Should use RichPrompter
        assert isinstance(prompter, RichPrompter)
        assert io.is_fully_interactive is True
        assert io.quiet_output is False

    @patch('sys.stdin.isatty', return_value=True)
    @patch('sys.stdout.isatty', return_value=False)
    def test_semi_interactive_workflow(self, mock_stdout_tty, mock_stdin_tty):
        """Test complete workflow when stdout is piped."""
        io = IOContext.create()
        prompter = create_prompter(io)

        # Should use StdioPrompter for semi-interactive
        assert isinstance(prompter, StdioPrompter)
        assert io.is_semi_interactive is True
        assert io.quiet_output is True  # Auto-quiet

    @patch('sys.stdin.isatty', return_value=False)
    @patch('sys.stdout.isatty', return_value=True)
    def test_non_interactive_workflow(self, mock_stdout_tty, mock_stdin_tty):
        """Test workflow when stdin is piped."""
        io = IOContext.create()

        # Should use StdioPrompter
        prompter = create_prompter(io)
        assert isinstance(prompter, StdioPrompter)
        assert io.is_non_interactive is True

        # Stdin prompts should raise EOFError in this mode
        with patch('builtins.input', side_effect=EOFError):
            with pytest.raises(EOFError):
                prompter.prompt_text("Enter something:")
