"""Providers API router for Promptheus Web UI."""
import json
import os
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from promptheus.config import Config
from promptheus.providers import get_available_providers, validate_provider

router = APIRouter()

class ProviderInfo(BaseModel):
    id: str
    name: str
    available: bool
    default_model: str
    example_models: List[str] = []


class ProviderSelection(BaseModel):
    provider_id: str


class ModelSelection(BaseModel):
    provider_id: str
    model: str


class ProvidersResponse(BaseModel):
    current_provider: str
    current_model: str
    available_providers: List[ProviderInfo]


class ModelsResponse(BaseModel):
    provider_id: str
    models: List[str]
    current_model: str


def load_providers_config() -> Dict[str, Any]:
    """Load providers configuration from providers.json."""
    providers_json_path = Path(__file__).parent.parent.parent / "providers.json"
    with open(providers_json_path, 'r') as f:
        return json.load(f)


async def fetch_all_models_from_provider(provider_id: str, app_config: Config, providers_config: Dict[str, Any]) -> List[str]:
    """Fetch all available models from a provider's API.

    Args:
        provider_id: The provider ID (e.g., 'gemini', 'openai')
        app_config: Configuration object
        providers_config: Providers configuration from JSON

    Returns:
        List of model names/IDs
    """
    import os

    provider_config = providers_config['providers'].get(provider_id, {})

    try:
        if provider_id == 'openai':
            try:
                from openai import OpenAI
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    return provider_config.get('example_models', [])

                client = OpenAI(api_key=api_key)
                models_response = client.models.list()
                # Filter for chat/completion models (GPT, o1, o3)
                models = [model.id for model in models_response.data
                         if any(prefix in model.id.lower() for prefix in ['gpt', 'o1', 'o3', 'chatgpt'])]
                return sorted(models, reverse=True)  # Reverse to show newer models first
            except Exception as e:
                print(f"Error listing OpenAI models: {e}")
                return provider_config.get('example_models', [])

        elif provider_id == 'anthropic':
            # Anthropic doesn't have a models API, return predefined list
            return [
                'claude-sonnet-4-5-20250929',
                'claude-haiku-4-5-20251001',
                'claude-3.7-sonnet-20250219',
                'claude-opus-4-20250514',
                'claude-3-5-sonnet-20241022',
                'claude-3-5-haiku-20241022',
                'claude-3-opus-20240229',
                'claude-3-sonnet-20240229',
                'claude-3-haiku-20240307'
            ]

        elif provider_id == 'gemini':
            # Try using the new google-genai SDK first, then fall back to google-generativeai
            api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if not api_key:
                return provider_config.get('example_models', [])

            try:
                # Try new google-genai SDK
                from google import genai
                client = genai.Client(api_key=api_key)
                models_response = client.models.list()
                models = []
                for model in models_response:
                    # Extract model name from full path (e.g., "models/gemini-2.0-flash" -> "gemini-2.0-flash")
                    model_name = model.name.split('/')[-1] if '/' in model.name else model.name
                    # Only include models that support generation
                    if hasattr(model, 'supported_generation_methods'):
                        if 'generateContent' in model.supported_generation_methods or 'generate_content' in model.supported_generation_methods:
                            models.append(model_name)
                    else:
                        # If no supported_generation_methods attribute, include if name contains 'gemini'
                        if 'gemini' in model_name.lower():
                            models.append(model_name)
                return sorted(set(models))
            except ImportError:
                # Fall back to old google-generativeai library
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    models_response = genai.list_models()
                    models = [model.name.replace('models/', '') for model in models_response
                             if hasattr(model, 'supported_generation_methods') and
                             'generateContent' in model.supported_generation_methods]
                    return sorted(models)
                except Exception as e:
                    print(f"Error listing Gemini models: {e}")
                    # Fallback to comprehensive predefined list
                    return [
                        'gemini-2.5-flash',
                        'gemini-2.5-pro',
                        'gemini-2.0-flash-exp',
                        'gemini-2.0-flash-thinking-exp-1219',
                        'gemini-2.0-flash',
                        'gemini-1.5-pro',
                        'gemini-1.5-flash',
                        'gemini-1.5-flash-8b',
                        'gemini-1.0-pro'
                    ]
            except Exception as e:
                print(f"Error listing Gemini models with new SDK: {e}")
                # Fallback to comprehensive predefined list
                return [
                    'gemini-2.5-flash',
                    'gemini-2.5-pro',
                    'gemini-2.0-flash-exp',
                    'gemini-2.0-flash-thinking-exp-1219',
                    'gemini-2.0-flash',
                    'gemini-1.5-pro',
                    'gemini-1.5-flash',
                    'gemini-1.5-flash-8b',
                    'gemini-1.0-pro'
                ]

        elif provider_id == 'groq':
            # Groq API often returns only active/popular models, so we combine API results with known models
            api_key = os.getenv('GROQ_API_KEY')

            # Comprehensive list of known Groq models (updated Dec 2024)
            known_groq_models = [
                'llama-3.3-70b-versatile',
                'llama-3.3-70b-specdec',
                'llama-3.2-1b-preview',
                'llama-3.2-3b-preview',
                'llama-3.2-11b-vision-preview',
                'llama-3.2-90b-vision-preview',
                'llama-3.1-70b-versatile',
                'llama-3.1-8b-instant',
                'llama3-70b-8192',
                'llama3-8b-8192',
                'llama3-groq-70b-8192-tool-use-preview',
                'llama3-groq-8b-8192-tool-use-preview',
                'mixtral-8x7b-32768',
                'gemma2-9b-it',
                'gemma-7b-it'
            ]

            if not api_key:
                # Return known models if no API key
                return known_groq_models

            try:
                from groq import Groq
                client = Groq(api_key=api_key)
                models_response = client.models.list()
                api_models = [model.id for model in models_response.data]

                # Combine API results with known models, remove duplicates
                all_models = list(set(api_models + known_groq_models))
                return sorted(all_models, reverse=True)
            except Exception as e:
                print(f"Error listing Groq models: {e}")
                # Fallback to known models
                return known_groq_models

        elif provider_id == 'qwen':
            # Qwen/DashScope doesn't expose a models API easily, return predefined list
            return [
                'qwen-turbo',
                'qwen-plus',
                'qwen-max',
                'qwen-max-longcontext',
                'qwen-vl-plus',
                'qwen-vl-max'
            ]

        elif provider_id == 'glm':
            # GLM/Zhipu doesn't expose a models API easily, return predefined list
            return [
                'glm-4.6',
                'glm-4.5-air',
                'glm-4',
                'glm-4-plus',
                'glm-4-air',
                'glm-3-turbo'
            ]

        else:
            # Default to example models
            return provider_config.get('example_models', [])

    except Exception as e:
        # On any error, fallback to example models
        print(f"Error fetching models for {provider_id}: {e}")
        return provider_config.get('example_models', [])


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers():
    """Get available providers and current selection."""
    try:
        app_config = Config()
        providers_config = load_providers_config()

        # Get available providers
        available_providers_data = get_available_providers(app_config)

        provider_infos = []
        for provider_id, provider_data in available_providers_data.items():
            # Get example models from providers.json
            provider_config = providers_config.get('providers', {}).get(provider_id, {})
            example_models = provider_config.get('example_models', [])

            provider_infos.append(ProviderInfo(
                id=provider_id,
                name=provider_data.get('name', provider_id.title()),
                available=provider_data.get('available', False),
                default_model=provider_data.get('default_model', 'default'),
                example_models=example_models
            ))

        return ProvidersResponse(
            current_provider=app_config.provider or "gemini",
            current_model=app_config.get_model(),
            available_providers=provider_infos
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/select")
async def select_provider(selection: ProviderSelection):
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
            detected_provider = app_config.provider or "gemini"
            return {"current_provider": detected_provider}

        # Validate the provider
        if not validate_provider(selection.provider_id, app_config):
            raise HTTPException(status_code=400, detail=f"Provider {selection.provider_id} is not available")

        # Update the configuration
        app_config.set_provider(selection.provider_id)

        # Persist the change to environment
        from dotenv import set_key
        from promptheus.config import find_and_load_dotenv

        env_path = find_and_load_dotenv()
        if env_path:
            set_key(env_path, "PROMPTHEUS_PROVIDER", selection.provider_id)
        os.environ["PROMPTHEUS_PROVIDER"] = selection.provider_id

        return {"current_provider": selection.provider_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/{provider_id}/models", response_model=ModelsResponse)
async def get_provider_models(provider_id: str, fetch_all: bool = False):
    """Get available models for a specific provider.

    Args:
        provider_id: The provider ID (e.g., 'gemini', 'openai')
        fetch_all: If True, fetch all available models from the provider API (slower)
                   If False, return only example models from config (faster, default)
    """
    try:
        app_config = Config()
        providers_config = load_providers_config()

        # Validate provider exists
        if provider_id not in providers_config.get('providers', {}):
            raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")

        provider_config = providers_config['providers'][provider_id]

        # Fetch models based on fetch_all parameter
        if fetch_all:
            models = await fetch_all_models_from_provider(provider_id, app_config, providers_config)
        else:
            models = provider_config.get('example_models', [])

        # Get current model for this provider
        current_model = provider_config.get('default_model', models[0] if models else 'default')

        # If this is the current provider, get the configured model
        if app_config.provider == provider_id:
            current_model = app_config.get_model()

        return ModelsResponse(
            provider_id=provider_id,
            models=models,
            current_model=current_model
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/select-model")
async def select_model(selection: ModelSelection):
    """Select a model for a specific provider."""
    try:
        app_config = Config()
        providers_config = load_providers_config()

        # Validate provider and model
        if selection.provider_id not in providers_config.get('providers', {}):
            raise HTTPException(status_code=404, detail=f"Provider {selection.provider_id} not found")

        provider_config = providers_config['providers'][selection.provider_id]
        available_models = provider_config.get('example_models', [])

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

        return {
            "provider_id": selection.provider_id,
            "current_model": selection.model
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
