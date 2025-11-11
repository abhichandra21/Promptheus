"""
Configuration management for Promptheus.
Handles environment variables, .env files, and provider selection.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from promptheus.utils import sanitize_error_message

logger = logging.getLogger(__name__)

_PROJECT_ROOT_MARKERS = (".git", "pyproject.toml", "setup.py")


def _is_project_root(directory: Path) -> bool:
    """Return True when the directory looks like the project root."""
    return any((directory / marker).exists() for marker in _PROJECT_ROOT_MARKERS)


def find_and_load_dotenv(filename: str = ".env") -> Optional[Path]:
    """
    Search upward from the current working directory for a dotenv file
    and load it if found. Stops once the project root markers are crossed.
    Returns the path that was loaded or None.
    """
    current_dir = Path.cwd().resolve()

    for parent in (current_dir, *current_dir.parents):
        env_path = parent / filename
        if env_path.is_file():
            load_dotenv(dotenv_path=env_path)
            logger.debug("Loaded environment configuration from %s", env_path)
            return env_path

        if _is_project_root(parent):
            break

    logger.debug("No .env file discovered via upward search from %s", current_dir)
    return None


_LOADED_ENV_PATH = find_and_load_dotenv()

# Providers with full runtime support (keep in sync with promptheus.providers.get_provider)
SUPPORTED_PROVIDER_IDS = {"gemini", "anthropic", "openai", "groq", "qwen", "glm"}


class Config:
    """Configuration manager for Promptheus."""

    def __init__(self) -> None:
        self._provider: Optional[str] = None
        self.model: Optional[str] = None
        self._status_messages: List[str] = []
        self._error_messages: List[str] = []
        self._provider_config: Optional[Dict[str, Any]] = None

    def load_provider_config(self) -> Dict[str, Any]:
        """Load the provider configuration from the JSON file."""
        config_path = Path(__file__).parent / "providers.json"
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _ensure_provider_config(self) -> Dict[str, Any]:
        if self._provider_config is None:
            self._provider_config = self.load_provider_config()
        return self._provider_config

    def reset(self) -> None:
        """Reset provider/model selections and clear messages."""
        self._provider = None
        self.model = None
        self._status_messages.clear()
        self._error_messages.clear()
        self._provider_config = None

    # ------------------------------------------------------------------ #
    # Message helpers
    # ------------------------------------------------------------------ #
    def _record_status(self, message: str) -> None:
        self._status_messages.append(message)
        logger.debug(message)

    def _record_error(self, message: str) -> None:
        self._error_messages.append(message)
        logger.error(message)

    def consume_status_messages(self) -> List[str]:
        """Return and clear buffered status messages."""
        messages = self._status_messages[:]
        self._status_messages.clear()
        return messages

    def consume_error_messages(self) -> List[str]:
        """Return and clear buffered error messages."""
        messages = self._error_messages[:]
        self._error_messages.clear()
        return messages

    @property
    def provider(self) -> Optional[str]:
        if self._provider is None:
            self._detect_provider()
        return self._provider

    def set_provider(self, provider: str) -> None:
        """Manually set the provider (e.g., from CLI flag)."""
        config_data = self._ensure_provider_config()
        lowered = provider.lower()
        if lowered not in config_data.get("providers", {}):
            raise ValueError(f"Unknown provider: {provider}")
        if lowered not in SUPPORTED_PROVIDER_IDS:
            raise ValueError(f"Provider '{provider}' is not supported yet.")
        self._provider = lowered
        friendly = config_data.get("provider_aliases", {}).get(lowered, lowered.title())
        self._record_status(f"Switched to {friendly}")

    # ------------------------------------------------------------------ #
    # Provider detection and configuration
    # ------------------------------------------------------------------ #
    def _detect_provider(self) -> None:
        """Auto-detect provider based on environment variables."""
        if self._provider is not None:
            return

        config_data = self._ensure_provider_config()

        explicit_provider = os.getenv("PROMPTHEUS_PROVIDER")
        if explicit_provider:
            lowered = explicit_provider.lower()
            if lowered not in config_data.get("providers", {}):
                self._record_error(f"Unknown provider '{explicit_provider}' in PROMPTHEUS_PROVIDER")
            elif lowered in SUPPORTED_PROVIDER_IDS:
                self._provider = lowered
                friendly = config_data.get("provider_aliases", {}).get(lowered, lowered.title())
                self._record_status(f"Using {friendly}")
                return
            else:
                supported = ", ".join(sorted(SUPPORTED_PROVIDER_IDS))
                self._record_status(
                    f"Ignoring unsupported provider '{explicit_provider}'. Supported providers: {supported}"
                )

        providers = config_data.get("providers", {})
        priority = [name for name in providers.keys() if name in SUPPORTED_PROVIDER_IDS]
        if not priority:
            priority = ["gemini"] if "gemini" in providers else list(providers.keys()) or ["gemini"]

        for name in priority:
            info = providers.get(name, {})
            if name not in SUPPORTED_PROVIDER_IDS:
                continue
            env_keys = info.get("api_key_env")
            keys = env_keys if isinstance(env_keys, list) else [env_keys]
            if any(key and os.getenv(key) for key in keys):
                self._provider = name
                friendly = config_data.get("provider_aliases", {}).get(name, name.title())
                self._record_status(f"Using {friendly}")
                return

        # No credentials found; default to first provider in config (usually Gemini)
        fallback = priority[0]
        self._provider = fallback
        friendly = config_data.get("provider_aliases", {}).get(fallback, fallback.title())
        self._record_status(f"No API key found - using {friendly} (add your API key to switch)")

    def set_model(self, model: str) -> None:
        """Manually set the model (e.g., from CLI flag)."""
        self.model = model
        self._record_status(f"Using model: {self.model}")

    def get_model(self) -> str:
        """
        Get the model to use, following a specific override hierarchy.
        Hierarchy: CLI flag > Provider-specific Env Var > Global Env Var > Default
        """
        # 1. CLI flag (--model)
        if self.model:
            return self.model

        config_data = self._ensure_provider_config()
        provider_id = self.provider or "gemini"
        provider_info = config_data.get("providers", {}).get(provider_id, {})

        # 2. Provider-specific environment variable (e.g., OPENAI_MODEL)
        model_env_var = provider_info.get("model_env")
        if model_env_var:
            env_model = os.getenv(model_env_var)
            if env_model:
                return env_model

        # 3. Global environment variable (PROMPTHEUS_MODEL)
        global_env_model = os.getenv("PROMPTHEUS_MODEL")
        if global_env_model:
            return global_env_model

        # 4. Default model from providers.json
        return provider_info.get("default_model", "")

    def get_provider_config(self) -> Dict[str, Any]:
        """Get provider-specific configuration."""
        config_data = self._ensure_provider_config()
        provider = self.provider or "gemini"
        provider_info = config_data["providers"][provider]

        api_key = None
        api_key_env = provider_info.get("api_key_env")
        if isinstance(api_key_env, list):
            for key_env in api_key_env:
                if os.getenv(key_env):
                    api_key = os.getenv(key_env)
                    break
        elif api_key_env:
            api_key = os.getenv(api_key_env)

        config = {"api_key": api_key}

        # Add other optional env-based fields
        optional_env_fields = {
            "base_url": provider_info.get("base_url_env"),
            "organization": provider_info.get("organization_env"),
            "project": provider_info.get("project_env"),
        }
        for key, env_var in optional_env_fields.items():
            if not env_var:
                continue
            value = os.getenv(env_var)
            if value:
                config[key] = value

        return config

    def get_configured_providers(self) -> List[str]:
        """Return a list of providers that have an API key configured."""
        configured_providers = []
        config_data = self._ensure_provider_config()
        providers = config_data.get("providers", {})
        for name in SUPPORTED_PROVIDER_IDS:
            info = providers.get(name, {})
            env_keys = info.get("api_key_env")
            if not env_keys:
                continue
            keys = env_keys if isinstance(env_keys, list) else [env_keys]
            if any(key and os.getenv(key) for key in keys):
                configured_providers.append(name)
        return configured_providers

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def _validate_api_key_format(self, provider: str, api_key: Optional[str]) -> bool:
        if not api_key:
            return False

        config_data = self._ensure_provider_config()
        provider_info = config_data.get("providers", {}).get(provider, {})
        prefixes = provider_info.get("api_key_prefixes")
        if not prefixes:
            return True
        return any(api_key.startswith(prefix) for prefix in prefixes)

    def validate(self) -> bool:
        """Validate that required credentials are available and well-formed."""
        config_data = self._ensure_provider_config()
        provider_config = self.get_provider_config()
        api_key = provider_config.get("api_key")

        provider_names = config_data.get("provider_aliases", {})
        friendly_name = provider_names.get(self.provider or "", self.provider or "")

        if not api_key:
            self._record_error(f"Oops! No API key found for {friendly_name}")
            self._record_error(self._missing_key_instructions())
            return False

        # Always validate the API key format.
        if not self._validate_api_key_format(self.provider or "", api_key):
            has_custom_endpoint = (
                self.provider == "anthropic" and provider_config.get("base_url")
            )
            
            # For custom endpoints, show a warning but allow proceeding.
            if has_custom_endpoint:
                self._record_status(f"Warning: API key for {friendly_name} does not match the standard format, but proceeding due to custom endpoint.")
            else:
                # For standard endpoints, this is an error.
                sanitized = sanitize_error_message(api_key)
                self._record_error(f"Hmm, that API key for {friendly_name} doesn't look quite right (starts with '{sanitized[:4]}...').")
                self._record_error(self._missing_key_instructions())
                return False

        return True

    def _missing_key_instructions(self) -> str:
        if self.provider == "gemini":
            return (
                "To use Gemini, add GEMINI_API_KEY to your .env file.\n"
                "Get your free API key at: https://makersuite.google.com/app/apikey"
            )
        if self.provider == "anthropic":
            return (
                "To use Claude, add ANTHROPIC_API_KEY to your .env file.\n"
                "Get your API key at: https://console.anthropic.com\n"
                "(Or for Z.ai, use ANTHROPIC_AUTH_TOKEN and ANTHROPIC_BASE_URL)"
            )
        if self.provider == "openai":
            return (
                "To use OpenAI, add OPENAI_API_KEY to your .env file.\n"
                "Get your API key at: https://platform.openai.com/"
            )
        if self.provider == "groq":
            return (
                "To use Groq, add GROQ_API_KEY to your .env file.\n"
                "Get your API key at: https://console.groq.com/keys"
            )
        if self.provider == "qwen":
            return (
                "To use Qwen (DashScope-compatible), add DASHSCOPE_API_KEY to your .env file.\n"
                "Optionally set DASHSCOPE_HTTP_BASE_URL if you need the China region endpoint.\n"
                "Get your API key at: https://dashscope.aliyun.com/apiKey"
            )
        if self.provider == "glm":
            return (
                "To use GLM (Zhipu), add ZAI_API_KEY to your .env file.\n"
                "Optionally set ZAI_BASE_URL for self-hosted gateways."
            )
        return "Set the appropriate API key for the selected provider."

    # ------------------------------------------------------------------ #
    # History configuration
    # ------------------------------------------------------------------ #
    @property
    def history_enabled(self) -> bool:
        """
        Determine if history persistence should be enabled.

        Auto-detection strategy:
        - Interactive mode (sys.stdin.isatty() == True): Default to True
        - Non-interactive mode (sys.stdin.isatty() == False): Default to False
        - PROMPTHEUS_ENABLE_HISTORY environment variable overrides auto-detection

        This prevents silent persistence of sensitive prompts in batch scripts
        while maintaining a good default experience for interactive use.
        """
        # Explicit environment variable takes precedence
        explicit_setting = os.getenv("PROMPTHEUS_ENABLE_HISTORY")
        if explicit_setting is not None:
            return explicit_setting.lower() in ("1", "true", "yes", "on")

        # Auto-detect based on TTY status
        is_interactive = sys.stdin.isatty()
        return is_interactive


# Global config instance
config = Config()
