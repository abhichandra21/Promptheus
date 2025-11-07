from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

PROVIDER_CHOICES = ["gemini", "anthropic", "openai", "groq", "qwen", "glm"]


def build_parser(include_history: bool = True) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promptheus - AI-powered prompt engineering CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  promptheus "Write a blog post"              # Single-shot mode (process and exit)
  promptheus                                   # Interactive mode (continuous loop)
  promptheus --list-models                     # List available models from configured providers
  promptheus --validate --test-connection      # Check environment and test API keys
  promptheus --template openai > .env         # Generate an environment file template
  promptheus history                          # View prompt history
""",
    )

    # Main prompt refinement arguments
    main_group = parser.add_argument_group("Main Prompting Arguments")
    if not include_history:
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
    behavior_group.add_argument(
        "--static",
        "--mvp",
        action="store_true",
        dest="static",
        help="Use static questions instead of dynamic AI-generated questions",
    )
    behavior_group.add_argument(
        "-q",
        "--quick",
        action="store_true",
        help="Skip all questions, run prompt directly (for analysis/research tasks)",
    )
    behavior_group.add_argument(
        "-r",
        "--refine",
        action="store_true",
        help="Force clarifying questions even for analysis tasks",
    )

    # Output handling arguments
    output_group = parser.add_argument_group("Output Handling")
    output_group.add_argument(
        "-c",
        "--copy",
        action="store_true",
        help="Copy the refined prompt to clipboard",
    )
    output_group.add_argument(
        "-e",
        "--edit",
        action="store_true",
        help="Open the refined prompt in your default editor",
    )

    # Utility commands that usually exit immediately
    utility_group = parser.add_argument_group("Utility Commands")
    utility_group.add_argument(
        "--list-models",
        action="store_true",
        help="List available models from configured providers and exit.",
    )
    utility_group.add_argument(
        "--validate",
        action="store_true",
        help="Validate environment configuration and exit.",
    )
    utility_group.add_argument(
        "--test-connection",
        action="store_true",
        help="Test API connection for configured providers (use with --validate).",
    )
    utility_group.add_argument(
        "--template",
        choices=PROVIDER_CHOICES,
        help="Generate a .env file template for a specific provider and exit.",
    )

    # General arguments
    general_group = parser.add_argument_group("General")
    general_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug output",
    )

    if include_history:
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        subparsers.required = False
        parser.set_defaults(command=None)
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

    return parser


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments while supporting both history command and standard prompts."""
    argv_list = list(sys.argv[1:] if argv is None else argv)

    if any(arg in {"-h", "--help"} for arg in argv_list):
        parser = build_parser(include_history=True)
        return parser.parse_args(argv_list)

    if argv_list and argv_list[0] == "history":
        parser = build_parser(include_history=True)
        args = parser.parse_args(argv_list)
        args.prompt = None
        return args

    parser = build_parser(include_history=False)
    return parser.parse_args(argv_list)
