#!/usr/bin/env python3
"""
get_models.py - Utility script to fetch available models from LLM provider APIs.

This script connects to the APIs of supported LLM providers using the actual
provider implementations and fetches current lists of their available models
to help keep models.json up-to-date.
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Install with: pip install -r requirements-get-models.txt")
    sys.exit(1)

# Add src to path to import promptheus modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from promptheus.config import Config
    from promptheus.providers import get_provider
    from promptheus.utils import sanitize_error_message
except ImportError as e:
    print(f"Failed to import promptheus modules: {e}")
    print("Make sure you're running this from the project root with the virtual environment activated")
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and display available models for each configured LLM provider."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of models to display per provider (0 = show all).",
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        choices=["gemini", "anthropic", "openai", "groq", "qwen", "glm"],
        help="Subset of providers to query. Defaults to all supported providers.",
    )
    parser.add_argument(
        "--include-nontext",
        action="store_true",
        help="Show all models, including embeddings/audio/vision ones (default: text-capable only).",
    )
    return parser.parse_args()


def load_env() -> None:
    """Load environment variables from .env file."""
    env_file = None

    # Search for .env file in current directory and parent directories
    current_dir = os.getcwd()
    while current_dir != os.path.dirname(current_dir):
        env_file_path = os.path.join(current_dir, '.env')
        if os.path.exists(env_file_path):
            env_file = env_file_path
            break
        current_dir = os.path.dirname(current_dir)

    if env_file and os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value


def get_provider_models(provider_name: str) -> Tuple[List[str], Optional[str]]:
    """Get models for a specific provider using the actual provider implementation."""
    try:
        # Force the provider to be the one we want, regardless of auto-detection
        import os
        from dotenv import load_dotenv
        load_dotenv()

        # Set environment variable to force this provider
        original_provider = os.environ.get('PROMPTHEUS_PROVIDER')
        os.environ['PROMPTHEUS_PROVIDER'] = provider_name

        try:
            # Create a config for this specific provider
            config = Config()

            # Try to create the provider
            provider = get_provider(provider_name, config)

            # Try to get available models
            try:
                models = provider.get_available_models()
                return models, None
            except NotImplementedError:
                return [], f"Note: {provider_name.capitalize()} does not provide a public API to list available models"
            except Exception as exc:
                error_msg = sanitize_error_message(str(exc))
                return [], f"Error: {error_msg}"

        finally:
            # Restore original provider setting
            if original_provider is not None:
                os.environ['PROMPTHEUS_PROVIDER'] = original_provider
            else:
                os.environ.pop('PROMPTHEUS_PROVIDER', None)

    except Exception as exc:
        # This could be a configuration error (missing API key, etc.)
        error_msg = sanitize_error_message(str(exc))
        if "API key" in error_msg.lower() or "authentication" in error_msg.lower():
            return [], f"Error: API key not found or invalid"
        return [], f"Error: {error_msg}"


TEXT_ONLY_EXCLUDES = ("embed", "embedding", "image", "vision", "audio", "speech", "video", "sound", "draw", "paint", "whisper")


def _filter_text_models(models: List[str]) -> List[str]:
    filtered = []
    for model in models:
        lower = model.lower()
        if any(token in lower for token in TEXT_ONLY_EXCLUDES):
            continue
        filtered.append(model)
    return filtered


def main() -> None:
    """Main function to fetch and display models from all providers."""
    args = parse_args()
    # Load environment variables
    load_env()

    console = Console()

    # List of supported providers
    providers = args.providers or ["gemini", "anthropic", "openai", "groq", "qwen", "glm"]

    results = {}

    # Fetch models for each provider
    for provider_name in providers:
        console.print(f"Fetching models for {provider_name}...", style="dim")

        models, error = get_provider_models(provider_name)
        results[provider_name] = {"models": models, "error": error}

    # Display per-provider tables for readability
    for provider_name in providers:
        record = results.get(provider_name, {})
        models = record.get("models", [])
        filtered = models if args.include_nontext else _filter_text_models(models)
        error = record.get("error")

        display_name = "GLM" if provider_name == "glm" else provider_name.capitalize()
        provider_table = Table(
            title=f"{display_name} Models",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        provider_table.add_column("#", justify="right", style="dim", no_wrap=True)
        provider_table.add_column("Model / Status", style="green")

        if error:
            provider_table.add_row("-", f"[red]{error}[/red]")
        elif not filtered:
            message = (
                "[yellow]No models returned[/yellow]"
                if not models
                else "[yellow]No text-capable models after filtering (use --include-nontext)[/yellow]"
            )
            provider_table.add_row("-", message)
        else:
            limit = None if args.limit <= 0 else args.limit
            display_models = filtered if limit is None else filtered[:limit]
            for idx, model in enumerate(display_models, 1):
                provider_table.add_row(str(idx), model)
            total_count = len(filtered)
            if limit is not None and total_count > limit:
                provider_table.add_row(
                    "…",
                    f"[dim]+{total_count - limit} more (use --limit 0 to show all)[/dim]",
                )

            if not args.include_nontext and len(filtered) < len(models):
                provider_table.add_row(
                    "-",
                    f"[dim]Filtered {len(models) - len(filtered)} non-text models (use --include-nontext to show all)[/dim]",
                )

        console.print(provider_table)
        console.print()

    # Print summary
    total_providers = len(providers)
    successful_providers = sum(1 for r in results.values() if not r["error"] or "Note:" in r["error"])
    api_key_errors = sum(1 for r in results.values() if r["error"] and ("API key" in r["error"] or "authentication" in r["error"].lower()))
    other_errors = sum(1 for r in results.values() if r["error"] and "API key" not in r["error"] and "Note:" not in r["error"])

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"Total providers: {total_providers}")
    console.print(f"Successfully fetched: {successful_providers}")
    console.print(f"API key errors: {api_key_errors}")
    console.print(f"API limitations: {total_providers - successful_providers - api_key_errors}")

    try:
        model_config = Config().load_model_config()
        provider_metadata = model_config.get("providers", {})
    except Exception:
        provider_metadata = {}

    if api_key_errors > 0:
        console.print(f"\n[yellow]To see results from more providers, add API keys to your .env file:[/yellow]")
        for provider_name, result in results.items():
            if result["error"] and ("API key" in result["error"] or "authentication" in result["error"].lower()):
                provider_info = provider_metadata.get(provider_name, {})
                api_key_env = provider_info.get("api_key_env", f"{provider_name.upper()}_API_KEY")
                if isinstance(api_key_env, list):
                    api_key_env = api_key_env[0]

                provider_label = "GLM" if provider_name == "glm" else provider_name.capitalize()
                console.print(f"  {provider_label}: {api_key_env}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
