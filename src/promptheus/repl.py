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
import time
from rich.text import Text

import pyperclip

from promptheus.config import Config
from promptheus.constants import VERSION, GITHUB_REPO, GITHUB_ISSUES
from promptheus.history import get_history
from promptheus.providers import LLMProvider, get_provider
from promptheus.utils import sanitize_error_message
from promptheus.exceptions import PromptCancelled

MessageSink = Callable[[str], None]
ProcessPromptFn = Callable[
    [LLMProvider, str, Namespace, bool, bool, MessageSink, Config, bool, Optional[Console], Optional[Console]],
    Optional[Tuple[str, str]],
]

logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str, console: Console) -> None:
    """Copy text to clipboard."""
    try:
        pyperclip.copy(text)
        console.print("[green]✓[/green] Copied to clipboard!")
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        console.print(f"[yellow]Warning: Failed to copy to clipboard: {sanitized}[/yellow]")
        logger.exception("Clipboard copy failed")


class CommandCompleter(Completer):
    """
    Custom completer for slash commands.

    Shows completions when user types / with command descriptions.
    """

    def __init__(self):
        self.commands = {
            'about': 'Show version info',
            'bug': 'Submit a bug report',
            'clear-history': 'Clear all history',
            'copy': 'Copy the last result to clipboard',
            'exit': 'Exit Promptheus',
            'help': 'Show available commands',
            'history': 'View recent prompts',
            'load': 'Load a prompt by number (e.g., /load 5)',
            'quit': 'Exit Promptheus',
            'set': 'Change provider or model (e.g., /set provider claude)',
            'status': 'Show current session settings',
            'toggle': 'Toggle refine or quick mode (e.g., /toggle refine)',
        }

    def get_completions(self, document: Document, complete_event):
        """Generate completions for the current document."""
        text = document.text_before_cursor

        # Only provide completions if text starts with /
        if not text.startswith('/'):
            return

        # Remove the leading /
        command_part = text[1:]

        # Split into parts, preserving empty strings
        parts = command_part.split()

        # Determine if we have a trailing space (indicates moving to next argument)
        has_trailing_space = command_part.endswith(' ') and command_part.strip()

        if not parts:
            # Just "/" typed, show all commands
            for cmd, description in self.commands.items():
                yield Completion(
                    cmd,
                    start_position=0,
                    display=cmd,
                    display_meta=description,
                )
            return

        command = parts[0].lower()

        if len(parts) == 1 and not has_trailing_space:
            # Completing the command itself
            search_term = command
            for cmd, description in self.commands.items():
                if cmd.startswith(search_term):
                    yield Completion(
                        cmd,
                        start_position=-len(search_term),
                        display=cmd,
                        display_meta=description,
                    )
        elif (len(parts) == 2 and has_trailing_space and command == 'set' and parts[1] == 'provider') or \
             (len(parts) == 3 and command == 'set' and parts[1] == 'provider'):
            # Completing /set provider with available providers (must check before general case)
            try:
                from promptheus.config import Config
                config = Config()
                providers = config.get_configured_providers()
                search_term = parts[2] if len(parts) == 3 else ''
                for provider in providers:
                    if provider.startswith(search_term):
                        yield Completion(
                            provider,
                            start_position=-len(search_term),
                            display=provider,
                            display_meta=f'Switch to {provider}',
                        )
            except Exception:
                pass

        elif (len(parts) == 1 and has_trailing_space) or len(parts) == 2:
            # Completing first argument after command
            search_term = parts[1] if len(parts) == 2 else ''

            if command == 'load':
                # Completing /load with history indices
                try:
                    history = get_history()
                    recent = history.get_recent(20)
                    for idx, entry in enumerate(recent, 1):
                        idx_str = str(idx)
                        if idx_str.startswith(search_term):
                            preview = entry.original_prompt[:50]
                            if len(entry.original_prompt) > 50:
                                preview += "..."
                            yield Completion(
                                idx_str,
                                start_position=-len(search_term),
                                display=f"{idx_str}",
                                display_meta=preview,
                            )
                except Exception:
                    pass

            elif command == 'set':
                # Completing /set with 'provider' or 'model'
                subcommands = {
                    'provider': 'Change the AI provider',
                    'model': 'Change the model',
                }
                for subcmd, desc in subcommands.items():
                    if subcmd.startswith(search_term):
                        yield Completion(
                            subcmd,
                            start_position=-len(search_term),
                            display=subcmd,
                            display_meta=desc,
                        )

            elif command == 'toggle':
                # Completing /toggle with 'refine' or 'quick'
                subcommands = {
                    'refine': 'Toggle refine mode on/off',
                    'quick': 'Toggle quick mode on/off',
                }
                for subcmd, desc in subcommands.items():
                    if subcmd.startswith(search_term):
                        yield Completion(
                            subcmd,
                            start_position=-len(search_term),
                            display=subcmd,
                            display_meta=desc,
                        )


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
    console.print("[bold cyan]Session Commands:[/bold cyan]")
    console.print()
    console.print("  [bold]/set model <name>[/bold]     Change model (e.g., /set model gpt-4)")
    console.print("  [bold]/set provider <name>[/bold]  Change AI provider (e.g., /set provider claude)")
    console.print("  [bold]/status[/bold]               Show current session settings")
    console.print("  [bold]/toggle quick[/bold]         Toggle quick mode on/off")
    console.print("  [bold]/toggle refine[/bold]        Toggle refine mode on/off")
    console.print()
    console.print("[bold cyan]Other Commands:[/bold cyan]")
    console.print()
    console.print("  [bold]/about[/bold]                Show version info")
    console.print("  [bold]/bug[/bold]                  Submit a bug report")
    console.print("  [bold]/clear-history[/bold]        Clear all history")
    console.print("  [bold]/copy[/bold]                 Copy the last result to clipboard")
    console.print("  [bold]/exit[/bold] or [bold]/quit[/bold]       Exit Promptheus")
    console.print("  [bold]/help[/bold]                 Show this help message")
    console.print("  [bold]/history[/bold]              View recent prompts")
    console.print("  [bold]/load <number>[/bold]        Load a prompt from history")
    console.print()
    console.print("[bold cyan]Key Bindings:[/bold cyan]")
    console.print()
    console.print("  [bold]Enter[/bold]                 Submit your prompt")
    console.print("  [bold]Shift+Enter[/bold]           Add a new line (multiline input)")
    console.print("  [bold]Option/Alt+Enter[/bold]      Alternate shortcut for new line")
    console.print("  [bold]Ctrl+C[/bold]                Cancel input (press twice to exit)")
    console.print("  [bold]Ctrl+D[/bold]                Exit Promptheus")
    console.print()
    console.print("[dim]Tip: Type / then Tab to see all available commands[/dim]")
    console.print()


def show_about(console: Console, app_config: Config) -> None:
    """Display version and system information."""
    import platform
    import sys

    console.print()
    console.print("[bold cyan]Promptheus - AI-powered Prompt Engineering[/bold cyan]")
    console.print()
    console.print(f"  [bold]Version:[/bold]       {VERSION}")
    console.print(f"  [bold]GitHub:[/bold]        {GITHUB_REPO}")
    console.print()
    console.print("[bold cyan]System Information:[/bold cyan]")
    console.print()
    console.print(f"  [bold]Python:[/bold]        {sys.version.split()[0]}")
    console.print(f"  [bold]Platform:[/bold]      {platform.system()} {platform.release()}")
    console.print()
    console.print("[bold cyan]Current Configuration:[/bold cyan]")
    console.print()
    console.print(f"  [bold]Provider:[/bold]      {app_config.provider or 'auto-detect'}")
    console.print(f"  [bold]Model:[/bold]         {app_config.get_model() or 'default'}")

    configured = app_config.get_configured_providers()
    if configured:
        console.print(f"  [bold]Available:[/bold]     {', '.join(configured)}")
    console.print()


def show_bug_report(console: Console) -> None:
    """Display bug report information and optionally open GitHub issues."""
    import webbrowser

    console.print()
    console.print("[bold cyan]Bug Report[/bold cyan]")
    console.print()
    console.print("Found a bug? We'd love to hear about it!")
    console.print()
    console.print(f"  [bold]Report issues at:[/bold] {GITHUB_ISSUES}")
    console.print()

    try:
        open_browser = questionary.confirm(
            "Open GitHub issues in your browser?",
            default=True,
        ).ask()

        if open_browser:
            webbrowser.open(GITHUB_ISSUES)
            console.print("[green]✓[/green] Opened in browser")
        else:
            console.print("[yellow]Cancelled[/yellow]")
    except KeyboardInterrupt:
        console.print("[yellow]Cancelled[/yellow]")

    console.print()


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


def show_status(console: Console, app_config: Config, args: Namespace) -> None:
    """Display current session settings."""
    console.print()
    console.print("[bold cyan]Current Session Settings:[/bold cyan]")
    console.print()
    console.print(f"  [bold]Provider:[/bold]      {app_config.provider or 'auto-detect'}")
    console.print(f"  [bold]Model:[/bold]         {app_config.get_model() or 'default'}")
    console.print()
    console.print("[bold cyan]Active Modes:[/bold cyan]")
    console.print()
    console.print(f"  [bold]Quick mode:[/bold]    {'ON' if args.quick else 'OFF'}")
    console.print(f"  [bold]Refine mode:[/bold]   {'ON' if args.refine else 'OFF'}")
    console.print(f"  [bold]Static mode:[/bold]   {'ON' if args.static else 'OFF'}")
    console.print()

    configured = app_config.get_configured_providers()
    if configured:
        console.print(f"  [bold]Available providers:[/bold] {', '.join(configured)}")
        console.print()


def handle_repl_command(
    command_str: str,
    app_config: Config,
    args: Namespace,
    console: Console,
    notify: MessageSink,
) -> Optional[str]:
    """
    Handle in-session commands like /set, /toggle, /status.

    Returns:
        'reload_provider' if the provider needs to be reloaded,
        'handled' if the command was handled but doesn't need reload,
        None if this is not a session command
    """
    parts = command_str.strip().split()
    if not parts:
        return None

    command = parts[0][1:].lower()  # Remove the '/' and normalize

    if command == "set":
        if len(parts) < 3:
            notify("[yellow]Usage: /set provider <name> or /set model <name>[/yellow]")
            return "handled"

        setting = parts[1].lower()
        value = parts[2]

        if setting == "provider":
            configured = app_config.get_configured_providers()
            if value not in configured:
                notify(f"[red]✗[/red] Provider '{value}' is not configured or available")
                notify(f"[dim]Available providers: {', '.join(configured)}[/dim]")
                return "handled"

            app_config.set_provider(value)
            notify(f"[green]✓[/green] Provider set to '{value}'")
            return "reload_provider"

        elif setting == "model":
            app_config.set_model(value)
            notify(f"[green]✓[/green] Model set to '{value}'")
            return "reload_provider"

        else:
            notify(f"[yellow]Unknown setting: {setting}. Use 'provider' or 'model'.[/yellow]")
            return "handled"

    elif command == "toggle":
        if len(parts) < 2:
            notify("[yellow]Usage: /toggle refine or /toggle quick[/yellow]")
            return "handled"

        mode = parts[1].lower()

        if mode == "refine":
            args.refine = not args.refine
            if args.refine:
                args.quick = False  # Mutually exclusive
            status = "ON" if args.refine else "OFF"
            notify(f"[green]✓[/green] Refine mode is now {status}")
            return "handled"

        elif mode == "quick":
            args.quick = not args.quick
            if args.quick:
                args.refine = False  # Mutually exclusive
            status = "ON" if args.quick else "OFF"
            notify(f"[green]✓[/green] Quick mode is now {status}")
            return "handled"

        else:
            notify(f"[yellow]Unknown mode: {mode}. Use 'refine' or 'quick'.[/yellow]")
            return "handled"

    elif command == "status":
        show_status(console, app_config, args)
        return "handled"

    else:
        # Not a session command, return None to let the existing handler deal with it
        return None


def reload_provider_instance(
    app_config: Config,
    console: Console,
    notify: MessageSink,
) -> Optional[LLMProvider]:
    """
    Reload the provider instance based on current config.

    Returns:
        New provider instance, or None if initialization failed
    """
    provider_name = app_config.provider or "gemini"
    model_name = app_config.get_model()

    try:
        with console.status(f"[bold blue]Initializing {provider_name}...", spinner="dots"):
            new_provider = get_provider(provider_name, app_config, model_name)
        notify(f"[green]✓[/green] Successfully initialized {provider_name} with model {model_name}")
        return new_provider
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        notify(f"[red]✗[/red] Failed to initialize provider: {sanitized}")
        logger.exception("Provider reload failed")
        return None


def interactive_mode(
    provider: LLMProvider,
    app_config: Config,
    args: Namespace,
    debug_enabled: bool,
    plain_mode: bool,
    notify: MessageSink,
    console: Console,
    process_prompt: ProcessPromptFn,
    quiet_output: bool = False,
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
    if quiet_output:
        console.print("[red]✗[/red] Cannot enter interactive mode in quiet mode")
        return

    # Welcome message
    console.print("[bold cyan]Welcome to Promptheus![/bold cyan]")
    console.print("[dim]Interactive mode ready. Type / for commands.[/dim]\n")

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
                reload_signal = handle_repl_command(user_input, app_config, args, console, notify)

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
                        copy_to_clipboard(last_result, console)
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
                    current_provider, user_input, args, debug_enabled, plain_mode, notify, app_config, False, None, console
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

            # Extract the refined prompt from the result
            final_prompt, task_type = result

            # Store the result for /copy command
            last_result = final_prompt

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
                # Try to recover by falling back to plain mode
                use_prompt_toolkit = False
                plain_mode = True
                session = None
                continue
            else:
                # Already in plain mode, can't recover
                console.print("\n[bold yellow]Goodbye![/bold yellow]")
                break
