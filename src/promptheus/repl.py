from __future__ import annotations

import logging
from argparse import Namespace
from typing import Callable, Optional, Tuple

import questionary
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
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


class CommandCompleter(Completer):
    """
    Custom completer for slash commands.

    Shows completions when user types / with command descriptions.
    """

    def __init__(self):
        self.commands = {
            'history': 'View recent prompts',
            'clear-history': 'Clear all history',
            'load': 'Load a prompt by number (e.g., /load 5)',
            'help': 'Show available commands',
            'exit': 'Exit Promptheus',
            'quit': 'Exit Promptheus',
        }

    def get_completions(self, document: Document, complete_event):
        """Generate completions for the current document."""
        text = document.text_before_cursor

        # Only provide completions if text starts with /
        if not text.startswith('/'):
            return

        # Remove the leading /
        command_part = text[1:].lower()

        # Check if we're completing a command or its arguments
        parts = command_part.split(None, 1)

        if len(parts) <= 1:
            # Completing the command itself
            search_term = parts[0] if parts else ''
            for cmd, description in self.commands.items():
                if cmd.startswith(search_term):
                    yield Completion(
                        cmd,
                        start_position=-len(search_term),
                        display=cmd,
                        display_meta=description,
                    )
        elif len(parts) == 2 and parts[0] == 'load':
            # Completing /load with history indices
            # Show recent history entries
            try:
                history = get_history()
                recent = history.get_recent(20)
                for idx, entry in enumerate(recent, 1):
                    idx_str = str(idx)
                    if idx_str.startswith(parts[1]):
                        preview = entry.original_prompt[:50]
                        if len(entry.original_prompt) > 50:
                            preview += "..."
                        yield Completion(
                            idx_str,
                            start_position=-len(parts[1]),
                            display=f"{idx_str}",
                            display_meta=preview,
                        )
            except Exception:
                pass


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
    notify("[dim]Use '/load <number>' to load a prompt from history[/dim]")


def show_help(console: Console) -> None:
    """Display help information about available commands."""
    console.print()
    console.print("[bold cyan]Available Commands:[/bold cyan]")
    console.print()
    console.print("  [bold]/history[/bold]              View recent prompts")
    console.print("  [bold]/clear-history[/bold]        Clear all history")
    console.print("  [bold]/load <number>[/bold]        Load a prompt from history")
    console.print("  [bold]/help[/bold]                 Show this help message")
    console.print("  [bold]/exit[/bold] or [bold]/quit[/bold]       Exit Promptheus")
    console.print()
    console.print("[bold cyan]Key Bindings:[/bold cyan]")
    console.print()
    console.print("  [bold]Enter[/bold]                 Submit your prompt")
    console.print("  [bold]Alt+Enter[/bold]             Add a new line (multiline input)")
    console.print("  [bold]Ctrl+C[/bold]                Cancel or exit")
    console.print()
    console.print("[dim]Tip: Type / to see all available commands with Tab[/dim]")
    console.print()


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


def create_bottom_toolbar(provider: str, model: str) -> HTML:
    """
    Create the bottom toolbar with provider/model info and key bindings.

    Format: gemini | gemini-2.0 │ [Enter] submit │ [Alt+Enter] new line │ [/] commands
    """
    return HTML(
        f' <ansicyan>{provider}</ansicyan> | <ansicyan>{model}</ansicyan> │ '
        f'<b>[Enter]</b> submit │ <b>[Alt+Enter]</b> new line │ <b>[/]</b> commands'
    )


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
    - Bottom toolbar with provider/model info and key bindings
    - Multiline input support (Alt+Enter)
    - Rich markdown rendering for AI responses
    - Slash command completion (type / to see commands)
    - Enter to submit, Alt+Enter for new line
    """
    # Welcome message
    console.print("[bold cyan]Welcome to Promptheus![/bold cyan]")
    console.print("[dim]Interactive mode ready. Type / for commands.[/dim]\n")

    prompt_count = 1
    use_prompt_toolkit = not plain_mode

    # Get provider and model names for the toolbar
    provider_name = app_config.provider or "unknown"
    model_name = app_config.get_model() or "default"

    # Define the UI components for prompt_toolkit
    prompt_message = HTML('<b>&gt; </b>')

    # Create toolbar with provider/model info
    bottom_toolbar = create_bottom_toolbar(provider_name, model_name)

    style = Style.from_dict({
        'bottom-toolbar': 'bg:#2d2d2d #00ff00',  # Dark gray bg, bright green text
        'completion-menu': 'bg:#3d3d3d #ffffff',
        'completion-menu.completion': 'bg:#3d3d3d #ffffff',
        'completion-menu.completion.current': 'bg:#00ff00 #000000',
        'completion-menu.meta': 'bg:#3d3d3d #888888',
        'completion-menu.meta.current': 'bg:#00ff00 #000000',
    })

    # Create custom key bindings and completer
    bindings = create_key_bindings()
    completer = CommandCompleter()

    session: Optional[PromptSession] = None
    if use_prompt_toolkit:
        try:
            history_file = get_history().get_prompt_history_file()
            session = PromptSession(
                history=FileHistory(str(history_file)),
                multiline=True,
                prompt_continuation='… ',  # Continuation prompt for wrapped lines
                key_bindings=bindings,
                completer=completer,
                complete_while_typing=True,  # Show completions as you type
                enable_history_search=False,  # Disable Ctrl+R to avoid conflicts
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

            # Handle slash commands
            if user_input.startswith("/"):
                command_parts = user_input[1:].split(None, 1)
                if not command_parts:
                    show_help(console)
                    continue

                command = command_parts[0].lower()

                if command == "history":
                    display_history(console, notify)
                    continue
                elif command == "help":
                    show_help(console)
                    continue
                elif command in ("exit", "quit"):
                    console.print("[bold yellow]Goodbye![/bold yellow]")
                    break
                elif command == "load" and len(command_parts) > 1:
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
                        console.print("[yellow]Invalid history index. Use '/load <number>'[/yellow]")
                        continue
                elif command == "clear-history":
                    try:
                        confirm = questionary.confirm(
                            "Are you sure you want to clear all history?",
                            default=False,
                        ).ask()
                        if confirm:
                            get_history().clear()
                            console.print("[green]✓[/green] History cleared")
                    except KeyboardInterrupt:
                        console.print("[yellow]Cancelled[/yellow]")
                    continue
                else:
                    console.print(f"[yellow]Unknown command: /{command}[/yellow]")
                    console.print("[dim]Type /help to see available commands[/dim]")
                    continue

            # Don't process empty prompts
            if not user_input:
                continue

            # Process the prompt (no echo, no wrapper spinner)
            console.print()
            try:
                result = process_prompt(
                    provider, user_input, args, debug_enabled, plain_mode, notify, app_config
                )
            except KeyboardInterrupt:
                console.print("\n[yellow]Cancelled[/yellow]")
                console.print()
                continue
            except Exception as exc:
                sanitized = sanitize_error_message(str(exc))
                console.print(f"[bold red]✗ Error:[/bold red] {sanitized}")
                if debug_enabled:
                    console.print_exception()
                logger.exception("Error processing prompt")
                console.print()
                continue

            # Handle the result
            if result is None:
                console.print("[yellow]No response generated[/yellow]\n")
                continue

            # Extract the refined prompt from the result
            final_prompt, task_type = result

            # Render the response as Markdown
            console.print(Markdown(final_prompt))
            console.print()

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
