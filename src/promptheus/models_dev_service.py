"""
Models.dev service for dynamic model listing.

This module provides a cached async client for fetching model catalogs
from models.dev API and exposing provider-specific model lists.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import aiohttp

# Mapping from canonical provider IDs to models.dev API IDs
PROVIDER_ID_MAPPING = {
    "google": "google",
    "anthropic": "anthropic",
    "openai": "openai",
    "groq": "groq",
    "qwen": "alibaba",
    "glm": "zhipuai"
}

# Canonical provider IDs that we support
MODELS_DEV_IDS = set(PROVIDER_ID_MAPPING.keys())

# Cache duration in seconds (24 hours)
CACHE_DURATION = 86400

# Platform-specific cache directory
if os.name == "nt":
    CACHE_DIR = Path(os.environ.get("APPDATA", "")) / "promptheus"
else:
    CACHE_DIR = Path.home() / ".promptheus"

CACHE_FILE = CACHE_DIR / "models_cache.json"


class ModelsDevService:
    """Async service for fetching and caching models from models.dev API."""

    MODELS_DEV_URL = "https://models.dev/api.json"

    def __init__(self):
        self._cache: Optional[Dict] = None
        self._cache_timestamp: Optional[float] = None
        # Try loading disk cache eagerly to avoid unnecessary network fetches
        asyncio.get_event_loop().create_task(self._load_cache_from_disk()) if asyncio.get_event_loop().is_running() else None

    async def _ensure_cache_loaded(self) -> None:
        """Ensure cache is loaded and fresh."""
        if self._cache is None and self._cache_timestamp is None:
            await self._load_cache_from_disk()

        if self._cache is None or self._is_cache_expired():
            await self._refresh_cache()

    def _is_cache_expired(self) -> bool:
        """Check if cache is expired."""
        if self._cache_timestamp is None:
            return True
        return time.time() - self._cache_timestamp > CACHE_DURATION

    async def refresh_cache(self) -> None:
        """Public method to refresh cache from models.dev API."""
        await self._refresh_cache()

    async def _refresh_cache(self) -> None:
        """Refresh cache from models.dev API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.MODELS_DEV_URL) as response:
                    response.raise_for_status()
                    data = await response.json()

                    self._cache = data
                    self._cache_timestamp = time.time()

                    # Save to disk
                    await self._save_cache_to_disk()

        except Exception as exc:
            # If we have cached data, use it even if expired
            if self._cache is not None:
                return
            # Otherwise raise the error
            raise RuntimeError(f"Failed to fetch models from models.dev: {exc}") from exc

    async def _save_cache_to_disk(self) -> None:
        """Save cache to disk."""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_data = {
                "cache": self._cache,
                "timestamp": self._cache_timestamp
            }
            with open(CACHE_FILE, "w") as f:
                json.dump(cache_data, f, indent=2)
        except Exception:
            # Ignore cache save errors - it's a nice-to-have
            pass

    async def _load_cache_from_disk(self) -> None:
        """Load cache from disk if available."""
        if not CACHE_FILE.exists():
            return

        try:
            with open(CACHE_FILE, "r") as f:
                cache_data = json.load(f)
                self._cache = cache_data.get("cache")
                self._cache_timestamp = cache_data.get("timestamp", 0)
        except Exception:
            # Ignore cache load errors - we'll fetch fresh data
            pass

    async def get_models_for_provider(self, provider_id: str, filter_text_only: bool = True) -> List[str]:
        """
        Get list of models for a specific provider.
        """
        all_models, text_models = await self.get_models_for_provider_split(provider_id)
        return text_models if filter_text_only else all_models

    async def get_models_for_provider_split(self, provider_id: str) -> tuple[List[str], List[str]]:
        """Return (all_models, text_models) for a provider using a single cache load."""
        if provider_id not in MODELS_DEV_IDS:
            raise ValueError(f"Unsupported provider ID: {provider_id}. Supported: {sorted(MODELS_DEV_IDS)}")

        await self._ensure_cache_loaded()

        if not self._cache:
            raise RuntimeError("Unable to load models from models.dev API")

        models_dev_id = PROVIDER_ID_MAPPING[provider_id]
        provider_data = self._cache.get(models_dev_id, {})
        models_data = provider_data.get("models", {})

        all_models = list(models_data.keys())
        text_models = [model_id for model_id, model_info in models_data.items() if self._is_text_generation_model(model_info)]
        return all_models, text_models

    def get_cache_timestamp(self) -> Optional[float]:
        """Return the epoch timestamp of the last successful cache refresh (if any)."""
        return self._cache_timestamp

    def _is_text_generation_model(self, model_info: Dict[str, Any]) -> bool:
        """
        Determine if a model is suitable for text generation based on models.dev metadata.

        Args:
            model_info: Model metadata from models.dev

        Returns:
            True if model is suitable for text generation
        """
        modalities = model_info.get("modalities", {})
        output_modalities = modalities.get("output", [])

        # Must output text
        if "text" not in output_modalities:
            return False

        # Exclude models that only do embeddings, audio generation, image generation, etc.
        model_id = model_info.get("id", "").lower()

        # Common patterns for non-text-generation models
        exclude_patterns = [
            "embed", "embedding",           # Embedding models
            "tts", "speech", "voice", "audio", # Text-to-speech models
            "image", "vision", "draw", "paint", # Image generation (unless also text)
            "video", "multimodal",           # Video generation
        ]

        # Check if model ID contains excluded patterns
        for pattern in exclude_patterns:
            if pattern in model_id:
                # Allow vision models if they also support text input/output
                if pattern in ["image", "vision"] and "text" in modalities.get("input", []):
                    continue
                return False

        return True

    async def get_model_metadata(self, provider_id: str, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed metadata for a specific model.

        Args:
            provider_id: Canonical provider ID
            model_id: Model ID

        Returns:
            Model metadata from models.dev, or None if not found
        """
        if provider_id not in MODELS_DEV_IDS:
            return None

        await self._ensure_cache_loaded()

        if not self._cache:
            return None

        # Map canonical provider ID to models.dev API ID
        models_dev_id = PROVIDER_ID_MAPPING[provider_id]

        # Extract models for the provider from cache
        provider_data = self._cache.get(models_dev_id, {})
        models_data = provider_data.get("models", {})

        return models_data.get(model_id)

    def get_supported_provider_ids(self) -> Set[str]:
        """Get set of supported provider IDs."""
        return MODELS_DEV_IDS.copy()

    async def get_all_models(self) -> Dict[str, List[str]]:
        """
        Get all models from all providers.

        Returns:
            Dict mapping provider_id to list of models
        """
        await self._ensure_cache_loaded()

        if not self._cache:
            raise RuntimeError("Unable to load models from models.dev API")

        result = {}
        for provider_id in MODELS_DEV_IDS:
            result[provider_id] = await self.get_models_for_provider(provider_id)

        return result

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self._cache = None
        self._cache_timestamp = None

    @classmethod
    def clear_disk_cache(cls) -> None:
        """Clear disk cache file."""
        if CACHE_FILE.exists():
            try:
                CACHE_FILE.unlink()
            except Exception:
                pass


# Sync helper for CLI usage
def get_sync_models_for_provider(provider_id: str, filter_text_only: bool = True) -> List[str]:
    """
    Synchronous helper for CLI usage.

    Args:
        provider_id: Canonical provider ID
        filter_text_only: If True, only return text-generation models (default: True)

    Returns:
        List of model names for the provider
    """
    async def _get_models():
        service = ModelsDevService()
        # Try to load from disk first for CLI speed
        await service._load_cache_from_disk()
        return await service.get_models_for_provider(provider_id, filter_text_only)

    try:
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an event loop, create a task and run it
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_models())
                return future.result()
        except RuntimeError:
            # No event loop running, use asyncio.run()
            return asyncio.run(_get_models())
    except Exception as exc:
        raise RuntimeError(f"Failed to get models for provider {provider_id}: {exc}") from exc


# Global service instance (one per process)
_service_instance: Optional[ModelsDevService] = None


def get_service() -> ModelsDevService:
    """Get or create global service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ModelsDevService()
    return _service_instance
