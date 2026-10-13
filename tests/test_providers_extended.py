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

    assert "<<<CURRENT_PROMPT>>>" in payload
    assert "Current prompt" in payload
    assert "<<<END_CURRENT_PROMPT>>>" in payload
    assert "<<<TWEAK_REQUEST>>>" in payload
    assert "Make it more formal" in payload
    assert "<<<END_TWEAK_REQUEST>>>" in payload
    assert "Now return the tweaked prompt:" in payload


def test_format_tweak_payload_adds_guards_and_delimiters():
    """Tweak payload should include delimiters and preservation instructions."""
    provider = MockProvider()

    payload = provider._format_tweak_payload(
        "Line one\n- Bullet\nLine two",
        "Keep format, change tone"
    )

    assert "Preserve all line breaks" in payload
    assert "Keep length within ±10%" in payload
    assert "<<<CURRENT_PROMPT>>>" in payload
    assert "<<<END_CURRENT_PROMPT>>>" in payload
    assert "<<<TWEAK_REQUEST>>>" in payload
    assert "<<<END_TWEAK_REQUEST>>>" in payload


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


# --------------------------------------------------------------------------- #
# Structured question output and current-model response shapes
# --------------------------------------------------------------------------- #
from types import SimpleNamespace

from promptheus.exceptions import ProviderAPIError
from promptheus.providers import QUESTION_SCHEMA

_QUESTION_JSON = '{"task_type": "generation", "questions": []}'


class _BadRequest(Exception):
    """Stand-in for an SDK 400 error."""

    status_code = 400


def _anthropic_response(content, stop_reason="end_turn"):
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
    )


def _mock_anthropic_stream(provider, *results):
    """Point provider.client.messages.stream at canned results (responses or exceptions)."""
    provider.client = Mock()
    outcomes = list(results)

    def fake_stream(**kwargs):
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        manager = MagicMock()
        manager.__enter__.return_value.get_final_message.return_value = outcome
        return manager

    provider.client.messages.stream.side_effect = fake_stream
    return provider.client.messages.stream


def test_anthropic_skips_thinking_blocks():
    """Text is collected from text blocks even when a thinking block comes first."""
    provider = AnthropicProvider(api_key="test-key")
    _mock_anthropic_stream(
        provider,
        _anthropic_response(
            [
                SimpleNamespace(type="thinking", thinking=""),
                SimpleNamespace(type="text", text="refined "),
                SimpleNamespace(type="text", text="prompt"),
            ]
        ),
    )

    assert provider._generate_text("prompt", "system") == "refined prompt"


def test_anthropic_refusal_raises_provider_error():
    provider = AnthropicProvider(api_key="test-key")
    _mock_anthropic_stream(provider, _anthropic_response([], stop_reason="refusal"))

    with pytest.raises(ProviderAPIError, match="refusal"):
        provider._generate_text("prompt", "system")


def test_anthropic_questions_use_output_config_schema():
    provider = AnthropicProvider(api_key="test-key")
    stream = _mock_anthropic_stream(provider, _anthropic_response([SimpleNamespace(type="text", text=_QUESTION_JSON)]))

    result = provider.generate_questions("Write a post", "system")

    assert result == {"task_type": "generation", "questions": []}
    kwargs = stream.call_args.kwargs
    assert kwargs["output_config"] == {"format": {"type": "json_schema", "schema": QUESTION_SCHEMA}}


def test_anthropic_questions_retry_without_schema_on_400():
    """Models or proxies that reject output_config fall back to prompt-only JSON."""
    provider = AnthropicProvider(api_key="test-key")
    stream = _mock_anthropic_stream(
        provider,
        _BadRequest("output_config not supported"),
        _anthropic_response([SimpleNamespace(type="text", text=f"```json\n{_QUESTION_JSON}\n```")]),
    )

    result = provider.generate_questions("Write a post", "system")

    assert result == {"task_type": "generation", "questions": []}
    second_call = stream.call_args_list[1].kwargs
    assert "output_config" not in second_call
    assert provider._question_schema_enabled is False


def test_anthropic_questions_do_not_retry_on_non_400():
    provider = AnthropicProvider(api_key="test-key")
    error = _BadRequest("schema server error")
    error.status_code = 500
    stream = _mock_anthropic_stream(provider, error)

    with pytest.raises(ProviderAPIError):
        provider.generate_questions("Write a post", "system")
    assert stream.call_count == 1


def test_anthropic_questions_do_not_retry_on_unrelated_400():
    """A 400 that is not about the schema (e.g. low credit balance) must not disable it."""
    provider = AnthropicProvider(api_key="test-key")
    stream = _mock_anthropic_stream(provider, _BadRequest("Your credit balance is too low"))

    with pytest.raises(ProviderAPIError):
        provider.generate_questions("Write a post", "system")
    assert stream.call_count == 1
    assert provider._question_schema_enabled is True


def test_anthropic_truncated_reply_raises():
    """Hitting max_tokens with partial text must not be returned as a finished prompt."""
    provider = AnthropicProvider(api_key="test-key")
    _mock_anthropic_stream(
        provider,
        _anthropic_response([SimpleNamespace(type="text", text="half a prom")], stop_reason="max_tokens"),
    )

    with pytest.raises(ProviderAPIError, match="truncated"):
        provider._generate_text("prompt", "system")


def test_anthropic_raises_low_max_tokens_to_floor():
    from promptheus.constants import ANTHROPIC_MIN_MAX_TOKENS

    provider = AnthropicProvider(api_key="test-key")
    stream = _mock_anthropic_stream(provider, _anthropic_response([SimpleNamespace(type="text", text="ok")]))

    provider._generate_text("prompt", "system", max_tokens=4000)
    assert stream.call_args.kwargs["max_tokens"] == ANTHROPIC_MIN_MAX_TOKENS


def _chat_provider(cls, tmp_path, **kwargs):
    provider = cls(api_key="test-key", **kwargs)
    provider._endpoint_cache_path = tmp_path / "endpoint_cache.json"
    provider._endpoint_cache = {provider.model_name: "chat"}
    provider.client = Mock()
    provider.client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=_QUESTION_JSON))],
        usage=None,
    )
    return provider


def test_openai_chat_questions_use_strict_json_schema(tmp_path):
    provider = _chat_provider(OpenAIProvider, tmp_path)

    assert provider.generate_questions("Write a post", "system") == {"task_type": "generation", "questions": []}
    response_format = provider.client.chat.completions.create.call_args.kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"] == QUESTION_SCHEMA


def test_openai_chat_questions_fall_back_to_json_object_on_400(tmp_path):
    provider = _chat_provider(QwenProvider, tmp_path)
    ok = provider.client.chat.completions.create.return_value
    provider.client.chat.completions.create.side_effect = [_BadRequest("schema not available for model"), ok]

    assert provider.generate_questions("Write a post", "system") == {"task_type": "generation", "questions": []}
    second_call = provider.client.chat.completions.create.call_args_list[1].kwargs
    assert second_call["response_format"] == {"type": "json_object"}


def test_openai_responses_questions_use_text_format_schema(tmp_path):
    provider = OpenAIProvider(api_key="test-key")
    provider._endpoint_cache_path = tmp_path / "endpoint_cache.json"
    provider._endpoint_cache = {provider.model_name: "responses"}
    provider.client = Mock()
    provider.client.responses.create.return_value = SimpleNamespace(output_text=_QUESTION_JSON, usage=None)

    assert provider.generate_questions("Write a post", "system") == {"task_type": "generation", "questions": []}
    text_format = provider.client.responses.create.call_args.kwargs["text"]["format"]
    assert text_format["type"] == "json_schema"
    assert text_format["schema"] == QUESTION_SCHEMA


def test_glm_questions_use_json_object(tmp_path):
    """Z.ai only documents json_object, so GLM never sends a schema."""
    provider = _chat_provider(GLMProvider, tmp_path)

    provider.generate_questions("Write a post", "system")
    response_format = provider.client.chat.completions.create.call_args.kwargs["response_format"]
    assert response_format == {"type": "json_object"}


def test_gemini_questions_use_response_json_schema():
    provider = GeminiProvider(api_key="AIza-test")
    provider.client = Mock()
    provider.client.models.generate_content.return_value = SimpleNamespace(text=_QUESTION_JSON, usage_metadata=None)

    assert provider.generate_questions("Write a post", "system") == {"task_type": "generation", "questions": []}
    config = provider.client.models.generate_content.call_args.kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == QUESTION_SCHEMA


def test_provider_defaults_match_providers_json():
    """Constructor defaults should not drift from the curated providers.json defaults."""
    from pathlib import Path
    import inspect

    data = json.loads((Path(__file__).parent.parent / "src" / "promptheus" / "providers.json").read_text())
    defaults = {name: info["default_model"] for name, info in data["providers"].items()}
    classes = {
        "anthropic": AnthropicProvider,
        "google": GeminiProvider,
        "openai": OpenAIProvider,
        "groq": GroqProvider,
        "qwen": QwenProvider,
        "glm": GLMProvider,
        "openrouter": OpenRouterProvider,
    }
    for name, cls in classes.items():
        assert inspect.signature(cls.__init__).parameters["model_name"].default == defaults[name], name


def test_anthropic_gateway_keeps_caller_max_tokens():
    """Gateways may serve models with small output caps, so the 16k floor is first-party only."""
    provider = AnthropicProvider(api_key="test-key", base_url="https://api.z.ai/api/anthropic")
    stream = _mock_anthropic_stream(provider, _anthropic_response([SimpleNamespace(type="text", text="ok")]))

    provider._generate_text("prompt", "system", max_tokens=4000)
    assert stream.call_args.kwargs["max_tokens"] == 4000


def test_anthropic_gateway_from_env_keeps_caller_max_tokens(monkeypatch):
    """The SDK reads ANTHROPIC_BASE_URL itself, so the env var must also disable the floor."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://gateway.example.com")
    provider = AnthropicProvider(api_key="test-key")
    stream = _mock_anthropic_stream(provider, _anthropic_response([SimpleNamespace(type="text", text="ok")]))

    provider._generate_text("prompt", "system", max_tokens=4000)
    assert stream.call_args.kwargs["max_tokens"] == 4000


def test_schema_retry_survives_endpoint_switch(tmp_path):
    """A schema 400 on Chat makes the provider try Responses; a 404 there must not hide the 400."""

    class _NotFound(Exception):
        status_code = 404

    provider = _chat_provider(OpenAIProvider, tmp_path, base_url="https://llm.internal.example/v1")
    ok = provider.client.chat.completions.create.return_value
    provider.client.chat.completions.create.side_effect = [
        _BadRequest("Unsupported parameter: response_format.json_schema"),
        ok,
    ]
    provider.client.responses.create.side_effect = _NotFound("404 page not found")

    assert provider.generate_questions("Write a post", "system") == {"task_type": "generation", "questions": []}
    last_call = provider.client.chat.completions.create.call_args.kwargs
    assert last_call["response_format"] == {"type": "json_object"}
