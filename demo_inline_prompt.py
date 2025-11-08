#!/usr/bin/env python3
"""
Demo script for the new inline prompt interface.

This demonstrates the prompt_toolkit with bottom toolbar and rich markdown rendering.
Uses the mock AI handler from core.py for testing without API keys.
"""

import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown

# Import the core AI response function
from promptheus.core import get_ai_response


def main():
    """
    Demo of the inline prompt interface.
    """
    # Use Rich Console for all output
    console = Console()

    # Create a PromptSession for persistent history
    session = PromptSession()

    # --- Define the UI components ---

    # 1. The prompt message itself (the ">" symbol)
    prompt_message = HTML('<b>&gt; </b>')

    # 2. The static bottom toolbar
    bottom_toolbar = HTML(
        ' <b>[Enter]</b> to submit, <b>[Alt+Enter]</b> for new line, <b>[Ctrl+C]</b> to quit'
    )

    # 3. Style for the bottom toolbar
    style = Style.from_dict({
        'bottom-toolbar': 'bg:#1e1e1e #ffffff',  # Dark background, white text
    })

    # --- Start the Application ---
    console.print("[bold cyan]Welcome to Promptheus Demo![/bold cyan]")
    console.print("Type your prompt below. Use Alt+Enter for multi-line input.")
    console.print()

    try:
        while True:
            # --- Get Input from User ---
            prompt_text = session.prompt(
                prompt_message,
                bottom_toolbar=bottom_toolbar,
                style=style,
                multiline=True,
                prompt_continuation='  '  # Indent for continued lines
            )

            # Do not process empty prompts
            if not prompt_text.strip():
                continue

            # --- Process and Display ---

            # 1. Print the user's prompt (using dim style)
            console.print("\n👤 [bold]You:[/bold]")
            console.print(f"> {prompt_text}", style="dim")

            # 2. Show a spinner while waiting for the AI
            try:
                with console.status("[bold green]AI is thinking...", spinner="dots"):
                    # Call the blocking AI function
                    response = get_ai_response(prompt_text)

                # 3. Print the AI's response as Markdown
                console.print("\n🤖 [bold]AI:[/bold]")
                console.print(Markdown(response))
                console.print()  # Add a blank line for spacing

            except Exception as e:
                console.print(f"[bold red]Error: {e}[/bold red]")

    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold yellow]Goodbye![/bold yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
