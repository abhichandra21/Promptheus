"""Essential tests for provider functionality."""

import json
import os
from unittest.mock import Mock, patch, MagicMock
import pytest

from promptheus.providers import (
    LLMProvider,
    GeminiProvider,
    AnthropicProvider,
    OpenAIProvider,
    GroqProvider,
    QwenProvider,
    GLMProvider,
    OpenRouterProvider,
    get_provider,
    _parse_question_payload,
    _append_json_instruction,
    _build_chat_messages,
    _coerce_message_content,
)
from promptheus.config import Config


class MockProvider(LLMProvider):
    """Mock provider for testing purposes."""
    
    def generate_questions(self, initial_prompt: str, system_instruction: str):
        # Not used in these tests but required for abstract base class
        return None
    
    def get_available_models(self):
        return ["test-model"]
    
    def _generate_text(self, prompt: str, system_instruction: str, json_mode: bool = False, max_tokens=None):
        return "Mocked response from provider"


def test_abstract_base_class():
    """Test that LLMProvider can't be instantiated without implementing abstract methods."""
    with pytest.raises(TypeError, match="abstract methods"):
        LLMProvider()


def test_parse_question_payload_valid():
    """Test parsing of valid JSON question payload."""
    valid_json = '{"task_type": "generation", "questions": [{"question": "Test?"}]}'
    result = _parse_question_payload("TestProvider", valid_json)
    
    assert result == {"task_type": "generation", "questions": [{"question": "Test?"}]}


def test_parse_question_payload_invalid_json():
    """Test parsing of invalid JSON."""
    invalid_json = "not json at all"
    result = _parse_question_payload("TestProvider", invalid_json)
    
    assert result is None


def test_parse_question_payload_missing_task_type():
    """Test parsing of JSON without task_type."""
    json_without_task_type = '{"questions": [{"question": "Test?"}]}'
    result = _parse_question_payload("TestProvider", json_without_task_type)
    
    assert result is None


def test_parse_question_payload_adds_empty_questions():
    """Test that missing questions field gets added."""
    json_without_questions = '{"task_type": "analysis"}'
    result = _parse_question_payload("TestProvider", json_without_questions)
    
    assert result == {"task_type": "analysis", "questions": []}


def test_append_json_instruction():
    """Test appending JSON instruction to prompts."""
    result = _append_json_instruction("Hello world")
    expected_suffix = (
        "Respond ONLY with a valid JSON object using double-quoted keys. "
        "Include the fields specified in the instructions (for example, task_type and questions). "
        "Do not wrap the JSON in markdown code fences or add commentary."
    )
    
    assert result.endswith(expected_suffix)


def test_append_json_instruction_idempotent():
    """Test that appending JSON instruction is idempotent."""
    prompt = "Hello world"
    first_result = _append_json_instruction(prompt)
    second_result = _append_json_instruction(first_result)
    
    assert first_result == second_result


def test_build_chat_messages():
    """Test building chat messages from system instruction and prompt."""
    messages = _build_chat_messages("system", "user prompt")
    
    assert len(messages) == 2
    assert messages[0] == {"role": "system", "content": "system"}
    assert messages[1] == {"role": "user", "content": "user prompt"}


def test_build_chat_messages_no_system():
    """Test building chat messages with no system instruction."""
    messages = _build_chat_messages("", "user prompt")
    
    assert len(messages) == 1
    assert messages[0] == {"role": "user", "content": "user prompt"}


def test_coerce_message_content_string():
    """Test coercing message content from string."""
    result = _coerce_message_content("hello world")
    assert result == "hello world"


def test_coerce_message_content_list():
    """Test coercing message content from list."""
    content_list = [{"text": "hello"}, {"content": "world"}]
    result = _coerce_message_content(content_list)
    assert result == "helloworld"


def test_coerce_message_content_with_attr():
    """Test coercing message content from object with text attribute."""
    mock_obj = Mock()
    mock_obj.text = "hello from object"
    result = _coerce_message_content(mock_obj)
    assert result == "hello from object"


def test_provider_factory_google(monkeypatch):
    """Test provider factory function for Google (Gemini models)."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    sample_models = {
        "providers": {
            "google": {
                "default_model": "gemini-pro",
                "models": ["gemini-pro", "gemini-1.5-pro"],
                "api_key_env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
                "api_key_prefixes": ["AIza", "AQ."],
            }
        },
        "provider_aliases": {"gemini": "google"},
    }
    monkeypatch.setattr("promptheus.config.Config.load_provider_config", lambda self: sample_models)
    
    config = Config()
    config.set_provider("google")
    
    provider = get_provider("google", config, "gemini-pro")
    
    assert isinstance(provider, GeminiProvider)
    assert provider.model_name == "gemini-pro"


def test_provider_factory_openai(monkeypatch):
    """Test provider factory function for OpenAI."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    
    sample_models = {
        "providers": {
            "openai": {
                "default_model": "gpt-4o",
                "models": ["gpt-4o", "gpt-4o-mini"],
                "api_key_env": "OPENAI_API_KEY",
                "api_key_prefixes": ["sk-"],
            }
        },
        "provider_aliases": {"openai": "OpenAI"},
    }
    monkeypatch.setattr("promptheus.config.Config.load_provider_config", lambda self: sample_models)
    
    config = Config()
    config.set_provider("openai")
    
    provider = get_provider("openai", config, "gpt-4o-mini")
    
    assert isinstance(provider, OpenAIProvider)
    assert provider.model_name == "gpt-4o-mini"


def test_provider_factory_unknown():
    """Test provider factory function with unknown provider."""
    config = Mock()
    
    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        get_provider("unknown", config)


def test_format_refinement_payload():
    """Test formatting of refinement payload."""
    # Since _format_refinement_payload is a concrete method that doesn't use abstract methods,
    # we can test it by creating a mock provider that implements abstract methods
    provider = MockProvider()
    
    payload = provider._format_refinement_payload(
        "Initial prompt",
        {"audience": "developers", "tone": "professional"},
        {"audience": "Who is the audience?", "tone": "What tone to use?"}
    )
    
    assert "Initial Prompt: Initial prompt" in payload
    assert "Who is the audience?: developers" in payload
    assert "What tone to use?: professional" in payload
    assert "Please generate a refined, optimized prompt" in payload


def test_format_tweak_payload():
    """Test formatting of tweak payload."""
    # Use the mock provider to test the concrete method
    provider = MockProvider()
    
    payload = provider._format_tweak_payload(
        "Current prompt",
        "Make it more formal"
    )
    
    assert "Current Prompt:" in payload
    assert "Current prompt" in payload
    assert "User's Modification Request:" in payload
    assert "Make it more formal" in payload
    assert "Return the tweaked prompt:" in payload


def test_refine_from_answers():
    """Test refining prompt from answers."""
    provider = MockProvider()
    # Mock the _generate_text method to return a specific value
    with patch.object(provider, '_generate_text', return_value="refined prompt") as mock_gen:
        result = provider.refine_from_answers(
            "initial",
            {"audience": "developers"},
            {"audience": "Who is the audience?"},
            "system instruction"
        )
        
        assert result == "refined prompt"
        mock_gen.assert_called_once()
        # Check that the call includes the formatted payload
        call_args = mock_gen.call_args
        assert "initial" in call_args[0][0]  # first argument is the prompt
        assert "Who is the audience?: developers" in call_args[0][0]


def test_tweak_prompt():
    """Test tweaking prompt with instruction."""
    provider = MockProvider()
    with patch.object(provider, '_generate_text', return_value="tweaked prompt") as mock_gen:
        result = provider.tweak_prompt(
            "current prompt",
            "Make it shorter",
            "system instruction"
        )
        
        assert result == "tweaked prompt"
        mock_gen.assert_called_once()
        call_args = mock_gen.call_args
        assert "current prompt" in call_args[0][0]
        assert "Make it shorter" in call_args[0][0]


def test_light_refine():
    """Test light refinement functionality."""
    provider = MockProvider()
    with patch.object(provider, '_generate_text', return_value="light refined prompt") as mock_gen:
        result = provider.light_refine("initial prompt", "system instruction")

        assert result == "light refined prompt"
        mock_gen.assert_called_once()


# ========================
# OpenAI-Compatible Provider Utility Tests
# ========================

def test_coerce_message_content_various_types():
    """Test _coerce_message_content handles various input types."""
    from promptheus.providers import _coerce_message_content

    # Test empty list
    result = _coerce_message_content([])
    assert result == ""

    # Test mixed types in list
    content_list = [{"text": "hello"}, "world", {"type": "text", "content": "test"}]
    result = _coerce_message_content(content_list)
    assert result == "hellotest"

    # Test None input
    result = _coerce_message_content(None)
    assert result == ""

    # Test numeric input
    result = _coerce_message_content(123)
    assert result == "123"


# ========================
# OpenRouter Provider Tests
# ========================


def _make_httpx_response(status_code=200, text="", json_data=None):
    """Helper to build a minimal httpx-like response object for OpenRouter tests."""

    class DummyResponse:
        def __init__(self, code, body, data):
            self.status_code = code
            self.text = body
            self._data = data

        def json(self):
            if isinstance(self._data, Exception):
                raise self._data
            return self._data

    return DummyResponse(status_code, text, json_data)


def test_openrouter_text_success(monkeypatch):
    """OpenRouterProvider should return text when API responds with choices."""
    import httpx

    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        data = {
            "choices": [
                {"message": {"content": "hello from openrouter"}},
            ]
        }
        return _make_httpx_response(status_code=200, text="", json_data=data)

    monkeypatch.setattr(httpx, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model_name="openrouter/auto")
    result = provider._generate_text("prompt", "system", json_mode=False, max_tokens=32)

    assert result == "hello from openrouter"
    assert len(calls) == 1
    assert calls[0]["json"]["model"] == "openrouter/auto"


def test_openrouter_uses_fallback_model_when_no_providers(monkeypatch):
    """OpenRouterProvider should fall back to OPENROUTER_FALLBACK_MODEL when platform returns 404 with No allowed providers."""
    import httpx

    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(json["model"])
        if len(calls) == 1:
            # First call: auto-routing model with no allowed providers
            return _make_httpx_response(
                status_code=404,
                text="No allowed providers for this key",
                json_data={"error": "No allowed providers"},
            )
        # Second call: fallback model succeeds
        data = {
            "choices": [
                {"message": {"content": "fallback response"}},
            ]
        }
        return _make_httpx_response(status_code=200, text="", json_data=data)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("OPENROUTER_FALLBACK_MODEL", "fallback/model")

    provider = OpenRouterProvider(api_key="test-key", model_name="openrouter/auto")
    result = provider._generate_text("prompt", "system", json_mode=False, max_tokens=16)

    assert result == "fallback response"
    # First call should use openrouter/auto, second the fallback
    assert calls == ["openrouter/auto", "fallback/model"]


def test_openrouter_non_200_raises_provider_error(monkeypatch):
    """Non-200 responses should raise ProviderAPIError with sanitized message."""
    import httpx
    from promptheus.exceptions import ProviderAPIError

    def fake_post(url, headers, json, timeout):
        return _make_httpx_response(status_code=500, text="Internal server error", json_data={})

    monkeypatch.setattr(httpx, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model_name="openrouter/auto")

    with pytest.raises(ProviderAPIError) as excinfo:
        provider._generate_text("prompt", "system")

    message = str(excinfo.value)
    assert "API call failed" in message
    assert "Status 500" in message


def test_openrouter_invalid_json_raises_provider_error(monkeypatch):
    """Invalid JSON from OpenRouter should raise ProviderAPIError."""
    import httpx
    from promptheus.exceptions import ProviderAPIError

    def fake_post(url, headers, json, timeout):
        # json() raises ValueError to simulate invalid JSON
        return _make_httpx_response(status_code=200, text="not-json", json_data=ValueError("invalid json"))

    monkeypatch.setattr(httpx, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model_name="openrouter/auto")

    with pytest.raises(ProviderAPIError) as excinfo:
        provider._generate_text("prompt", "system")

    assert "Invalid JSON response from OpenRouter" in str(excinfo.value)


def test_openrouter_missing_choices_raises_provider_error(monkeypatch):
    """Responses without choices should raise ProviderAPIError."""
    import httpx
    from promptheus.exceptions import ProviderAPIError

    def fake_post(url, headers, json, timeout):
        # No 'choices' key
        return _make_httpx_response(status_code=200, text="", json_data={"object": "chat.completion"})

    monkeypatch.setattr(httpx, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model_name="openrouter/auto")

    with pytest.raises(ProviderAPIError) as excinfo:
        provider._generate_text("prompt", "system")

    assert "OpenRouter response missing choices" in str(excinfo.value)


def test_openrouter_missing_text_raises_provider_error(monkeypatch):
    """Responses with empty message content should raise ProviderAPIError."""
    import httpx
    from promptheus.exceptions import ProviderAPIError

    def fake_post(url, headers, json, timeout):
        data = {"choices": [{"message": {"content": ""}}]}
        return _make_httpx_response(status_code=200, text="", json_data=data)

    monkeypatch.setattr(httpx, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model_name="openrouter/auto")

    with pytest.raises(ProviderAPIError) as excinfo:
        provider._generate_text("prompt", "system")

    assert "OpenRouter response missing text output" in str(excinfo.value)


def test_openrouter_error_payload_raises_provider_error(monkeypatch):
    """JSON responses with an error field should raise ProviderAPIError."""
    import httpx
    from promptheus.exceptions import ProviderAPIError

    def fake_post(url, headers, json, timeout):
        data = {"error": "simulated platform error"}
        return _make_httpx_response(status_code=200, text="", json_data=data)

    monkeypatch.setattr(httpx, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model_name="openrouter/auto")

    with pytest.raises(ProviderAPIError) as excinfo:
        provider._generate_text("prompt", "system")

    message = str(excinfo.value)
    assert "API call failed" in message
    assert "simulated platform error" in message


def test_openrouter_available_models_auto_only():
    """get_available_models should return the curated auto-routing model list."""
    provider = OpenRouterProvider(api_key="test-key", model_name="openrouter/auto")
    models = provider.get_available_models()

    assert models == ["openrouter/auto"]
