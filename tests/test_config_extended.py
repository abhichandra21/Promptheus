"""Essential tests for configuration functionality."""

import os
import tempfile
from unittest.mock import patch, Mock, MagicMock
import pytest
import json

from promptheus.config import Config, find_and_load_dotenv, _is_project_root
from pathlib import Path


@pytest.fixture
def temp_env_file():
    """Create a temporary .env file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
        f.write("GEMINI_API_KEY=AIza-test-key-from-env\n")
        f.write("OPENAI_API_KEY=sk-test-openai-key\n")
        temp_path = f.name
    
    yield Path(temp_path)
    
    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def config():
    """Create a fresh config instance for each test."""
    config = Config()
    # Reset to clear any cached values from other tests
    config.reset()
    return config


def test_config_initialization(config):
    """Test config initialization."""
    # Config auto-detects provider on first access to .provider property
    # so let's check after reset that provider is reset
    config.reset()
    assert config.model is None  # Model should be None initially
    assert config._status_messages == []  # After reset, messages should be cleared
    assert config._error_messages == []
    # Provider will be auto-detected when accessed, but after reset it's None until accessed
    assert config._provider is None


def test_load_model_config(config):
    """Test loading model configuration from JSON file."""
    config_data = config.load_provider_config()
    assert isinstance(config_data, dict)
    assert "providers" in config_data
    assert "provider_aliases" in config_data


def test_reset_config(config):
    """Test config reset functionality."""
    config._provider = "test"
    config.model = "test-model"
    config._status_messages = ["test message"]
    config._error_messages = ["test error"]
    
    config.reset()
    
    assert config._provider is None
    assert config.model is None
    assert config._status_messages == []
    assert config._error_messages == []


def test_message_consumption(config):
    """Test message consumption functionality."""
    config._record_status("status message")
    config._record_error("error message")
    
    status_messages = config.consume_status_messages()
    error_messages = config.consume_error_messages()
    
    assert status_messages == ["status message"]
    assert error_messages == ["error message"]
    
    # Messages should be cleared after consumption
    assert config.consume_status_messages() == []
    assert config.consume_error_messages() == []


def test_provider_property_auto_detection(monkeypatch, config):
    """Test provider auto-detection based on environment variables."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-key")
    
    # Reset config to trigger auto-detection
    config.reset()
    provider = config.provider
    
    assert provider == "gemini"


def test_provider_property_multiple_env_vars(monkeypatch, config):
    """Test provider auto-detection with multiple API keys."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-key")
    
    # Reset config to trigger auto-detection
    config.reset()
    provider = config.provider
    
    # Anthropic should be detected first based on priority order
    assert provider in ["anthropic", "gemini"]


def test_set_provider_valid(config):
    """Test setting a valid provider."""
    config.set_provider("gemini")
    
    assert config._provider == "gemini"


def test_set_provider_invalid(config):
    """Test setting an invalid provider."""
    with pytest.raises(ValueError, match="Unknown provider: invalid_provider"):
        config.set_provider("invalid_provider")


def test_set_provider_unsupported(monkeypatch, config):
    """Test setting an unsupported provider."""
    # Mock model config to include our provider but mark as unsupported
    original_load = config.load_provider_config
    def mock_load_config():
        config_data = original_load()
        config_data["providers"]["unsupported"] = {
            "default_model": "test-model",
            "models": ["test-model"],
            "api_key_env": "UNSUPPORTED_API_KEY"
        }
        return config_data
    
    monkeypatch.setattr(config, 'load_provider_config', mock_load_config)
    
    with pytest.raises(ValueError, match="not supported yet"):
        config.set_provider("unsupported")


def test_set_model(config):
    """Test setting a model."""
    config.set_model("test-model")
    
    assert config.model == "test-model"


def test_get_model_default(config, monkeypatch):
    """Test getting model with default fallback."""
    # Ensure no environment variable is set
    monkeypatch.delenv("PROMPTHEUS_MODEL", raising=False)
    
    model = config.get_model()
    
    # Should return default model for default provider (likely gemini)
    assert isinstance(model, str)
    assert len(model) > 0


def test_get_model_from_env(monkeypatch, config):
    """Test getting model from environment variable."""
    monkeypatch.setenv("PROMPTHEUS_MODEL", "env-model")
    
    model = config.get_model()
    
    assert model == "env-model"


def test_get_provider_config_gemini(monkeypatch, config):
    """Test getting provider configuration for Gemini."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-key")
    config.set_provider("gemini")

    provider_config = config.get_provider_config()

    assert provider_config["api_key"] == "AIza-test-key"
    assert isinstance(provider_config, dict)


def test_get_provider_config_openai(monkeypatch, config):
    """Test getting provider configuration for OpenAI."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    config.set_provider("openai")

    provider_config = config.get_provider_config()

    assert provider_config["api_key"] == "sk-test-key"
    assert isinstance(provider_config, dict)


def test_get_configured_providers(monkeypatch, config):
    """Test getting list of configured providers."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    
    configured = config.get_configured_providers()
    
    assert "gemini" in configured
    assert "anthropic" in configured


def test_validate_no_api_key():
    """Validation should fail loudly when the API key is missing."""
    # Save original os.getenv
    original_getenv = os.getenv

    # Define a custom getenv that returns None for API keys
    def mock_getenv(key, default=None):
        api_keys = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                    "GROQ_API_KEY", "DASHSCOPE_API_KEY", "ZAI_API_KEY"]
        if key in api_keys:
            return None
        return original_getenv(key, default)

    # Patch os.getenv in the config module where it's actually used
    with patch('promptheus.config.os.getenv', side_effect=mock_getenv):
        # Create a fresh config instance with mocked getenv
        config = Config()
        config.set_provider("gemini")  # Set a provider to validate
        is_valid = config.validate()

        assert not is_valid
        error_messages = config.consume_error_messages()
        assert any("No API key" in msg or "To use Gemini" in msg for msg in error_messages)


def test_validate_with_api_key(monkeypatch, config):
    """Test validation with valid API key."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-valid-key")
    config.set_provider("gemini")
    
    is_valid = config.validate()
    
    assert is_valid


def test_validate_invalid_api_key_format(monkeypatch, config):
    """Test validation with invalid API key format."""
    monkeypatch.setenv("GEMINI_API_KEY", "invalid-key-format")
    config.set_provider("gemini")
    
    is_valid = config.validate()
    
    assert not is_valid
    error_messages = config.consume_error_messages()
    assert any("doesn't look quite right" in msg for msg in error_messages)


def test_validate_valid_anthropic_key_format(monkeypatch, config):
    """Test validation with valid Anthropic API key format."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    config.set_provider("anthropic")
    
    is_valid = config.validate()
    
    assert is_valid


def test_validate_custom_endpoint_skips_format_check(monkeypatch, config):
    """Test that custom endpoints skip format validation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "invalid-format-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://custom.example.com")
    config.set_provider("anthropic")
    
    is_valid = config.validate()
    
    # Should be valid despite invalid format because of custom endpoint
    assert is_valid


def test_prometheus_provider_env_var(monkeypatch, config):
    """Test provider detection from PROMPTHEUS_PROVIDER environment variable."""
    monkeypatch.setenv("PROMPTHEUS_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    
    # Reset config to trigger detection
    config.reset()
    provider = config.provider
    
    assert provider == "openai"


def test_prometheus_provider_env_var_unknown(monkeypatch):
    """Test unknown provider in PROMPTHEUS_PROVIDER environment variable."""
    monkeypatch.delenv("PROMPTHEUS_PROVIDER", raising=False)
    monkeypatch.setenv("PROMPTHEUS_PROVIDER", "unknown_provider")

    config = Config()
    config.reset()  # Force re-evaluation of environment variables
    # Access the provider property to trigger validation
    _ = config.provider
    # Get the error messages - they should contain the unknown provider message
    error_messages = config.consume_error_messages()
    assert any("Unknown provider" in msg and "unknown_provider" in msg for msg in error_messages)


def test_load_dotenv_functionality(temp_env_file, monkeypatch):
    """Test the find_and_load_dotenv function."""
    # Temporarily change to the directory containing the temp file
    original_cwd = os.getcwd()
    temp_dir = temp_env_file.parent
    
    try:
        os.chdir(temp_dir)
        
        # Remove any existing env vars that might interfere
        for key in ["GEMINI_API_KEY", "OPENAI_API_KEY"]:
            monkeypatch.delenv(key, raising=False)
        
        # Call the function
        result = find_and_load_dotenv(temp_env_file.name)
        
        # Verify it loaded the file
        assert result is not None
        assert result.name == temp_env_file.name
        
        # Verify environment variables were loaded
        assert os.getenv("GEMINI_API_KEY") == "AIza-test-key-from-env"
        assert os.getenv("OPENAI_API_KEY") == "sk-test-openai-key"
        
    finally:
        os.chdir(original_cwd)


def test_is_project_root_with_git_marker(tmp_path):
    """Test _is_project_root with .git marker."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    
    assert _is_project_root(tmp_path)


def test_is_project_root_with_pyproject_marker(tmp_path):
    """Test _is_project_root with pyproject.toml marker."""
    (tmp_path / "pyproject.toml").touch()
    
    assert _is_project_root(tmp_path)


def test_is_project_root_with_setup_marker(tmp_path):
    """Test _is_project_root with setup.py marker."""
    (tmp_path / "setup.py").touch()
    
    assert _is_project_root(tmp_path)


def test_is_project_root_not_project(tmp_path):
    """Test _is_project_root with no markers."""
    assert not _is_project_root(tmp_path)
