from types import SimpleNamespace

from promptheus.config import Config
from promptheus.providers import GeminiProvider, get_provider


def test_gemini_generate_text_applies_max_tokens():
    """Ensure the Gemini provider forwards max_tokens into the API call."""
    provider = GeminiProvider.__new__(GeminiProvider)
    provider.genai = SimpleNamespace()
    provider._fatal_exceptions = ()
    provider.model_name = "gemini-pro"
    provider._model_cache = {}
    provider._available_models = ["gemini-pro"]

    captured_config = {}

    def fake_get_model(self, model_name, system_instruction, json_mode):
        class FakeModel:
            def generate_content(self, prompt, generation_config=None):
                captured_config["config"] = generation_config
                return SimpleNamespace(text="result")

        return FakeModel()

    provider._get_model = fake_get_model.__get__(provider, GeminiProvider)

    result = provider._generate_text("prompt", "system", max_tokens=321)

    assert result == "result"
    assert captured_config["config"] == {"max_output_tokens": 321}


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
