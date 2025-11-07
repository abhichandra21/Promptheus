from __future__ import annotations

import logging
from argparse import Namespace
from typing import Callable, Optional, Tuple

import questionary
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
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
    """Interactive REPL mode - continuously process prompts until user types exit/quit."""
    notify("[bold cyan]Welcome to Promptheus Interactive Mode![/bold cyan]")
    notify(f"[dim]Using provider: {app_config.provider} | Model: {app_config.get_model()}[/dim]")
    notify("[dim]Type 'exit' or 'quit' to exit, ':history' to view history[/dim]\n")

    prompt_count = 1
    use_prompt_toolkit = not plain_mode

    session: Optional[PromptSession] = None
    if use_prompt_toolkit:
        try:
            history_file = get_history().get_prompt_history_file()
            session = PromptSession(history=FileHistory(str(history_file)))
        except Exception as exc:
            logger.warning("Failed to initialize history: %s", sanitize_error_message(str(exc)))
            use_prompt_toolkit = False
            plain_mode = True

    while True:
        try:
            if use_prompt_toolkit and session:
                try:
                    user_input = session.prompt(f"promptheus [{prompt_count}]> ").strip()
                except KeyboardInterrupt:
                    notify("\n[yellow]Exiting...[/yellow]")
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
                except EOFError:
                    notify("\n[yellow]Exiting...[/yellow]")
                    break

            if user_input.lower() in {"exit", "quit", "q"}:
                notify("[green]Goodbye![/green]")
                break

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
                            notify(f"[green]✓[/green] Loaded prompt #{index} from history")
                            user_input = entry.original_prompt
                        else:
                            notify(f"[yellow]No history entry found at index {index}[/yellow]")
                            continue
                    except ValueError:
                        notify("[yellow]Invalid history index. Use ':load <number>'[/yellow]")
                        continue
                elif command == ":clear-history":
                    confirm = questionary.confirm(
                        "Are you sure you want to clear all history?",
                        default=False,
                    ).ask()
                    if confirm:
                        get_history().clear()
                        notify("[green]✓[/green] History cleared")
                    continue
                else:
                    notify(f"[yellow]Unknown command: {command}[/yellow]")
                    notify("[dim]Available commands: :history, :load <number>, :clear-history[/dim]")
                    continue

            if not user_input:
                continue

            notify("")
            result = process_prompt(provider, user_input, args, debug_enabled, plain_mode, notify, app_config)

            if result is None:
                notify("")
                continue

            prompt_count += 1
            notify("")

        except KeyboardInterrupt:
            notify("\n[yellow]Exiting...[/yellow]")
            break
        except Exception as exc:
            sanitized = sanitize_error_message(str(exc))
            notify(f"[bold red]Error:[/bold red] {sanitized}\n")
            if debug_enabled:
                console.print_exception()
            logger.exception("Unexpected error in interactive mode")
            if use_prompt_toolkit:
                use_prompt_toolkit = False
                plain_mode = True
                session = None
            continue
