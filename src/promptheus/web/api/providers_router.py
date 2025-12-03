"""Providers API router for Promptheus Web UI."""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from promptheus.config import Config
from promptheus.providers import get_available_providers, validate_provider, get_provider
from promptheus.models_dev_service import get_service
from promptheus.utils import sanitize_error_message, get_user_email, get_device_category

router = APIRouter()
logger = logging.getLogger(__name__)

class ProviderInfo(BaseModel):
    id: str
    name: str
    available: bool
    default_model: str
    models: List[str] = []
    capabilities: Optional[Dict[str, Any]] = None

class ModelsResponseWithFilter(BaseModel):
    provider_id: str
    models: List[str]
    current_model: str
    text_generation_models: List[str]
    all_models: List[str]
    cache_last_updated: Optional[str] = None


class PreflightResult(BaseModel):
    provider_id: str
    display_name: str
    status: str  # ok | missing_key | error
    message: Optional[str] = None
    detail: Optional[str] = None
    duration_ms: Optional[int] = None
    model_used: Optional[str] = None


class ProviderSelection(BaseModel):
    provider_id: str


class ModelSelection(BaseModel):
    provider_id: str
    model: str


class ProvidersResponse(BaseModel):
    current_provider: str
    current_model: str
    available_providers: List[ProviderInfo]
    cache_last_updated: Optional[str] = None


class ModelsResponse(BaseModel):
    provider_id: str
    models: List[str]
    current_model: str


def load_providers_config() -> Dict[str, Any]:
    """Load providers configuration from providers.json."""
    providers_json_path = Path(__file__).parent.parent.parent / "providers.json"
    with open(providers_json_path, 'r') as f:
        return json.load(f)


async def get_models_for_provider(provider_id: str) -> List[str]:
    """Get models for a provider using models.dev service.

    Args:
        provider_id: The canonical provider ID (e.g., 'google', 'openai')

    Returns:
        List of model names/IDs from models.dev
    """
    service = get_service()
    return await service.get_models_for_provider(provider_id)


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers():
    """Get available providers and current selection."""
    try:
        app_config = Config()
        providers_config = load_providers_config()
        service = get_service()

        # Get available providers
        available_providers_data = get_available_providers(app_config)

        provider_infos = []
        for provider_id, provider_data in available_providers_data.items():
            provider_config = providers_config.get('providers', {}).get(provider_id, {})

            # For most providers, use models.dev for model listing. OpenRouter is handled
            # separately since models.dev does not track its aggregated catalog.
            if provider_id == "openrouter":
                models = provider_config.get("example_models") or ["openrouter/auto"]
            else:
                try:
                    models = await service.get_models_for_provider(provider_id)
                except Exception:
                    # If models.dev fails, use empty list
                    models = []

            provider_infos.append(ProviderInfo(
                id=provider_id,
                name=provider_data.get('name', provider_id.title()),
                available=provider_data.get('available', False),
                default_model=provider_data.get('default_model', 'default'),
                models=models,
                capabilities=provider_config.get('capabilities')
            ))

        cache_ts = service.get_cache_timestamp()
        cache_last_updated = datetime.fromtimestamp(cache_ts).isoformat() if cache_ts else None

        return ProvidersResponse(
            current_provider=app_config.provider or "google",
            current_model=app_config.get_model(),
            available_providers=provider_infos,
            cache_last_updated=cache_last_updated
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/select")
async def select_provider(selection: ProviderSelection, request: Request):
    """Select a provider as the current default."""
    try:
        app_config = Config()

        # Handle "Auto" provider (empty string means auto-detect)
        if selection.provider_id == "" or selection.provider_id.lower() == "auto":
            # Clear the provider preference to enable auto-detection
            from dotenv import set_key, unset_key
            from promptheus.config import find_and_load_dotenv

            env_path = find_and_load_dotenv()
            if env_path:
                try:
                    unset_key(env_path, "PROMPTHEUS_PROVIDER")
                except Exception:
                    # If unset_key doesn't exist, set to empty string
                    set_key(env_path, "PROMPTHEUS_PROVIDER", "")

            os.environ.pop("PROMPTHEUS_PROVIDER", None)

            # Auto-detect the provider again
            app_config.reset()
            detected_provider = app_config.provider or "google"

            # Log successful user action
            logger.info(
                "User selected auto provider",
                extra={
                    "user": get_user_email(request),
                    "action": "provider_select",
                    "provider": "auto",
                    "detected_provider": detected_provider,
                    "device_category": get_device_category(request),
                    "success": True,
                }
            )

            return {"current_provider": detected_provider}

        # Update the configuration
        app_config.set_provider(selection.provider_id)

        # Get the default model for this provider and set it
        providers_config = load_providers_config()
        provider_config = providers_config.get('providers', {}).get(selection.provider_id, {})
        default_model = provider_config.get('default_model', '')

        # Force OpenRouter to use auto-routing and keep envs in sync
        if selection.provider_id == "openrouter":
            default_model = "openrouter/auto"

        # Persist the changes to environment
        from dotenv import set_key
        from promptheus.config import find_and_load_dotenv

        env_path = find_and_load_dotenv()
        if env_path:
            set_key(env_path, "PROMPTHEUS_PROVIDER", selection.provider_id)
            # Set the model to the provider's default
            if default_model:
                model_env_key = provider_config.get('model_env', 'PROMPTHEUS_MODEL')
                set_key(env_path, model_env_key, default_model)
                # Keep the global PROMPTHEUS_MODEL aligned for OpenRouter
                if selection.provider_id == "openrouter":
                    set_key(env_path, "PROMPTHEUS_MODEL", default_model)

        os.environ["PROMPTHEUS_PROVIDER"] = selection.provider_id
        # Set the model in environment as well
        if default_model:
            model_env_key = provider_config.get('model_env', 'PROMPTHEUS_MODEL')
            os.environ[model_env_key] = default_model
            if selection.provider_id == "openrouter":
                os.environ["PROMPTHEUS_MODEL"] = default_model

        available = validate_provider(selection.provider_id, app_config)

        # Log successful user action
        logger.info(
            "User selected provider",
            extra={
                "user": get_user_email(request),
                "action": "provider_select",
                "provider": selection.provider_id,
                "available": available,
                "default_model": default_model,
                "device_category": get_device_category(request),
                "success": True,
            }
        )

        return {"current_provider": selection.provider_id, "available": available}
    except Exception as e:
        # Log failed user action
        logger.error(
            "User provider selection failed",
            extra={
                "user": get_user_email(request),
                "action": "provider_select",
                "provider": selection.provider_id,
                "success": False,
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/{provider_id}/models", response_model=ModelsResponseWithFilter)
async def get_provider_models(provider_id: str, include_nontext: bool = False, fetch_all: bool = False):
    """Get available models for a specific provider.

    For most providers, uses models.dev service for comprehensive model listings.
    For OpenRouter, queries the provider's API directly since:
    - OpenRouter is an aggregator with hundreds of models from multiple providers
    - Model availability is API-key specific (not all users can access all models)
    - models.dev doesn't have OpenRouter's dynamic, user-specific model catalog

    Args:
        provider_id: The provider ID (e.g., 'google', 'openai', 'openrouter')
        include_nontext: If True, include non-text-generation models
        fetch_all: Compatibility alias for include_nontext (used by Web UI)
    """
    try:
        app_config = Config()
        providers_config = load_providers_config()

        # Validate provider exists
        if provider_id not in providers_config.get('providers', {}):
            raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")

        provider_config = providers_config['providers'][provider_id]

        # Special handling for OpenRouter: query the provider's API directly
        if provider_id == "openrouter":
            try:
                provider = get_provider(provider_id, app_config)
                models = provider.get_available_models()

                # Get current model for OpenRouter
                current_model = provider_config.get('default_model', 'openrouter/auto')
                if app_config.provider == provider_id:
                    current_model = app_config.get_model()

                return ModelsResponseWithFilter(
                    provider_id=provider_id,
                    models=models,
                    current_model=current_model,
                    text_generation_models=models,
                    all_models=models,
                    cache_last_updated=None
                )
            except Exception as e:
                error_msg = sanitize_error_message(str(e))
                raise HTTPException(status_code=500, detail=f"Failed to fetch models from OpenRouter API: {error_msg}")

        # For other providers, use models.dev service
        service = get_service()

        # Get models from models.dev with single fetch and local filtering
        try:
            all_models, text_models = await service.get_models_for_provider_split(provider_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch models from models.dev: {str(e)}")

        # Use appropriate model list based on filter
        include_all = include_nontext or fetch_all
        models = all_models if include_all else text_models

        # Get current model for this provider
        current_model = provider_config.get('default_model', models[0] if models else 'default')

        # If this is the current provider, get the configured model
        if app_config.provider == provider_id:
            current_model = app_config.get_model()

        cache_ts = service.get_cache_timestamp()
        cache_last_updated = datetime.fromtimestamp(cache_ts).isoformat() if cache_ts else None

        return ModelsResponseWithFilter(
            provider_id=provider_id,
            models=models,
            current_model=current_model,
            text_generation_models=text_models,
            all_models=all_models,
            cache_last_updated=cache_last_updated
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/cache/refresh")
async def refresh_models_cache():
    """Force refresh the models.dev cache and return the new timestamp."""
    service = get_service()
    await service.refresh_cache()
    cache_ts = service.get_cache_timestamp()
    return {
        "refreshed": True,
        "cache_last_updated": datetime.fromtimestamp(cache_ts).isoformat() if cache_ts else None,
    }


@router.get("/providers/preflight", response_model=List[PreflightResult])
async def preflight_providers():
    """Validate configured providers with a lightweight refinement call."""
    config_data = load_providers_config()
    results: List[PreflightResult] = []

    for provider_id, provider_info in config_data.get("providers", {}).items():
        display_name = provider_info.get("display_name", provider_id.title())
        api_key_env = provider_info.get("api_key_env")
        keys = api_key_env if isinstance(api_key_env, list) else [api_key_env]

        if not any(k and os.getenv(k) for k in keys):
            results.append(PreflightResult(
                provider_id=provider_id,
                display_name=display_name,
                status="missing_key",
                message=f"Missing API key: {', '.join([k for k in keys if k])}"
            ))
            continue

        # Use a fresh Config per provider to avoid cross-contamination
        app_config = Config()
        try:
            app_config.set_provider(provider_id)
        except Exception as exc:
            results.append(PreflightResult(
                provider_id=provider_id,
                display_name=display_name,
                status="error",
                message="Failed to initialize provider",
                detail=sanitize_error_message(str(exc))
            ))
            continue

        start = datetime.now()
        try:
            provider = get_provider(provider_id, app_config, app_config.get_model())
            _ = provider.light_refine("Validation ping", "Respond with OK")
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)
            results.append(PreflightResult(
                provider_id=provider_id,
                display_name=display_name,
                status="ok",
                message="Ready",
                duration_ms=duration_ms,
                model_used=app_config.get_model()
            ))
        except Exception as exc:
            duration_ms = int((datetime.now() - start).total_seconds() * 1000)
            results.append(PreflightResult(
                provider_id=provider_id,
                display_name=display_name,
                status="error",
                message="Provider call failed",
                detail=sanitize_error_message(str(exc)),
                duration_ms=duration_ms,
                model_used=app_config.get_model()
            ))

    return results


@router.post("/providers/select-model")
async def select_model(selection: ModelSelection, request: Request):
    """Select a model for a specific provider."""
    try:
        app_config = Config()
        providers_config = load_providers_config()

        # Validate provider and model
        if selection.provider_id not in providers_config.get('providers', {}):
            raise HTTPException(status_code=404, detail=f"Provider {selection.provider_id} not found")

        provider_config = providers_config['providers'][selection.provider_id]

        # Validate model based on provider type
        if selection.provider_id == "openrouter":
            # For OpenRouter, get models from provider API
            try:
                provider = get_provider(selection.provider_id, app_config)
                models = provider.get_available_models()
                if selection.model not in models:
                    raise HTTPException(status_code=400, detail=f"Model {selection.model} not found for provider {selection.provider_id}")
            except HTTPException:
                raise
            except Exception:
                # If API call fails, still allow the selection
                pass
        else:
            # For other providers, validate using models.dev
            try:
                models = await get_models_for_provider(selection.provider_id)
                if selection.model not in models:
                    raise HTTPException(status_code=400, detail=f"Model {selection.model} not found for provider {selection.provider_id}")
            except Exception as e:
                # If models.dev is unavailable, still allow the selection
                pass

        # Update the configuration
        app_config.set_model(selection.model)

        # Persist the change to environment based on provider
        from dotenv import set_key
        from promptheus.config import find_and_load_dotenv

        env_path = find_and_load_dotenv()
        if env_path:
            model_env_key = provider_config.get('model_env')
            if model_env_key:
                set_key(env_path, model_env_key, selection.model)
            else:
                set_key(env_path, "PROMPTHEUS_MODEL", selection.model)

        model_env_key = provider_config.get('model_env')
        if model_env_key:
            os.environ[model_env_key] = selection.model
        os.environ["PROMPTHEUS_MODEL"] = selection.model

        # Log successful user action
        logger.info(
            "User selected model",
            extra={
                "user": get_user_email(request),
                "action": "model_select",
                "provider": selection.provider_id,
                "model": selection.model,
                "device_category": get_device_category(request),
                "success": True,
            }
        )

        return {
            "provider_id": selection.provider_id,
            "current_model": selection.model
        }
    except HTTPException:
        raise
    except Exception as e:
        # Log failed user action
        logger.error(
            "User model selection failed",
            extra={
                "user": get_user_email(request),
                "action": "model_select",
                "provider": selection.provider_id,
                "model": selection.model,
                "success": False,
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
