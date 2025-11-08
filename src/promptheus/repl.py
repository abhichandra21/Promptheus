from __future__ import annotations

import logging
from argparse import Namespace
from typing import Callable, Optional, Tuple

import questionary
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from promptheus.config import Config
from promptheus.history import get_history
from promptheus.providers import LLMProvider
from promptheus.utils import sanitize_error_message

MessageSink = Callable[[str], None]
ProcessPromptFn = Callable[
    [LLMProvider, str, Namespace, bool, bool, MessageSink, Config],
    Optional[Tuple[str, str]],
]

logger = logging.getLogger(__name__)


def display_history(console: Console, notify: MessageSink, limit: int = 20) -> None:
    """Display recent history entries."""
    history = get_history()
    entries = history.get_recent(limit)

    if not entries:
        notify("[yellow]No history entries found.[/yellow]")
        return

    table = Table(title="Prompt History", show_header=True, header_style="bold cyan", show_lines=True)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Date", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Original → Refined", style="white")

    for idx, entry in enumerate(entries, 1):
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(entry.timestamp)
            timestamp_str = dt.strftime("%m-%d %H:%M")
        except Exception:  # pragma: no cover - defensive
            timestamp_str = entry.timestamp[5:16]

        original = entry.original_prompt[:60] + "..." if len(entry.original_prompt) > 60 else entry.original_prompt
        refined = entry.refined_prompt[:60] + "..." if len(entry.refined_prompt) > 60 else entry.refined_prompt

        original = original.replace("\n", " ")
        refined = refined.replace("\n", " ")

        task_type = entry.task_type or "unknown"
        combined = f"[white]{original}[/white]\n[dim]→[/dim] [yellow]{refined}[/yellow]"

        table.add_row(str(idx), timestamp_str, task_type, combined)

    console.print()
    console.print(table)
    console.print()
    notify("[dim]Use ':load <number>' to load a prompt from history[/dim]")


def interactive_mode(
    provider: LLMProvider,
    app_config: Config,
    args: Namespace,
    debug_enabled: bool,
    plain_mode: bool,
    notify: MessageSink,
    console: Console,
    process_prompt: ProcessPromptFn,
) -> None:
    """
    Interactive REPL mode with rich inline prompt.

    Features:
    - Bottom toolbar with help text
    - Multiline input support
    - Rich markdown rendering for AI responses
    - Loading spinner during processing
    """
    # Welcome message with rich formatting
    console.print("[bold cyan]Welcome to Promptheus Interactive Mode![/bold cyan]")
    console.print(f"[dim]Using provider: {app_config.provider} | Model: {app_config.get_model()}[/dim]")
    console.print("[dim]Type 'exit' or 'quit' to exit, ':history' to view history[/dim]\n")

    prompt_count = 1
    use_prompt_toolkit = not plain_mode

    # Define the UI components for prompt_toolkit
    prompt_message = HTML('<b>&gt; </b>')
    bottom_toolbar = HTML(
        ' <b>[Enter]</b> to submit, <b>[Alt+Enter]</b> for new line, <b>[Ctrl+C]</b> to quit'
    )
    style = Style.from_dict({
        'bottom-toolbar': 'bg:#1e1e1e #ffffff',  # Dark background, white text
    })

    session: Optional[PromptSession] = None
    if use_prompt_toolkit:
        try:
            history_file = get_history().get_prompt_history_file()
            session = PromptSession(
                history=FileHistory(str(history_file)),
                multiline=True,
                prompt_continuation='  ',  # Indent for continued lines
            )
        except Exception as exc:
            logger.warning("Failed to initialize history: %s", sanitize_error_message(str(exc)))
            use_prompt_toolkit = False
            plain_mode = True

    while True:
        try:
            if use_prompt_toolkit and session:
                try:
                    user_input = session.prompt(
                        prompt_message,
                        bottom_toolbar=bottom_toolbar,
                        style=style,
                    ).strip()
                except KeyboardInterrupt:
                    console.print("\n[bold yellow]Goodbye![/bold yellow]")
                    break
                except (EOFError, OSError, RuntimeError) as exc:
                    logger.warning(
                        "Interactive prompt failed (%s); switching to plain mode",
                        sanitize_error_message(str(exc)),
                    )
                    use_prompt_toolkit = False
                    plain_mode = True
                    session = None
                    continue
            else:
                try:
                    user_input = input(f"promptheus [{prompt_count}]> ").strip()
                except (EOFError, KeyboardInterrupt):
                    console.print("\n[bold yellow]Goodbye![/bold yellow]")
                    break

            # Handle exit commands
            if user_input.lower() in {"exit", "quit", "q"}:
                console.print("[bold yellow]Goodbye![/bold yellow]")
                break

            # Handle special commands
            if user_input.startswith(":"):
                command_parts = user_input.split(None, 1)
                command = command_parts[0].lower()

                if command == ":history":
                    display_history(console, notify)
                    continue
                if command == ":load" and len(command_parts) > 1:
                    try:
                        index = int(command_parts[1])
                        entry = get_history().get_by_index(index)
                        if entry:
                            console.print(f"[green]✓[/green] Loaded prompt #{index} from history")
                            user_input = entry.original_prompt
                        else:
                            console.print(f"[yellow]No history entry found at index {index}[/yellow]")
                            continue
                    except ValueError:
                        console.print("[yellow]Invalid history index. Use ':load <number>'[/yellow]")
                        continue
                elif command == ":clear-history":
                    confirm = questionary.confirm(
                        "Are you sure you want to clear all history?",
                        default=False,
                    ).ask()
                    if confirm:
                        get_history().clear()
                        console.print("[green]✓[/green] History cleared")
                    continue
                else:
                    console.print(f"[yellow]Unknown command: {command}[/yellow]")
                    console.print("[dim]Available commands: :history, :load <number>, :clear-history[/dim]")
                    continue

            # Don't process empty prompts
            if not user_input:
                continue

            # Print the user's prompt with rich formatting
            console.print()
            console.print("👤 [bold]You:[/bold]")
            console.print(f"[dim]> {user_input}[/dim]")
            console.print()

            # Process the prompt with a loading spinner
            try:
                with console.status("[bold green]AI is thinking...", spinner="dots"):
                    result = process_prompt(
                        provider, user_input, args, debug_enabled, plain_mode, notify, app_config
                    )

                if result is None:
                    console.print("[yellow]No response generated[/yellow]\n")
                    continue

                # Extract the refined prompt from the result
                final_prompt, task_type = result

                # Render the response as Markdown
                console.print("🤖 [bold]AI:[/bold]")
                console.print(Markdown(final_prompt))
                console.print()

            except Exception as exc:
                sanitized = sanitize_error_message(str(exc))
                console.print(f"[bold red]Error: {sanitized}[/bold red]")
                if debug_enabled:
                    console.print_exception()
                logger.exception("Error processing prompt")

            prompt_count += 1

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Goodbye![/bold yellow]")
            break
        except Exception as exc:
            sanitized = sanitize_error_message(str(exc))
            console.print(f"[bold red]Error:[/bold red] {sanitized}\n")
            if debug_enabled:
                console.print_exception()
            logger.exception("Unexpected error in interactive mode")
            if use_prompt_toolkit:
                use_prompt_toolkit = False
                plain_mode = True
                session = None
            continue
