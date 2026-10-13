"""Tests for the fast/balanced/best model tiers and the weekly tier updater."""

import importlib.util
import io
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from promptheus.config import MODEL_TIERS, Config, resolve_model_tier
from promptheus.providers import get_provider

REPO_ROOT = Path(__file__).parent.parent
PROVIDERS_JSON = REPO_ROOT / "src" / "promptheus" / "providers.json"
PROVIDERS = json.loads(PROVIDERS_JSON.read_text())["providers"]


def _load_updater():
    spec = importlib.util.spec_from_file_location("update_model_tiers", REPO_ROOT / "scripts" / "update_model_tiers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tiers_are_well_formed_and_default_is_balanced():
    for name, info in PROVIDERS.items():
        tiers = info.get("tiers")
        if not tiers:
            continue
        assert set(tiers) <= set(MODEL_TIERS), name
        assert info["default_model"] == tiers["balanced"], name


def test_resolve_model_tier():
    anthropic = PROVIDERS["anthropic"]
    assert resolve_model_tier(anthropic, "best") == anthropic["tiers"]["best"]
    assert resolve_model_tier(anthropic, "Fast") == anthropic["tiers"]["fast"]
    assert resolve_model_tier(anthropic, "claude-sonnet-4-5") == "claude-sonnet-4-5"
    assert resolve_model_tier(anthropic, None) is None
    # GLM has no "best" tier, so it falls back to the default model.
    assert resolve_model_tier(PROVIDERS["glm"], "best") == PROVIDERS["glm"]["default_model"]


def test_tier_name_in_env_var_resolves(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "fast")
    config = Config()
    config.reset()
    config.set_provider("anthropic", source="auto")
    assert config.get_model() == PROVIDERS["anthropic"]["tiers"]["fast"]


def test_tier_name_passed_to_get_provider_resolves(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    config = Config()
    config.reset()
    config.set_provider("anthropic")
    provider = get_provider("anthropic", config, model_name="best")
    assert provider.model_name == PROVIDERS["anthropic"]["tiers"]["best"]


def test_list_models_shows_tiers_without_fetching_catalog():
    config = Config()
    output = io.StringIO()
    console = Console(file=output, width=200)
    with patch("promptheus.commands.providers.get_provider_models", side_effect=AssertionError("fetched catalog")):
        from promptheus.commands.providers import list_models
        list_models(config, console)
    text = output.getvalue()
    for tier_model in PROVIDERS["anthropic"]["tiers"].values():
        assert tier_model in text
    assert "--all" in text


@pytest.mark.anyio
async def test_web_models_endpoint_returns_only_recommended_picks():
    from promptheus.web.api import providers_router

    catalog = ["claude-old-1", *PROVIDERS["anthropic"]["tiers"].values(), "claude-old-2"]

    class _Service:
        async def get_models_for_provider_split(self, provider_id):
            return catalog, catalog, catalog

        def get_cache_timestamp(self):
            return None

    with patch.object(providers_router, "get_service", return_value=_Service()):
        response = await providers_router.get_provider_models("anthropic")
        everything = await providers_router.get_provider_models("anthropic", fetch_all=True)

    tiers = PROVIDERS["anthropic"]["tiers"]
    assert response.tiers == tiers
    assert set(tiers.values()) <= set(response.models)
    assert "claude-old-1" not in response.models
    assert everything.models == catalog


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def updater(tmp_path):
    """The updater pointed at scratch copies of providers.json and providers.py."""
    module = _load_updater()
    module.PROVIDERS_JSON = tmp_path / "providers.json"
    module.PROVIDERS_PY = tmp_path / "providers.py"
    shutil.copy(PROVIDERS_JSON, module.PROVIDERS_JSON)
    shutil.copy(REPO_ROOT / "src" / "promptheus" / "providers.py", module.PROVIDERS_PY)
    return module


def _catalog_with(anthropic_models):
    catalog = {"anthropic": {"models": {}}}
    for model_id, release_date, extra in anthropic_models:
        catalog["anthropic"]["models"][model_id] = {"id": model_id, "release_date": release_date, **extra}
    return catalog


def _run_updater(updater, catalog, tmp_path, monkeypatch):
    payload = io.BytesIO(json.dumps(catalog).encode())
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *a, **k: payload)
    monkeypatch.setattr("sys.argv", ["update_model_tiers.py", "--summary-file", str(tmp_path / "changes.md")])
    assert updater.main() == 0


def test_updater_moves_tiers_forward_only(updater, tmp_path, monkeypatch):
    tiers = PROVIDERS["anthropic"]["tiers"]
    catalog = _catalog_with([
        (tiers["fast"], "2026-10-01", {}),
        (tiers["balanced"], "2026-10-01", {}),
        (tiers["best"], "2026-10-01", {}),
        ("claude-sonnet-9", "2027-01-01", {}),                         # newer: should win
        ("claude-opus-9", "2027-01-01", {"status": "deprecated"}),    # deprecated: skipped
        ("claude-haiku-1", "2020-01-01", {}),                          # older: ignored
        ("claude-sonnet-9-20270101", "2027-02-01", {}),               # dated snapshot: not a tier name
    ])
    _run_updater(updater, catalog, tmp_path, monkeypatch)

    new_providers = json.loads(updater.PROVIDERS_JSON.read_text())["providers"]
    assert new_providers["anthropic"]["tiers"] == {**tiers, "balanced": "claude-sonnet-9"}
    assert new_providers["anthropic"]["default_model"] == "claude-sonnet-9"
    assert 'model_name: str = "claude-sonnet-9"' in updater.PROVIDERS_PY.read_text()
    # Other providers are untouched because the fake catalog has no models for them.
    assert new_providers["openai"] == PROVIDERS["openai"]
    assert "claude-sonnet-9" in (tmp_path / "changes.md").read_text()


def test_updater_leaves_files_alone_when_current(updater, tmp_path, monkeypatch):
    tiers = PROVIDERS["anthropic"]["tiers"]
    catalog = _catalog_with([(model, "2026-10-01", {}) for model in tiers.values()])
    before = updater.PROVIDERS_JSON.read_text()
    _run_updater(updater, catalog, tmp_path, monkeypatch)
    assert updater.PROVIDERS_JSON.read_text() == before
    assert not (tmp_path / "changes.md").exists()
