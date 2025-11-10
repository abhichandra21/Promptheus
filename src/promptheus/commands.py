"""
Command implementations for utility functions like listing models and validating config.
"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

from promptheus.config import Config
from promptheus.providers import get_provider, LLMProvider
from promptheus.utils import sanitize_error_message

logger = logging.getLogger(__name__)


# --- Completion Script Templates ---

BASH_COMPLETION_TEMPLATE = '''
#!/bin/bash

_promptheus_complete() {
    local cur prev words cword
    _get_comp_words_by_ref -n : cur prev words cword

    # Helper to find the executable
    _get_promptheus_executable() {
        if [[ -n "$VIRTUAL_ENV" ]] && [[ -x "$VIRTUAL_ENV/bin/promptheus" ]]; then echo "$VIRTUAL_ENV/bin/promptheus"; return; fi
        if command -v poetry &> /dev/null && [[ -f "pyproject.toml" ]]; then echo "poetry run promptheus"; return; fi
        if command -v promptheus &> /dev/null; then echo "promptheus"; return; fi
    }

    local executable=$(_get_promptheus_executable)
    if [[ -z "$executable" ]]; then return 1; fi

    # Dynamic completions
    case "${prev}" in
        --provider|--providers)
            local providers=$($executable __complete providers 2>/dev/null)
            COMPREPLY=( $(compgen -W "${providers}" -- "${cur}") )
            return 0
            ;;
        --model)
            local provider_val=""
            for i in "${!words[@]}"; do
                if [[ "${words[i]}" == "--provider" || "${words[i]}" == "--providers" ]]; then
                    provider_val="${words[i+1]}"
                    break
                fi
            done
            if [[ -n "$provider_val" ]]; then
                local models=$($executable __complete models --provider "$provider_val" 2>/dev/null)
                COMPREPLY=( $(compgen -W "${models}" -- "${cur}") )
            fi
            return 0
            ;;
        -o|--output-format)
            COMPREPLY=( $(compgen -W "plain json" -- "${cur}") )
            return 0
            ;;
        -f|--file)
            COMPREPLY=( $(compgen -f -- "${cur}") )
            return 0
            ;;
        completion)
            COMPREPLY=( $(compgen -W "bash zsh" -- "${cur}") )
            return 0
            ;;
    esac

    # Check if we're in a subcommand
    local in_subcommand=""
    local i
    for (( i=0; i < cword; i++ )); do
        if [[ "${words[i]}" =~ ^(history|list-models|validate|template|completion)$ ]]; then
            in_subcommand="${words[i]}"
            break
        fi
    done

    if [[ -n "$in_subcommand" ]]; then
        case "$in_subcommand" in
            history)
                local history_opts="--clear --limit --verbose --help"
                COMPREPLY=( $(compgen -W "${history_opts}" -- "${cur}") )
                return 0
                ;;
            list-models)
                local list_models_opts="--providers --limit --include-nontext --verbose --help"
                COMPREPLY=( $(compgen -W "${list_models_opts}" -- "${cur}") )
                return 0
                ;;
            validate)
                local validate_opts="--test-connection --providers --verbose --help"
                COMPREPLY=( $(compgen -W "${validate_opts}" -- "${cur}") )
                return 0
                ;;
            template)
                local template_opts="--providers --verbose --help"
                COMPREPLY=( $(compgen -W "${template_opts}" -- "${cur}") )
                return 0
                ;;
        esac
        return 0
    fi

    # Static completions for main command
    if [[ "${cur}" == -* ]]; then
        local main_opts="--provider --model --skip-questions --refine --output-format --copy --file --verbose --help"
        COMPREPLY=( $(compgen -W "${main_opts}" -- "${cur}") )
        return 0
    fi

    local subcommands="history list-models validate template completion"
    COMPREPLY=( $(compgen -W "${subcommands}" -- "${cur}") )
    return 0
}

complete -F _promptheus_complete promptheus
'''

ZSH_COMPLETION_TEMPLATE = '''#compdef promptheus

_promptheus() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _get_promptheus_executable() {
        if [[ -n "$VIRTUAL_ENV" ]] && [[ -x "$VIRTUAL_ENV/bin/promptheus" ]]; then
            echo "$VIRTUAL_ENV/bin/promptheus"
        elif command -v poetry &> /dev/null && [[ -f "pyproject.toml" ]]; then
            echo "poetry run promptheus"
        elif command -v promptheus &> /dev/null; then
            echo "promptheus"
        else
            return 1
        fi
    }

    local executable=$(_get_promptheus_executable)
    if [[ -z "$executable" ]]; then return 1; fi

    _arguments -C \
        '(- *)'{-h,--help}'[Show help message]' \
        '(- *)'{-v,--verbose}'[Enable verbose debug output]' \
        '1: :->cmds' \
        '*::arg:->args' && return 0

    case "$state" in
        cmds)
            local -a commands
            commands=(
                'history:View and manage prompt history'
                'list-models:List available models from providers'
                'validate:Validate environment configuration'
                'template:Generate a .env file template'
                'completion:Generate shell completion script'
            )
            _describe 'command' commands
            _arguments \
                '--provider[LLM provider to use]:provider:' \
                '--model[Specific model to use]:model:' \
                '(-s --skip-questions)'{-s,--skip-questions}'[Skip clarifying questions]' \
                '(-r --refine)'{-r,--refine}'[Force clarifying questions]' \
                '(-o --output-format)'{-o,--output-format}'[Output format]:format:(plain json)' \
                '(-c --copy)'{-c,--copy}'[Copy to clipboard]' \
                '(-f --file)'{-f,--file}'[Read from file]:file:_files'
            ;;
        args)
            case ${words[1]} in
                history)
                    _arguments \
                        '--clear[Clear all history]' \
                        '--limit[Number of entries to display]:limit:' \
                        '(- *)'{-h,--help}'[Show help message]' \
                        '(- *)'{-v,--verbose}'[Enable verbose output]'
                    ;;
                list-models)
                    _arguments \
                        '--providers[Comma-separated list of providers]:providers:' \
                        '--limit[Number of models to display]:limit:' \
                        '--include-nontext[Include non-text models]' \
                        '(- *)'{-h,--help}'[Show help message]' \
                        '(- *)'{-v,--verbose}'[Enable verbose output]'
                    ;;
                validate)
                    _arguments \
                        '--test-connection[Test API connection]' \
                        '--providers[Comma-separated list of providers]:providers:' \
                        '(- *)'{-h,--help}'[Show help message]' \
                        '(- *)'{-v,--verbose}'[Enable verbose output]'
                    ;;
                template)
                    _arguments \
                        '--providers[Comma-separated list of providers]:providers:' \
                        '(- *)'{-h,--help}'[Show help message]' \
                        '(- *)'{-v,--verbose}'[Enable verbose output]'
                    ;;
                completion)
                    _arguments \
                        '1:shell:(bash zsh)' \
                        '--install[Automatically install completion]' \
                        '(- *)'{-h,--help}'[Show help message]' \
                        '(- *)'{-v,--verbose}'[Enable verbose output]'
                    ;;
            esac
            ;;
    esac
}

_promptheus "$@"
'''

def generate_completion_script(shell: str):
    """Prints the completion script for the specified shell."""
    if not shell:
        logger.error("Shell type must be specified when not using --install")
        sys.exit(1)
    if shell == "bash":
        print(BASH_COMPLETION_TEMPLATE)
    elif shell == "zsh":
        print(ZSH_COMPLETION_TEMPLATE)
    else:
        logger.error("Invalid shell specified for completion: %s", shell)
        sys.exit(1)


def install_completion(shell: Optional[str], console: Console) -> None:
    """
    Automatically install shell completion by:
    1. Detecting the shell if not provided
    2. Finding the promptheus executable
    3. Creating a shell alias
    4. Installing the completion script
    5. Updating shell config
    """
    import subprocess
    import shutil
    from pathlib import Path

    # Detect shell if not provided
    if not shell:
        shell_path = os.getenv("SHELL", "")
        if "zsh" in shell_path:
            shell = "zsh"
        elif "bash" in shell_path:
            shell = "bash"
        else:
            console.print(f"[red]Could not detect shell from SHELL={shell_path}[/red]")
            console.print("Please specify shell explicitly: [cyan]promptheus completion --install bash[/cyan] or [cyan]zsh[/cyan]")
            sys.exit(1)

    console.print(f"[bold]Installing completion for {shell}...[/bold]\n")

    # Find promptheus executable
    try:
        # Try to find the actual promptheus script
        result = subprocess.run(
            ["which", "promptheus"],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0 and result.stdout.strip():
            promptheus_path = result.stdout.strip()
        else:
            # Fallback: check if we're in a poetry project
            if Path("pyproject.toml").exists():
                try:
                    result = subprocess.run(
                        ["poetry", "run", "which", "promptheus"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    promptheus_path = result.stdout.strip()
                except subprocess.CalledProcessError:
                    console.print("[red]Could not find promptheus executable[/red]")
                    console.print("Make sure promptheus is installed: [cyan]pip install -e .[/cyan]")
                    sys.exit(1)
            else:
                console.print("[red]Could not find promptheus executable[/red]")
                console.print("Make sure promptheus is installed: [cyan]pip install -e .[/cyan]")
                sys.exit(1)
    except Exception as exc:
        console.print(f"[red]Error finding promptheus: {exc}[/red]")
        sys.exit(1)

    console.print(f"[green]✓[/green] Found promptheus at: [cyan]{promptheus_path}[/cyan]")

    # Determine shell config file
    home = Path.home()
    if shell == "zsh":
        shell_config = home / ".zshrc"
        completion_dir = home / ".zsh" / "completions"
        completion_file = completion_dir / "_promptheus"
    else:  # bash
        shell_config = home / ".bashrc"
        completion_dir = home / ".bash_completion.d"
        completion_file = completion_dir / "promptheus.bash"

    # Create completion directory if it doesn't exist
    completion_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓[/green] Completion directory: [cyan]{completion_dir}[/cyan]")

    # Generate and save completion script
    template = ZSH_COMPLETION_TEMPLATE if shell == "zsh" else BASH_COMPLETION_TEMPLATE
    completion_file.write_text(template)
    console.print(f"[green]✓[/green] Saved completion script to: [cyan]{completion_file}[/cyan]")

    # Check if already configured
    shell_config_content = shell_config.read_text() if shell_config.exists() else ""

    # Add alias if promptheus is not in a standard location
    needs_alias = "/site-packages/" not in promptheus_path and ".local/bin" not in promptheus_path

    config_lines = []
    config_lines.append(f"\n# Promptheus completion (added by promptheus completion --install)")

    if needs_alias:
        alias_line = f'alias promptheus="{promptheus_path}"'
        if alias_line not in shell_config_content:
            config_lines.append(alias_line)
            console.print(f"[green]✓[/green] Adding alias: [cyan]{alias_line}[/cyan]")

    # Add completion loading
    if shell == "zsh":
        # Only add fpath if this specific directory isn't already there
        if str(completion_dir) not in shell_config_content:
            config_lines.append(f'fpath=({completion_dir} $fpath)')

        # Force reload completion and register for alias
        config_lines.append('autoload -Uz compinit && compinit -i')
        if needs_alias:
            config_lines.append('compdef _promptheus promptheus')
    else:  # bash
        source_line = f'source {completion_file}'
        if source_line not in shell_config_content:
            config_lines.append(source_line)

    # Write to shell config
    if len(config_lines) > 1:  # More than just the comment
        with open(shell_config, "a") as f:
            f.write("\n".join(config_lines) + "\n")
        console.print(f"[green]✓[/green] Updated shell config: [cyan]{shell_config}[/cyan]")
    else:
        console.print(f"[yellow]→[/yellow] Shell config already configured")

    # Final instructions
    console.print("\n[bold green]Installation complete![/bold green]\n")
    console.print("To activate completion in your current shell, run:")
    console.print(f"  [cyan]source {shell_config}[/cyan]\n")
    console.print("Or simply open a new terminal window.\n")
    console.print("[dim]Test it by typing:[/dim] [cyan]promptheus <TAB>[/cyan]")

def handle_completion_request(config: Config, args: "Namespace") -> None:
    """Handles the internal __complete command and prints completion data."""
    import json
    comp_type = args.type
    completions = []

    if comp_type == "providers":
        # Use all providers from the json, not just configured ones, for completion
        provider_data = config._ensure_provider_config().get("providers", {})
        completions = list(provider_data.keys())
    elif comp_type == "models":
        provider_name = args.provider
        if provider_name:
            # Get example models, as listing all models can be slow/require auth
            provider_data = config._ensure_provider_config().get("providers", {}).get(provider_name, {})
            completions = provider_data.get("example_models", [])

    # Print space-separated for bash completion (backward compatibility)
    print(" ".join(completions))


logger = logging.getLogger(__name__)

TEXT_ONLY_EXCLUDES = ("embed", "embedding", "image", "vision", "audio", "speech", "video", "sound", "draw", "paint", "whisper")


def _filter_text_models(models: List[str]) -> List[str]:
    """Filter out models that are not text-based."""
    filtered = []
    for model in models:
        lower = model.lower()
        if any(token in lower for token in TEXT_ONLY_EXCLUDES):
            continue
        filtered.append(model)
    return filtered


def get_provider_models(provider_name: str, config: Config) -> Tuple[List[str], Optional[str]]:
    """Get models for a specific provider using the actual provider implementation."""
    try:
        # Temporarily set the provider to the one we want to query
        original_provider = config.provider
        config.set_provider(provider_name)

        if not config.validate():
            # Extract the specific error message for the key
            error = config.consume_error_messages()
            if error and "API key" in error[0]:
                return [], "Error: API key not found or invalid"
            return [], f"Error: {error[0] if error else 'Unknown configuration error'}"

        provider = get_provider(provider_name, config)
        try:
            models = provider.get_available_models()
            logger.debug("Provider %s returned %d models (before filtering)", provider_name, len(models))
            return models, None
        except NotImplementedError:
            return [], f"Note: {provider_name.capitalize()} does not support listing models via API."
        except Exception as exc:
            error_msg = sanitize_error_message(str(exc))
            return [], f"Error: {error_msg}"

    except Exception as exc:
        error_msg = sanitize_error_message(str(exc))
        return [], f"Error: {error_msg}"
    finally:
        # Restore original provider setting
        if original_provider:
            config.set_provider(original_provider)
        else:
            config.reset() # Clear the temporary provider setting


def list_models(config: Config, console: Console, providers: Optional[List[str]] = None, include_nontext: bool = False, limit: int = 20) -> None:
    """Fetch and display available models for each configured LLM provider."""
    provider_config = config._ensure_provider_config()
    all_providers = providers or sorted(provider_config.get("providers", {}).keys())
    logger.debug("Listing models for providers: %s", all_providers)

    results = {}
    console.print(f"[dim]Querying {len(all_providers)} provider(s)...[/dim]")

    with console.status("[bold blue]📦 Fetching available models...", spinner="aesthetic"):
        for provider_name in all_providers:
            models, error = get_provider_models(provider_name, config)
            results[provider_name] = {"models": models, "error": error}

    console.print()
    # Display per-provider tables for readability
    for provider_name in all_providers:
        record = results.get(provider_name, {})
        models = record.get("models", [])
        filtered = models if include_nontext else _filter_text_models(models)
        if not include_nontext and len(models) > len(filtered):
            logger.debug("Filtered %d non-text models for provider %s", len(models) - len(filtered), provider_name)
        error = record.get("error")

        provider_aliases = provider_config.get("provider_aliases", {})
        display_name = provider_aliases.get(provider_name, provider_name.capitalize())

        provider_table = Table(
            title=f"{display_name} Models",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        provider_table.add_column("#", justify="right", style="dim", no_wrap=True)
        provider_table.add_column("Model ID / Status", style="green")

        if error:
            provider_table.add_row("-", f"[red]{error}[/red]")
        elif not filtered:
            message = (
                "[yellow]No models returned from API[/yellow]"
                if not models
                else "[yellow]No text-capable models found (use --include-nontext to show all)[/yellow]"
            )
            provider_table.add_row("-", message)
        else:
            display_models = filtered if limit <= 0 else filtered[:limit]
            for idx, model in enumerate(display_models, 1):
                provider_table.add_row(str(idx), model)
            total_count = len(filtered)
            if limit > 0 and total_count > limit:
                provider_table.add_row(
                    "…",
                    f"[dim]+{total_count - limit} more (use --limit 0 to show all)[/dim]",
                )

            if not include_nontext and len(filtered) < len(models):
                provider_table.add_row(
                    "-",
                    f"[dim]Filtered {len(models) - len(filtered)} non-text models (use --include-nontext to show all)[/dim]",
                )

        console.print(provider_table)
        console.print()


def _select_test_model(provider_name: str, config: Config) -> Optional[str]:
    """Pick a provider-specific model for connection testing."""
    provider_meta = config._ensure_provider_config().get("providers", {}).get(provider_name, {})

    # 1) Provider-specific MODEL env vars (e.g., OPENAI_MODEL) take precedence
    model_env = provider_meta.get("model_env")
    if model_env:
        env_value = os.getenv(model_env)
        if env_value:
            return env_value

    # 2) Use the provider's curated default model from providers.json
    default_model = provider_meta.get("default_model")
    if default_model:
        return default_model

    # 3) Fall back to the first example model if provided
    examples = provider_meta.get("example_models") or []
    if examples:
        return examples[0]

    # 4) Absolute fallback: global override (PROMPTHEUS_MODEL)
    return os.getenv("PROMPTHEUS_MODEL")


def _test_provider_connection(provider_name: str, config: Config) -> Tuple[bool, str]:
    """Attempt a simple API call to test credentials for a provider."""
    original_provider = None
    try:
        # Temporarily set the provider to ensure we use its settings for the test
        original_provider = config.provider
        config.set_provider(provider_name)

        test_model = _select_test_model(provider_name, config)
        logger.debug("Testing connection for %s with model %s", provider_name, test_model)
        provider = get_provider(provider_name, config, model_name=test_model)

        # Use a simple, low-cost prompt for testing
        provider._generate_text("ping", "", max_tokens=8)
        return True, ""
    except Exception as exc:
        if provider_name == "gemini" and "did not include text content" in str(exc):
            return False, "Connection failed. Note: Standard Gemini API keys may have limitations."
        return False, sanitize_error_message(str(exc))
    finally:
        # Restore original provider setting
        if original_provider:
            config.set_provider(original_provider)
        else:
            config.reset() # Clear the temporary provider setting


def validate_environment(config: Config, console: Console, test_connection: bool = False, providers: Optional[List[str]] = None) -> None:
    """Check environment for required API keys and optionally test connections."""
    console.print("[bold]Promptheus Environment Validator[/bold]")
    all_provider_data = config._ensure_provider_config().get("providers", {})
    provider_aliases = config._ensure_provider_config().get("provider_aliases", {})

    # If specific providers are requested, filter the data
    if providers:
        provider_data = {p: all_provider_data[p] for p in providers if p in all_provider_data}
        invalid_providers = [p for p in providers if p not in all_provider_data]
        if invalid_providers:
            console.print(f"[yellow]Warning: Unknown provider(s) specified: {', '.join(invalid_providers)}[/yellow]")
    else:
        provider_data = all_provider_data
    logger.debug("Validating providers: %s", list(provider_data.keys()))

    table = Table(title="Environment Validation Results")
    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("API Key Status", style="yellow")
    if test_connection:
        table.add_column("Connection", style="green")

    if not provider_data:
        console.print("[yellow]No providers to validate.[/yellow]")
        return

    ready_providers = []

    for name, info in sorted(provider_data.items()):
        display_name = provider_aliases.get(name, name.capitalize())
        api_key_env = info.get("api_key_env")
        keys = api_key_env if isinstance(api_key_env, list) else [api_key_env]
        
        key_found = any(os.getenv(key) for key in keys if key)
        logger.debug("Provider %s: key_found=%s", name, key_found)
        status = "[green]✓ Ready[/green]" if key_found else "[red]✗ Not Configured[/red]"
        key_status = "[green]Set[/green]" if key_found else f"[dim]Missing {keys[0] if keys else 'N/A'}[/dim]"

        row = [display_name, status, key_status]
        
        connection_passed = False
        if test_connection:
            if not key_found:
                row.append("[dim]Skipped[/dim]")
            else:
                with console.status(f"[dim]🔌 Testing {display_name}...[/dim]", spinner="simpleDots"):
                    connected, error = _test_provider_connection(name, config)
                logger.debug("Provider %s: connected=%s", name, connected)
                if connected:
                    row.append("[green]✓ Connected[/green]")
                    connection_passed = True
                else:
                    row.append(f"[red]✗ Failed: {error}[/red]")
        table.add_row(*row)

        # Logic for adding to recommendations
        if test_connection:
            if connection_passed:
                ready_providers.append(name)
        elif key_found:
            ready_providers.append(name)

    console.print(table)

    # Provide recommendations
    console.print("\n[bold]Recommendations:[/bold]")
    if not ready_providers:
        if providers:
            console.print("[yellow]None of the specified providers are ready.[/yellow]")
        else:
            console.print("[yellow]No providers configured. Use 'promptheus template <provider>' to get started.[/yellow]")
    else:
        console.print("[green]✓ Ready to use providers:[/green] " + ", ".join(f"[cyan]{p}[/cyan]" for p in ready_providers))


def generate_template(config: Config, console: Console, providers_input: str) -> None:
    """Generate and print an environment file template for one or more providers."""
    provider_names = [p.strip() for p in providers_input.split(',')]
    logger.debug("Generating .env template for providers: %s", provider_names)
    provider_data = config._ensure_provider_config().get("providers", {})
    provider_aliases = config._ensure_provider_config().get("provider_aliases", {})

    invalid_providers = [p for p in provider_names if p not in provider_data]
    if invalid_providers:
        print(f"Error: Unknown provider(s): {', '.join(invalid_providers)}", file=sys.stderr)
        print(f"Valid providers: {', '.join(provider_data.keys())}", file=sys.stderr)
        sys.exit(1)

    all_template_lines = []

    for idx, provider_name in enumerate(provider_names):
        provider_info = provider_data[provider_name]
        display_name = provider_aliases.get(provider_name, provider_name.capitalize())

        template_lines = []
        if idx > 0:
            template_lines.append("")

        template_lines.append(f"# {display_name} Environment Configuration")
        template_lines.append("")

        api_key_env = provider_info.get("api_key_env")
        keys = api_key_env if isinstance(api_key_env, list) else [api_key_env]

        # Handle multiple API keys with proper comments
        if len(keys) > 1:
            template_lines.append("# Required Variables (only one is needed)")
            for key in keys:
                if key:
                    template_lines.append(f"# {key}='YOUR_{key.upper()}_HERE'")
            # Uncomment the first one as the primary suggestion
            if keys[0]:
                template_lines[-1] = template_lines[-1].replace("# ", "")
        else:
            template_lines.append("# Required Variables")
            for key in keys:
                if key:
                    template_lines.append(f"{key}='YOUR_{key.upper()}_HERE'")

        optional_vars = [v for k, v in provider_info.items() if k.endswith("_env") and k not in ["api_key_env", "model_env"]]
        if optional_vars:
            template_lines.append("")
            template_lines.append("# Optional Variables")
            for var in optional_vars:
                if var:
                    template_lines.append(f"#{var}=")

        all_template_lines.extend(template_lines)

    print('\n'.join(all_template_lines))




