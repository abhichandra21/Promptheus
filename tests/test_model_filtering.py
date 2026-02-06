"""Tests for metadata-driven model filtering in ModelsDevService."""

import asyncio

from promptheus.models_dev_service import ModelsDevService


def _make_service(**cache_overrides):
    """Create a ModelsDevService with pre-loaded cache (no disk/network)."""
    svc = ModelsDevService()
    svc._cache = cache_overrides.get("cache", {})
    svc._cache_timestamp = cache_overrides.get("timestamp", 9999999999)
    return svc


# ---------------------------------------------------------------------------
# _is_suitable_for_refinement -- unit tests
# ---------------------------------------------------------------------------

class TestIsSuitableForRefinement:

    def setup_method(self):
        self.svc = _make_service()

    def test_high_output_limit_passes(self):
        info = {"limit": {"output": 8192}, "modalities": {"input": ["text"], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is True

    def test_low_output_limit_rejected(self):
        info = {"limit": {"output": 2048}, "modalities": {"input": ["text"], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is False

    def test_boundary_output_limit_passes(self):
        info = {"limit": {"output": 4096}, "modalities": {"input": ["text"], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is True

    def test_just_below_boundary_rejected(self):
        info = {"limit": {"output": 4095}, "modalities": {"input": ["text"], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is False

    def test_missing_limit_passes(self):
        info = {"modalities": {"input": ["text"], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is True

    def test_missing_output_limit_passes(self):
        info = {"limit": {"context": 128000}, "modalities": {"input": ["text"], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is True

    def test_audio_only_input_rejected(self):
        info = {"limit": {"output": 8192}, "modalities": {"input": ["audio"], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is False

    def test_text_and_image_input_passes(self):
        info = {"limit": {"output": 16384}, "modalities": {"input": ["text", "image"], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is True

    def test_empty_input_modalities_passes(self):
        info = {"limit": {"output": 8192}, "modalities": {"input": [], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is True

    def test_no_modalities_key_passes(self):
        info = {"limit": {"output": 8192}}
        assert self.svc._is_suitable_for_refinement(info) is True

    def test_completely_empty_info_passes(self):
        assert self.svc._is_suitable_for_refinement({}) is True

    def test_embedding_model_output_rejected(self):
        info = {"limit": {"output": 1536}, "modalities": {"input": ["text"], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is False

    def test_tiny_specialized_model_rejected(self):
        info = {"limit": {"output": 512}, "modalities": {"input": ["text"], "output": ["text"]}}
        assert self.svc._is_suitable_for_refinement(info) is False


# ---------------------------------------------------------------------------
# get_models_for_provider_split -- 3-tuple partitioning
# ---------------------------------------------------------------------------

MOCK_MODELS = {
    "good-chat-model": {
        "id": "good-chat-model",
        "limit": {"output": 16384, "context": 128000},
        "modalities": {"input": ["text", "image"], "output": ["text"]},
    },
    "text-embedding-3-small": {
        "id": "text-embedding-3-small",
        "limit": {"output": 1536, "context": 8191},
        "modalities": {"input": ["text"], "output": ["text"]},
    },
    "asr-flash": {
        "id": "asr-flash",
        "limit": {"output": 4096, "context": 53248},
        "modalities": {"input": ["audio"], "output": ["text"]},
    },
    "tts-model": {
        "id": "tts-model",
        "limit": {"output": 16000, "context": 8000},
        "modalities": {"input": ["text"], "output": ["audio"]},
    },
    "low-output-model": {
        "id": "low-output-model",
        "limit": {"output": 2048, "context": 32768},
        "modalities": {"input": ["text"], "output": ["text"]},
    },
}


def test_split_returns_three_lists():
    svc = _make_service(cache={"openai": {"models": MOCK_MODELS}})
    all_models, text_models, refinement_models = asyncio.run(
        svc.get_models_for_provider_split("openai")
    )

    # all_models: everything
    assert set(all_models) == set(MOCK_MODELS.keys())

    # text_models: excludes tts-model (output=audio)
    assert "good-chat-model" in text_models
    assert "tts-model" not in text_models

    # refinement_models: excludes embedding (1536), low-output (2048),
    # tts (not text gen), asr (audio-only input)
    assert "good-chat-model" in refinement_models
    assert "text-embedding-3-small" not in refinement_models
    assert "low-output-model" not in refinement_models
    assert "tts-model" not in refinement_models
    assert "asr-flash" not in refinement_models


def test_default_filter_returns_refinement_models():
    svc = _make_service(cache={"openai": {"models": MOCK_MODELS}})
    models = asyncio.run(svc.get_models_for_provider("openai"))
    assert "good-chat-model" in models
    assert "text-embedding-3-small" not in models
    assert "low-output-model" not in models


def test_unfiltered_returns_all_models():
    svc = _make_service(cache={"openai": {"models": MOCK_MODELS}})
    models = asyncio.run(svc.get_models_for_provider("openai", filter_text_only=False))
    assert set(models) == set(MOCK_MODELS.keys())


# ---------------------------------------------------------------------------
# _model_sort_key -- metadata-driven ranking
# ---------------------------------------------------------------------------

SORT_MOCK_MODELS = {
    "flagship": {
        "id": "flagship",
        "limit": {"output": 16384, "context": 128000},
        "modalities": {"input": ["text"], "output": ["text"]},
        "release_date": "2025-05-01",
    },
    "budget": {
        "id": "budget",
        "limit": {"output": 8192, "context": 32000},
        "modalities": {"input": ["text"], "output": ["text"]},
        "release_date": "2025-06-01",
    },
    "mega-context": {
        "id": "mega-context",
        "limit": {"output": 8192, "context": 1000000},
        "modalities": {"input": ["text"], "output": ["text"]},
        "release_date": "2024-12-01",
    },
    "no-metadata": {
        "id": "no-metadata",
        "limit": {"output": 4096, "context": 16000},
        "modalities": {"input": ["text"], "output": ["text"]},
    },
}


def test_refinement_models_sorted_by_output_then_context():
    svc = _make_service(cache={"openai": {"models": SORT_MOCK_MODELS}})
    _, _, refinement = asyncio.run(svc.get_models_for_provider_split("openai"))
    assert refinement[0] == "flagship", f"highest output budget should be first, got {refinement}"
    assert refinement[1] == "mega-context", f"next should be higher context among remaining, got {refinement}"


def test_sort_tiebreak_by_release_date():
    """When context is equal, newer release_date wins."""
    models = {
        "older": {
            "id": "older",
            "limit": {"output": 8192, "context": 128000},
            "modalities": {"input": ["text"], "output": ["text"]},
            "release_date": "2024-01-01",
        },
        "newer": {
            "id": "newer",
            "limit": {"output": 8192, "context": 128000},
            "modalities": {"input": ["text"], "output": ["text"]},
            "release_date": "2025-06-15",
        },
    }
    svc = _make_service(cache={"openai": {"models": models}})
    _, _, refinement = asyncio.run(svc.get_models_for_provider_split("openai"))
    assert refinement[0] == "newer"


def test_sort_missing_release_date_last():
    svc = _make_service(cache={"openai": {"models": SORT_MOCK_MODELS}})
    _, _, refinement = asyncio.run(svc.get_models_for_provider_split("openai"))
    assert refinement[-1] == "no-metadata", f"missing release_date should sort last, got {refinement}"


def test_sort_key_unit():
    svc = ModelsDevService()
    high = {"limit": {"context": 128000, "output": 16384}, "release_date": "2025-08-01"}
    low = {"limit": {"context": 32000, "output": 4096}, "release_date": "2025-08-01"}
    assert svc._model_sort_key(high) < svc._model_sort_key(low)

    newer = {"limit": {"context": 128000, "output": 8192}, "release_date": "2025-08-01"}
    older = {"limit": {"context": 128000, "output": 8192}, "release_date": "2024-01-01"}
    assert svc._model_sort_key(newer) < svc._model_sort_key(older)

    empty = {}
    assert svc._model_sort_key(empty) > svc._model_sort_key(high)
