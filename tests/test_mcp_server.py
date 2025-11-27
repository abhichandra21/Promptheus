import sys
import types
from typing import Any, Dict, List, Tuple


def _install_dummy_mcp():
    """Install a minimal dummy mcp.server.fastmcp implementation for tests."""
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
        prompt="Write something", answers={"q0": "Audience", "q1": "Tone"}
    )

    assert result["type"] == "refined"
    assert result["prompt"].startswith("refined:Write something")

    # Verify refine_from_answers was called with a mapping built from keys
    assert fake.calls[0][0] == "refine_from_answers"
    _, initial_prompt, answers, mapping, _ = fake.calls[0]
    assert initial_prompt == "Write something"
    assert answers == {"q0": "Audience", "q1": "Tone"}
    # Mapping should contain the same keys
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

