#!/usr/bin/env python3
"""
Promptheus - AI-powered prompt engineering CLI tool.
Unified version with multi-provider support.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import tempfile
from argparse import Namespace
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import questionary
import pyperclip
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from promptheus.config import config
from promptheus.constants import PROMPTHEUS_DEBUG_ENV
from promptheus.history import get_history
from promptheus.prompts import (
    ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION,
    CLARIFICATION_SYSTEM_INSTRUCTION,
    GENERATION_SYSTEM_INSTRUCTION,
    TWEAK_SYSTEM_INSTRUCTION,
)
from promptheus.providers import LLMProvider, get_provider
from promptheus.utils import configure_logging, sanitize_error_message

console = Console()
logger = logging.getLogger(__name__)

MessageSink = Callable[[str], None]


@dataclass
class QuestionPlan:
    skip_questions: bool
    task_type: str
    questions: List[Dict[str, Any]]
    mapping: Dict[str, str]


def get_static_questions() -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Return the static list of questions for MVP mode along with mapping."""
    specs = [
        ("goal", "What is the goal of this prompt?", True),
        ("audience", "Who is the target audience?", True),
        ("tone", "What tone should it have? (e.g., formal, casual)", False),
        ("format", "What is the desired output format? (e.g., list, paragraph, JSON)", False),
    ]

    questions: List[Dict[str, Any]] = []
    mapping: Dict[str, str] = {}
    for key, message, required in specs:
        mapping[key] = message
        questions.append(
            {
                "key": key,
                "message": message if required else f"{message} (optional)",
                "type": "text",
                "options": [],
                "required": required,
                "default": "",
            }
        )
    return questions, mapping


def convert_json_to_question_definitions(
    questions_json: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Convert JSON question format to internal question definitions.
    Handles required vs optional questions with visual indicators.
    """
    question_defs: List[Dict[str, Any]] = []
    question_mapping: Dict[str, str] = {}

    for idx, q in enumerate(questions_json):
        question_text = q.get("question", f"Question {idx + 1}")
        question_type = q.get("type", "text")
        options = q.get("options", [])
        required = q.get("required", True)

        key = f"q{idx}"
        question_mapping[key] = question_text

        display_text = question_text if required else f"{question_text} (optional)"

        question_defs.append(
            {
                "key": key,
                "message": display_text,
                "type": question_type.lower(),
                "options": options or [],
                "required": required,
                "default": q.get("default", ""),
            }
        )

    return question_defs, question_mapping


def display_output(prompt: str, is_refined: bool = True) -> None:
    """Display the prompt in a panel."""
    title = "[bold green]Refined Prompt[/bold green]" if is_refined else "[bold blue]Your Prompt[/bold blue]"
    border_color = "green" if is_refined else "blue"

    prompt_text = Text(prompt)
    panel = Panel(prompt_text, title=title, border_style=border_color, padding=(1, 2))

    console.print("\n")
    console.print(panel)

    console.print()


def copy_to_clipboard(text: str) -> None:
    """Copy text to clipboard."""
    try:
        pyperclip.copy(text)
        console.print("[green]✓[/green] Copied to clipboard!")
    except Exception as exc:  # pragma: no cover - platform dependent
        sanitized = sanitize_error_message(str(exc))
        console.print(f"[yellow]Warning: Failed to copy to clipboard: {sanitized}[/yellow]")
        logger.exception("Clipboard copy failed")


def open_in_editor(text: str) -> None:
    """Open the text in the user's default editor."""
    try:
        editor = os.environ.get("EDITOR", "vim")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
            tf.write(text)
            temp_path = tf.name

        try:
            subprocess.run([editor, temp_path], check=True)
            console.print(f"[green]✓[/green] Opened in {editor}")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as exc:  # pragma: no cover - external editor
        sanitized = sanitize_error_message(str(exc))
        console.print(f"[yellow]Warning: Failed to open editor: {sanitized}[/yellow]")
        logger.exception("Opening editor failed")


def iterative_refinement(
    provider: LLMProvider,
    current_prompt: str,
    plain_mode: bool,
    notify: MessageSink,
) -> str:
    """
    Allow user to iteratively refine the prompt with simple tweaks.
    Returns the final accepted prompt.
    """
    iteration = 1

    while True:
        try:
            if plain_mode:
                tweak_instruction = input("Tweak? (Enter to accept, or describe your change) ").strip()
            else:
                answer = questionary.text(
                    "Tweak? (Enter to accept, or describe your change)"
                ).ask()
                if answer is None:
                    notify("\n[yellow]Cancelled tweaks.[/yellow]\n")
                    return current_prompt
                tweak_instruction = answer.strip()
        except EOFError:
            notify("\n[yellow]Cancelled tweaks.[/yellow]\n")
            return current_prompt

        if not tweak_instruction:
            notify("\n[green]✓[/green] Prompt accepted!\n")
            return current_prompt

        iteration += 1

        notify(f"\n[blue]⟳[/blue] Tweaking prompt (v{iteration})...\n")

        try:
            with console.status("[bold blue]Tweaking your prompt...", spinner="dots"):
                current_prompt = provider.tweak_prompt(
                    current_prompt, tweak_instruction, TWEAK_SYSTEM_INSTRUCTION
                )

            display_output(current_prompt, is_refined=True)

        except Exception as exc:
            sanitized = sanitize_error_message(str(exc))
            notify(f"[bold red]Error:[/bold red] Failed to tweak prompt: {sanitized}")
            notify("[yellow]Keeping previous version[/yellow]\n")
            logger.exception("Prompt tweak failed")


def determine_question_plan(
    provider: LLMProvider,
    initial_prompt: str,
    args: Namespace,
    debug_enabled: bool,
    notify: MessageSink,
) -> QuestionPlan:
    """
    Decide whether to ask clarifying questions and prepare them if needed.
    """
    if args.static:
        notify("\n[bold]Using static questions (MVP mode)[/bold]\n")
        questions, mapping = get_static_questions()
        return QuestionPlan(skip_questions=False, task_type="generation", questions=questions, mapping=mapping)

    if args.quick:
        notify("\n[bold blue]✓[/bold blue] Quick mode - using original prompt without modification\n")
        return QuestionPlan(skip_questions=True, task_type="analysis", questions=[], mapping={})

    with console.status("[bold blue]Analyzing your prompt...", spinner="dots"):
        result = provider.generate_questions(initial_prompt, CLARIFICATION_SYSTEM_INSTRUCTION)

    if result is None:
        notify("\n[bold]Using static questions (fallback)[/bold]\n")
        questions, mapping = get_static_questions()
        return QuestionPlan(skip_questions=False, task_type="generation", questions=questions, mapping=mapping)

    task_type = result.get("task_type", "generation")
    questions_json = result.get("questions", [])

    if debug_enabled:
        notify(
            f"[dim]Debug: task_type={task_type}, questions={len(questions_json)}, refine={args.refine}[/dim]"
        )

    if task_type == "analysis" and not args.refine:
        notify("\n[bold blue]✓[/bold blue] Analysis task detected - performing light refinement")
        notify("[dim]  (Use --quick to skip, or --refine to force questions)[/dim]\n")
        return QuestionPlan(True, task_type, [], {})

    if not questions_json:
        notify("\n[bold blue]✓[/bold blue] No clarifying questions needed\n")
        return QuestionPlan(True, task_type, [], {})

    if task_type == "generation" and not args.refine:
            notify(
                f"\n[bold green]✓[/bold green] Creative task detected with {len(questions_json)} clarifying questions"
            )
            try:
                confirm = questionary.confirm(
                    "Ask clarifying questions to refine your prompt?", default=True
                ).ask()
            except KeyboardInterrupt:
                notify("[yellow]Skipping questions - using original prompt[/yellow]")
                return QuestionPlan(True, task_type, [], {})
            if not confirm:
                notify("\n[bold]Skipping questions - using original prompt\n")
                return QuestionPlan(True, task_type, [], {})

    questions, mapping = convert_json_to_question_definitions(questions_json)
    if args.refine:
        notify(f"[bold green]✓[/bold green] Refine mode - {len(questions)} questions generated\n")
    return QuestionPlan(False, task_type, questions, mapping)


def ask_clarifying_questions(
    plan: QuestionPlan,
    notify: MessageSink,
) -> Optional[Dict[str, Any]]:
    """Prompt the user with clarifying questions and return their answers."""
    if plan.skip_questions or not plan.questions:
        return {}

    notify("[bold]Please answer the following questions to refine your prompt:[/bold]\n")

    answers: Dict[str, Any] = {}

    for question in plan.questions:
        key = question["key"]
        qtype = question.get("type", "text").lower()
        message = question.get("message", key)
        required = question.get("required", True)
        options = question.get("options") or []
        default = question.get("default", "")

        try:
            if qtype == "radio" and options:
                answer = questionary.select(message, choices=options).ask()
            elif qtype == "checkbox" and options:
                answer = questionary.checkbox(message, choices=options).ask()
            elif qtype == "confirm":
                default_bool = bool(default) if isinstance(default, bool) else True
                answer = questionary.confirm(message, default=default_bool).ask()
            else:
                answer = questionary.text(message, default=str(default)).ask()
        except KeyboardInterrupt:
            notify("[yellow]Cancelled.[/yellow]")
            return None

        if answer is None:
            notify("[yellow]Cancelled.[/yellow]")
            return None

        if isinstance(answer, str):
            answer = answer.strip()

        if not answer:
            if qtype == "checkbox":
                answer = []
            elif not required:
                answer = ""

        answers[key] = answer

    return answers


def generate_final_prompt(
    provider: LLMProvider,
    initial_prompt: str,
    answers: Dict[str, Any],
    mapping: Dict[str, str],
    notify: MessageSink,
) -> Tuple[str, bool]:
    """Generate the refined prompt (or return original if no answers)."""
    if not answers:
        return initial_prompt, False

    try:
        with console.status("[bold blue]Generating your refined prompt...", spinner="dots"):
            final_prompt = provider.refine_from_answers(
                initial_prompt, answers, mapping, GENERATION_SYSTEM_INSTRUCTION
            )
        return final_prompt, True
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        notify(f"[bold red]Error:[/bold red] Failed to generate refined prompt: {sanitized}")
        logger.exception("Failed to generate refined prompt")
        raise


def process_single_prompt(
    provider: LLMProvider,
    initial_prompt: str,
    args: Namespace,
    debug_enabled: bool,
    plain_mode: bool,
    notify: MessageSink,
) -> Optional[Tuple[str, str]]:
    """
    Process a single prompt through the refinement pipeline.

    Returns:
        Tuple of (final_prompt, task_type) if successful, None otherwise
    """
    try:
        plan = determine_question_plan(provider, initial_prompt, args, debug_enabled, notify)

        # This is the main logic branching
        is_light_refinement = (
            plan.task_type == "analysis" and plan.skip_questions and not args.quick
        )

        if is_light_refinement:
            try:
                with console.status("[bold blue]Performing light refinement...", spinner="dots"):
                    final_prompt = provider.light_refine(
                        initial_prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
                    )
                is_refined = True
            except Exception as exc:
                logger.warning("Light refinement failed: %s", sanitize_error_message(str(exc)))
                notify("[yellow]Warning: Light refinement failed. Using original prompt.[/yellow]")
                final_prompt = initial_prompt
                is_refined = False
        else:
            # The standard flow: ask questions if needed, then generate
            answers = ask_clarifying_questions(plan, notify)
            if answers is None:
                return None
            final_prompt, is_refined = generate_final_prompt(
                provider, initial_prompt, answers, plan.mapping, notify
            )

    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        notify(f"[red]✗[/red] Something went wrong: {sanitized}")
        if debug_enabled:
            notify(f"[dim]Enable --verbose for full error details[/dim]")
        logger.exception("Failed to process prompt")
        return None

    display_output(final_prompt, is_refined=is_refined)

    interactive_tweaks = sys.stdin.isatty() and not args.quick
    if interactive_tweaks:
        final_prompt = iterative_refinement(provider, final_prompt, plain_mode, notify)
    else:
        if args.quick:
            notify("[dim]Skipping interactive tweaking (quick mode)[/dim]\n")
        else:
            notify("[dim]Skipping interactive tweaking (stdin is not a TTY)[/dim]\n")

    # Save to history
    try:
        history = get_history()
        history.save_entry(
            original_prompt=initial_prompt,
            refined_prompt=final_prompt,
            task_type=plan.task_type
        )
        logger.debug("Saved prompt to history")
    except Exception as exc:
        logger.warning(f"Failed to save prompt to history: {sanitize_error_message(str(exc))}")

    if args.copy:
        copy_to_clipboard(final_prompt)

    if args.edit:
        open_in_editor(final_prompt)

    return final_prompt, plan.task_type


def display_history(limit: int = 20, notify: MessageSink = console.print) -> None:
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
        # Parse timestamp
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(entry.timestamp)
            timestamp_str = dt.strftime("%m-%d %H:%M")
        except:
            timestamp_str = entry.timestamp[5:16]

        # Truncate long prompts
        original = entry.original_prompt[:60] + "..." if len(entry.original_prompt) > 60 else entry.original_prompt
        refined = entry.refined_prompt[:60] + "..." if len(entry.refined_prompt) > 60 else entry.refined_prompt

        # Replace newlines with spaces for display
        original = original.replace('\n', ' ')
        refined = refined.replace('\n', ' ')

        task_type = entry.task_type or "unknown"

        # Combine original and refined into one column
        combined = f"[white]{original}[/white]\n[dim]→[/dim] [yellow]{refined}[/yellow]"

        table.add_row(str(idx), timestamp_str, task_type, combined)

    console.print()
    console.print(table)
    console.print()
    notify("[dim]Use ':load <number>' to load a prompt from history[/dim]")


def interactive_mode(
    provider: LLMProvider,
    args: Namespace,
    debug_enabled: bool,
    plain_mode: bool,
    notify: MessageSink,
) -> None:
    """Interactive REPL mode - continuously process prompts until user types exit/quit."""
    notify("[bold cyan]Welcome to Promptheus Interactive Mode![/bold cyan]")
    notify(f"[dim]Using provider: {config.provider} | Model: {config.get_model()}[/dim]")
    notify("[dim]Type 'exit' or 'quit' to exit, ':history' to view history[/dim]\n")

    prompt_count = 1
    use_prompt_toolkit = not plain_mode

    # Initialize prompt_toolkit session with history
    session = None
    if use_prompt_toolkit:
        try:
            history_file = get_history().get_prompt_history_file()
            session = PromptSession(history=FileHistory(str(history_file)))
        except Exception as exc:
            logger.warning(f"Failed to initialize history: {sanitize_error_message(str(exc))}")
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

            if user_input.lower() in ["exit", "quit", "q"]:
                notify("[green]Goodbye![/green]")
                break

            # Handle special commands
            if user_input.startswith(":"):
                command_parts = user_input.split(None, 1)
                command = command_parts[0].lower()

                if command == ":history":
                    display_history(notify=notify)
                    continue
                elif command == ":load" and len(command_parts) > 1:
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
                    confirm = questionary.confirm("Are you sure you want to clear all history?", default=False).ask()
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
            result = process_single_prompt(provider, user_input, args, debug_enabled, plain_mode, notify)

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


def main() -> None:
    """Main entry point for Promptheus."""
    configure_logging()

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

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # History command
    history_parser = subparsers.add_parser(
        "history",
        help="View and manage prompt history"
    )
    history_parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all history"
    )
    history_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of history entries to display (default: 20)"
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
        choices=["gemini", "anthropic"],
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

    args = parser.parse_args()

    if args.verbose:
        os.environ[PROMPTHEUS_DEBUG_ENV] = "1"
        configure_logging(logging.DEBUG)

    notify: MessageSink = console.print
    plain_mode = False

    # Handle history command (doesn't need provider)
    if args.command == "history":
        if args.clear:
            confirm = questionary.confirm(
                "Are you sure you want to clear all history?",
                default=False
            ).ask()
            if confirm:
                get_history().clear()
                notify("[green]✓[/green] History cleared")
            else:
                notify("[yellow]Cancelled[/yellow]")
        else:
            display_history(limit=args.limit, notify=notify)
        sys.exit(0)

    # Show provider status in a friendly way
    for message in config.consume_status_messages():
        notify(f"[cyan]●[/cyan] {message}")

    if args.provider:
        config.set_provider(args.provider)
    if args.model:
        config.set_model(args.model)

    for message in config.consume_status_messages():
        notify(f"[cyan]●[/cyan] {message}")

    # Friendly error handling
    if not config.validate():
        notify("")
        for message in config.consume_error_messages():
            # Split multi-line messages and format nicely
            lines = message.split('\n')
            if len(lines) == 1:
                notify(f"[red]✗[/red] {message}")
            else:
                notify(f"[red]✗[/red] {lines[0]}")
                for line in lines[1:]:
                    notify(f"  {line}")
        notify("")
        sys.exit(1)

    # Get initial prompt from file, stdin, or argument
    initial_prompt: Optional[str] = None

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as file_handle:
                initial_prompt = file_handle.read().strip()
            notify(f"[green]✓[/green] Loaded prompt from {args.file}")
        except FileNotFoundError:
            notify(f"[red]✗[/red] Couldn't find file: {args.file}")
            sys.exit(1)
        except Exception as exc:  # pragma: no cover - file I/O
            sanitized = sanitize_error_message(str(exc))
            notify(f"[red]✗[/red] Failed to read file: {sanitized}")
            sys.exit(1)

    elif args.prompt and args.prompt.startswith("@"):
        filename = args.prompt[1:]
        try:
            with open(filename, "r", encoding="utf-8") as file_handle:
                initial_prompt = file_handle.read().strip()
            notify(f"[green]✓[/green] Loaded prompt from {filename}")
        except FileNotFoundError:
            notify(f"[red]✗[/red] Couldn't find file: {filename}")
            sys.exit(1)
        except Exception as exc:  # pragma: no cover - file I/O
            sanitized = sanitize_error_message(str(exc))
            notify(f"[red]✗[/red] Failed to read file: {sanitized}")
            sys.exit(1)

    elif not sys.stdin.isatty():
        initial_prompt = sys.stdin.read().strip()
        if initial_prompt:
            notify("[green]✓[/green] Got prompt from stdin")

    else:
        initial_prompt = args.prompt

    provider_name = config.provider or "gemini"
    try:
        provider = get_provider(provider_name, config, config.get_model())
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        notify(f"[red]✗[/red] Couldn't connect to AI provider: {sanitized}")
        logger.exception("Provider initialization failure")
        sys.exit(1)

    debug_enabled = args.verbose or os.getenv(PROMPTHEUS_DEBUG_ENV, "").lower() in {"1", "true", "yes", "on"}

    if initial_prompt is None or not initial_prompt:
        interactive_mode(provider, args, debug_enabled, plain_mode, notify)
    else:
        notify(f"[dim]Using provider: {provider_name} | Model: {config.get_model()}[/dim]\n")
        process_single_prompt(provider, initial_prompt, args, debug_enabled, plain_mode, notify)


if __name__ == "__main__":
    main()
