"""
Textual TUI for Promptheus - Modern terminal user interface.

This module provides a full-screen, chat-like interface for Promptheus
using the Textual framework.
"""

from __future__ import annotations

import logging
from typing import Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Log, TextArea

logger = logging.getLogger(__name__)


class PromptheusApp(App):
    """
    Promptheus TUI Application.

    A full-screen chat interface with:
    - A scrollable chat log at the top (85% of screen)
    - A text input area at the bottom (15% of screen)
    - Keybindings for quit and dark mode toggle
    """

    CSS = """
    Screen {
        background: $background;
    }

    #history {
        height: 85%;
        border: solid $primary;
        padding: 1;
        margin: 0 1;
    }

    #input-box {
        height: 15%;
        border: solid $accent;
        margin: 0 1 1 1;
    }

    #input {
        height: 100%;
        width: 100%;
    }

    Log {
        scrollbar-gutter: stable;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+s", "toggle_dark", "Toggle Dark Mode"),
    ]

    def __init__(self, ai_handler: Callable[[str], str], **kwargs) -> None:
        """
        Initialize the Promptheus TUI.

        Args:
            ai_handler: A callable that takes a prompt string and returns an AI response.
                       This should be a blocking function (will be run in a worker thread).
            **kwargs: Additional arguments passed to the App constructor.
        """
        super().__init__(**kwargs)
        self.ai_handler = ai_handler
        self.last_log_line: int = -1  # Track the last line we wrote "Thinking..." to

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        yield Vertical(
            Log(id="history", auto_scroll=True, highlight=True, markup=True),
            Vertical(
                TextArea(id="input", show_line_numbers=False),
                id="input-box",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        # Write welcome message
        log = self.query_one(Log)
        log.write_line("[bold cyan]Welcome to Promptheus TUI![/bold cyan]")
        log.write_line("[dim]Type your prompt and press Ctrl+Enter to submit.[/dim]")
        log.write_line("[dim]Press Ctrl+C to quit, Ctrl+S to toggle dark mode.[/dim]")
        log.write_line("")

        # Set focus to the text input
        text_area = self.query_one("#input", TextArea)
        text_area.focus()

    def on_text_area_submitted(self, event: TextArea.Submitted) -> None:
        """
        Handle text submission from the TextArea.

        This is triggered when the user presses Ctrl+Enter (default submit key).
        """
        # Get the submitted text
        prompt = event.text.strip()

        # Ignore empty submissions
        if not prompt:
            return

        # Clear the input
        text_area = self.query_one("#input", TextArea)
        text_area.clear()

        # Write user's prompt to the log
        log = self.query_one(Log)
        log.write_line("")
        log.write_line(f"[bold green]👤 You:[/bold green]")
        log.write_line(f"[white]{prompt}[/white]")
        log.write_line("")

        # Write "Thinking..." placeholder
        log.write_line(f"[bold blue]🤖 AI:[/bold blue]")
        self.last_log_line = log.lines  # Track the line number for replacement
        log.write_line("[dim]Thinking...[/dim]")

        # Run the AI handler in a worker thread to avoid blocking the UI
        self.run_worker(self.call_ai(prompt), exclusive=False)

    async def call_ai(self, prompt: str) -> None:
        """
        Worker method to call the AI handler.

        This runs in a separate thread to avoid blocking the UI.
        The AI response is sent back to the main thread for display.

        Args:
            prompt: The user's prompt string
        """
        try:
            # This is a blocking call that runs in the worker thread
            response = self.ai_handler(prompt)

            # Use call_from_thread to update the UI from the worker thread
            self.call_from_thread(self.update_log, response, is_error=False)

        except Exception as exc:
            # Handle errors and display them in the log
            error_message = f"Error: {str(exc)}"
            logger.exception("AI handler failed")
            self.call_from_thread(self.update_log, error_message, is_error=True)

    def update_log(self, response: str, is_error: bool = False) -> None:
        """
        Update the log with the AI response.

        This method is called from the main thread via call_from_thread.

        Args:
            response: The AI's response or error message
            is_error: Whether this is an error message
        """
        log = self.query_one(Log)

        # Remove the "Thinking..." line by clearing and rewriting
        # Since Log doesn't have a replace method in older versions,
        # we'll just write the response on a new line
        if is_error:
            log.write_line(f"[bold red]{response}[/bold red]")
        else:
            # Write the actual response
            log.write_line(f"[yellow]{response}[/yellow]")

        log.write_line("")

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark
