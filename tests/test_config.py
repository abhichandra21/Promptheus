import os
import json
from unittest.mock import patch, mock_open
from promptheus.config import Config, config

# Sample models.json content for testing
MODELS_JSON_CONTENT = {
    "providers": {
        "gemini": {
            "default_model": "gemini-pro",
            "models": ["gemini-pro", "gemini-1.5-pro"],
            "api_key_env": "GEMINI_API_KEY",
            "api_key_prefixes": ["AIza"]
        },
        "anthropic": {
            "default_model": "claude-3-opus",
            "models": ["claude-3-opus", "claude-3-sonnet"],
            "api_key_env": ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"],
            "base_url_env": "ANTHROPIC_BASE_URL",
            "api_key_prefixes": ["sk-ant-", "anthropic-"]
        }
    },
    "provider_aliases": {
        "gemini": "Gemini",
        "anthropic": "Claude"
    }
}

@patch.dict(os.environ, {}, clear=True)
@patch("promptheus.config.Config.load_model_config", return_value=MODELS_JSON_CONTENT)
def test_config_loads_from_json(mock_load_config, config):
    assert config.get_model() == "gemini-pro"  # Default provider

    config.set_provider("anthropic")
    assert config.get_model() == "claude-3-opus"

@patch.dict(os.environ, {"PROMPTHEUS_MODEL": "gemini-1.5-pro"}, clear=True)
@patch("promptheus.config.Config.load_model_config", return_value=MODELS_JSON_CONTENT)
def test_config_respects_env_var_for_model(mock_load_config, config):
    assert config.get_model() == "gemini-1.5-pro"

@patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-some-key"}, clear=True)
@patch("promptheus.config.Config.load_model_config", return_value=MODELS_JSON_CONTENT)
def test_config_detects_gemini_provider(mock_load_config, config):
    assert config.provider == "gemini"

@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-some-key"}, clear=True)
@patch("promptheus.config.Config.load_model_config", return_value=MODELS_JSON_CONTENT)
def test_config_detects_anthropic_provider(mock_load_config, config):
    assert config.provider == "anthropic"

@patch.dict(os.environ, {}, clear=True)
@patch("promptheus.config.Config.load_model_config", return_value=MODELS_JSON_CONTENT)
def test_get_provider_config(mock_load_config, config):
    gemini_config = config.get_provider_config()
    assert gemini_config["models"] == ["gemini-pro", "gemini-1.5-pro"]

    config.set_provider("anthropic")
    anthropic_config = config.get_provider_config()
    assert anthropic_config["models"] == ["claude-3-opus", "claude-3-sonnet"]

import pytest

@pytest.fixture
def config():
    return Config()
