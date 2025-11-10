"""Completion-related command functionality."""

import logging
import sys
from typing import Optional

from rich.console import Console

from promptheus.completions import generate_completion_script, install_completion

logger = logging.getLogger(__name__)


def handle_completion_request(config, args):
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