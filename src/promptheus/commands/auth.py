"""
Authentication command for Promptheus.
Based on OpenCode's authentication approach but adapted for Python.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from rich.console import Console
import questionary

console = Console()

def add_arguments(parser):
    parser.add_argument(
        "provider",
        nargs="?",
        help="The provider to authenticate with."
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip API key validation test"
    )

def get_available_providers() -> list[str]:
    """Get list of available providers based on the providers.json configuration."""
    try:
        from promptheus.config import Config
        config = Config()
        providers_config = config._ensure_provider_config()
        providers = list(providers_config.get("providers", {}).keys())
        return sorted(providers)
    except Exception:
        # Fallback to a default list of providers
        return ["anthropic", "openai", "google", "openrouter", "groq", "qwen", "glm"]

def update_env_file(env_var: str, value: str) -> None:
    """Update or add the environment variable to the .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        env_path.touch()

    # Read current .env content
    with open(env_path, "r") as f:
        content = f.read()

    # Update or add the environment variable
    lines = content.splitlines()
    env_line = f"{env_var}={value}"
    found = False
    new_lines = []

    for line in lines:
        if line.startswith(f"{env_var}="):
            new_lines.append(env_line)
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(env_line)

    # Write back to .env
    with open(env_path, "w") as f:
        f.write("\n".join(new_lines) + "\n")

def test_api_key(provider: str, api_key: str) -> bool:
    """Test if an API key is valid by making a simple test call."""
    import os
    from promptheus.config import Config
    from promptheus._provider_data import _test_provider_connection

    # Get provider info
    config = Config()
    providers_config = config._ensure_provider_config()
    provider_info = providers_config.get("providers", {}).get(provider, {})

    api_key_envs = provider_info.get("api_key_env", [])
    if isinstance(api_key_envs, str):
        api_key_envs = [api_key_envs]

    if not api_key_envs:
        return False

    env_var = api_key_envs[0]
    original_value = os.environ.get(env_var)

    try:
        # Temporarily set the API key in environment
        os.environ[env_var] = api_key

        # Create a fresh config to pick up the test API key
        test_config = Config()

        # Use the existing validation function
        connected, error = _test_provider_connection(provider, test_config)

        if not connected:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"API key validation failed for {provider}: {error}")

        return connected
    finally:
        # Restore original environment
        if original_value is not None:
            os.environ[env_var] = original_value
        elif env_var in os.environ:
            del os.environ[env_var]

def handle_provider_auth(provider: str, skip_validation: bool = False) -> bool:
    """Handle authentication for a specific provider."""
    from promptheus.config import Config
    config = Config()
    providers_config = config._ensure_provider_config()
    provider_info = providers_config.get("providers", {}).get(provider, {})

    # Get display name for user-friendly output
    display_name = config.get_display_name(provider, provider_info)

    if not provider_info:
        console.print(f"[red]✗ Provider '{provider}' is not supported yet.[/red]")
        return False

    api_key_envs = provider_info.get("api_key_env", [])
    if isinstance(api_key_envs, str):
        api_key_envs = [api_key_envs]

    if not api_key_envs:
        console.print(f"[red]✗ No API key environment variables defined for '{provider}'.[/red]")
        return False

    env_var = api_key_envs[0]  # Use the first available environment variable

    # Show intro
    console.print()
    console.print("[dim]┌[/dim] [bold]Add credential[/bold]")

    # Get provider information to show relevant instructions
    provider_desc = provider_info.get("display_name", display_name)

    # Get API key URL from provider configuration if available
    api_key_url = provider_info.get("api_key_url")
    if api_key_url:
        console.print(f"[dim]│[/dim]")
        console.print(f"[dim]│ {api_key_url}[/dim]")
    else:
        console.print(f"[dim]│[/dim]")
        console.print(f"[dim]│ Get your {provider_desc} API key from the provider's website[/dim]")

    console.print()
    api_key = questionary.password(
        f"Enter your {display_name} API key:",
        qmark="◆"
    ).ask()

    if not api_key:
        console.print(f"[dim]│[/dim]")
        console.print(f"[dim]└[/dim] [yellow]Cancelled[/yellow]")
        console.print()
        return False

    # Test the API key before saving (unless skipped)
    if not skip_validation:
        console.print(f"[dim]│[/dim]")
        console.print("[dim]│ Testing API key...[/dim]")
        if not test_api_key(provider, api_key):
            console.print(f"[dim]│[/dim]")
            console.print(f"[dim]└[/dim] [red]Failed[/red] - Invalid API key")
            console.print(f"[dim]  (Use --skip-validation to bypass this check)[/dim]")
            console.print()
            return False
    else:
        console.print(f"[dim]│[/dim]")
        console.print("[dim]│ Skipping validation[/dim]")

    # Save to .env file
    update_env_file(env_var, api_key)

    console.print(f"[dim]│[/dim]")
    console.print(f"[dim]└[/dim] [green]Done[/green]")
    console.print()
    return True

def auth_command(provider: Optional[str] = None, skip_validation: bool = False) -> None:
    """Handle the authentication flow for the specified provider."""
    from promptheus.config import Config

    all_providers = get_available_providers()

    # Create a mapping of display names to provider IDs
    config = Config()
    providers_config = config._ensure_provider_config()

    if not provider:
        # Show intro
        console.print()
        console.print("[dim]┌[/dim] [bold]Add credential[/bold]")
        console.print("[dim]│[/dim]")

        # Prepare choices with friendly names
        choices = []
        for prov_id in all_providers:
            provider_info = providers_config.get("providers", {}).get(prov_id, {})
            display_name = config.get_display_name(prov_id, provider_info)
            choices.append({
                'name': display_name,
                'value': prov_id
            })

        # Sort by common providers first
        priority = {
            'anthropic': 1,
            'openai': 2,
            'google': 3,
            'groq': 4,
            'openrouter': 5
        }
        choices.sort(key=lambda x: (priority.get(x['value'], 99), x['name']))

        # Add hints for recommended providers
        formatted_choices = []
        for choice in choices:
            prov_id = choice['value']
            name = choice['name']
            if priority.get(prov_id, 99) <= 2:
                formatted_choices.append(questionary.Choice(f"{name} (recommended)", value=prov_id))
            else:
                formatted_choices.append(questionary.Choice(name, value=prov_id))

        provider = questionary.select(
            "Select provider",
            choices=formatted_choices,
            qmark="◆",
            pointer="❯"
        ).ask()

        if not provider:
            console.print("[dim]│[/dim]")
            console.print(f"[dim]└[/dim] [yellow]Cancelled[/yellow]")
            console.print()
            return

    if provider not in all_providers:
        console.print(f"[red]✗ Provider '{provider}' is not supported yet.[/red]")
        return

    handle_provider_auth(provider, skip_validation=skip_validation)
