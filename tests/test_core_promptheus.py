"""Essential tests for core Promptheus functionality."""

import os
from io import StringIO
from argparse import Namespace
from unittest.mock import Mock, patch, MagicMock

import pytest
from rich.console import Console

from promptheus.main import (
    process_single_prompt,
    determine_question_plan,
    ask_clarifying_questions,
    generate_final_prompt,
    iterative_refinement,
    convert_json_to_question_definitions,
    QuestionPlan,
)
from promptheus.config import Config
from promptheus.io_context import IOContext
from promptheus.providers import LLMProvider
from promptheus.history import PromptHistory


class MockProvider(LLMProvider):
    """Mock provider for testing purposes."""
    
    def generate_questions(self, initial_prompt: str, system_instruction: str):
        # Return a mock response for question generation
        return {
            "task_type": "generation",
            "questions": [
                {
                    "question": "What is the target audience?",
                    "type": "text",
                    "required": True
                }
            ]
        }
    
    def get_available_models(self):
        return ["test-model"]
    
    def _generate_text(self, prompt: str, system_instruction: str, json_mode: bool = False, max_tokens=None):
        return "Mocked response from provider"


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def mock_config():
    config = Mock(spec=Config)
    config.provider = "test"
    config.get_model.return_value = "test-model"
    config.validate.return_value = True
    config.consume_status_messages.return_value = []
    config.consume_error_messages.return_value = []
    config.history_enabled = True  # Add missing attribute for telemetry
    return config


@pytest.fixture
def mock_notify():
    return Mock()


def test_convert_json_to_question_definitions():
    """Test conversion of JSON questions to internal format."""
    json_questions = [
        {
            "question": "What is your goal?",
            "type": "text",
            "required": True
        },
        {
            "question": "What tone should it have?",
            "type": "radio",
            "options": ["formal", "casual"],
            "required": False
        }
    ]
    
    questions, mapping = convert_json_to_question_definitions(json_questions)
    
    assert len(questions) == 2
    assert questions[0]['type'] == 'text'
    assert questions[1]['type'] == 'radio'
    assert questions[1]['options'] == ["formal", "casual"]
    assert not questions[1]['required']  # optional since required=False


def test_determine_question_plan_skip_questions_mode(mock_provider, mock_config, mock_notify):
    """Test question plan determination in skip-questions mode."""
    from promptheus.main import QuestionPlan

    args = Namespace(skip_questions=True, refine=False)
    plan = determine_question_plan(mock_provider, "test prompt", args, False, mock_notify, mock_config)

    assert isinstance(plan, QuestionPlan)
    assert plan.skip_questions
    assert plan.task_type == "analysis"


def test_ask_clarifying_questions_skip_questions():
    """Test that clarifying questions are skipped when requested."""
    from promptheus.main import QuestionPlan
    
    plan = QuestionPlan(skip_questions=True, task_type="generation", questions=[], mapping={})
    result = ask_clarifying_questions(plan, Mock())
    
    assert result == {}


def test_ask_clarifying_questions_empty_questions():
    """Test that clarifying questions return empty dict when no questions provided."""
    from promptheus.main import QuestionPlan
    
    plan = QuestionPlan(skip_questions=False, task_type="generation", questions=[], mapping={})
    result = ask_clarifying_questions(plan, Mock())
    
    assert result == {}


@patch('promptheus.main.questionary')
def test_generate_final_prompt_no_answers(mock_questionary, mock_provider):
    """Test that original prompt is returned when no answers are provided."""
    final_prompt, is_refined = generate_final_prompt(
        mock_provider, 
        "original prompt", 
        {},  # empty answers
        {},  # empty mapping
        Mock()
    )
    
    assert final_prompt == "original prompt"
    assert not is_refined


@patch('promptheus.main.questionary')
def test_generate_final_prompt_with_answers(mock_questionary, mock_provider):
    """Test that refined prompt is returned when answers are provided."""
    # Since mock_provider is an instance, we need to patch the method differently
    with patch.object(mock_provider, 'refine_from_answers', return_value="refined prompt"):
        final_prompt, is_refined = generate_final_prompt(
            mock_provider,
            "original prompt",
            {"audience": "developers"},
            {"audience": "Who is the target audience?"},
            Mock()
        )
        
        assert final_prompt == "refined prompt"
        assert is_refined


def test_process_single_prompt_quick_mode(mock_provider, mock_config, mock_notify):
    """Test single prompt processing in quick mode."""
    args = Namespace(quick=True, copy=False, edit=False)
    
    result = process_single_prompt(
        mock_provider,
        "test prompt",
        args,
        False,  # debug_enabled
        False,  # plain_mode
        mock_notify,
        mock_config
    )
    
    # Should return the original prompt since in quick mode
    if result:
        final_prompt, task_type = result
        assert final_prompt == "test prompt"


def test_process_single_prompt_with_refinement(mock_provider, mock_config, mock_notify):
    """Test single prompt processing with refinement."""
    args = Namespace(quick=False, copy=False, edit=False)
    
    # Mock the provider's light_refine method
    with patch.object(mock_provider, 'light_refine', return_value="refined prompt"):
        # Mock the determine_question_plan to return analysis task type
        with patch('promptheus.main.determine_question_plan') as mock_plan:
            from promptheus.main import QuestionPlan
            plan = QuestionPlan(skip_questions=True, task_type="analysis", questions=[], mapping={})
            mock_plan.return_value = plan
            
            result = process_single_prompt(
                mock_provider,
                "test prompt",
                args,
                False,  # debug_enabled
                False,  # plain_mode
                mock_notify,
                mock_config
            )
            
            if result:
                final_prompt, task_type = result
                assert final_prompt == "refined prompt"


class DummyConfig:
    """Simple config stub for end-to-end style tests."""

    provider = "google"

    def get_model(self) -> str:
        return "gemini-1.5-pro"

    def get_configured_providers(self):
        return ["google", "openai"]


class FullFlowProvider:
    """Provider stub that behaves like a happy-path generation backend."""

    name = "stub-google"

    def generate_questions(self, initial_prompt: str, system_instruction: str):
        return {
            "task_type": "generation",
            "questions": [
                {
                    "question": "What details should the AI include?",
                    "type": "text",
                    "required": True,
                }
            ],
        }

    def refine_from_answers(self, initial_prompt, answers, mapping, system_instruction):
        return f"Refined: {answers.get('q0', '')}"

    def light_refine(self, prompt, system_instruction):  # pragma: no cover - safety net for misuse
        raise AssertionError("Light refinement should not run in this flow")


class FailingLightRefineProvider:
    """Provider stub that raises when light refinement is attempted."""

    name = "stub-anthropic"

    def light_refine(self, prompt, system_instruction):
        raise RuntimeError("Simulated provider outage")


class StaticPrompter:
    """Lightweight QuestionPrompter substitute returning canned responses."""

    def __init__(self, text_answers, confirm=True):
        self._answers = iter(text_answers)
        self._confirm = confirm

    def prompt_confirmation(self, message, default=True):
        return self._confirm

    def prompt_text(self, message, default=""):
        return next(self._answers)

    def prompt_radio(self, message, choices):  # pragma: no cover - fallback behavior
        return choices[0] if choices else ""

    def prompt_checkbox(self, message, choices):  # pragma: no cover - fallback behavior
        return []


def _build_io_context(*, quiet_output: bool, stdin_is_tty: bool, stdout_is_tty: bool):
    stdout_buffer = StringIO()
    stderr_buffer = StringIO()
    notifications = []

    def notifier(message: str):
        notifications.append(message)

    io_ctx = IOContext(
        stdin_is_tty=stdin_is_tty,
        stdout_is_tty=stdout_is_tty,
        console_out=Console(file=stdout_buffer, force_terminal=False, color_system=None),
        console_err=Console(file=stderr_buffer, force_terminal=False, color_system=None),
        notify=notifier,
        quiet_output=quiet_output,
        plain_mode=False,
    )
    return io_ctx, notifications


def test_process_single_prompt_runs_full_generation_flow(monkeypatch):
    """End-to-end: question confirmation, answers, refinement, and history save."""

    io_ctx, _ = _build_io_context(quiet_output=True, stdin_is_tty=True, stdout_is_tty=False)
    provider = FullFlowProvider()
    args = Namespace(skip_questions=False, quick=False, copy=False, edit=False, refine=False)
    config = DummyConfig()

    def fake_create_prompter(io_unused):
        return StaticPrompter(["Detailed onboarding brief"])

    saved_entry = {}

    class DummyHistory:
        def save_entry(self, **payload):
            saved_entry.update(payload)

    monkeypatch.setattr("promptheus.main.create_prompter", fake_create_prompter)
    monkeypatch.setattr("promptheus.main.get_history", lambda cfg: DummyHistory())
    monkeypatch.setattr("promptheus.main.display_output", lambda prompt, io, is_refined=True: None)

    result = process_single_prompt(provider, "Draft onboarding brief", args, False, False, io_ctx, config)

    assert result == ("Refined: Detailed onboarding brief", "generation")
    assert saved_entry["original_prompt"] == "Draft onboarding brief"
    assert saved_entry["refined_prompt"] == "Refined: Detailed onboarding brief"
    assert saved_entry["task_type"] == "generation"


def test_process_single_prompt_light_refine_failure_keeps_original(monkeypatch):
    """Integration: provider failure during light refinement falls back to input."""

    io_ctx, notifications = _build_io_context(quiet_output=True, stdin_is_tty=True, stdout_is_tty=False)
    provider = FailingLightRefineProvider()
    args = Namespace(skip_questions=False, quick=False, copy=False, edit=False, refine=False)
    config = DummyConfig()

    monkeypatch.setattr(
        "promptheus.main.determine_question_plan",
        lambda *call_args, **kwargs: QuestionPlan(True, "analysis", [], {}),
    )

    saved_entry = {}

    class DummyHistory:
        def save_entry(self, **payload):
            saved_entry.update(payload)

    monkeypatch.setattr("promptheus.main.get_history", lambda cfg: DummyHistory())
    monkeypatch.setattr("promptheus.main.display_output", lambda prompt, io, is_refined=True: None)

    result = process_single_prompt(provider, "Need graceful fallback", args, False, False, io_ctx, config)

    assert result == ("Need graceful fallback", "analysis")
    assert any("Light refinement failed" in msg for msg in notifications)
    assert saved_entry["refined_prompt"] == "Need graceful fallback"


def test_determine_question_plan_declined_questions_use_light_refinement(monkeypatch):
    """Unit: declining clarifying questions should trigger light refinement path."""

    io_ctx, _ = _build_io_context(quiet_output=False, stdin_is_tty=True, stdout_is_tty=True)
    provider = FullFlowProvider()
    args = Namespace(skip_questions=False, refine=False)
    config = DummyConfig()

    def declining_prompter(io_unused):
        return StaticPrompter(["unused"], confirm=False)

    monkeypatch.setattr("promptheus.main.create_prompter", declining_prompter)

    plan = determine_question_plan(provider, "Scope new onboarding doc", args, False, io_ctx, config)

    assert plan.skip_questions is True
    assert plan.use_light_refinement is True
    assert plan.questions == []


def test_process_single_prompt_history_failure_does_not_abort(monkeypatch):
    """Regression: history persistence errors should not prevent returning prompts."""

    io_ctx, _ = _build_io_context(quiet_output=True, stdin_is_tty=True, stdout_is_tty=False)
    provider = FullFlowProvider()
    args = Namespace(skip_questions=False, quick=False, copy=False, edit=False, refine=False)
    config = DummyConfig()

    def fake_history(_cfg):
        raise RuntimeError("disk full")

    logger_mock = Mock()
    logger_mock.debug = Mock()
    logger_mock.warning = Mock()
    logger_mock.exception = Mock()

    monkeypatch.setattr("promptheus.main.create_prompter", lambda io_unused: StaticPrompter(["Plan outputs"]))
    monkeypatch.setattr("promptheus.main.display_output", lambda prompt, io, is_refined=True: None)
    monkeypatch.setattr("promptheus.main.get_history", fake_history)
    monkeypatch.setattr("promptheus.main.logger", logger_mock)

    result = process_single_prompt(provider, "Persist this prompt", args, False, False, io_ctx, config)

    assert result == ("Refined: Plan outputs", "generation")
    logger_mock.warning.assert_called_once()


def test_main_mcp_subcommand_dispatches_and_handles_import_error(monkeypatch):
    """CLI wiring: main() should dispatch to run_mcp_server and handle ImportError."""
    import promptheus.main as main_module

    # Simulate parsed arguments for the mcp subcommand.
    args = Namespace(
        command="mcp",
        version=False,
        verbose=False,
        provider=None,
        model=None,
    )

    monkeypatch.setattr(main_module, "parse_arguments", lambda: args)

    notifications = []

    class DummyIO:
        def __init__(self) -> None:
            self.notify = notifications.append

    monkeypatch.setattr(main_module, "IOContext", type("IOContextStub", (), {"create": staticmethod(lambda: DummyIO())}))

    def failing_run_mcp_server():
        raise ImportError("The 'mcp' package is not installed. Please install it with 'pip install mcp'.")

    monkeypatch.setattr("promptheus.mcp_server.run_mcp_server", failing_run_mcp_server)

    with pytest.raises(SystemExit) as excinfo:
        main_module.main()

    # CLI should exit with non-zero status and emit a helpful message.
    assert excinfo.value.code == 1
    assert any("The 'mcp' package is not installed" in msg for msg in notifications)
