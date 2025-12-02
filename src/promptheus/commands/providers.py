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
from promptheus._provider_data import _select_test_model, _test_provider_connection
from promptheus.models_dev_service import get_sync_models_for_provider

logger = logging.getLogger(__name__)


def get_provider_models(provider_name: str, config: Config, filter_text_only: bool = True) -> Tuple[List[str], Optional[str]]:
    """Get models for a specific provider.

    For most providers, uses models.dev service for comprehensive model listings.
    For OpenRouter, queries the provider's API directly since:
    - OpenRouter is an aggregator with hundreds of models from multiple providers
    - Model availability is API-key specific (not all users can access all models)
    - models.dev doesn't have OpenRouter's dynamic, user-specific model catalog
    """
    # Special handling for OpenRouter: query the provider's API directly
    if provider_name == "openrouter":
        try:
            provider = get_provider(provider_name, config)
            models = provider.get_available_models()
            logger.debug("Provider %s returned %d models from API", provider_name, len(models))
            return models, None
        except Exception as exc:
            error_msg = sanitize_error_message(str(exc))
            return [], f"Error fetching models from OpenRouter API: {error_msg}"

    # For other providers, use models.dev service
    try:
        models = get_sync_models_for_provider(provider_name, filter_text_only)
        logger.debug("Provider %s returned %d models from models.dev (filtered: %s)", provider_name, len(models), filter_text_only)
        return models, None
    except ValueError as exc:
        return [], f"Error: {str(exc)}"
    except Exception as exc:
        error_msg = sanitize_error_message(str(exc))
        return [], f"Error fetching models from models.dev: {error_msg}"


def list_models(config: Config, console: Console, providers: Optional[List[str]] = None, include_nontext: bool = False, limit: int = 20) -> None:
    """Fetch and display available models for each configured LLM provider."""
    provider_config = config._ensure_provider_config()
    all_providers = providers or sorted(provider_config.get("providers", {}).keys())
    logger.debug("Listing models for providers: %s", all_providers)

    results = {}
    console.print(f"[dim]Querying {len(all_providers)} provider(s)...[/dim]")

    with console.status("[bold blue]📦 Fetching available models...", spinner="aesthetic"):
        for provider_name in all_providers:
            # Use improved filtering from models.dev service
            models, error = get_provider_models(provider_name, config, filter_text_only=not include_nontext)
            results[provider_name] = {"models": models, "error": error}

    console.print()
    # Display per-provider tables for readability
    for provider_name in all_providers:
        record = results.get(provider_name, {})
        models = record.get("models", [])
        error = record.get("error")

        provider_info = provider_config.get("providers", {}).get(provider_name, {})
        display_name = config.get_display_name(provider_name, provider_info)

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
        elif not models:
            message = "[yellow]No models returned from API[/yellow]"
            provider_table.add_row("-", message)
        else:
            display_models = models if limit <= 0 else models[:limit]
            for idx, model in enumerate(display_models, 1):
                provider_table.add_row(str(idx), model)
            total_count = len(models)
            if limit > 0 and total_count > limit:
                provider_table.add_row(
                    "…",
                    f"[dim]+{total_count - limit} more (use --limit 0 to show all)[/dim]",
                )

            if not include_nontext:
                provider_table.add_row(
                    "-",
                    f"[dim]Showing text-generation models only (use --include-nontext to see all models)[/dim]",
                )

            # Add special note for OpenRouter
            if provider_name == "openrouter":
                provider_table.add_row(
                    "ℹ",
                    "[cyan]OpenRouter recommendation: Use 'openrouter/auto' for intelligent routing.\n"
                    "You can manually specify any model from https://openrouter.ai/models if you have access.[/cyan]",
                )

        console.print(provider_table)
        console.print()




def get_models_data(config: Config, providers: Optional[List[str]] = None, include_nontext: bool = False, limit: int = 20) -> dict:
    """
    Get models data for API/MCP usage (returns dict instead of printing).

    Returns:
        {
            "provider_name": {
                "available": bool,
                "models": [str, ...],
                "error": str (optional)
            }
        }
    """
    provider_config = config._ensure_provider_config()
    all_providers = providers or sorted(provider_config.get("providers", {}).keys())

    results = {}
    for provider_name in all_providers:
        models, error = get_provider_models(provider_name, config, filter_text_only=not include_nontext)

        if error:
            results[provider_name] = {
                "available": False,
                "error": error,
                "models": []
            }
        else:
            display_models = models if limit <= 0 else models[:limit]
            results[provider_name] = {
                "available": True,
                "models": [{"id": m, "name": m} for m in display_models],
                "total_count": len(models),
                "showing": len(display_models)
            }

    return results


def get_validation_data(config: Config, providers: Optional[List[str]] = None, test_connection: bool = False) -> dict:
    """
    Get validation data for API/MCP usage (returns dict instead of printing).

    Returns:
        {
            "provider_name": {
                "configured": bool,
                "api_key_status": str,
                "connection_test": str (if test_connection=True)
            }
        }
    """
    all_provider_data = config._ensure_provider_config().get("providers", {})

    if providers:
        provider_data = {p: all_provider_data[p] for p in providers if p in all_provider_data}
    else:
        provider_data = all_provider_data

    results = {}

    for name, info in provider_data.items():
        api_key_env = info.get("api_key_env")
        keys = api_key_env if isinstance(api_key_env, list) else [api_key_env]

        key_found = any(os.getenv(key) for key in keys if key)

        provider_result = {
            "configured": key_found,
            "api_key_status": "set" if key_found else f"missing_{keys[0] if keys else 'unknown'}"
        }

        if test_connection:
            if not key_found:
                provider_result["connection_test"] = "skipped"
            else:
                connected, error = _test_provider_connection(name, config)
                if connected:
                    provider_result["connection_test"] = "passed"
                else:
                    provider_result["connection_test"] = f"failed: {error}"

        results[name] = provider_result

    return results


def validate_environment(config: Config, console: Console, test_connection: bool = False, providers: Optional[List[str]] = None) -> None:
    """Check environment for required API keys and optionally test connections."""
    console.print("[bold]Promptheus Environment Validator[/bold]")
    all_provider_data = config._ensure_provider_config().get("providers", {})

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
        display_name = config.get_display_name(name, info)
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
