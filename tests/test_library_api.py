"""
Tests for the library API (api.py).

These tests verify that Promptheus can be used as a library for
programmatic prompt refinement.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from promptheus import (
    refine_prompt,
    tweak_prompt,
    generate_questions,
    refine_with_answers,
    list_available_providers,
    list_available_models,
    Config,
    ProviderAPIError,
    InvalidProviderError,
)


class TestRefinePrompt:
    """Test the main refine_prompt() function."""

    def test_refine_prompt_light_mode(self):
        """Test light refinement (skip_questions=True)."""
        with patch('promptheus.api.get_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.name = 'google'
            mock_provider.light_refine.return_value = "Refined prompt here"
            mock_get_provider.return_value = mock_provider

            with patch('promptheus.api.Config') as mock_config_class:
                mock_config = Mock()
                mock_config.validate.return_value = True
                mock_config.provider = 'google'
                mock_config.get_model.return_value = 'gemini-2.0-flash'
                mock_config_class.return_value = mock_config

                result = refine_prompt(
                    "Test prompt",
                    skip_questions=True
                )

                assert result['refined_prompt'] == "Refined prompt here"
                assert result['task_type'] == "analysis"
                assert result['was_refined'] is True
                assert result['provider'] == 'google'
                assert result['model'] == 'gemini-2.0-flash'

                mock_provider.light_refine.assert_called_once()

    def test_refine_prompt_with_provider_override(self):
        """Test refining with specific provider."""
        with patch('promptheus.api.get_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.name = 'openai'
            mock_provider.light_refine.return_value = "Refined"
            mock_get_provider.return_value = mock_provider

            with patch('promptheus.api.Config') as mock_config_class:
                mock_config = Mock()
                mock_config.validate.return_value = True
                mock_config.provider = 'openai'
                mock_config.get_model.return_value = 'gpt-4o'
                mock_config_class.return_value = mock_config

                result = refine_prompt(
                    "Test",
                    provider="openai",
                    model="gpt-4o",
                    skip_questions=True
                )

                mock_config.set_provider.assert_called_once_with("openai")
                mock_config.set_model.assert_called_once_with("gpt-4o")
                assert result['provider'] == 'openai'

    def test_refine_prompt_with_config_object(self):
        """Test using a Config object."""
        with patch('promptheus.api.get_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.name = 'anthropic'
            mock_provider.light_refine.return_value = "Refined"
            mock_get_provider.return_value = mock_provider

            mock_config = Mock()
            mock_config.validate.return_value = True
            mock_config.provider = 'anthropic'
            mock_config.get_model.return_value = 'claude-3-5-sonnet-20241022'

            result = refine_prompt(
                "Test",
                config=mock_config,
                skip_questions=True
            )

            assert result['refined_prompt'] == "Refined"

    def test_refine_prompt_invalid_config(self):
        """Test error handling for invalid configuration."""
        with patch('promptheus.api.Config') as mock_config_class:
            mock_config = Mock()
            mock_config.validate.return_value = False
            mock_config.consume_error_messages.return_value = ['Missing API key']
            mock_config_class.return_value = mock_config

            with pytest.raises(ValueError, match="Configuration invalid"):
                refine_prompt("Test", skip_questions=True)

    def test_refine_prompt_provider_error(self):
        """Test handling of provider API errors."""
        with patch('promptheus.api.get_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.light_refine.side_effect = Exception("API Error")
            mock_get_provider.return_value = mock_provider

            with patch('promptheus.api.Config') as mock_config_class:
                mock_config = Mock()
                mock_config.validate.return_value = True
                mock_config.provider = 'google'
                mock_config.get_model.return_value = 'gemini-2.0-flash'
                mock_config_class.return_value = mock_config

                with pytest.raises(ProviderAPIError):
                    refine_prompt("Test", skip_questions=True)


class TestGenerateQuestions:
    """Test the generate_questions() function."""

    def test_generate_questions_success(self):
        """Test successful question generation."""
        with patch('promptheus.api.get_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.name = 'google'
            mock_provider.generate_questions.return_value = {
                'task_type': 'generation',
                'questions': [
                    {'question': 'What is the target audience?', 'type': 'text', 'required': True},
                    {'question': 'What is the desired length?', 'type': 'text', 'required': True}
                ]
            }
            mock_get_provider.return_value = mock_provider

            with patch('promptheus.api.Config') as mock_config_class:
                mock_config = Mock()
                mock_config.validate.return_value = True
                mock_config.provider = 'google'
                mock_config.get_model.return_value = 'gemini-2.0-flash'
                mock_config_class.return_value = mock_config

                result = generate_questions("Write a blog post")

                assert result['task_type'] == 'generation'
                assert len(result['questions']) == 2
                assert 'question_mapping' in result
                assert result['question_mapping']['q0'] == 'What is the target audience?'
                assert result['question_mapping']['q1'] == 'What is the desired length?'

    def test_generate_questions_empty_result(self):
        """Test handling of empty question result."""
        with patch('promptheus.api.get_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.generate_questions.return_value = None
            mock_get_provider.return_value = mock_provider

            with patch('promptheus.api.Config') as mock_config_class:
                mock_config = Mock()
                mock_config.validate.return_value = True
                mock_config_class.return_value = mock_config

                with pytest.raises(ProviderAPIError, match="Provider returned no questions"):
                    generate_questions("Test")


class TestRefineWithAnswers:
    """Test the refine_with_answers() function."""

    def test_refine_with_answers_success(self):
        """Test refinement with provided answers."""
        with patch('promptheus.api.get_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.name = 'google'
            mock_provider.refine_from_answers.return_value = "Detailed refined prompt"
            mock_get_provider.return_value = mock_provider

            with patch('promptheus.api.Config') as mock_config_class:
                mock_config = Mock()
                mock_config.validate.return_value = True
                mock_config.provider = 'google'
                mock_config.get_model.return_value = 'gemini-2.0-flash'
                mock_config_class.return_value = mock_config

                answers = {
                    'q0': 'Technical developers',
                    'q1': '1500 words'
                }
                question_mapping = {
                    'q0': 'What is the target audience?',
                    'q1': 'What is the desired length?'
                }

                result = refine_with_answers(
                    "Write a blog post",
                    answers,
                    question_mapping
                )

                assert result['refined_prompt'] == "Detailed refined prompt"
                assert result['provider'] == 'google'
                mock_provider.refine_from_answers.assert_called_once()

    def test_refine_with_answers_no_mapping(self):
        """Test refinement without question mapping."""
        with patch('promptheus.api.get_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.name = 'google'
            mock_provider.refine_from_answers.return_value = "Refined"
            mock_get_provider.return_value = mock_provider

            with patch('promptheus.api.Config') as mock_config_class:
                mock_config = Mock()
                mock_config.validate.return_value = True
                mock_config.provider = 'google'
                mock_config.get_model.return_value = 'gemini-2.0-flash'
                mock_config_class.return_value = mock_config

                answers = {'q0': 'Answer'}

                result = refine_with_answers("Test", answers)

                # Should create a basic mapping
                call_args = mock_provider.refine_from_answers.call_args
                assert call_args[0][2] == {'q0': 'Question q0'}


class TestTweakPrompt:
    """Test the tweak_prompt() function."""

    def test_tweak_prompt_success(self):
        """Test successful prompt tweaking."""
        with patch('promptheus.api.get_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.name = 'google'
            mock_provider.tweak_prompt.return_value = "Tweaked prompt"
            mock_get_provider.return_value = mock_provider

            with patch('promptheus.api.Config') as mock_config_class:
                mock_config = Mock()
                mock_config.validate.return_value = True
                mock_config.provider = 'google'
                mock_config.get_model.return_value = 'gemini-2.0-flash'
                mock_config_class.return_value = mock_config

                result = tweak_prompt(
                    "Original prompt",
                    "make it more concise"
                )

                assert result['tweaked_prompt'] == "Tweaked prompt"
                assert result['provider'] == 'google'
                mock_provider.tweak_prompt.assert_called_once()


class TestProviderDiscovery:
    """Test provider and model discovery functions."""

    def test_list_available_providers(self):
        """Test listing available providers."""
        with patch('promptheus.api.Config') as mock_config_class:
            mock_config = Mock()
            mock_config.get_configured_providers.return_value = ['google', 'openai', 'anthropic']
            mock_config_class.return_value = mock_config

            providers = list_available_providers()

            assert providers == ['google', 'openai', 'anthropic']

    def test_list_available_models_all(self):
        """Test listing all models."""
        with patch('promptheus.api.PROVIDER_DATA', {
            'google': {
                'models': [
                    {'name': 'gemini-2.0-flash'},
                    {'name': 'gemini-1.5-pro'}
                ]
            },
            'openai': {
                'models': [
                    {'name': 'gpt-4o'},
                    {'name': 'gpt-4-turbo'}
                ]
            }
        }):
            models = list_available_models()

            assert 'google' in models
            assert 'openai' in models
            assert 'gemini-2.0-flash' in models['google']
            assert 'gpt-4o' in models['openai']

    def test_list_available_models_specific_provider(self):
        """Test listing models for a specific provider."""
        with patch('promptheus.api.PROVIDER_DATA', {
            'google': {
                'models': [
                    {'name': 'gemini-2.0-flash'},
                    {'name': 'gemini-1.5-pro'}
                ]
            }
        }):
            models = list_available_models(provider='google')

            assert 'google' in models
            assert len(models) == 1
            assert 'gemini-2.0-flash' in models['google']

    def test_list_available_models_invalid_provider(self):
        """Test error for invalid provider."""
        with patch('promptheus.api.PROVIDER_DATA', {}):
            with pytest.raises(ValueError, match="Unknown provider"):
                list_available_models(provider='invalid')


class TestIntegrationScenarios:
    """Test common integration scenarios."""

    def test_question_answer_workflow(self):
        """Test full question-answer workflow."""
        with patch('promptheus.api.get_provider') as mock_get_provider:
            mock_provider = Mock()
            mock_provider.name = 'google'

            # Mock question generation
            mock_provider.generate_questions.return_value = {
                'task_type': 'generation',
                'questions': [
                    {'question': 'Target audience?', 'type': 'text', 'required': True}
                ]
            }

            # Mock answer refinement
            mock_provider.refine_from_answers.return_value = "Final refined prompt"

            mock_get_provider.return_value = mock_provider

            with patch('promptheus.api.Config') as mock_config_class:
                mock_config = Mock()
                mock_config.validate.return_value = True
                mock_config.provider = 'google'
                mock_config.get_model.return_value = 'gemini-2.0-flash'
                mock_config_class.return_value = mock_config

                # Step 1: Generate questions
                q_result = generate_questions("Write a blog post")
                assert len(q_result['questions']) == 1

                # Step 2: Provide answers
                answers = {'q0': 'Developers'}

                # Step 3: Refine
                final = refine_with_answers(
                    "Write a blog post",
                    answers,
                    q_result['question_mapping']
                )

                assert final['refined_prompt'] == "Final refined prompt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
