"""Tests for REPL functionality and interactive mode helpers."""

import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pytest
from argparse import Namespace

from promptheus.repl import (
    interactive_mode,
    display_history,
    format_toolbar_text,
)
from promptheus.config import Config
from promptheus.providers import LLMProvider
from promptheus.history import PromptHistory, HistoryEntry
from promptheus.exceptions import PromptCancelled


class MockProvider(LLMProvider):
    """Mock provider for testing purposes."""

    def generate_questions(self, initial_prompt: str, system_instruction: str):
        return {
            "task_type": "generation",
            "questions": [{"question": "Test?", "type": "text", "required": True}]
        }

    def get_available_models(self):
        return ["test-model"]

    def _generate_text(self, prompt: str, system_instruction: str, json_mode: bool = False, max_tokens=None):
        return "Mocked response"


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def mock_config():
    config = Mock(spec=Config)
    config.provider = "test"
    config.get_model.return_value = "test-model"
    config.validate.return_value = True
    config.consume_status_messages.return_value = []
    config.consume_error_messages.return_value = []
    return config


@pytest.fixture
def mock_notify():
    return Mock()


@pytest.fixture
def mock_console():
    console = Mock()
    console.print = Mock()
    return console


@pytest.fixture
def sample_history_entries():
    return [
        HistoryEntry(
            original_prompt="Write code for sorting algorithm",
            refined_prompt="Write Python code for quicksort algorithm",
            task_type="generation",
            timestamp="2024-01-15T10:30:00"
        ),
        HistoryEntry(
            original_prompt="Explain machine learning",
            refined_prompt="Explain machine learning concepts for beginners",
            task_type="analysis",
            timestamp="2024-01-15T11:45:00"
        )
    ]


@patch('promptheus.repl.get_history')
def test_display_history_no_entries(mock_get_history, mock_console, mock_notify):
    """Test display_history when no entries exist."""
    mock_history = Mock()
    mock_history.get_recent.return_value = []
    mock_get_history.return_value = mock_history

    display_history(mock_console, mock_notify, limit=20)

    mock_notify.assert_called_once_with("[yellow]No history entries found.[/yellow]")


@patch('promptheus.repl.get_history')
def test_display_history_with_entries(mock_get_history, mock_console, mock_notify, sample_history_entries):
    """Test display_history with sample entries."""
    mock_history = Mock()
    mock_history.get_recent.return_value = sample_history_entries
    mock_get_history.return_value = mock_history

    display_history(mock_console, mock_notify, limit=20)

    # Should call console.print for table and spacing
    assert mock_console.print.call_count >= 3

    # Should call notify with usage hint
    mock_notify.assert_any_call("[dim]Use '/load <number>' to load a prompt from history[/dim]")


@patch('promptheus.repl.get_history')
@patch('builtins.input')
def test_interactive_mode_plain_mode_exit(mock_input, mock_get_history,
                                         mock_provider, mock_config, mock_notify, mock_console):
    """Test interactive mode plain input with exit command."""
    mock_input.side_effect = ["exit"]
    mock_history = Mock()
    mock_history.get_prompt_history_file.return_value = "test_history"
    mock_get_history.return_value = mock_history

    args = Namespace()

    interactive_mode(
        mock_provider,
        mock_config,
        args,
        False,  # debug_enabled
        True,   # plain_mode
        mock_notify,
        mock_console,
        Mock()  # process_prompt function
    )

    toolbar_message = format_toolbar_text("test", "test-model")
    # Should show welcome, toolbar, and goodbye via console
    mock_console.print.assert_any_call("[bold cyan]Welcome to Promptheus![/bold cyan]")
    mock_console.print.assert_any_call(toolbar_message)
    mock_console.print.assert_any_call("[bold yellow]Goodbye![/bold yellow]")


@patch('promptheus.repl.get_history')
@patch('builtins.input')
def test_interactive_mode_plain_mode_quit_command(mock_input, mock_get_history,
                                                mock_provider, mock_config, mock_notify, mock_console):
    """Test various quit commands in plain mode."""
    for quit_cmd in ["quit", "q"]:
        mock_input.reset_mock()
        mock_notify.reset_mock()
        mock_input.side_effect = [quit_cmd]

        mock_history = Mock()
        mock_history.get_prompt_history_file.return_value = "test_history"
        mock_get_history.return_value = mock_history

        args = Namespace()

        interactive_mode(
            mock_provider,
            mock_config,
            args,
            False,  # debug_enabled
            True,   # plain_mode
            mock_notify,
            mock_console,
            Mock()  # process_prompt function
        )

        toolbar_message = format_toolbar_text("test", "test-model")
        mock_console.print.assert_any_call("[bold yellow]Goodbye![/bold yellow]")
        mock_console.print.assert_any_call(toolbar_message)


@patch('promptheus.repl.get_history')
@patch('builtins.input')
def test_interactive_mode_history_command(mock_input, mock_get_history,
                                         mock_provider, mock_config, mock_notify, mock_console,
                                         sample_history_entries):
    """Test /history command in interactive mode."""
    mock_input.side_effect = ["/history", "exit"]
    mock_history = Mock()
    mock_history.get_prompt_history_file.return_value = "test_history"
    mock_history.get_recent.return_value = sample_history_entries
    mock_get_history.return_value = mock_history

    args = Namespace()

    with patch('promptheus.repl.display_history') as mock_display:
        interactive_mode(
            mock_provider,
            mock_config,
            args,
            False,  # debug_enabled
            True,   # plain_mode
            mock_notify,
            mock_console,
            Mock()  # process_prompt function
        )

        mock_display.assert_called_once_with(mock_console, mock_notify)


@patch('promptheus.repl.get_history')
@patch('builtins.input')
def test_interactive_mode_load_command_valid(mock_input, mock_get_history,
                                           mock_provider, mock_config, mock_notify, mock_console,
                                           sample_history_entries):
    """Test /load command with valid index."""
    mock_input.side_effect = ["/load 1", "exit"]
    mock_history = Mock()
    mock_history.get_prompt_history_file.return_value = "test_history"
    mock_history.get_by_index.return_value = sample_history_entries[0]
    mock_get_history.return_value = mock_history

    args = Namespace()
    mock_process_prompt = Mock(return_value=("processed", "task"))

    interactive_mode(
        mock_provider,
        mock_config,
        args,
        False,  # debug_enabled
        True,   # plain_mode
        mock_notify,
        mock_console,
        mock_process_prompt
    )

    # Should show success message
    mock_console.print.assert_any_call("[green]✓[/green] Loaded prompt #1 from history")
    # Should process the loaded prompt
    mock_process_prompt.assert_called()


@patch('promptheus.repl.get_history')
@patch('builtins.input')
def test_interactive_mode_load_command_invalid(mock_input, mock_get_history,
                                             mock_provider, mock_config, mock_notify, mock_console):
    """Test /load command with invalid index."""
    mock_input.side_effect = ["/load 999", "exit"]
    mock_history = Mock()
    mock_history.get_prompt_history_file.return_value = "test_history"
    mock_history.get_by_index.return_value = None
    mock_get_history.return_value = mock_history

    args = Namespace()

    interactive_mode(
        mock_provider,
        mock_config,
        args,
        False,  # debug_enabled
        True,   # plain_mode
        mock_notify,
        mock_console,
        Mock()  # process_prompt function
    )

    mock_console.print.assert_any_call("[yellow]No history entry found at index 999[/yellow]")


@patch('promptheus.repl.get_history')
@patch('builtins.input')
@patch('promptheus.repl.questionary.confirm')
def test_interactive_mode_clear_history_confirmed(mock_confirm, mock_input, mock_get_history, mock_provider, mock_config,
                                                 mock_notify, mock_console):
    """Test /clear-history command with confirmation."""
    mock_confirm.return_value.ask.return_value = True
    mock_input.side_effect = ["/clear-history", "exit"]
    mock_history = Mock()
    mock_history.get_prompt_history_file.return_value = "test_history"
    mock_get_history.return_value = mock_history

    args = Namespace()

    interactive_mode(
        mock_provider,
        mock_config,
        args,
        False,  # debug_enabled
        True,   # plain_mode
        mock_notify,
        mock_console,
        Mock()  # process_prompt function
    )

    mock_history.clear.assert_called_once()
    mock_console.print.assert_any_call("[green]✓[/green] History cleared")


@patch('promptheus.repl.get_history')
@patch('builtins.input')
def test_interactive_mode_unknown_command(mock_input, mock_get_history,
                                         mock_provider, mock_config, mock_notify, mock_console):
    """Test unknown command handling."""
    mock_input.side_effect = ["/unknown", "exit"]
    mock_history = Mock()
    mock_history.get_prompt_history_file.return_value = "test_history"
    mock_get_history.return_value = mock_history

    args = Namespace()

    interactive_mode(
        mock_provider,
        mock_config,
        args,
        False,  # debug_enabled
        True,   # plain_mode
        mock_notify,
        mock_console,
        Mock()  # process_prompt function
    )

    mock_console.print.assert_any_call("[yellow]Unknown command: /unknown[/yellow]")
    mock_console.print.assert_any_call("[dim]Type /help to see available commands[/dim]")


@patch('promptheus.repl.get_history')
@patch('builtins.input')
def test_interactive_mode_process_prompt_cancelled(mock_input, mock_get_history,
                                                  mock_provider, mock_config, mock_notify, mock_console):
    """Ensure PromptCancelled from process_prompt is handled gracefully."""
    mock_input.side_effect = ["run", "exit"]
    mock_history = Mock()
    mock_history.get_prompt_history_file.return_value = "test_history"
    mock_get_history.return_value = mock_history

    args = Namespace()
    mock_process_prompt = Mock(side_effect=PromptCancelled("Analysis cancelled"))

    interactive_mode(
        mock_provider,
        mock_config,
        args,
        False,  # debug_enabled
        True,   # plain_mode
        mock_notify,
        mock_console,
        mock_process_prompt
    )

    mock_console.print.assert_any_call("\n[yellow]Analysis cancelled[/yellow]")
    mock_process_prompt.assert_called_once()


@patch('promptheus.repl.get_history')
@patch('builtins.input')
def test_interactive_mode_empty_input(mock_input, mock_get_history,
                                     mock_provider, mock_config, mock_notify, mock_console):
    """Test that empty input is skipped."""
    mock_input.side_effect = ["", "   ", "exit"]
    mock_history = Mock()
    mock_history.get_prompt_history_file.return_value = "test_history"
    mock_get_history.return_value = mock_history

    args = Namespace()

    interactive_mode(
        mock_provider,
        mock_config,
        args,
        False,  # debug_enabled
        True,   # plain_mode
        mock_notify,
        mock_console,
        Mock()  # process_prompt function
    )

    toolbar_message = format_toolbar_text("test", "test-model")
    # Should still show welcome, toolbar, and goodbye
    mock_console.print.assert_any_call("[bold cyan]Welcome to Promptheus![/bold cyan]")
    mock_console.print.assert_any_call(toolbar_message)
    mock_console.print.assert_any_call("[bold yellow]Goodbye![/bold yellow]")


@patch('promptheus.repl.get_history')
@patch('builtins.input')
def test_interactive_mode_keyboard_interrupt(mock_input, mock_get_history,
                                           mock_provider, mock_config, mock_notify, mock_console):
    """Test KeyboardInterrupt handling."""
    mock_input.side_effect = KeyboardInterrupt()
    mock_history = Mock()
    mock_history.get_prompt_history_file.return_value = "test_history"
    mock_get_history.return_value = mock_history

    args = Namespace()

    interactive_mode(
        mock_provider,
        mock_config,
        args,
        False,  # debug_enabled
        True,   # plain_mode
        mock_notify,
        mock_console,
        Mock()  # process_prompt function
    )

    mock_console.print.assert_any_call("\n[bold yellow]Goodbye![/bold yellow]")
