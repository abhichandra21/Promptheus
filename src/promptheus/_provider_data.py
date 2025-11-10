"""
Shared provider utilities used by completion and validation commands.

This module contains common provider-related functionality that is used
across different command modules to avoid code duplication.
"""

import os
from typing import Optional, Tuple

from promptheus.config import Config
from promptheus.providers import get_provider
from promptheus.utils import sanitize_error_message


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


def _filter_text_models(models, excludes=None):
    """Filter out models that are not text-based."""
    if excludes is None:
        excludes = ("embed", "embedding", "image", "vision", "audio", "speech", "video", "sound", "draw", "paint", "whisper")

    filtered = []
    for model in models:
        lower = model.lower()
        if any(token in lower for token in excludes):
            continue
        filtered.append(model)
    return filtered