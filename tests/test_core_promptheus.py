"""Essential tests for core Promptheus functionality."""

import os
from unittest.mock import Mock, patch, MagicMock
import pytest
from argparse import Namespace

from promptheus.main import (
    process_single_prompt,
    determine_question_plan,
    ask_clarifying_questions,
    generate_final_prompt,
    iterative_refinement,
    convert_json_to_question_definitions
)
from promptheus.config import Config
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