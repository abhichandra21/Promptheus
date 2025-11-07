import json
from types import SimpleNamespace

from promptheus.config import Config
from promptheus.providers import (
    GeminiProvider,
    GLMProvider,
    GroqProvider,
    OpenAIProvider,
    QwenProvider,
    _JSON_ONLY_SUFFIX,
    _append_json_instruction,
    _parse_question_payload,
    get_provider,
)


def test_gemini_generate_text_applies_max_tokens():
    """Ensure the Gemini provider forwards max_tokens into the API call."""
    from unittest.mock import Mock, patch

    # Mock the import - patch 'google.genai.Client' where it's imported from
    with patch('google.genai.Client') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock the generate_content response
        mock_response = Mock()
        mock_response.text = "result"
        mock_client.models.generate_content.return_value = mock_response

        # Create provider with mocked dependencies
        provider = GeminiProvider("fake-key")

        result = provider._generate_text("prompt", "system", max_tokens=321)

        # Verify the result
        assert result == "result"

        # Verify the API was called with correct parameters
        mock_client.models.generate_content.assert_called_once()
        call_args = mock_client.models.generate_content.call_args

        # Check that max_output_tokens was set in the config
        config_arg = call_args[1]['config']  # config is passed as keyword argument

        # GenerateContentConfig is created with max_output_tokens=321
        from google.genai import types
        assert isinstance(config_arg, types.GenerateContentConfig)

        # Check the config has the correct max_output_tokens
        assert isinstance(config_arg, types.GenerateContentConfig)

        # The config should contain max_output_tokens=321
        assert 'max_output_tokens=321' in repr(config_arg)


def test_get_provider_supplies_available_models(monkeypatch):
    """get_provider should pass configured models into GeminiProvider."""
    sample_models = {
        "providers": {
            "gemini": {
                "default_model": "gemini-pro",
                "models": ["gemini-pro", "gemini-1.5-pro"],
                "api_key_env": "GEMINI_API_KEY",
                "api_key_prefixes": ["AIza"],
            }
        },
        "provider_aliases": {"gemini": "Gemini"},
    }

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr("promptheus.config.Config.load_model_config", lambda self: sample_models)

    cfg = Config()
    cfg.set_provider("gemini")

    captured_kwargs = {}

    class DummyGemini:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    monkeypatch.setattr("promptheus.providers.GeminiProvider", DummyGemini)

    get_provider("gemini", cfg, "gemini-pro")

    assert captured_kwargs["api_key"] == "fake-key"
    assert captured_kwargs["model_name"] == "gemini-pro"
    assert captured_kwargs["available_models"] == ["gemini-pro", "gemini-1.5-pro"]


def test_get_provider_handles_openai(monkeypatch):
    sample_models = {
        "providers": {
            "openai": {
                "default_model": "gpt-4o",
                "models": ["gpt-4o", "gpt-4o-mini"],
                "api_key_env": "OPENAI_API_KEY",
                "api_key_prefixes": ["sk-"],
                "base_url_env": "OPENAI_BASE_URL",
                "organization_env": "OPENAI_ORG_ID",
                "project_env": "OPENAI_PROJECT",
            }
        },
        "provider_aliases": {"openai": "OpenAI"},
    }

    monkeypatch.setenv("OPENAI_API_KEY", "sk-unit-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test")
    monkeypatch.setattr("promptheus.config.Config.load_model_config", lambda self: sample_models)

    cfg = Config()
    cfg.set_provider("openai")

    captured_kwargs = {}

    class DummyOpenAI:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    monkeypatch.setattr("promptheus.providers.OpenAIProvider", DummyOpenAI)

    get_provider("openai", cfg, "gpt-4o-mini")

    assert captured_kwargs["api_key"] == "sk-unit-test"
    assert captured_kwargs["model_name"] == "gpt-4o-mini"
    assert captured_kwargs["base_url"] == "https://example.test"


def test_append_json_instruction_is_idempotent():
    """Ensure JSON instruction suffix is appended once and preserved."""
    result = _append_json_instruction("Hello world")
    assert result.endswith(_JSON_ONLY_SUFFIX)
    assert result.count(_JSON_ONLY_SUFFIX) == 1
    # Calling again should not duplicate the suffix
    assert _append_json_instruction(result) == result


def test_parse_question_payload_requires_task_type(caplog):
    """Parser should return None when task_type missing, valid dict otherwise."""
    valid_payload = json.dumps({"task_type": "generation", "questions": [{"question": "Q"}]})
    parsed = _parse_question_payload("TestProvider", valid_payload)
    assert parsed == {"task_type": "generation", "questions": [{"question": "Q"}]}

    missing_task = json.dumps({"questions": []})
    assert _parse_question_payload("TestProvider", missing_task) is None
    assert _parse_question_payload("TestProvider", "not-json") is None


def test_openai_provider_sets_json_mode(monkeypatch):
    """OpenAI provider should request json_object responses when needed."""
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider.model_name = "gpt-4o-mini"
    captured = {}

    class DummyCompletions:
        def create(self, **kwargs):
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
            )

    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=DummyCompletions()))

    text = provider._generate_text("Prompt", "System", json_mode=True, max_tokens=42)

    assert text == '{"ok": true}'
    params = captured["kwargs"]
    assert params["model"] == "gpt-4o-mini"
    assert params["response_format"] == {"type": "json_object"}
    assert params["max_tokens"] == 42
    assert params["messages"][0]["role"] == "system"
    assert params["messages"][1]["content"].endswith(_JSON_ONLY_SUFFIX)


def test_groq_provider_uses_openai_base(monkeypatch):
    """Groq provider should configure the OpenAI client with Groq's base URL."""
    captured = {}

    def fake_init(self, api_key=None, model_name=None, base_url=None, **kwargs):
        captured.update({"api_key": api_key, "model_name": model_name, "base_url": base_url})

    monkeypatch.setattr("promptheus.providers.OpenAIProvider.__init__", fake_init, raising=False)
    monkeypatch.delenv("GROQ_BASE_URL", raising=False)

    provider = GroqProvider("gsk-test", model_name="llama-3.3-70b-versatile")
    assert isinstance(provider, GroqProvider)
    assert captured["api_key"] == "gsk-test"
    assert captured["model_name"] == "llama-3.3-70b-versatile"
    assert captured["base_url"] == GroqProvider.DEFAULT_BASE_URL


def test_qwen_provider_uses_dashscope_base(monkeypatch):
    """Qwen provider should pass the DashScope base URL into the OpenAI client."""
    captured = {}

    def fake_init(self, api_key=None, model_name=None, base_url=None, **kwargs):
        captured.update({"api_key": api_key, "model_name": model_name, "base_url": base_url})

    monkeypatch.setattr("promptheus.providers.OpenAIProvider.__init__", fake_init, raising=False)
    monkeypatch.delenv("DASHSCOPE_HTTP_BASE_URL", raising=False)

    provider = QwenProvider("sk-dashscope", model_name="qwen-plus")
    assert isinstance(provider, QwenProvider)
    assert captured["api_key"] == "sk-dashscope"
    assert captured["model_name"] == "qwen-plus"
    assert captured["base_url"] == QwenProvider.DEFAULT_BASE_URL


def test_glm_provider_builds_messages():
    """GLM provider should pass system/user messages through to the client."""
    provider = GLMProvider.__new__(GLMProvider)
    provider.model_name = "glm-4"
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="response text"))]
        )

    class DummyCompletions:
        def __init__(self, func):
            self.create = func

    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=DummyCompletions(fake_create)))

    text = provider._generate_text("Draft email", "Follow company tone", json_mode=False, max_tokens=30)

    assert text == "response text"
    msgs = captured["messages"]
    assert msgs[0] == {"role": "system", "content": "Follow company tone"}
    assert msgs[1]["role"] == "user"
    assert "Draft email" in msgs[1]["content"]


def test_glm_provider_uses_default_base_url(monkeypatch):
    """GLM provider should pass the Zhipu base URL into the OpenAI client."""
    captured = {}

    def fake_init(self, api_key=None, model_name=None, base_url=None, **kwargs):
        captured.update({"api_key": api_key, "model_name": model_name, "base_url": base_url})

    monkeypatch.setattr("promptheus.providers.OpenAIProvider.__init__", fake_init, raising=False)

    provider = GLMProvider("zai-key", model_name="glm-4-air")
    assert isinstance(provider, GLMProvider)
    assert captured["api_key"] == "zai-key"
    assert captured["model_name"] == "glm-4-air"
    assert captured["base_url"] == GLMProvider.DEFAULT_BASE_URL
