"""
Core AI response wrapper for TUI integration.
This module provides a simplified interface for the TUI to interact with the AI backend.
"""

from __future__ import annotations

import logging
import time
from argparse import Namespace
from typing import Optional

from promptheus.config import Config
from promptheus.main import process_single_prompt
from promptheus.providers import LLMProvider, get_provider
from promptheus.utils import sanitize_error_message

logger = logging.getLogger(__name__)


def get_ai_response(prompt: str, provider: Optional[LLMProvider] = None, config: Optional[Config] = None) -> str:
    """
    Simplified AI response function for TUI integration.

    This is a BLOCKING function that takes a user prompt,
    processes it through the Promptheus pipeline, and returns the refined response.

    Args:
        prompt: The user's input prompt
        provider: Optional LLMProvider instance (will create default if not provided)
        config: Optional Config instance (will create default if not provided)

    Returns:
        The refined prompt string

    Raises:
        RuntimeError: If the AI call fails
    """
    try:
        # Simulate processing time for demo purposes
        time.sleep(0.5)

        # Initialize config and provider if not provided
        if config is None:
            config = Config()

        if provider is None:
            provider_name = config.provider or "gemini"
            provider = get_provider(provider_name, config, config.get_model())

        # Create minimal args for quick mode (skip questions)
        args = Namespace(
            static=False,
            quick=True,  # Skip questions for TUI mode
            refine=False,
            copy=False,
            edit=False,
            verbose=False,
            file=None,
            prompt=prompt,
            provider=None,
            model=None,
            list_models=False,
            validate=False,
            test_connection=False,
            template=None,
            command=None,
        )

        # Capture output messages
        messages = []
        def capture_notify(msg: str) -> None:
            """Capture notification messages."""
            messages.append(msg)

        # Process the prompt through the main pipeline
        result = process_single_prompt(
            provider=provider,
            initial_prompt=prompt,
            args=args,
            debug_enabled=False,
            plain_mode=True,
            notify=capture_notify,
            app_config=config,
        )

        if result is None:
            raise RuntimeError("Failed to process prompt")

        final_prompt, task_type = result
        return final_prompt

    except Exception as exc:
        sanitized = sanitize_error_message(str(exc))
        error_msg = f"AI Error: {sanitized}"
        logger.exception("AI response generation failed")
        raise RuntimeError(error_msg) from exc
