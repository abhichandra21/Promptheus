from __future__ import annotations

import argparse
from typing import List, Optional

PROVIDER_CHOICES = ["gemini", "anthropic", "openai", "groq", "qwen", "glm"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promptheus - AI-powered prompt engineering CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  promptheus "Write a blog post"              # Single-shot mode (process and exit)
  promptheus                                   # Interactive mode (continuous loop)
  promptheus "Explore this codebase"          # Auto-detects analysis task, skips questions
  promptheus -q "Analyze data.csv"            # Quick mode, always skips questions
  promptheus -r "Explore code"                # Force questions even for analysis
  promptheus --static "My prompt"             # Use static MVP questions
  promptheus -f prompt.txt                    # Read prompt from file (single-shot)
  promptheus @prompt.txt                      # Alternative file syntax
  cat prompt.txt | promptheus                 # Read from stdin (single-shot)
  promptheus --provider anthropic "Prompt"    # Use specific provider
  promptheus --model gemini-pro "Prompt"      # Use specific model
  promptheus -c "My prompt"                   # Copy result to clipboard
  promptheus -e "My prompt"                   # Open result in editor
  promptheus history                          # View prompt history
  promptheus history --clear                  # Clear all history
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
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

    parser.add_argument(
        "prompt",
        nargs="?",
        help="Initial prompt (optional, will ask if not provided). Use @filename to read from file.",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Read prompt from file instead of command line",
    )
    parser.add_argument(
        "--provider",
        choices=PROVIDER_CHOICES,
        help="LLM provider to use (overrides config)",
    )
    parser.add_argument(
        "--model",
        help="Specific model to use (e.g., gemini-pro, claude-3-5-sonnet-20241022)",
    )
    parser.add_argument(
        "--static",
        "--mvp",
        action="store_true",
        dest="static",
        help="Use static questions instead of dynamic AI-generated questions",
    )
    parser.add_argument(
        "-q",
        "--quick",
        action="store_true",
        help="Skip all questions, run prompt directly (for analysis/research tasks)",
    )
    parser.add_argument(
        "-r",
        "--refine",
        action="store_true",
        help="Force clarifying questions even for analysis tasks",
    )
    parser.add_argument(
        "-c",
        "--copy",
        action="store_true",
        help="Copy the refined prompt to clipboard",
    )
    parser.add_argument(
        "-e",
        "--edit",
        action="store_true",
        help="Open the refined prompt in your default editor",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug output",
    )

    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)
