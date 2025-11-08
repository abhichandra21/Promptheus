#!/usr/bin/env python3
"""
Demo script for the new inline prompt interface.

This demonstrates the prompt_toolkit with bottom toolbar and rich markdown rendering.
Uses the mock AI handler from core.py for testing without API keys.

Key bindings:
- Enter: Submit the prompt
- Alt+Enter: Add a new line
- Ctrl+C: Quit
"""

import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown

# Import the core AI response function
from promptheus.core import get_ai_response


def create_key_bindings() -> KeyBindings:
    """
    Create custom key bindings for the prompt.

    - Enter: Submit the prompt
    - Alt+Enter (Meta+Enter): Add a new line
    """
    kb = KeyBindings()

    @kb.add('enter')
    def _(event):
        """Submit on Enter."""
        event.current_buffer.validate_and_handle()

    @kb.add('escape', 'enter')  # Alt+Enter on most systems
    def _(event):
        """Insert newline on Alt+Enter."""
        event.current_buffer.insert_text('\n')

    return kb


def create_bottom_toolbar(provider: str = "demo", model: str = "mock-ai") -> HTML:
    """
    Create the bottom toolbar with provider/model info and key bindings.

    Format: demo | mock-ai │ [Enter] submit │ [Alt+Enter] new line │ [Ctrl+C] quit
    """
    return HTML(
        f' {provider} | {model} │ '
        f'<b>[Enter]</b> submit │ <b>[Alt+Enter]</b> new line │ <b>[Ctrl+C]</b> quit'
    )


def main():
    """
    Demo of the inline prompt interface.
    """
    # Use Rich Console for all output
    console = Console()

    # Create custom key bindings
    bindings = create_key_bindings()

    # Create a PromptSession for persistent history
    session = PromptSession(
        multiline=True,
        prompt_continuation='… ',
        key_bindings=bindings,
    )

    # --- Define the UI components ---

    # 1. The prompt message itself (the ">" symbol)
    prompt_message = HTML('<b>&gt; </b>')

    # 2. The static bottom toolbar with provider/model info
    bottom_toolbar = create_bottom_toolbar()

    # 3. Style for the bottom toolbar
    style = Style.from_dict({
        'bottom-toolbar': 'bg:#1a1a1a #888888',  # Very dark background, medium gray text
    })

    # --- Start the Application ---
    console.print("[bold cyan]Welcome to Promptheus Demo![/bold cyan]")
    console.print("[dim]Interactive mode ready. Type your prompt below.[/dim]")
    console.print()

    try:
        while True:
            # --- Get Input from User ---
            prompt_text = session.prompt(
                prompt_message,
                bottom_toolbar=bottom_toolbar,
                style=style,
            )

            # Do not process empty prompts
            if not prompt_text.strip():
                continue

            # --- Process and Display ---

            # Print the user's prompt
            console.print()
            console.print(f"[dim]{prompt_text}[/dim]")
            console.print()

            # Call the AI function (simulates 1.5s delay)
            try:
                response = get_ai_response(prompt_text)

                # Print the AI's response as Markdown
                console.print(Markdown(response))
                console.print()

            except Exception as e:
                console.print(f"[bold red]Error: {e}[/bold red]")

    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold yellow]Goodbye![/bold yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
