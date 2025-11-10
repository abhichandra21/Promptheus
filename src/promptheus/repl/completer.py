"""Command completion functionality for the REPL."""

from typing import Dict

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from promptheus.config import Config
from promptheus.history import get_history


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
            'toggle': 'Toggle refine or skip-questions mode (e.g., /toggle refine)',
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
                # Completing /toggle with 'refine' or 'skip-questions'
                subcommands = {
                    'refine': 'Toggle refine mode on/off',
                    'skip-questions': 'Toggle skip-questions mode on/off',
                }
                for subcmd, desc in subcommands.items():
                    if subcmd.startswith(search_term):
                        yield Completion(
                            subcmd,
                            start_position=-len(search_term),
                            display=subcmd,
                            display_meta=desc,
                        )