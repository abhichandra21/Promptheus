"""
Command implementations for utility functions like listing models and validating config.
"""

# Re-export all functionality from submodules
from .completion import handle_completion_request
from .providers import list_models, validate_environment
from .template import generate_template
from promptheus.completions import generate_completion_script, install_completion
from promptheus._provider_data import _select_test_model, _test_provider_connection
from promptheus.providers import get_provider

__all__ = [
    # Completion-related commands
    "handle_completion_request",
    "generate_completion_script",
    "install_completion",

    # Provider-related commands
    "list_models",
    "validate_environment",
    "get_provider",

    # Template commands
    "generate_template",

    # Internal test utilities (needed for tests)
    "_select_test_model",
    "_test_provider_connection",
]