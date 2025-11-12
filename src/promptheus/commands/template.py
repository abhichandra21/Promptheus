"""Template generation functionality."""

import logging
from typing import List

from rich.console import Console

from promptheus.config import Config
from promptheus.exceptions import InvalidProviderError

logger = logging.getLogger(__name__)


def generate_template(config: Config, console: Console, providers_input: str) -> str:
    """
    Generate an environment file template for one or more providers.

    Args:
        config: Configuration object containing provider information
        console: Console object for output
        providers_input: Comma-separated list of provider names

    Returns:
        The generated template as a string

    Raises:
        InvalidProviderError: When unknown providers are specified
    """
    provider_names = [p.strip() for p in providers_input.split(',')]
    logger.debug("Generating .env template for providers: %s", provider_names)
    provider_data = config._ensure_provider_config().get("providers", {})
    provider_aliases = config._ensure_provider_config().get("provider_aliases", {})

    invalid_providers = [p for p in provider_names if p not in provider_data]
    if invalid_providers:
        error_msg = f"Unknown provider(s): {', '.join(invalid_providers)}"
        valid_msg = f"Valid providers: {', '.join(provider_data.keys())}"

        # Use the provided console for error output
        console.print(f"[red]Error:[/red] {error_msg}")
        console.print(f"[dim]Valid providers: {valid_msg}[/dim]")

        raise InvalidProviderError(error_msg)

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

    return '\n'.join(all_template_lines)