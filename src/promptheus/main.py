#!/usr/bin/env python3
"""
Promptheus - AI-powered prompt engineering CLI tool.
Unified version with multi-provider support.
"""

from __future__ import annotations

import logging
import os
import sys
from argparse import Namespace
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import questionary
import pyperclip
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from promptheus.config import Config
from promptheus.constants import PROMPTHEUS_DEBUG_ENV, VERSION
from promptheus.history import get_history
from promptheus.io_context import IOContext
from promptheus.question_prompter import create_prompter
from promptheus.prompts import (
    ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION,
    CLARIFICATION_SYSTEM_INSTRUCTION,
    GENERATION_SYSTEM_INSTRUCTION,
    TWEAK_SYSTEM_INSTRUCTION,
)
from promptheus.providers import LLMProvider, get_provider
from promptheus.utils import configure_logging, sanitize_error_message
from promptheus.cli import parse_arguments
from promptheus.repl import display_history, interactive_mode
from promptheus.exceptions import PromptCancelled, ProviderAPIError, InvalidProviderError
from promptheus.commands import list_models, validate_environment, generate_template, generate_completion_script, handle_completion_request

console = Console()
logger = logging.getLogger(__name__)

MessageSink = Callable[[str], None]


@dataclass
class QuestionPlan:
    skip_questions: bool
    task_type: str
    questions: List[Dict[str, Any]]
    mapping: Dict[str, str]
    use_light_refinement: bool = False


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


def display_output(
    prompt: str,
    io: IOContext,
    is_refined: bool = True,
) -> None:
    """Display the prompt in a panel or as plain text."""
    if io.quiet_output:
        # In quiet mode, don't display anything here - output is handled by the caller
        return

    # In non-quiet mode, display the Rich panel on stderr
    title = "[bold green]Refined Prompt[/bold green]" if is_refined else "[bold blue]Your Prompt[/bold blue]"
    border_color = "green" if is_refined else "blue"

    prompt_text = Text(prompt)
    panel = Panel(prompt_text, title=title, border_style=border_color, padding=(1, 2))

    io.console_err.print("\n")
    io.console_err.print(panel)
    io.console_err.print()


def copy_to_clipboard(text: str, notify: Optional[MessageSink] = None) -> None:
    """Copy text to clipboard."""
    if notify is None:
        notify = console.print
    try:
        pyperclip.copy(text)
        notify("[green]✓[/green] Copied to clipboard!")
    except Exception as exc:  # pragma: no cover - platform dependent
        sanitized = sanitize_error_message(str(exc))
        notify(f"[yellow]Warning: Failed to copy to clipboard: {sanitized}[/yellow]")
        logger.exception("Clipboard copy failed")


def iterative_refinement(
    provider: LLMProvider,
    current_prompt: str,
    io: IOContext,
    plain_mode: bool,
) -> str:
    """
    Allow user to iteratively refine the prompt with simple tweaks.
    Returns the final accepted prompt.
    """
    # Skip iterative refinement in quiet mode
    if io.quiet_output:
        return current_prompt

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
                    io.notify("\n[yellow]Cancelled tweaks.[/yellow]\n")
                    return current_prompt
                tweak_instruction = answer.strip()
        except (EOFError, KeyboardInterrupt):
            io.notify("\n[yellow]Cancelled tweaks.[/yellow]\n")
            return current_prompt

        if not tweak_instruction:
            io.notify("\n[green]✓[/green] Prompt accepted!\n")
            return current_prompt

        iteration += 1

        io.notify(f"\n[blue]⟳[/blue] Tweaking prompt (v{iteration})...\n")

        try:
            with io.console_err.status("[bold cyan]✨ Sprinkling some refinement magic...", spinner="bouncingBall"):
                current_prompt = provider.tweak_prompt(
                    current_prompt, tweak_instruction, TWEAK_SYSTEM_INSTRUCTION
                )

            display_output(current_prompt, io, is_refined=True)

        except KeyboardInterrupt:
            io.notify("\n[yellow]Cancelled tweaks.[/yellow]\n")
            return current_prompt
        except Exception as exc:
            sanitized = sanitize_error_message(str(exc))
            io.notify(f"[bold red]Error:[/bold red] Failed to tweak prompt: {sanitized}")
            io.notify("[yellow]Keeping previous version[/yellow]\n")
            logger.exception("Prompt tweak failed")


def determine_question_plan(
    provider: LLMProvider,
    initial_prompt: str,
    args: Namespace,
    debug_enabled: bool,
    io: IOContext,
    app_config: Config,
) -> QuestionPlan:
    """
    Decide whether to ask clarifying questions and prepare them if needed.
    """
    if getattr(args, "skip_questions", False):
        io.notify("\n[bold blue]✓[/bold blue] Skip questions mode - improving prompt directly\n")
        return QuestionPlan(skip_questions=True, task_type="analysis", questions=[], mapping={})

    try:
        if not io.quiet_output:
            with io.console_err.status("[bold magenta]🔍 Analyzing your prompt and crafting questions...", spinner="arc"):
                result = provider.generate_questions(initial_prompt, CLARIFICATION_SYSTEM_INSTRUCTION)
        else:
            result = provider.generate_questions(initial_prompt, CLARIFICATION_SYSTEM_INSTRUCTION)
    except ProviderAPIError as exc:
        current_provider = app_config.provider or ""
        provider_display = current_provider.title() if current_provider else "Provider"
        # Pass a larger max_length to prevent truncation of the core error message
        sanitized_error = sanitize_error_message(str(exc), max_length=500)

        io.notify(f"\n[bold red]✗ {provider_display} Error:[/bold red] [red]{sanitized_error}[/red]")
        io.notify(f"[dim](set {PROMPTHEUS_DEBUG_ENV}=1 to print full debug output)[/dim]\n")

        available_providers = app_config.get_configured_providers()
        other_providers = [p for p in available_providers if p != current_provider]
        provider_label = current_provider or "default"

        if other_providers:
            io.notify(f"[dim]💡 Current provider: '[cyan]{provider_label}[/cyan]'. Perhaps try a different one?[/dim]")
            for p in other_providers:
                io.notify(f"[dim]  - [cyan]promptheus --provider {p} ...[/cyan][/dim]")
        else:
            io.notify("[dim]💡 Double-check your credentials, or use '--quick' for offline questions.[/dim]")
        io.notify("")
        raise RuntimeError("AI provider unavailable for question generation") from exc
    except KeyboardInterrupt as exc:
        raise PromptCancelled("Analysis cancelled") from exc

    if result is None:
        # This block should now be much harder to reach, but serves as a fallback.
        current_provider = app_config.provider or ""
        provider_display = current_provider.title() if current_provider else "Provider"
        io.notify(
            f"\n[bold yellow]⚠ {provider_display} is taking a break![/bold yellow] "
            f"[dim](set {PROMPTHEUS_DEBUG_ENV}=1 to print debug output)[/dim]"
        )
        io.notify(f"[dim]Reason: Your {provider_display} provider returned an unexpected empty result.[/dim]")
        io.notify("[dim]We need a working AI to generate questions for your prompt.[/dim]")
        io.notify("")
        raise RuntimeError("AI provider returned an unexpected empty result.")

    task_type = result.get("task_type", "generation")
    questions_json = result.get("questions", [])

    if debug_enabled:
        io.notify(
            f"[dim]Debug: task_type={task_type}, questions={len(questions_json)}, refine={args.refine}[/dim]"
        )

    if task_type == "analysis" and not args.refine:
        io.notify("\n[bold blue]✓[/bold blue] Analysis task detected - performing light refinement")
        io.notify("[dim]  (Use --skip-questions to skip, or --refine to force questions)[/dim]\n")
        return QuestionPlan(True, task_type, [], {})

    if not questions_json:
        io.notify("\n[bold blue]✓[/bold blue] No clarifying questions needed\n")
        return QuestionPlan(True, task_type, [], {})

    if task_type == "generation" and not args.refine:
        io.notify(
            f"\n[bold green]✓[/bold green] Creative task detected with {len(questions_json)} clarifying questions"
        )
        try:
            # Create appropriate prompter based on I/O context
            prompter = create_prompter(io)
            confirm = prompter.prompt_confirmation(
                "Ask clarifying questions to refine your prompt?", default=True
            )
        except EOFError:
            io.notify("[yellow]stdin not interactive - skipping questions, using light refinement[/yellow]")
            return QuestionPlan(True, task_type, [], {}, use_light_refinement=True)
        except KeyboardInterrupt:
            io.notify("[yellow]Skipping questions - performing light refinement[/yellow]")
            return QuestionPlan(True, task_type, [], {}, use_light_refinement=True)
        if not confirm:
            io.notify("\n[bold]Skipping questions - performing light refinement\n")
            return QuestionPlan(True, task_type, [], {}, use_light_refinement=True)

    questions, mapping = convert_json_to_question_definitions(questions_json)
    if args.refine:
        io.notify(f"[bold green]✓[/bold green] Refine mode - {len(questions)} questions generated\n")
    return QuestionPlan(False, task_type, questions, mapping)


def ask_clarifying_questions(
    plan: QuestionPlan,
    io: IOContext,
) -> Optional[Dict[str, Any]]:
    """Prompt the user with clarifying questions and return their answers."""
    if plan.skip_questions or not plan.questions:
        return {}

    io.notify("[bold]Please answer the following questions to refine your prompt:[/bold]\n")

    answers: Dict[str, Any] = {}

    # Create appropriate prompter based on I/O context
    prompter = create_prompter(io)

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
                    answer = prompter.prompt_radio(message, options)
                elif qtype == "checkbox" and options:
                    answer = prompter.prompt_checkbox(message, options)
                elif qtype == "confirm":
                    default_bool = bool(default) if isinstance(default, bool) else True
                    answer = prompter.prompt_confirmation(message, default_bool)
                else:
                    answer = prompter.prompt_text(message, str(default))
            except EOFError:
                io.notify("[red]Error: stdin is not interactive but questions need to be answered[/red]")
                io.notify("[dim]Use --skip-questions to skip questions or provide input via interactive terminal[/dim]")
                return None
            except KeyboardInterrupt:
                io.notify("[yellow]Cancelled.[/yellow]")
                return None

            # Normalize answer
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
                io.notify("[yellow]This answer is required. Please provide a response.[/yellow]")
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
    io: IOContext,
) -> Tuple[str, bool]:
    """Generate the refined prompt (or return original if no answers)."""
    if not answers:
        return initial_prompt, False

    try:
        if not io.quiet_output:
            with io.console_err.status("[bold green]🎨 Crafting your refined prompt...", spinner="moon"):
                final_prompt = provider.refine_from_answers(
                    initial_prompt, answers, mapping, GENERATION_SYSTEM_INSTRUCTION
                )
        else:
            final_prompt = provider.refine_from_answers(
                initial_prompt, answers, mapping, GENERATION_SYSTEM_INSTRUCTION
            )
        return final_prompt, True
    except KeyboardInterrupt as exc:
        raise PromptCancelled("Refinement cancelled") from exc
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        io.notify(f"[bold red]Error:[/bold red] Failed to generate refined prompt: {sanitized}")
        logger.exception("Failed to generate refined prompt")
        raise


def process_single_prompt(
    provider: LLMProvider,
    initial_prompt: str,
    args: Namespace,
    debug_enabled: bool,
    plain_mode: bool,
    io: IOContext,
    app_config: Config,
) -> Optional[Tuple[str, str]]:
    """
    Process a single prompt through the refinement pipeline.

    Returns:
        Tuple of (final_prompt, task_type) if successful, None otherwise
    """
    try:
        plan = determine_question_plan(provider, initial_prompt, args, debug_enabled, io, app_config)

        # This is the main logic branching
        is_light_refinement = (
            (plan.task_type == "analysis" and plan.skip_questions) or
            plan.use_light_refinement
        )

        if is_light_refinement:
            try:
                if not io.quiet_output:
                    with io.console_err.status("[bold blue]⚡ Performing light refinement...", spinner="simpleDots"):
                        final_prompt = provider.light_refine(
                            initial_prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
                        )
                else:
                    final_prompt = provider.light_refine(
                        initial_prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
                    )
                is_refined = True
            except KeyboardInterrupt as exc:
                raise PromptCancelled("Light refinement cancelled") from exc
            except Exception as exc:
                logger.warning("Light refinement failed: %s", sanitize_error_message(str(exc)))
                io.notify("[yellow]Warning: Light refinement failed. Using original prompt.[/yellow]")
                final_prompt = initial_prompt
                is_refined = False
        else:
            # The standard flow: ask questions if needed, then generate
            answers = ask_clarifying_questions(plan, io)
            if answers is None:
                return None
            final_prompt, is_refined = generate_final_prompt(
                provider, initial_prompt, answers, plan.mapping, io
            )

    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        io.notify(f"[red]✗[/red] Something went wrong: {sanitized}")
        if not debug_enabled:
            io.notify(f"[dim]Enable --verbose for full error details[/dim]")
        logger.exception("Failed to process prompt")
        return None

    display_output(final_prompt, io, is_refined=is_refined)

    # Skip interactive tweaks in quiet mode or when skip-questions is set
    interactive_tweaks = io.stdin_is_tty and not getattr(args, "skip_questions", False) and not io.quiet_output
    if interactive_tweaks:
        final_prompt = iterative_refinement(provider, final_prompt, io, plain_mode)
    else:
        if getattr(args, "skip_questions", False):
            io.notify("[dim]Skipping interactive tweaking (skip-questions mode)[/dim]\n")
        elif io.quiet_output:
            # Don't notify in quiet mode
            pass
        else:
            io.notify("[dim]Skipping interactive tweaking (stdin is not a TTY)[/dim]\n")

    # Save to history
    try:
        history = get_history(app_config)
        history.save_entry(
            original_prompt=initial_prompt,
            refined_prompt=final_prompt,
            task_type=plan.task_type
        )
        logger.debug("Saved prompt to history")
    except Exception as exc:
        logger.warning(f"Failed to save prompt to history: {sanitize_error_message(str(exc))}")

    # Skip clipboard in quiet mode
    if not io.quiet_output:
        if getattr(args, "copy", False):
            copy_to_clipboard(final_prompt, io.notify)

    return final_prompt, plan.task_type


def main() -> None:
    """Main entry point for Promptheus."""
    configure_logging()
    app_config = Config()

    args = parse_arguments()

    # Handle version flag first (before any setup)
    if args.version:
        console.print(f"Promptheus v{VERSION}")
        sys.exit(0)

    # Create I/O context for terminal handling
    io = IOContext.create()

    if args.verbose:
        os.environ[PROMPTHEUS_DEBUG_ENV] = "1"
        configure_logging(logging.DEBUG)

    # Handle utility commands that exit immediately
    if getattr(args, "command", None) == "completion":
        if getattr(args, "install", False):
            from promptheus.commands import install_completion
            install_completion(args.shell, io.console_err)
        else:
            generate_completion_script(args.shell)
        sys.exit(0)

    if getattr(args, "command", None) == "__complete":
        # Note: __complete is a hidden command used by the shell completion scripts
        handle_completion_request(app_config, args)
        sys.exit(0)

    # Handle utility commands that exit immediately
    if getattr(args, "command", None) == "list-models":
        if args.providers:
            providers_to_list = [p.strip() for p in args.providers.split(',')]
        else:
            providers_to_list = None
        # Create a simple console for output
        utility_console = Console()
        list_models(
            app_config,
            utility_console,
            providers=providers_to_list,
            limit=args.limit,
            include_nontext=args.include_nontext
        )
        sys.exit(0)

    if getattr(args, "command", None) == "validate":
        providers_to_validate = None
        if args.providers:
            providers_to_validate = [p.strip() for p in args.providers.split(',')]

        # Create a simple console for output
        utility_console = Console()
        validate_environment(
            app_config,
            utility_console,
            test_connection=getattr(args, "test_connection", False),
            providers=providers_to_validate
        )
        sys.exit(0)

    if getattr(args, "command", None) == "template":
        # Create a simple console for output
        utility_console = Console()
        try:
            template = generate_template(app_config, utility_console, args.providers)
            utility_console.print(template)
        except Exception as exc:
            utility_console.print(f"[red]Error generating template:[/red] {exc}")
            sys.exit(1)
        sys.exit(0)

    if getattr(args, "command", None) == "history":
        if getattr(args, "clear", False):
            confirm = questionary.confirm(
                "Are you sure you want to clear all history?",
                default=False,
            ).ask()
            if confirm:
                get_history(app_config).clear()
                io.notify("[green]✓[/green] History cleared")
            else:
                io.notify("[yellow]Cancelled[/yellow]")
        else:
            display_history(io.console_err, io.notify, limit=args.limit)
        sys.exit(0)

    # Show provider status in a friendly way
    for message in app_config.consume_status_messages():
        io.notify(f"[cyan]●[/cyan] {message}")

    if args.provider:
        app_config.set_provider(args.provider)
    if args.model:
        app_config.set_model(args.model)

    for message in app_config.consume_status_messages():
        io.notify(f"[cyan]●[/cyan] {message}")

  
    # Friendly error handling
    if not app_config.validate():
        io.notify("")
        for message in app_config.consume_error_messages():
            # Split multi-line messages and format nicely
            lines = message.split('\n')
            if len(lines) == 1:
                io.notify(f"[red]✗[/red] {message}")
            else:
                io.notify(f"[red]✗[/red] {lines[0]}")
                for line in lines[1:]:
                    io.notify(f"  {line}")
        io.notify("")
        sys.exit(1)

    # Get initial prompt from file, stdin, or argument
    initial_prompt: Optional[str] = None

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as file_handle:
                initial_prompt = file_handle.read().strip()
            io.notify(f"[green]✓[/green] Loaded prompt from {args.file}")
        except FileNotFoundError:
            io.notify(f"[red]✗[/red] Couldn't find file: {args.file}")
            sys.exit(1)
        except Exception as exc:  # pragma: no cover - file I/O
            sanitized = sanitize_error_message(str(exc))
            io.notify(f"[red]✗[/red] Failed to read file: {sanitized}")
            sys.exit(1)

    elif args.prompt and args.prompt.startswith("@"):
        filename = args.prompt[1:]
        try:
            with open(filename, "r", encoding="utf-8") as file_handle:
                initial_prompt = file_handle.read().strip()
            io.notify(f"[green]✓[/green] Loaded prompt from {filename}")
        except FileNotFoundError:
            io.notify(f"[red]✗[/red] Couldn't find file: {filename}")
            sys.exit(1)
        except Exception as exc:  # pragma: no cover - file I/O
            sanitized = sanitize_error_message(str(exc))
            io.notify(f"[red]✗[/red] Failed to read file: {sanitized}")
            sys.exit(1)

    elif not io.stdin_is_tty:
        initial_prompt = sys.stdin.read().strip()
        if initial_prompt:
            io.notify("[green]✓[/green] Got prompt from stdin")

    else:
        initial_prompt = args.prompt

    provider_name = app_config.provider or "gemini"
    try:
        provider = get_provider(provider_name, app_config, app_config.get_model())
    except Exception as exc:
        error_msg = str(exc)
        sanitized = sanitize_error_message(error_msg)
        io.notify(f"[red]✗[/red] Couldn't connect to AI provider: {sanitized}\n")

        # Provide helpful context for common errors
        if "401" in error_msg or "403" in error_msg or "Unauthorized" in error_msg:
            io.notify(f"[yellow]Authentication Failed:[/yellow] Check your API key for {provider_name}\n")
        elif "404" in error_msg:
            io.notify(f"[yellow]Model Not Found:[/yellow] The model may not exist or be available\n")

        logger.exception("Provider initialization failure")
        sys.exit(1)

    debug_enabled = args.verbose or os.getenv(PROMPTHEUS_DEBUG_ENV, "").lower() in {"1", "true", "yes", "on"}
    plain_mode = io.plain_mode

    if initial_prompt is None or not initial_prompt:
        # Cannot enter interactive mode in quiet mode without a prompt
        if io.quiet_output:
            io.console_err.print("[red]✗[/red] Error: Cannot enter interactive mode when stdout is not a TTY")
            io.console_err.print("[dim]Provide a prompt as an argument, via --file, or from stdin[/dim]")
            io.console_err.print("[dim]Example: promptheus \"your prompt here\" | cat[/dim]")
            sys.exit(1)

        # Warn if history is disabled in interactive mode
        if not app_config.history_enabled:
            io.notify("[yellow]⚠[/yellow] History persistence is disabled. Your prompts won't be saved.\n")
            io.notify("[dim]Enable with: export PROMPTHEUS_ENABLE_HISTORY=1[/dim]\n")

        interactive_mode(
            provider,
            app_config,
            args,
            debug_enabled,
            plain_mode,
            io,
            process_single_prompt,
        )
    else:
        io.notify(f"[dim]Using provider: {provider_name} | Model: {app_config.get_model()}[/dim]\n")
        try:
            result = process_single_prompt(
                provider, initial_prompt, args, debug_enabled, plain_mode, io, app_config
            )
            if result:
                final_prompt, task_type = result
                # Write the final output to stdout based on output format
                output_format = getattr(args, "output_format", "plain")
                if output_format == "json":
                    import json
                    io.console_out.print(json.dumps({"prompt": final_prompt, "task_type": task_type}))
                else:  # plain
                    io.console_out.print(final_prompt)
            else:
                # process_single_prompt returned None - error occurred
                io.notify("[red]✗[/red] Failed to process prompt")
                sys.exit(1)
        except PromptCancelled as exc:
            io.notify(f"\n[yellow]{exc}[/yellow]\n")
            sys.exit(130)
        except KeyboardInterrupt:
            io.notify("\n[yellow]Cancelled by user[/yellow]\n")
            sys.exit(130)


if __name__ == "__main__":
    main()
