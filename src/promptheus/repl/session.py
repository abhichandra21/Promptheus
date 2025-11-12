"""Main REPL session functionality."""

import logging
import time
from argparse import Namespace
from typing import Callable, Optional, Tuple

import questionary
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

from promptheus.config import Config
from promptheus.constants import VERSION
from promptheus.history import get_history
from promptheus.io_context import IOContext
from promptheus.providers import LLMProvider
from promptheus.utils import sanitize_error_message, copy_to_clipboard
from promptheus.exceptions import PromptCancelled

from .commands import (
    show_help,
    show_about,
    show_bug_report,
    show_status,
    handle_session_command,
    reload_provider_instance,
)
from .completer import CommandCompleter
from .history_view import display_history

logger = logging.getLogger(__name__)

MessageSink = Callable[[str], None]
ProcessPromptFn = Callable[
    [LLMProvider, str, Namespace, bool, bool, IOContext, Config],
    Optional[Tuple[str, str]],
]


SHIFT_ENTER_SEQUENCES = {
    "\x1b[27;2;13~",  # Xterm modifyOtherKeys format
    "\x1b[13;2~",     # Some terminals (CSI 13;2~)
    "\x1b[13;2u",     # Kitty/WezTerm CSI-u format
}


def create_key_bindings() -> KeyBindings:
    """
    Create custom key bindings for the prompt.

    - Enter: Submit the prompt
    - Shift+Enter: Add a new line (fallback to Option/Alt+Enter on some terminals)
    """
    kb = KeyBindings()

    @kb.add('enter')
    def _(event):
        """Submit on Enter, unless Shift-modified sequences are detected."""
        data = event.key_sequence[-1].data or ""
        if data in SHIFT_ENTER_SEQUENCES:
            event.current_buffer.insert_text('\n')
        else:
            event.current_buffer.validate_and_handle()

    @kb.add('escape', 'enter', eager=True)  # Option/Alt+Enter fallback
    def _(event):
        """Insert newline on Option/Alt+Enter."""
        event.current_buffer.insert_text('\n')

    @kb.add('c-j', eager=True)  # Ctrl+J is another common newline combo
    def _(event):
        """Insert newline on Ctrl+J."""
        event.current_buffer.insert_text('\n')

    return kb


def format_toolbar_text(provider: str, model: str) -> Text:
    """
    Return a plain-text version of the toolbar so we can print it into the scrollback.
    """
    text = Text(f"{provider} | {model} │ [Enter] submit │ [Shift+Enter] new line │ [/] commands")
    text.stylize("dim")
    return text


def create_bottom_toolbar(provider: str, model: str) -> HTML:
    """
    Create the bottom toolbar with provider/model info and key bindings.
    """
    return HTML(
        f' {provider} | {model} │ '
        f'<b>[Enter]</b> submit │ <b>[Shift+Enter]</b> new line │ <b>[/]</b> commands'
    )


def display_clean_header(console, app_config: Config, args: Namespace) -> None:
    """Display a clean, minimal header similar to OpenAI Codex."""
    provider_name = app_config.provider or "auto"
    model_name = app_config.get_model() or "default"
    skip_qs_status = "ON" if getattr(args, 'skip_questions', False) else "OFF"

    # Fixed width for perfect alignment (matching OpenAI Codex style)
    box_width = 48

    # Create perfectly aligned header lines
    line1 = f" >_ Promptheus (v{VERSION})"
    line2 = ""
    line3 = f" model:     {model_name.ljust(17)} /model to change"
    line4 = f" provider:  {provider_name.ljust(17)} /provider"
    line5 = f" skip Qs:   {skip_qs_status.ljust(17)} /toggle"

    # Pad each line to exact box width
    header_lines = [
        line1.ljust(box_width),
        line2.ljust(box_width),
        line3.ljust(box_width),
        line4.ljust(box_width),
        line5.ljust(box_width),
    ]

    # Print the top of the box
    console.print("╭" + "─" * box_width + "╮")

    # Print each line inside the box
    for line in header_lines:
        console.print(f"│{line}│")

    # Print the bottom of the box
    console.print("╰" + "─" * box_width + "╯")

    # Print the getting started text
    console.print()
    console.print("To get started, provide a prompt or try one of these commands:")
    console.print("/help - show available commands")
    console.print("/status - show current session")
    console.print("/set - change provider or model")
    console.print("/toggle - toggle refine or skip-questions mode")
    console.print("/copy - copy last result to clipboard")
    console.print("/history - view prompt history")
    console.print("/load <n> - load prompt by number")
    console.print()


def interactive_mode(
    provider: LLMProvider,
    app_config: Config,
    args: Namespace,
    debug_enabled: bool,
    plain_mode: bool,
    io: IOContext,
    process_prompt: ProcessPromptFn,
) -> None:
    """
    Interactive REPL mode with rich inline prompt.

    Features:
    - Status banner printed above the prompt with provider/model info
    - Multiline input support (Shift+Enter, Option/Alt+Enter fallback)
    - Rich markdown rendering for AI responses
    - Slash command completion (type / to see commands)
    - Enter to submit, Shift+Enter for new line
    - In-session commands to change provider, model, and modes
    """
    # Should not enter interactive mode in quiet mode (guarded in main.py)
    if io.quiet_output:
        io.console_err.print("[red]✗[/red] Cannot enter interactive mode in quiet mode")
        return

    console = io.console_err
    notify = io.notify

    # Display clean header
    display_clean_header(console, app_config, args)

    prompt_count = 1
    last_ctrl_c_time = [0.0]  # Track time of last Ctrl+C for graceful exit
    use_prompt_toolkit = not plain_mode
    last_result: Optional[str] = None  # Track last refined prompt for /copy

    transient_toolbar_message: Optional[str] = None
    show_transient_message_for_next_prompt: bool = False
    consecutive_ctrl_c = 0  # Track consecutive Ctrl+C presses

    # Track current provider (may be reloaded during session)
    current_provider = provider

    prompt_message = HTML('<b>&gt; </b>')

    # Neutral, subtle styling - black text on gray background
    style = Style.from_dict({
        'bottom-toolbar': 'bg:#808080 #000000',
        'completion-menu': 'bg:#404040 #ffffff',
        'completion-menu.completion': 'bg:#404040 #ffffff',
        'completion-menu.completion.current': 'bg:#606060 #ffffff bold',
        'completion-menu.meta': 'bg:#404040 #888888',
        'completion-menu.meta.current': 'bg:#606060 #ffffff',
    })

    # Create custom key bindings and completer
    bindings = create_key_bindings()
    completer = CommandCompleter()

    session: Optional[PromptSession] = None
    if use_prompt_toolkit:
        try:
            # Only enable file-based history if history is enabled in config
            if app_config.history_enabled:
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
            else:
                # History disabled: no FileHistory, no disk persistence
                session = PromptSession(
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
            # Update toolbar with current provider/model info
            provider_name = app_config.provider or "unknown"
            model_name = app_config.get_model() or "default"

            if show_transient_message_for_next_prompt and transient_toolbar_message:
                current_toolbar_text = Text(transient_toolbar_message)
                current_toolbar_text.stylize("bold yellow")
                current_bottom_toolbar = HTML(f'<b><span style="color:yellow">{transient_toolbar_message}</span></b>')
                show_transient_message_for_next_prompt = False # Reset for next prompt
                transient_toolbar_message = None # Clear message
            else:
                current_toolbar_text = format_toolbar_text(provider_name, model_name)
                current_bottom_toolbar = create_bottom_toolbar(provider_name, model_name)

            if use_prompt_toolkit and session:
                try:
                    user_input = session.prompt(
                        prompt_message,
                        bottom_toolbar=current_bottom_toolbar,
                        style=style,
                    ).strip()
                except KeyboardInterrupt:
                    now = time.time()
                    if now - last_ctrl_c_time[0] < 1.5:
                        console.print("\n[yellow]Exiting.[/yellow]")
                        break
                    else:
                        transient_toolbar_message = "Press Ctrl+C again to exit."
                        show_transient_message_for_next_prompt = True
                        last_ctrl_c_time[0] = now
                        continue
                except EOFError:
                    # Ctrl+D should exit completely
                    console.print("\n[bold yellow]Goodbye![/bold yellow]")
                    break
                except (OSError, RuntimeError) as exc:
                    # Fall back to plain mode on terminal errors (resize, etc.)
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
                    console.print(current_toolbar_text)
                    user_input = input(f"promptheus [{prompt_count}]> ").strip()
                    # Reset consecutive Ctrl+C counter on successful input
                    consecutive_ctrl_c = 0
                except KeyboardInterrupt:
                    # Ctrl+C: increment counter
                    consecutive_ctrl_c += 1
                    if consecutive_ctrl_c >= 2:
                        # Two consecutive Ctrl+C presses -> exit
                        console.print("\n[bold yellow]Goodbye![/bold yellow]")
                        break
                    else:
                        # First Ctrl+C -> cancel and continue
                        console.print("\n[dim]Cancelled (press Ctrl+C again to exit)[/dim]")
                        continue
                except EOFError:
                    console.print("\n[bold yellow]Goodbye![/bold yellow]")
                    break

            # Handle exit commands
            if user_input.lower() in {"exit", "quit", "q"}:
                console.print("[bold yellow]Goodbye![/bold yellow]")
                break

            # Handle slash commands
            if user_input.startswith("/"):
                # Reset Ctrl+C counter when handling commands
                consecutive_ctrl_c = 0

                # First check if it's a session command (/set, /toggle, /status)
                reload_signal = handle_session_command(user_input, app_config, args, console, notify)

                if reload_signal == "reload_provider":
                    # Provider or model changed, reload the provider instance
                    new_provider = reload_provider_instance(app_config, console, notify)
                    if new_provider:
                        current_provider = new_provider
                        # Update toolbar with new provider/model info
                        provider_name = app_config.provider or "unknown"
                        model_name = app_config.get_model() or "default"

                    else:
                        notify("[yellow]Continuing with previous provider[/yellow]")
                    continue

                # If it was a session command (handled or reload_provider), don't fall through
                if reload_signal in ("handled", "reload_provider"):
                    continue

                # Otherwise, handle other slash commands
                command_parts = user_input[1:].split(None, 1)
                if not command_parts:
                    show_help(console)
                    continue

                command = command_parts[0].lower()

                if command == "about":
                    show_about(console, app_config)
                    continue
                elif command == "bug":
                    show_bug_report(console)
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
                elif command == "copy":
                    if last_result:
                        copy_to_clipboard(last_result, console, notify)
                    else:
                        console.print("[yellow]No result to copy yet. Process a prompt first.[/yellow]")
                    continue
                elif command in ("exit", "quit"):
                    console.print("[bold yellow]Goodbye![/bold yellow]")
                    break
                elif command == "help":
                    show_help(console)
                    continue
                elif command == "history":
                    display_history(console, notify)
                    continue
                elif command == "load":
                    if len(command_parts) > 1:
                        # Has an argument - try to load that specific entry
                        try:
                            index = int(command_parts[1])
                            entry = get_history().get_by_index(index)
                            if entry:
                                console.print(f"[green]✓[/green] Loaded prompt #{index} from history:\n")
                                console.print(f"[cyan]{entry.original_prompt}[/cyan]\n")

                                # Ask for confirmation
                                try:
                                    confirm = questionary.confirm(
                                        "Proceed with this prompt?",
                                        default=True,
                                    ).ask()
                                    if confirm:
                                        user_input = entry.original_prompt
                                    else:
                                        console.print("[yellow]Cancelled[/yellow]")
                                        continue
                                except KeyboardInterrupt:
                                    console.print("[yellow]Cancelled[/yellow]")
                                    continue
                            else:
                                console.print(f"[yellow]No history entry found at index {index}[/yellow]")
                                continue
                        except ValueError:
                            console.print("[yellow]Invalid history index. Use '/load <number>'[/yellow]")
                            continue
                    else:
                        # No argument - show history to help them choose
                        console.print("[yellow]Specify which prompt to load. Showing history:[/yellow]\n")
                        display_history(console, notify)
                        continue
                else:
                    console.print(f"[yellow]Unknown command: /{command}[/yellow]")
                    console.print("[dim]Type /help to see available commands[/dim]")
                    continue

            # Don't process empty prompts
            if not user_input:
                continue

            # Reset Ctrl+C counter when starting to process a prompt
            consecutive_ctrl_c = 0

            # Process the prompt (no echo, no wrapper spinner)
            console.print()
            try:
                result = process_prompt(
                    current_provider, user_input, args, debug_enabled, plain_mode, io, app_config
                )
            except PromptCancelled as cancel_exc:
                console.print(f"\n[yellow]{cancel_exc}[/yellow]")
                console.print()
                continue
            except KeyboardInterrupt:
                # Ctrl+C during processing - just cancel and continue
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

            # Extract refined prompt from the result
            final_prompt, task_type = result

            # Store result for /copy command
            last_result = final_prompt

            # Render response as Markdown
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
                # Try to recover by falling back to plain mode
                use_prompt_toolkit = False
                plain_mode = True
                session = None
                continue
            else:
                # Already in plain mode, can't recover
                console.print("\n[bold yellow]Goodbye![/bold yellow]")
                break