"""Tests for utility commands (validate, list models, etc.)."""

from promptheus._provider_data import _select_test_model, _test_provider_connection
from promptheus.config import Config


def test_select_test_model_prefers_provider_env(monkeypatch):
    """Provider-specific MODEL env vars should override defaults."""
    config = Config()
    config.reset()

    monkeypatch.setenv("OPENAI_MODEL", "gpt-env-override")
    monkeypatch.delenv("PROMPTHEUS_MODEL", raising=False)

    assert _select_test_model("openai", config) == "gpt-env-override"


def test_select_test_model_falls_back_to_default(monkeypatch):
    """When no env override exists, use the providers.json default."""
    config = Config()
    config.reset()

    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("PROMPTHEUS_MODEL", raising=False)

    assert _select_test_model("openai", config) == "gpt-4o"


def test_test_provider_connection_uses_selected_model(monkeypatch):
    """Connection tests should request the provider picked health-check model."""
    config = Config()
    config.reset()

    # Ensure provider detection works without hitting the network
    config.set_provider("gemini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    captured = {}

    class DummyProvider:
        def _generate_text(self, prompt, system_instruction, max_tokens=None):  # noqa: D401
            captured["prompt"] = prompt
            captured["max_tokens"] = max_tokens
            return "pong"

    def fake_get_provider(name, cfg, model_name=None):
        captured["model_name"] = model_name
        return DummyProvider()

    monkeypatch.setattr("promptheus._provider_data._select_test_model", lambda name, cfg: "health-model")
    monkeypatch.setattr("promptheus._provider_data.get_provider", fake_get_provider)

    success, error = _test_provider_connection("openai", config)

    assert success is True
    assert error == ""
    assert captured["model_name"] == "health-model"
    assert captured["prompt"] == "ping"
    assert captured["max_tokens"] == 8
