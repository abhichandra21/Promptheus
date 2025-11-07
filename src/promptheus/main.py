#!/usr/bin/env python3
"""
Promptheus - AI-powered prompt engineering CLI tool.
Unified version with multi-provider support.
"""

from __future__ import annotations

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
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from promptheus.config import Config
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
from promptheus.cli import build_parser
from promptheus.repl import display_history, interactive_mode

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
    app_config: Config,
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
        current_provider = app_config.provider or ""
        provider_display = current_provider.title() if current_provider else "Provider"
        provider_label = current_provider or "default"
        notify(
            f"\n[bold yellow]⚠ {provider_display} is taking a break![/bold yellow] "
            f"[dim](set {PROMPTHEUS_DEBUG_ENV}=1 to print debug output)[/dim]"
        )
        notify(f"[dim]Reason: Your {provider_display} provider couldn't respond or sent something unexpected.[/dim]")
        notify("[dim]We need a working AI to generate questions for your prompt.[/dim]")

        available_providers = app_config.get_configured_providers()

        other_providers = [p for p in available_providers if p != current_provider]

        if other_providers:
            notify(f"[dim]💡 Current provider: '[cyan]{provider_label}[/cyan]'. Perhaps try a different one?[/dim]")
            for p in other_providers:
                notify(f"[dim]  - [cyan]promptheus --provider {p} ...[/cyan][/dim]")
        else:
            notify("[dim]💡 Double-check your credentials, or use '--static' for offline questions.[/dim]")
        notify("") # Add an empty line for better readability
        raise RuntimeError("AI provider unavailable for question generation")

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

        while True:
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

            normalized = answer
            if isinstance(normalized, str):
                normalized = normalized.strip()

            if qtype == "checkbox":
                normalized = normalized or []

            missing_response = False
            if isinstance(normalized, str):
                missing_response = normalized == ""
            elif isinstance(normalized, list):
                missing_response = len(normalized) == 0

            if required and missing_response and qtype != "confirm":
                notify("[yellow]This answer is required. Please provide a response.[/yellow]")
                continue

            if not required and missing_response:
                normalized = [] if qtype == "checkbox" else ""

            answers[key] = normalized
            break

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
    app_config: Config,
) -> Optional[Tuple[str, str]]:
    """
    Process a single prompt through the refinement pipeline.

    Returns:
        Tuple of (final_prompt, task_type) if successful, None otherwise
    """
    try:
        plan = determine_question_plan(provider, initial_prompt, args, debug_enabled, notify, app_config)

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


def main() -> None:
    """Main entry point for Promptheus."""
    configure_logging()
    app_config = Config()

    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        os.environ[PROMPTHEUS_DEBUG_ENV] = "1"
        configure_logging(logging.DEBUG)

    notify: MessageSink = console.print
    plain_mode = False

    if getattr(args, "command", None) == "history":
        if getattr(args, "clear", False):
            confirm = questionary.confirm(
                "Are you sure you want to clear all history?",
                default=False,
            ).ask()
            if confirm:
                get_history().clear()
                notify("[green]✓[/green] History cleared")
            else:
                notify("[yellow]Cancelled[/yellow]")
        else:
            display_history(console, notify, limit=args.limit)
        sys.exit(0)

    # Show provider status in a friendly way
    for message in app_config.consume_status_messages():
        notify(f"[cyan]●[/cyan] {message}")

    if args.provider:
        app_config.set_provider(args.provider)
    if args.model:
        app_config.set_model(args.model)

    for message in app_config.consume_status_messages():
        notify(f"[cyan]●[/cyan] {message}")

    # Friendly error handling
    if not app_config.validate():
        notify("")
        for message in app_config.consume_error_messages():
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

    provider_name = app_config.provider or "gemini"
    try:
        provider = get_provider(provider_name, app_config, app_config.get_model())
    except Exception as exc:
        error_msg = str(exc)
        sanitized = sanitize_error_message(error_msg)
        notify(f"[red]✗[/red] Couldn't connect to AI provider: {sanitized}\n")

        # Provide helpful context for common errors
        if "401" in error_msg or "403" in error_msg or "Unauthorized" in error_msg:
            notify(f"[yellow]Authentication Failed:[/yellow] Check your API key for {provider_name}\n")
        elif "404" in error_msg:
            notify(f"[yellow]Model Not Found:[/yellow] The model may not exist or be available\n")

        logger.exception("Provider initialization failure")
        sys.exit(1)

    debug_enabled = args.verbose or os.getenv(PROMPTHEUS_DEBUG_ENV, "").lower() in {"1", "true", "yes", "on"}

    if initial_prompt is None or not initial_prompt:
        interactive_mode(
            provider,
            app_config,
            args,
            debug_enabled,
            plain_mode,
            notify,
            console,
            process_single_prompt,
        )
    else:
        notify(f"[dim]Using provider: {provider_name} | Model: {app_config.get_model()}[/dim]\n")
        process_single_prompt(provider, initial_prompt, args, debug_enabled, plain_mode, notify, app_config)


if __name__ == "__main__":
    main()
