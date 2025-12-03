"""Settings API router for Promptheus Web UI."""
import logging
import os
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

from promptheus.config import Config, find_and_load_dotenv
from promptheus.utils import get_user_email, get_device_category

router = APIRouter()
logger = logging.getLogger(__name__)

class SettingMetadata(BaseModel):
    key: str
    label: str
    description: str
    type: str  # "text", "password", "select", "checkbox"
    value: str
    options: Optional[List[str]] = None  # For select type
    category: str  # "provider", "api_keys", "general"
    masked: bool = False  # Whether the value is masked (for API keys)

class SettingsUpdate(BaseModel):
    key: str
    value: str


class SettingsResponse(BaseModel):
    settings: List[SettingMetadata]


class ValidationRequest(BaseModel):
    provider: str
    api_key: str


class ValidationResponse(BaseModel):
    valid: bool
    provider: str
    error: Optional[str] = None
    error_type: Optional[str] = None
    suggestion: Optional[str] = None
    models_available: Optional[List[str]] = None
    account_info: Optional[Dict] = None


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current settings from environment with metadata."""
    try:
        app_config = Config()

        settings_list = []

        # Provider Selection Setting
        settings_list.append(SettingMetadata(
            key="PROMPTHEUS_PROVIDER",
            label="AI Provider",
            description="Select the AI provider to use for prompt refinement",
            type="select",
            value=app_config.provider or "",
            options=["", "google", "anthropic", "openai", "groq", "qwen", "glm", "openrouter"],
            category="provider"
        ))

        # Model Selection Setting
        settings_list.append(SettingMetadata(
            key="PROMPTHEUS_MODEL",
            label="Model",
            description="Select the specific model to use (leave empty for default)",
            type="text",
            value=app_config.get_model() or "",
            category="provider"
        ))

        # History Setting
        history_value = "true" if app_config.history_enabled else "false"
        settings_list.append(SettingMetadata(
            key="PROMPTHEUS_ENABLE_HISTORY",
            label="Enable History",
            description="Save prompt refinement history for later reference",
            type="checkbox",
            value=history_value,
            category="general"
        ))

        # API Keys
        api_keys = [
            ("GOOGLE_API_KEY", "Google Gemini API Key", "API key for Google Gemini models"),
            ("OPENAI_API_KEY", "OpenAI API Key", "API key for OpenAI GPT models"),
            ("ANTHROPIC_API_KEY", "Anthropic API Key", "API key for Claude models"),
            ("GROQ_API_KEY", "Groq API Key", "API key for Groq models"),
            ("DASHSCOPE_API_KEY", "Qwen API Key", "API key for Qwen/DashScope models"),
            ("ZHIPUAI_API_KEY", "GLM API Key", "API key for Zhipu GLM models"),
            ("OPENROUTER_API_KEY", "OpenRouter API Key", "API key for OpenRouter models"),
        ]

        for key, label, description in api_keys:
            api_key = os.getenv(key, "")
            masked_value = ""
            is_masked = False

            if api_key:
                # Mask the API key, showing only last 4 characters
                masked_value = "●" * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else "●" * len(api_key)
                is_masked = True

            settings_list.append(SettingMetadata(
                key=key,
                label=label,
                description=description,
                type="password",
                value=masked_value,
                category="api_keys",
                masked=is_masked
            ))

        return SettingsResponse(settings=settings_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings")
async def update_settings(update: SettingsUpdate, request: Request):
    """Update a setting in the environment."""
    try:
        # Validate the setting key
        valid_keys = [
            "PROMPTHEUS_PROVIDER", "PROMPTHEUS_MODEL", "PROMPTHEUS_ENABLE_HISTORY",
            "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "GROQ_API_KEY", "DASHSCOPE_API_KEY", "ZHIPUAI_API_KEY", "OPENROUTER_API_KEY"
        ]

        if update.key not in valid_keys:
            # Log failed user action
            logger.warning(
                "User failed to update settings - invalid key",
                extra={
                    "user": get_user_email(request),
                    "action": "settings_update",
                    "key": update.key,
                    "success": False,
                }
            )
            raise HTTPException(status_code=400, detail=f"Invalid setting key: {update.key}")

        # Update the .env file (if present) and reload environment variables
        env_path = find_and_load_dotenv()
        if env_path:
            set_key(env_path, update.key, update.value)
            load_dotenv(dotenv_path=env_path, override=True)

        # Ensure the running process sees the updated value immediately
        os.environ[update.key] = update.value

        # If updating provider or model, update config as well
        app_config = Config()
        if update.key == "PROMPTHEUS_PROVIDER":
            app_config.set_provider(update.value)
        elif update.key == "PROMPTHEUS_MODEL":
            app_config.set_model(update.value)

        # Log successful user action (mask API key values for security)
        masked_value = update.value
        if "API_KEY" in update.key and update.value:
            masked_value = "●" * (len(update.value) - 4) + update.value[-4:] if len(update.value) > 4 else "●" * len(update.value)

        logger.info(
            "User updated settings",
            extra={
                "user": get_user_email(request),
                "action": "settings_update",
                "key": update.key,
                "value": masked_value,
                "device_category": get_device_category(request),
                "success": True,
            }
        )

        return {"success": True, "key": update.key, "value": update.value}
    except HTTPException:
        raise
    except Exception as e:
        # Log failed user action
        logger.error(
            "User settings update failed",
            extra={
                "user": get_user_email(request),
                "action": "settings_update",
                "key": update.key,
                "success": False,
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/validate", response_model=ValidationResponse)
async def validate_api_key(validation_request: ValidationRequest, request: Request):
    """Validate an API key by testing connection to the provider."""
    try:
        from promptheus.providers import get_provider
        from promptheus.utils import sanitize_error_message

        provider_id = validation_request.provider.lower()
        # Normalize legacy aliases
        if provider_id == "dashscope":
            provider_id = "qwen"
        if provider_id == "gemini":
            provider_id = "google"
        if provider_id in {"zai", "zhipuai"}:
            provider_id = "glm"
        api_key = validation_request.api_key

        # Temporarily set the API key in environment for validation
        env_key_map = {
            "google": "GOOGLE_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "groq": "GROQ_API_KEY",
            "qwen": "DASHSCOPE_API_KEY",
            "glm": "ZHIPUAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY"
        }

        if provider_id not in env_key_map:
            return ValidationResponse(
                valid=False,
                provider=provider_id,
                error=f"Unknown provider: {provider_id}",
                error_type="invalid_provider",
                suggestion="Choose a valid provider: google, openai, anthropic, groq, qwen, glm, or openrouter"
            )

        env_key = env_key_map[provider_id]
        original_key = os.getenv(env_key)

        # Save and clear any model env vars to prevent interference
        original_promptheus_model = os.getenv("PROMPTHEUS_MODEL")
        original_provider_model_env = provider_id.upper() + "_MODEL"
        original_provider_model = os.getenv(original_provider_model_env)

        try:
            # Temporarily set the API key
            os.environ[env_key] = api_key

            # Clear model environment variables to ensure validation uses specified model
            if "PROMPTHEUS_MODEL" in os.environ:
                del os.environ["PROMPTHEUS_MODEL"]
            if original_provider_model_env in os.environ:
                del os.environ[original_provider_model_env]

            # Build config scoped to this provider so validation uses the supplied key
            app_config = Config()
            app_config.set_provider(provider_id)

            # Determine a model that belongs to this provider (ignore global PROMPTHEUS_MODEL overrides)
            provider_configs = app_config._ensure_provider_config()
            provider_info = provider_configs.get("providers", {}).get(provider_id, {})
            default_model = provider_info.get("default_model")
            example_models = provider_info.get("example_models", [])
            model_for_validation = default_model or (example_models[0] if example_models else None)

            # Special handling for OpenRouter: always use 'openrouter/auto' for validation
            # This ensures the validation works regardless of the user's model access/credits
            if provider_id == "openrouter":
                import httpx

                model_for_validation = "openrouter/auto"

                # Validate OpenRouter keys via the lightweight models endpoint with a short timeout
                base_url = os.getenv(provider_info.get("base_url_env", ""), "").rstrip("/") or "https://openrouter.ai/api/v1"
                models_url = f"{base_url}/models"
                headers = {"Authorization": f"Bearer {api_key}"}

                try:
                    response = httpx.get(models_url, headers=headers, timeout=10.0)
                    if response.status_code == 200:
                        # Log successful validation
                        logger.info(
                            "User validated API key",
                            extra={
                                "user": get_user_email(request),
                                "action": "api_key_validation",
                                "provider": provider_id,
                                "device_category": get_device_category(request),
                                "success": True,
                            }
                        )
                        return ValidationResponse(
                            valid=True,
                            provider=provider_id,
                            models_available=["openrouter/auto"]
                        )

                    sanitized_error = sanitize_error_message(response.text or f"Status {response.status_code}")
                    return ValidationResponse(
                        valid=False,
                        provider=provider_id,
                        error=sanitized_error,
                        error_type="validation_error",
                        suggestion="Ensure the OpenRouter key has at least one allowed provider/model enabled; routing always uses openrouter/auto."
                    )
                except httpx.TimeoutException:
                    return ValidationResponse(
                        valid=False,
                        provider=provider_id,
                        error="OpenRouter validation timed out",
                        error_type="network_error",
                        suggestion="OpenRouter models endpoint did not respond in time; try again or check connectivity."
                    )
                except Exception as e:
                    sanitized_error = sanitize_error_message(str(e))
                    return ValidationResponse(
                        valid=False,
                        provider=provider_id,
                        error=sanitized_error,
                        error_type="validation_error",
                        suggestion="Ensure the OpenRouter key has at least one allowed provider/model enabled; routing always uses openrouter/auto."
                    )

            # Try to initialize the provider with current configuration and provider-scoped model
            provider = get_provider(provider_id, app_config, model_for_validation)

            # Test with a simple prompt
            test_prompt = "Validation ping"
            validation_instruction = "Respond with 'OK'"
            try:
                # Try to generate a response (this will validate the API key)
                response = provider.light_refine(
                    prompt=test_prompt,
                    system_instruction=validation_instruction
                )

                # If we got here, the API key is valid
                models_available = []
                try:
                    # Try to get available models if provider supports it
                    if hasattr(provider, 'get_available_models'):
                        models_available = provider.get_available_models()
                except Exception:
                    # Not all providers support this, so just continue
                    pass

                # Log successful validation
                logger.info(
                    "User validated API key",
                    extra={
                        "user": get_user_email(request),
                        "action": "api_key_validation",
                        "provider": provider_id,
                        "success": True,
                    }
                )

                return ValidationResponse(
                    valid=True,
                    provider=provider_id,
                    models_available=models_available if models_available else None
                )

            except Exception as e:
                error_msg = str(e)
                sanitized_error = sanitize_error_message(error_msg)

                # Determine error type and provide suggestions
                error_type = "unknown_error"
                suggestion = "Check your API key and try again"

                if "401" in error_msg or "unauthorized" in error_msg.lower() or "invalid" in error_msg.lower():
                    error_type = "authentication_error"
                    suggestion = f"Invalid API key. Check your key at the {provider_id} dashboard"
                elif "403" in error_msg or "forbidden" in error_msg.lower():
                    error_type = "permission_error"
                    suggestion = "API key lacks required permissions"
                elif "429" in error_msg or "rate" in error_msg.lower():
                    error_type = "rate_limit_error"
                    suggestion = "Rate limit exceeded. Try again in a few moments"
                elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                    error_type = "network_error"
                    suggestion = f"Unable to reach {provider_id} servers. Check your internet connection"

                # Log failed validation
                logger.warning(
                    "User API key validation failed",
                    extra={
                        "user": get_user_email(request),
                        "action": "api_key_validation",
                        "provider": provider_id,
                        "error_type": error_type,
                        "success": False,
                    }
                )

                return ValidationResponse(
                    valid=False,
                    provider=provider_id,
                    error=sanitized_error,
                    error_type=error_type,
                    suggestion=suggestion
                )

        finally:
            # Restore original API key
            if original_key is not None:
                os.environ[env_key] = original_key
            elif env_key in os.environ:
                del os.environ[env_key]

            # Restore original model environment variables
            if original_promptheus_model is not None:
                os.environ["PROMPTHEUS_MODEL"] = original_promptheus_model
            if original_provider_model is not None:
                os.environ[original_provider_model_env] = original_provider_model

    except Exception as e:
        from promptheus.utils import sanitize_error_message
        error_msg = sanitize_error_message(str(e))

        # Log failed validation
        logger.error(
            "User API key validation error",
            extra={
                "user": get_user_email(request),
                "action": "api_key_validation",
                "provider": validation_request.provider,
                "success": False,
            },
            exc_info=True
        )

        return ValidationResponse(
            valid=False,
            provider=validation_request.provider,
            error=error_msg,
            error_type="validation_error",
            suggestion="An unexpected error occurred during validation"
        )
