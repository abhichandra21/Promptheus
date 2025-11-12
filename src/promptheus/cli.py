from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

PROVIDER_CHOICES = ["gemini", "anthropic", "openai", "groq", "qwen", "glm"]


def build_parser(include_subcommands: bool = True) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promptheus - AI-powered prompt engineering CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  promptheus "Write a blog post"                        # Single-shot mode (process and exit)
  promptheus                                             # Interactive mode (continuous loop)
  promptheus list-models --provider openai               # List available models from a specific provider
  promptheus validate --test-connection                  # Check environment and test API keys
  promptheus template openai,gemini                      # Generate env template for multiple providers
  promptheus --skip-questions "Explain Docker"          # Skip questions, improve prompt directly
  promptheus -o json "Create API schema"                # Output in JSON format
  promptheus history                                     # View prompt history

Interactive Mode Commands (available when running without arguments):
  /help           Show all interactive commands
  /set            Change provider or model
  /toggle         Toggle refine/skip-questions modes
  /status         Show current settings
  /history        View prompt history
  /load <n>       Load prompt by number
  /copy           Copy last result
  /about          Show version info
  /exit           Exit interactive mode
""",
    )

    # Main prompt refinement arguments
    main_group = parser.add_argument_group("Main Prompting Arguments")
    if not include_subcommands:
        parser.set_defaults(command=None)
        main_group.add_argument(
            "prompt",
            nargs="?",
            help="Initial prompt (optional, will ask if not provided). Use @filename to read from file.",
        )
    main_group.add_argument(
        "-f",
        "--file",
        type=str,
        help="Read prompt from file instead of command line",
    )
    main_group.add_argument(
        "--provider",
        choices=PROVIDER_CHOICES,
        help="LLM provider to use (overrides config)",
    )
    main_group.add_argument(
        "--model",
        help="Specific model to use (e.g., gemini-pro, claude-3-5-sonnet-20240620)",
    )

    # Behavior modification arguments
    behavior_group = parser.add_argument_group("Behavior Customization")
    mode_group = behavior_group.add_mutually_exclusive_group()
    mode_group.add_argument(
        "-s",
        "--skip-questions",
        action="store_true",
        help="Skip clarifying questions and improve prompt directly (basic analysis mode)",
    )
    mode_group.add_argument(
        "-r",
        "--refine",
        action="store_true",
        help="Force clarifying questions even for analysis tasks",
    )

    # Output handling arguments
    output_group = parser.add_argument_group("Output Handling")
    output_group.add_argument(
        "-o",
        "--output-format",
        choices=["plain", "json"],
        default="plain",
        help="Output format for the refined prompt (default: plain)",
    )
    output_group.add_argument(
        "-c",
        "--copy",
        action="store_true",
        help="Copy the refined prompt to clipboard",
    )

    # General arguments
    general_group = parser.add_argument_group("General")
    general_group.add_argument(
        "--version",
        action="store_true",
        help="Show version information and exit",
    )
    general_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug output",
    )

    if include_subcommands:
        subparsers = parser.add_subparsers(
            dest="command",
            title="commands",
            description="Available subcommands for managing Promptheus",
            metavar="COMMAND",
            help="Use 'promptheus COMMAND --help' for more info"
        )
        subparsers.required = False
        parser.set_defaults(command=None)

        # history subcommand
        history_parser = subparsers.add_parser(
            "history",
            help="View and manage prompt history",
            description="View and manage prompt history",
        )
        history_parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all history",
        )
        history_parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Number of history entries to display (default: 20)",
        )

        # list-models subcommand
        list_models_parser = subparsers.add_parser(
            "list-models",
            help="List available models from providers",
            description="List available models from configured providers.",
        )
        list_models_parser.add_argument(
            "--providers",
            type=str,
            help="Optional: Comma-separated list of providers to query",
        )
        list_models_parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Number of models to display (default: 20, use 0 for all)",
        )
        list_models_parser.add_argument(
            "--include-nontext",
            action="store_true",
            help="Include non-text models (e.g., for vision, embedding) in the list",
        )

        # validate subcommand
        validate_parser = subparsers.add_parser(
            "validate",
            help="Validate environment configuration",
            description="Validate environment configuration and optionally test API connections.",
        )
        validate_parser.add_argument(
            "--test-connection",
            action="store_true",
            help="Test API connection for configured providers.",
        )
        validate_parser.add_argument(
            "--providers",
            type=str,
            help="Optional: Comma-separated list of providers to validate (e.g., openai,gemini)",
        )

        # template subcommand
        template_parser = subparsers.add_parser(
            "template",
            help="Generate a .env file template",
            description="Generate a .env file template for one or more providers.",
        )
        template_parser.add_argument(
            "--providers",
            type=str,
            required=True,
            help="Comma-separated list of providers (e.g., openai,gemini)",
        )

        # completion subcommand
        completion_parser = subparsers.add_parser(
            "completion",
            help="Generate shell completion script",
            description="Generate shell completion script for bash or zsh",
        )
        completion_parser.add_argument(
            "shell",
            nargs="?",
            choices=["bash", "zsh"],
            help="Shell type (bash or zsh, auto-detected if not specified)",
        )
        completion_parser.add_argument(
            "--install",
            action="store_true",
            help="Automatically install completion by updating shell config",
        )
        # verbose flag will be added by the loop below

        # __complete subcommand (hidden, for internal use)
        complete_parser = subparsers.add_parser(
            "__complete",
            help=argparse.SUPPRESS,  # Hide from help
            description=argparse.SUPPRESS,
            add_help=False,  # Don't add help to hidden command
        )
        complete_parser.add_argument(
            "type",
            choices=["providers", "models"],
            help=argparse.SUPPRESS,
        )
        complete_parser.add_argument(
            "--provider",
            help=argparse.SUPPRESS,
        )
        complete_parser.add_argument(
            "-v", "--verbose", action="store_true", help=argparse.SUPPRESS
        )

        # Add verbose and version flags to all subcommands for convenience
        for sub in [history_parser, list_models_parser, validate_parser, template_parser, completion_parser]:
            sub.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug output")
            sub.add_argument("--version", action="store_true", help="Show version information and exit")

    return parser


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments, building the correct parser for the context."""
    argv_list = sys.argv[1:] if argv is None else list(argv)

    known_subcommands = {"history", "list-models", "validate", "template", "completion", "__complete"}
    
    # If no args, or the first arg is a known subcommand or help, use the full parser.
    if not argv_list or argv_list[0] in known_subcommands or any(arg in {"-h", "--help"} for arg in argv_list):
        parser = build_parser(include_subcommands=True)
        args = parser.parse_args(argv_list)
        # The subcommand parser doesn't have a `prompt` positional argument.
        # We need to ensure the attribute exists for the main logic.
        if not hasattr(args, "prompt"):
            setattr(args, "prompt", None)
        return args

    # Otherwise, assume we are in prompting mode. Build the simpler parser.
    parser = build_parser(include_subcommands=False)
    return parser.parse_args(argv_list)
