"""REPL command parsing and handling functionality."""

import logging
from argparse import Namespace
from typing import Callable, Optional

from prompt_toolkit.formatted_text import HTML

from promptheus.config import Config
from promptheus.constants import VERSION, GITHUB_REPO, GITHUB_ISSUES
from promptheus.providers import LLMProvider, get_provider
from promptheus.utils import sanitize_error_message

logger = logging.getLogger(__name__)

MessageSink = Callable[[str], None]


def create_command_registry():
    """Create a registry of command handlers for extensibility."""
    from .history_view import display_history
    from promptheus.utils import copy_to_clipboard
    from promptheus.history import get_history

    def handle_about(args_list, app_config, args, console, notify):
        show_about(console, app_config)
        return "handled"

    def handle_bug(args_list, app_config, args, console, notify):
        show_bug_report(console)
        return "handled"

    def handle_clear_history(args_list, app_config, args, console, notify):
        import questionary
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
        return "handled"

    def handle_copy(args_list, app_config, args, console, notify, last_result=None):
        if last_result:
            copy_to_clipboard(last_result, console, notify)
        else:
            console.print("[yellow]No result to copy yet. Process a prompt first.[/yellow]")
        return "handled"

    def handle_help(args_list, app_config, args, console, notify):
        show_help(console)
        return "handled"

    def handle_history(args_list, app_config, args, console, notify):
        display_history(console, notify)
        return "handled"

    def handle_load(args_list, app_config, args, console, notify):
        if len(args_list) > 0:
            try:
                index = int(args_list[0])
                entry = get_history().get_by_index(index)
                if entry:
                    console.print(f"[green]✓[/green] Loaded prompt #{index} from history:\n")
                    console.print(f"[cyan]{entry.original_prompt}[/cyan]\n")
                    return ("load_prompt", entry.original_prompt)
                else:
                    console.print(f"[yellow]No history entry found at index {index}[/yellow]")
                    return "handled"
            except ValueError:
                console.print("[yellow]Invalid history index. Use '/load <number>'[/yellow]")
                return "handled"
        else:
            console.print("[yellow]Specify which prompt to load. Showing history:[/yellow]\n")
            display_history(console, notify)
            return "handled"

    return {
        'about': handle_about,
        'bug': handle_bug,
        'clear-history': handle_clear_history,
        'copy': handle_copy,
        'help': handle_help,
        'history': handle_history,
        'load': handle_load,
    }


def show_help(console) -> None:
    """Display help information about available commands."""
    console.print()
    console.print("[bold cyan]Session Commands:[/bold cyan]")
    console.print()
    console.print("  [bold]/set model <name>[/bold]     Change model (e.g., /set model gpt-4)")
    console.print("  [bold]/set provider <name>[/bold]  Change AI provider (e.g., /set provider claude)")
    console.print("  [bold]/status[/bold]               Show current session settings")
    console.print("  [bold]/toggle skip-questions[/bold] Toggle skip-questions mode on/off")
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


def show_about(console, app_config: Config) -> None:
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


def show_bug_report(console) -> None:
    """Display bug report information and optionally open GitHub issues."""
    import webbrowser
    import questionary

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


def show_status(console, app_config: Config, args: Namespace) -> None:
    """Display current session settings."""
    console.print()
    console.print("[bold cyan]Current Session Settings:[/bold cyan]")
    console.print()
    console.print(f"  [bold]Provider:[/bold]      {app_config.provider or 'auto-detect'}")
    console.print(f"  [bold]Model:[/bold]         {app_config.get_model() or 'default'}")
    console.print()
    console.print("[bold cyan]Active Modes:[/bold cyan]")
    console.print()
    console.print(f"  [bold]Skip questions:[/bold] {'ON' if getattr(args, 'skip_questions', False) else 'OFF'}")
    console.print(f"  [bold]Refine mode:[/bold]    {'ON' if args.refine else 'OFF'}")
    console.print()

    configured = app_config.get_configured_providers()
    if configured:
        console.print(f"  [bold]Available providers:[/bold] {', '.join(configured)}")
        console.print()


def handle_session_command(
    command_str: str,
    app_config: Config,
    args: Namespace,
    console,
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
            notify("[yellow]Usage: /toggle refine or /toggle skip-questions[/yellow]")
            return "handled"

        mode = parts[1].lower()

        if mode == "refine":
            args.refine = not args.refine
            if args.refine:
                args.skip_questions = False  # Mutually exclusive
            status = "ON" if args.refine else "OFF"
            notify(f"[green]✓[/green] Refine mode is now {status}")
            return "handled"

        elif mode == "skip-questions":
            args.skip_questions = not args.skip_questions
            if args.skip_questions:
                args.refine = False  # Mutually exclusive
            status = "ON" if args.skip_questions else "OFF"
            notify(f"[green]✓[/green] Skip-questions mode is now {status}")
            return "handled"

        else:
            notify(f"[yellow]Unknown mode: {mode}. Use 'refine' or 'skip-questions'.[/yellow]")
            return "handled"

    elif command == "status":
        show_status(console, app_config, args)
        return "handled"

    else:
        # Not a session command, return None to let the existing handler deal with it
        return None


def reload_provider_instance(
    app_config: Config,
    console,
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
        with console.status(f"[bold blue]🚀 Initializing {provider_name}...", spinner="aesthetic"):
            new_provider = get_provider(provider_name, app_config, model_name)
        notify(f"[green]✓[/green] Successfully initialized {provider_name} with model {model_name}")
        return new_provider
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        notify(f"[red]✗[/red] Failed to initialize provider: {sanitized}")
        logger.exception("Provider reload failed")
        return None