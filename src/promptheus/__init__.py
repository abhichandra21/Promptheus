"""
Promptheus - AI-powered prompt engineering tool and library.

Promptheus can be used as both a CLI tool and a Python library for
programmatic prompt refinement.

CLI Usage:
    $ promptheus "Write a blog post"
    $ promptheus --skip-questions "Explain Docker"

Library Usage:
    >>> from promptheus import refine_prompt, Config
    >>>
    >>> result = refine_prompt("Write a blog post about AI")
    >>> print(result['refined_prompt'])
    >>>
    >>> # With specific configuration
    >>> config = Config(provider="openai", model="gpt-4o")
    >>> result = refine_prompt(
    ...     "Explain quantum computing",
    ...     config=config,
    ...     skip_questions=True
    ... )
"""

__version__ = "0.3.1"

# Library API exports
from promptheus.api import (
    refine_prompt,
    tweak_prompt,
    generate_questions,
    refine_with_answers,
    list_available_providers,
    list_available_models,
)

# Core classes and functions
from promptheus.config import Config
from promptheus.providers import get_provider, LLMProvider

# Exceptions
from promptheus.exceptions import (
    PromptCancelled,
    ProviderAPIError,
    InvalidProviderError,
)

__all__ = [
    # Version
    "__version__",
    # Main API functions
    "refine_prompt",
    "tweak_prompt",
    "generate_questions",
    "refine_with_answers",
    "list_available_providers",
    "list_available_models",
    # Configuration
    "Config",
    # Provider management
    "get_provider",
    "LLMProvider",
    # Exceptions
    "PromptCancelled",
    "ProviderAPIError",
    "InvalidProviderError",
]
