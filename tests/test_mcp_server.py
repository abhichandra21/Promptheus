import sys
import types
import asyncio
from typing import Any, Dict, List, Tuple
from unittest.mock import Mock

import pytest


def _install_dummy_mcp():
    """Install a minimal dummy mcp.server.fastmcp implementation for tests."""
    # If the real mcp package is available, prefer it so that tests can
    # exercise the actual FastMCP integration.
    try:
        import mcp.server.fastmcp  # type: ignore[import]
        return
    except Exception:
        pass

    if "mcp.server.fastmcp" in sys.modules:
        return

    dummy_mcp_module = types.ModuleType("mcp")
    dummy_server_module = types.ModuleType("mcp.server")
    dummy_fastmcp_module = types.ModuleType("mcp.server.fastmcp")

    class DummyFastMCP:
        def __init__(self, name: str) -> None:
            self.name = name

        def tool(self):
            def decorator(fn):
                # FastMCP normally wraps the function; for tests we just return it
                return fn

            return decorator

        def run(self) -> None:
            # Not used in tests
            pass

    dummy_fastmcp_module.FastMCP = DummyFastMCP

    sys.modules["mcp"] = dummy_mcp_module
    sys.modules["mcp.server"] = dummy_server_module
    sys.modules["mcp.server.fastmcp"] = dummy_fastmcp_module


_install_dummy_mcp()

from promptheus import mcp_server  # noqa: E402


class FakeProvider:
    """Minimal fake provider used to stub LLMProvider behavior."""

    def __init__(self, analysis_result: Any = None) -> None:
        self.analysis_result = analysis_result
        self.calls: List[Tuple[str, Any]] = []

    def generate_questions(self, prompt: str, system_instruction: str) -> Any:
        self.calls.append(("generate_questions", prompt, system_instruction))
        return self.analysis_result

    def refine_from_answers(
        self,
        initial_prompt: str,
        answers: Dict[str, str],
        mapping: Dict[str, str],
        system_instruction: str,
    ) -> str:
        self.calls.append(
            ("refine_from_answers", initial_prompt, answers, mapping, system_instruction)
        )
        # Encode mapping keys into the result to make assertions simple
        mapping_keys = ",".join(sorted(mapping.keys()))
        return f"refined:{initial_prompt}|answers:{len(answers)}|mapping:{mapping_keys}"

    def light_refine(self, prompt: str, system_instruction: str) -> str:
        self.calls.append(("light_refine", prompt, system_instruction))
        return f"light:{prompt}"


def _stub_provider(analysis_result: Any) -> FakeProvider:
    """Helper to stub _initialize_provider and return a FakeProvider."""
    fake = FakeProvider(analysis_result=analysis_result)

    def _init_stub(provider: str | None, model: str | None):
        return fake, None

    mcp_server._initialize_provider = _init_stub  # type: ignore[attr-defined]
    return fake


def test_refine_prompt_with_answers_uses_refine_from_answers():
    """When answers are provided, refine_prompt should call refine_from_answers and return refined type."""
    fake = _stub_provider(analysis_result=None)

    result = mcp_server.refine_prompt(
        prompt="Write something", answers={"q0": "Developers", "q1": "Formal tone"}
    )

    assert result["type"] == "refined"
    assert result["prompt"].startswith("refined:Write something")

    # Verify refine_from_answers was called with a mapping built from keys
    assert fake.calls[0][0] == "refine_from_answers"
    _, initial_prompt, answers, mapping, _ = fake.calls[0]
    assert initial_prompt == "Write something"
    assert answers == {"q0": "Developers", "q1": "Formal tone"}
    # Mapping should fall back to generic labels when no answer_mapping is provided
    assert mapping["q0"] == "Question: q0"
    assert mapping["q1"] == "Question: q1"


def test_refine_prompt_returns_clarification_needed_when_questions_present():
    """When generate_questions returns questions, refine_prompt should return a clarification payload."""
    analysis_result = {
        "task_type": "generation",
        "questions": [
            {"question": "Who is the audience?", "type": "text"},
            {"question": "Preferred tone?", "type": "radio", "options": ["Formal", "Casual"]},
        ],
    }
    _stub_provider(analysis_result=analysis_result)

    result = mcp_server.refine_prompt(prompt="Write a blog post")

    assert result["type"] == "clarification_needed"
    assert result["task_type"] == "generation"

    questions_for_ask = result["questions_for_ask_user_question"]
    mapping = result["answer_mapping"]

    assert isinstance(questions_for_ask, list)
    assert len(questions_for_ask) == 2
    assert mapping == {
        "q0": "Who is the audience?",
        "q1": "Preferred tone?",
    }


def test_refine_prompt_uses_answer_mapping_when_provided():
    """When answer_mapping is provided, refine_prompt should pass it through to the provider."""
    fake = _stub_provider(analysis_result=None)

    answers = {"q0": "Developers", "q1": "Formal tone"}
    answer_mapping = {
        "q0": "Who is the audience?",
        "q1": "Preferred tone?",
    }

    result = mcp_server.refine_prompt(
        prompt="Write something detailed about APIs",
        answers=answers,
        answer_mapping=answer_mapping,
    )

    assert result["type"] == "refined"
    assert result["prompt"].startswith("refined:Write something detailed about APIs")

    # Verify refine_from_answers was called with the provided mapping
    assert fake.calls[0][0] == "refine_from_answers"
    _, initial_prompt, passed_answers, passed_mapping, _ = fake.calls[0]
    assert initial_prompt == "Write something detailed about APIs"
    assert passed_answers == answers
    assert passed_mapping == answer_mapping


def test_refine_prompt_light_refine_when_no_questions():
    """If generate_questions returns no questions, refine_prompt should fall back to light refinement."""
    analysis_result = {"task_type": "analysis", "questions": []}
    fake = _stub_provider(analysis_result=analysis_result)

    result = mcp_server.refine_prompt(prompt="Analyze this system")

    assert result["type"] == "refined"
    assert result["prompt"].startswith("light:Analyze this system")

    # Ensure light_refine was called
    assert any(call[0] == "light_refine" for call in fake.calls)


def test_refine_prompt_light_refine_on_analysis_failure():
    """If generate_questions fails (returns None), refine_prompt should perform light refinement."""
    fake = _stub_provider(analysis_result=None)

    result = mcp_server.refine_prompt(prompt="Describe this architecture")

    assert result["type"] == "refined"
    assert result["prompt"].startswith("light:Describe this architecture")
    assert any(call[0] == "light_refine" for call in fake.calls)


def test_refine_prompt_validation_error_for_empty_prompt():
    """Empty prompts should return a validation error before provider initialization."""
    # Use a stub that would fail if called to verify validate runs first
    def _init_stub(provider: str | None, model: str | None):
        raise AssertionError("Provider initialization should not be called for empty prompt")

    mcp_server._initialize_provider = _init_stub  # type: ignore[attr-defined]

    result = mcp_server.refine_prompt(prompt="")

    assert result["type"] == "error"
    assert result["error_type"] == "ValidationError"
    assert "cannot be empty" in result["message"]


def test_refine_prompt_uses_provider_error_response():
    """If provider initialization fails with an error response, it should be returned as-is."""
    error_response = {
        "type": "error",
        "error_type": "ConfigurationError",
        "message": "Missing API key",
    }

    def _init_stub(provider: str | None, model: str | None):
        return None, error_response

    mcp_server._initialize_provider = _init_stub  # type: ignore[attr-defined]

    result = mcp_server.refine_prompt(prompt="Write something")

    assert result is error_response


# ============================================================================
# Tests for tweak_prompt tool
# ============================================================================


class FakeTweakProvider:
    """Fake provider for tweak_prompt tests."""

    def __init__(self):
        self.calls = []

    def tweak_prompt(self, prompt: str, modification: str, system_instruction: str) -> str:
        self.calls.append(("tweak_prompt", prompt, modification, system_instruction))
        return f"tweaked:{prompt}|mod:{modification}"


def test_tweak_prompt_success():
    """tweak_prompt should call provider tweak_prompt and return result."""
    fake = FakeTweakProvider()

    def _init_stub(provider: str | None, model: str | None):
        return fake, None

    mcp_server._initialize_provider = _init_stub  # type: ignore[attr-defined]

    result = mcp_server.tweak_prompt(
        prompt="Write a technical blog post",
        modification="make it more beginner-friendly"
    )

    assert result["type"] == "refined"
    assert "tweaked:Write a technical blog post" in result["prompt"]
    assert "beginner-friendly" in result["prompt"]


def test_tweak_prompt_empty_modification():
    """tweak_prompt should return error for empty modification."""
    def _init_stub(provider: str | None, model: str | None):
        raise AssertionError("Should not initialize provider for empty modification")

    mcp_server._initialize_provider = _init_stub  # type: ignore[attr-defined]

    result = mcp_server.tweak_prompt(
        prompt="Some prompt",
        modification=""
    )

    assert result["type"] == "error"
    assert result["error_type"] == "ValidationError"
    assert "modification" in result["message"].lower()


def test_tweak_prompt_empty_prompt():
    """tweak_prompt should validate prompt before modification."""
    result = mcp_server.tweak_prompt(
        prompt="",
        modification="make it better"
    )

    assert result["type"] == "error"
    assert result["error_type"] == "ValidationError"


# ============================================================================
# Tests for list_models tool
# ============================================================================


def test_list_models_success(monkeypatch):
    """list_models should return model data from providers."""
    def mock_get_models_data(config, providers, include_nontext, limit):
        return {
            "google": {
                "available": True,
                "models": [
                    {"id": "gemini-pro", "name": "gemini-pro"},
                    {"id": "gemini-flash", "name": "gemini-flash"}
                ],
                "total_count": 2,
                "showing": 2
            },
            "openai": {
                "available": False,
                "error": "No API key found",
                "models": []
            }
        }

    monkeypatch.setattr(
        "promptheus.commands.providers.get_models_data",
        mock_get_models_data
    )

    result = mcp_server.list_models()

    assert result["type"] == "success"
    assert "google" in result["providers"]
    assert result["providers"]["google"]["available"] is True
    assert len(result["providers"]["google"]["models"]) == 2


def test_list_models_with_filters(monkeypatch):
    """list_models should pass provider filters, limit, and include_nontext."""
    called_with = {}

    def mock_get_models_data(config, providers, include_nontext, limit):
        called_with["providers"] = providers
        called_with["limit"] = limit
        called_with["include_nontext"] = include_nontext
        return {}

    monkeypatch.setattr(
        "promptheus.commands.providers.get_models_data",
        mock_get_models_data
    )

    mcp_server.list_models(providers=["google", "openai"], limit=10, include_nontext=True)

    assert called_with["providers"] == ["google", "openai"]
    assert called_with["limit"] == 10
    assert called_with["include_nontext"] is True


def test_list_models_defaults(monkeypatch):
    """list_models should use defaults when no parameters provided (matches CLI)."""
    called_with = {}

    def mock_get_models_data(config, providers, include_nontext, limit):
        called_with["providers"] = providers
        called_with["include_nontext"] = include_nontext
        called_with["limit"] = limit
        return {}

    monkeypatch.setattr(
        "promptheus.commands.providers.get_models_data",
        mock_get_models_data
    )

    mcp_server.list_models()

    # Providers should be None (all providers), not a specific list
    assert called_with["providers"] is None
    assert called_with["include_nontext"] is False
    assert called_with["limit"] == 20


# ============================================================================
# Tests for list_providers tool
# ============================================================================


def test_list_providers_success(monkeypatch):
    """list_providers should return status for all providers."""
    # Mock Config to return test data
    class MockConfig:
        def __init__(self):
            pass

        def set_provider(self, provider):
            pass

        def validate(self):
            return True

        def get_model(self):
            return "test-model"

        def consume_error_messages(self):
            return []

    monkeypatch.setattr("promptheus.mcp_server.Config", MockConfig)
    monkeypatch.setattr("promptheus.config.SUPPORTED_PROVIDER_IDS", ["google", "openai"])

    def mock_get_provider(provider_id, config, model):
        return Mock()

    monkeypatch.setattr("promptheus.mcp_server.get_provider", mock_get_provider)

    result = mcp_server.list_providers()

    assert result["type"] == "success"
    assert "google" in result["providers"]
    assert result["providers"]["google"]["configured"] is True


def test_list_providers_handles_per_provider_exceptions(monkeypatch):
    """list_providers should capture per-provider failures in the providers map."""

    class MockConfig:
        def __init__(self):
            self._validate_calls = 0

        def set_provider(self, provider):
            # No-op for this test
            pass

        def validate(self):
            self._validate_calls += 1
            # Simulate an unexpected error on the second validate call
            if self._validate_calls == 2:
                raise RuntimeError("Unexpected validation failure")
            return True

        def get_model(self):
            return "test-model"

        def consume_error_messages(self):
            return []

    monkeypatch.setattr("promptheus.mcp_server.Config", MockConfig)
    monkeypatch.setattr(
        "promptheus.config.SUPPORTED_PROVIDER_IDS", ["google", "openai"]
    )

    def mock_get_provider(provider_id, config, model):
        return Mock()

    monkeypatch.setattr("promptheus.mcp_server.get_provider", mock_get_provider)

    result = mcp_server.list_providers()

    assert result["type"] == "success"
    providers = result["providers"]
    assert providers["google"]["configured"] is True
    # The second provider should be marked as misconfigured with an error message
    assert providers["openai"]["configured"] is False
    assert "Unexpected validation failure" in providers["openai"]["error"]


# ============================================================================
# Tests for validate_environment tool
# ============================================================================


def test_validate_environment_basic(monkeypatch):
    """validate_environment should return configuration status."""
    def mock_get_validation_data(config, providers, test_connection):
        return {
            "google": {
                "configured": True,
                "api_key_status": "set"
            },
            "openai": {
                "configured": False,
                "api_key_status": "missing_OPENAI_API_KEY"
            }
        }

    monkeypatch.setattr(
        "promptheus.commands.providers.get_validation_data",
        mock_get_validation_data
    )

    result = mcp_server.validate_environment()

    assert result["type"] == "success"
    assert "google" in result["validation"]
    assert result["validation"]["google"]["configured"] is True


def test_validate_environment_with_connection_test(monkeypatch):
    """validate_environment with test_connection should include connection results."""
    def mock_get_validation_data(config, providers, test_connection):
        return {
            "google": {
                "configured": True,
                "api_key_status": "set",
                "connection_test": "passed"
            }
        }

    monkeypatch.setattr(
        "promptheus.commands.providers.get_validation_data",
        mock_get_validation_data
    )

    result = mcp_server.validate_environment(test_connection=True)

    assert result["validation"]["google"]["connection_test"] == "passed"


def test_validate_environment_defaults(monkeypatch):
    """validate_environment should validate all providers when none specified (matches CLI)."""
    called_with = {}

    def mock_get_validation_data(config, providers, test_connection):
        called_with["providers"] = providers
        called_with["test_connection"] = test_connection
        return {}

    monkeypatch.setattr(
        "promptheus.commands.providers.get_validation_data",
        mock_get_validation_data
    )

    mcp_server.validate_environment()

    # Providers should be None (all providers), not a specific list
    assert called_with["providers"] is None
    assert called_with["test_connection"] is False


def test_validate_environment_with_specific_providers(monkeypatch):
    """validate_environment should accept specific providers list."""
    called_with = {}

    def mock_get_validation_data(config, providers, test_connection):
        called_with["providers"] = providers
        called_with["test_connection"] = test_connection
        return {}

    monkeypatch.setattr(
        "promptheus.commands.providers.get_validation_data",
        mock_get_validation_data
    )

    mcp_server.validate_environment(providers=["openai", "anthropic"], test_connection=True)

    assert called_with["providers"] == ["openai", "anthropic"]
    assert called_with["test_connection"] is True


# ============================================================================
# Tests for helper functions
# ============================================================================


def test_validate_prompt_too_long():
    """Prompt exceeding MAX_PROMPT_LENGTH should fail validation."""
    long_prompt = "x" * (mcp_server.MAX_PROMPT_LENGTH + 1)
    result = mcp_server._validate_prompt(long_prompt)

    assert result is not None
    assert result["type"] == "error"
    assert "maximum length" in result["message"]


def test_build_question_mapping():
    """_build_question_mapping should create correct ID-to-text mapping."""
    questions = [
        {"question": "Q1"},
        {"question": "Q2"},
        {"question": "Q3"}
    ]

    mapping = mcp_server._build_question_mapping(questions)

    assert mapping == {
        "q0": "Q1",
        "q1": "Q2",
        "q2": "Q3"
    }


def test_ask_user_question_injection():
    """set_ask_user_question should inject custom function."""
    original_fn = mcp_server._ask_user_question_fn

    mock_fn = Mock()
    mcp_server.set_ask_user_question(mock_fn)

    assert mcp_server._ask_user_question_fn is mock_fn

    # Restore
    mcp_server.set_ask_user_question(original_fn)


def _install_interactive_stub(analysis_result: Any) -> FakeProvider:
    """Helper to configure provider and enable AskUserQuestion for interactive tests."""
    fake_provider = _stub_provider(analysis_result=analysis_result)
    return fake_provider


def test_refine_prompt_uses_interactive_answers_when_available():
    """Interactive AskUser path should refine directly when valid answers are returned."""
    analysis_result = {
        "task_type": "generation",
        "questions": [
            {"question": "Who is the audience?", "type": "text", "required": True},
            {
                "question": "Preferred tone?",
                "type": "radio",
                "options": ["Formal", "Casual"],
                "required": True,
            },
        ],
    }
    fake = _install_interactive_stub(analysis_result)

    original_fn = mcp_server._ask_user_question_fn

    def ask_user_fn(questions):
        # Each call receives a single question in a list
        assert isinstance(questions, list)
        assert len(questions) == 1
        q = questions[0]
        q_id = q["id"]
        if q_id == "q0":
            return {"answers": {q_id: "Developers"}}
        if q_id == "q1":
            return {"answers": {q_id: ["Formal"]}}
        return {"answers": {}}

    try:
        mcp_server.set_ask_user_question(ask_user_fn)

        result = mcp_server.refine_prompt(prompt="Write a blog post about our product")

        assert result["type"] == "refined"
        assert result["prompt"].startswith("refined:Write a blog post about our product")

        # Provider should see answers for both questions and the mapping ids
        assert any(call[0] == "refine_from_answers" for call in fake.calls)
        refine_call = next(call for call in fake.calls if call[0] == "refine_from_answers")
        _, initial_prompt, answers, mapping, _ = refine_call
        assert initial_prompt == "Write a blog post about our product"
        assert answers == {"q0": "Developers", "q1": "Formal"}
        assert mapping["q0"] == "Who is the audience?"
        assert mapping["q1"] == "Preferred tone?"
    finally:
        mcp_server.set_ask_user_question(original_fn)


def test_refine_prompt_falls_back_when_required_answer_missing():
    """If AskUserQuestion omits a required answer, refine_prompt should fall back to clarification_needed."""
    analysis_result = {
        "task_type": "generation",
        "questions": [
            {"question": "Who is the audience?", "type": "text", "required": True},
        ],
    }
    _install_interactive_stub(analysis_result)

    original_fn = mcp_server._ask_user_question_fn

    def ask_user_fn(questions):
        # Return empty mapping, simulating an interactive client that did not answer
        return {"answers": {}}

    try:
        mcp_server.set_ask_user_question(ask_user_fn)

        result = mcp_server.refine_prompt(prompt="Write a blog post")

        assert result["type"] == "clarification_needed"
        assert "questions_for_ask_user_question" in result
        assert result["task_type"] == "generation"
    finally:
        mcp_server.set_ask_user_question(original_fn)


def test_refine_prompt_falls_back_when_ask_user_raises():
    """If AskUserQuestion raises, refine_prompt should fall back to clarification_needed."""
    analysis_result = {
        "task_type": "generation",
        "questions": [
            {"question": "Who is the audience?", "type": "text", "required": True},
        ],
    }
    _install_interactive_stub(analysis_result)

    original_fn = mcp_server._ask_user_question_fn

    def ask_user_fn(questions):
        raise RuntimeError("simulated AskUser failure")

    try:
        mcp_server.set_ask_user_question(ask_user_fn)

        result = mcp_server.refine_prompt(prompt="Write a blog post")

        assert result["type"] == "clarification_needed"
        assert "questions_for_ask_user_question" in result
    finally:
        mcp_server.set_ask_user_question(original_fn)


def test_refine_prompt_falls_back_when_ask_user_returns_invalid_type():
    """Invalid AskUserQuestion return types should trigger structured clarification response."""
    analysis_result = {
        "task_type": "generation",
        "questions": [
            {"question": "Who is the audience?", "type": "text", "required": True},
        ],
    }
    _install_interactive_stub(analysis_result)

    original_fn = mcp_server._ask_user_question_fn

    def ask_user_fn(questions):
        # Return a type that _try_interactive_questions does not understand
        return 42

    try:
        mcp_server.set_ask_user_question(ask_user_fn)

        result = mcp_server.refine_prompt(prompt="Write a blog post")

        assert result["type"] == "clarification_needed"
        assert "questions_for_ask_user_question" in result
    finally:
        mcp_server.set_ask_user_question(original_fn)


# ============================================================================
# FastMCP integration smoke test using the real mcp package
# ============================================================================


def test_fastmcp_integration_with_real_package():
    """Smoke test that uses the real FastMCP when available."""
    fastmcp_module = pytest.importorskip("mcp.server.fastmcp")

    # Skip when the dummy stub is in use (no real mcp package installed).
    if getattr(fastmcp_module.FastMCP, "__name__", "") == "DummyFastMCP":
        pytest.skip("Real mcp FastMCP not available; using test stub")

    # At this point promptheus.mcp_server should have bound its global mcp
    # instance to the real FastMCP class.
    assert isinstance(mcp_server.mcp, fastmcp_module.FastMCP)

    # Stub provider initialization so the tool can run without real API keys.
    fake = _stub_provider(analysis_result=None)

    tools = mcp_server.mcp._tool_manager.list_tools()
    tool_names = [t.name for t in tools]
    assert "refine_prompt" in tool_names

    refine_tool = next(t for t in tools if t.name == "refine_prompt")

    async def invoke_tool() -> Dict[str, Any]:
        result = await mcp_server.mcp._tool_manager.call_tool(
            refine_tool.name,
            {"prompt": "Test prompt via FastMCP"},
        )
        return result

    result = asyncio.run(invoke_tool())

    assert isinstance(result, dict)
    assert result["type"] == "refined"
    assert result["prompt"].startswith("light:Test prompt via FastMCP")
    # Ensure our fake provider was exercised through the FastMCP tool wrapper
    assert any(call[0] == "light_refine" for call in fake.calls)


def test_ensure_mcp_available_raises_when_mcp_missing(monkeypatch):
    """_ensure_mcp_available should raise ImportError when FastMCP is not initialized."""
    monkeypatch.setattr(mcp_server, "mcp", None)

    with pytest.raises(ImportError) as excinfo:
        mcp_server._ensure_mcp_available()

    assert "The 'mcp' package is not installed" in str(excinfo.value)
