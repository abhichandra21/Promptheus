"""Settings API router for Promptheus Web UI."""
import os
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

from promptheus.config import Config, find_and_load_dotenv

router = APIRouter()

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
            options=["", "gemini", "anthropic", "openai", "groq", "qwen", "glm"],
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
            ("GEMINI_API_KEY", "Google Gemini API Key", "API key for Google Gemini models"),
            ("OPENAI_API_KEY", "OpenAI API Key", "API key for OpenAI GPT models"),
            ("ANTHROPIC_API_KEY", "Anthropic API Key", "API key for Claude models"),
            ("GROQ_API_KEY", "Groq API Key", "API key for Groq models"),
            ("QWEN_API_KEY", "Qwen API Key", "API key for Qwen/DashScope models"),
            ("GLM_API_KEY", "GLM API Key", "API key for Zhipu GLM models"),
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
async def update_settings(update: SettingsUpdate):
    """Update a setting in the environment."""
    try:
        # Validate the setting key
        valid_keys = [
            "PROMPTHEUS_PROVIDER", "PROMPTHEUS_MODEL", "PROMPTHEUS_ENABLE_HISTORY",
            "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", 
            "GROQ_API_KEY", "QWEN_API_KEY", "GLM_API_KEY"
        ]
        
        if update.key not in valid_keys:
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
        
        return {"success": True, "key": update.key, "value": update.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
