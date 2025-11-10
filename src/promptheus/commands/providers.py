"""Provider-related command functionality."""

import logging
import os
from typing import List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich import box

from promptheus.config import Config
from promptheus.providers import get_provider, LLMProvider
from promptheus.utils import sanitize_error_message
from promptheus._provider_data import _filter_text_models, _select_test_model, _test_provider_connection

logger = logging.getLogger(__name__)


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