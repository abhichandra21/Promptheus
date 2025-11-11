"""
Command implementations for utility functions like listing models and validating config.
"""

# Re-export all functionality from submodules
from .completion import handle_completion_request
from .personas import list_personas
from .providers import list_models, validate_environment
from .template import generate_template
from promptheus.completions import generate_completion_script, install_completion

__all__ = [
    # Completion-related commands
    "handle_completion_request",
    "generate_completion_script",
    "install_completion",

    # Persona-related commands
    "list_personas",

    # Provider-related commands
    "list_models",
    "validate_environment",

    # Template commands
    "generate_template",
]