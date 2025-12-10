"""
Promptheus Library API

This module provides a clean programmatic interface for using Promptheus
as a library in your Python applications.

Example usage:
    >>> from promptheus import refine_prompt, Config
    >>>
    >>> # Simple refinement
    >>> result = refine_prompt("Write a blog post about AI")
    >>> print(result['refined_prompt'])
    >>>
    >>> # With specific provider and model
    >>> config = Config(provider="openai", model="gpt-4o")
    >>> result = refine_prompt(
    ...     "Explain quantum computing",
    ...     config=config,
    ...     skip_questions=True
    ... )
    >>> print(result['refined_prompt'])
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from argparse import Namespace

from promptheus.config import Config
from promptheus.providers import LLMProvider, get_provider
from promptheus.prompts import (
    ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION,
    CLARIFICATION_SYSTEM_INSTRUCTION,
    GENERATION_SYSTEM_INSTRUCTION,
    TWEAK_SYSTEM_INSTRUCTION,
)
from promptheus.exceptions import ProviderAPIError, InvalidProviderError
from promptheus.utils import sanitize_error_message

logger = logging.getLogger(__name__)

__all__ = [
    "refine_prompt",
    "tweak_prompt",
    "generate_questions",
    "refine_with_answers",
    "list_available_providers",
    "list_available_models",
]


def refine_prompt(
    prompt: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    config: Optional[Config] = None,
    skip_questions: bool = True,
    answers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Refine a prompt using AI.

    This is the main library function for prompt refinement. It can operate in
    several modes:

    1. Light refinement (skip_questions=True, default):
       Quick improvement without asking clarifying questions

    2. Question-based refinement (skip_questions=False):
       Generates clarifying questions that you can answer programmatically

    3. Answer-based refinement (answers provided):
       Refines the prompt based on provided answers

    Args:
        prompt: The original prompt to refine
        provider: AI provider to use (google, openai, anthropic, etc.)
                 Overrides config if provided
        model: Specific model to use. Overrides config if provided
        config: Configuration object. If None, creates default config
        skip_questions: If True, performs light refinement without questions
        answers: Pre-provided answers to questions (dict of question_id -> answer)

    Returns:
        Dictionary containing:
        - refined_prompt (str): The refined prompt
        - task_type (str): Detected task type ('analysis' or 'generation')
        - was_refined (bool): Whether refinement was applied
        - provider (str): Provider used
        - model (str): Model used
        - questions (List[Dict], optional): Generated questions if skip_questions=False
        - question_mapping (Dict, optional): Mapping of question IDs to text

    Raises:
        ProviderAPIError: If the AI provider fails
        InvalidProviderError: If the specified provider is invalid
        ValueError: If invalid arguments are provided

    Examples:
        >>> # Simple light refinement
        >>> result = refine_prompt("Write a blog post")
        >>> print(result['refined_prompt'])

        >>> # Get questions for refinement
        >>> result = refine_prompt("Write a blog post", skip_questions=False)
        >>> if 'questions' in result:
        ...     # Present questions to user, collect answers
        ...     answers = {'q0': 'Technical audience', 'q1': '1000 words'}
        ...     final = refine_prompt("Write a blog post", answers=answers)
        ...     print(final['refined_prompt'])

        >>> # Use specific provider and model
        >>> config = Config(provider="anthropic", model="claude-3-5-sonnet-20241022")
        >>> result = refine_prompt("Explain Docker", config=config)
    """
    # Initialize configuration
    if config is None:
        config = Config()

    # Override provider/model if specified
    if provider:
        config.set_provider(provider)
    if model:
        config.set_model(model)

    # Validate configuration
    if not config.validate():
        error_messages = config.consume_error_messages()
        raise ValueError(f"Configuration invalid: {'; '.join(error_messages)}")

    # Get provider instance
    provider_name = config.provider or "google"
    provider_instance = get_provider(provider_name, config, config.get_model())

    # If answers are provided, do answer-based refinement
    if answers is not None:
        return _refine_with_answers_impl(
            provider_instance, prompt, answers, config
        )

    # If skip_questions=True, do light refinement
    if skip_questions:
        return _light_refine_impl(provider_instance, prompt, config)

    # Otherwise, generate questions for refinement
    return _generate_questions_impl(provider_instance, prompt, config)


def tweak_prompt(
    prompt: str,
    tweak_instruction: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    config: Optional[Config] = None,
) -> Dict[str, Any]:
    """
    Make a specific tweak to a prompt.

    This function applies a targeted modification to an existing prompt
    based on a natural language instruction.

    Args:
        prompt: The current prompt to modify
        tweak_instruction: Natural language description of the change
                          (e.g., "make it more concise", "add technical details")
        provider: AI provider to use (overrides config)
        model: Specific model to use (overrides config)
        config: Configuration object

    Returns:
        Dictionary containing:
        - tweaked_prompt (str): The modified prompt
        - provider (str): Provider used
        - model (str): Model used

    Raises:
        ProviderAPIError: If the AI provider fails
        ValueError: If arguments are invalid

    Examples:
        >>> result = tweak_prompt(
        ...     "Write a blog post about AI",
        ...     "make it more technical and add specific examples"
        ... )
        >>> print(result['tweaked_prompt'])
    """
    if config is None:
        config = Config()

    if provider:
        config.set_provider(provider)
    if model:
        config.set_model(model)

    if not config.validate():
        error_messages = config.consume_error_messages()
        raise ValueError(f"Configuration invalid: {'; '.join(error_messages)}")

    provider_name = config.provider or "google"
    provider_instance = get_provider(provider_name, config, config.get_model())

    try:
        tweaked = provider_instance.tweak_prompt(
            prompt, tweak_instruction, TWEAK_SYSTEM_INSTRUCTION
        )
        return {
            "tweaked_prompt": tweaked,
            "provider": provider_name,
            "model": config.get_model(),
        }
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        logger.exception("Tweak failed")
        raise ProviderAPIError(f"Failed to tweak prompt: {sanitized}") from exc


def generate_questions(
    prompt: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    config: Optional[Config] = None,
) -> Dict[str, Any]:
    """
    Generate clarifying questions for a prompt.

    This function analyzes a prompt and generates relevant clarifying
    questions that can help refine it.

    Args:
        prompt: The prompt to analyze
        provider: AI provider to use (overrides config)
        model: Specific model to use (overrides config)
        config: Configuration object

    Returns:
        Dictionary containing:
        - task_type (str): Detected task type ('analysis' or 'generation')
        - questions (List[Dict]): List of question objects with:
          - question (str): The question text
          - type (str): Question type (text, radio, checkbox, confirm)
          - options (List[str], optional): Answer options for radio/checkbox
          - required (bool): Whether the question is required
          - default (Any, optional): Default answer
        - question_mapping (Dict[str, str]): Maps question IDs (q0, q1...) to text
        - provider (str): Provider used
        - model (str): Model used

    Raises:
        ProviderAPIError: If the AI provider fails

    Examples:
        >>> result = generate_questions("Write a blog post about AI")
        >>> for q in result['questions']:
        ...     print(f"{q['question']} (type: {q['type']})")
        >>>
        >>> # Use the question_mapping to build answers
        >>> mapping = result['question_mapping']
        >>> answers = {
        ...     'q0': 'Technical audience',
        ...     'q1': '1500 words'
        ... }
    """
    if config is None:
        config = Config()

    if provider:
        config.set_provider(provider)
    if model:
        config.set_model(model)

    if not config.validate():
        error_messages = config.consume_error_messages()
        raise ValueError(f"Configuration invalid: {'; '.join(error_messages)}")

    provider_name = config.provider or "google"
    provider_instance = get_provider(provider_name, config, config.get_model())

    return _generate_questions_impl(provider_instance, prompt, config)


def refine_with_answers(
    prompt: str,
    answers: Dict[str, Any],
    question_mapping: Optional[Dict[str, str]] = None,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    config: Optional[Config] = None,
) -> Dict[str, Any]:
    """
    Refine a prompt using provided answers to clarifying questions.

    This function takes a prompt and answers to previously generated
    questions, and produces a refined prompt.

    Args:
        prompt: The original prompt
        answers: Dictionary mapping question IDs to answers
        question_mapping: Optional mapping of question IDs to question text
                         (provides context for better refinement)
        provider: AI provider to use (overrides config)
        model: Specific model to use (overrides config)
        config: Configuration object

    Returns:
        Dictionary containing:
        - refined_prompt (str): The refined prompt
        - provider (str): Provider used
        - model (str): Model used

    Raises:
        ProviderAPIError: If the AI provider fails

    Examples:
        >>> # First, generate questions
        >>> q_result = generate_questions("Write a blog post")
        >>>
        >>> # Collect answers (from user, database, etc.)
        >>> answers = {
        ...     'q0': 'Technical developers',
        ...     'q1': '1200 words',
        ...     'q2': ['SEO optimization', 'Code examples']
        ... }
        >>>
        >>> # Refine with answers
        >>> result = refine_with_answers(
        ...     "Write a blog post",
        ...     answers,
        ...     q_result['question_mapping']
        ... )
        >>> print(result['refined_prompt'])
    """
    if config is None:
        config = Config()

    if provider:
        config.set_provider(provider)
    if model:
        config.set_model(model)

    if not config.validate():
        error_messages = config.consume_error_messages()
        raise ValueError(f"Configuration invalid: {'; '.join(error_messages)}")

    provider_name = config.provider or "google"
    provider_instance = get_provider(provider_name, config, config.get_model())

    return _refine_with_answers_impl(
        provider_instance, prompt, answers, config, question_mapping
    )


def list_available_providers(config: Optional[Config] = None) -> List[str]:
    """
    List all available (configured) AI providers.

    Returns only providers that have valid API keys configured.

    Args:
        config: Optional configuration object

    Returns:
        List of provider names (e.g., ['google', 'openai', 'anthropic'])

    Examples:
        >>> providers = list_available_providers()
        >>> print(f"Available providers: {', '.join(providers)}")
    """
    if config is None:
        config = Config()

    return config.get_configured_providers()


def list_available_models(
    provider: Optional[str] = None,
    config: Optional[Config] = None,
) -> Dict[str, List[str]]:
    """
    List available models for one or all providers.

    Args:
        provider: Specific provider to list models for (None = all providers)
        config: Optional configuration object

    Returns:
        Dictionary mapping provider names to lists of model names
        Example: {'google': ['gemini-2.0-flash', 'gemini-1.5-pro'], ...}

    Examples:
        >>> # List all models
        >>> all_models = list_available_models()
        >>> for provider, models in all_models.items():
        ...     print(f"{provider}: {', '.join(models)}")
        >>>
        >>> # List models for specific provider
        >>> openai_models = list_available_models(provider='openai')
        >>> print(openai_models['openai'])
    """
    if config is None:
        config = Config()

    from promptheus._provider_data import PROVIDER_DATA

    if provider:
        if provider not in PROVIDER_DATA:
            raise ValueError(f"Unknown provider: {provider}")
        models = [m['name'] for m in PROVIDER_DATA[provider]['models']]
        return {provider: models}

    # Return all providers
    result = {}
    for prov_name, prov_data in PROVIDER_DATA.items():
        result[prov_name] = [m['name'] for m in prov_data['models']]

    return result


# Internal implementation functions

def _light_refine_impl(
    provider: LLMProvider,
    prompt: str,
    config: Config,
) -> Dict[str, Any]:
    """Internal: Perform light refinement without questions."""
    try:
        refined = provider.light_refine(
            prompt, ANALYSIS_REFINEMENT_SYSTEM_INSTRUCTION
        )
        return {
            "refined_prompt": refined,
            "task_type": "analysis",
            "was_refined": True,
            "provider": provider.name if hasattr(provider, 'name') else config.provider,
            "model": config.get_model(),
        }
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        logger.exception("Light refinement failed")
        raise ProviderAPIError(f"Light refinement failed: {sanitized}") from exc


def _generate_questions_impl(
    provider: LLMProvider,
    prompt: str,
    config: Config,
) -> Dict[str, Any]:
    """Internal: Generate clarifying questions."""
    try:
        result = provider.generate_questions(prompt, CLARIFICATION_SYSTEM_INSTRUCTION)

        if result is None:
            raise ProviderAPIError("Provider returned no questions")

        task_type = result.get("task_type", "generation")
        questions = result.get("questions", [])

        # Build question mapping
        question_mapping = {}
        for idx, q in enumerate(questions):
            question_mapping[f"q{idx}"] = q.get("question", f"Question {idx}")

        return {
            "task_type": task_type,
            "questions": questions,
            "question_mapping": question_mapping,
            "provider": provider.name if hasattr(provider, 'name') else config.provider,
            "model": config.get_model(),
        }
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        logger.exception("Question generation failed")
        raise ProviderAPIError(f"Question generation failed: {sanitized}") from exc


def _refine_with_answers_impl(
    provider: LLMProvider,
    prompt: str,
    answers: Dict[str, Any],
    config: Config,
    question_mapping: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Internal: Refine prompt with provided answers."""
    if question_mapping is None:
        # Build a basic mapping from answer keys
        question_mapping = {key: f"Question {key}" for key in answers.keys()}

    try:
        refined = provider.refine_from_answers(
            prompt, answers, question_mapping, GENERATION_SYSTEM_INSTRUCTION
        )
        return {
            "refined_prompt": refined,
            "provider": provider.name if hasattr(provider, 'name') else config.provider,
            "model": config.get_model(),
        }
    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        logger.exception("Answer-based refinement failed")
        raise ProviderAPIError(f"Answer-based refinement failed: {sanitized}") from exc
