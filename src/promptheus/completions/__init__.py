"""
Shell completion functionality for Promptheus.
"""

from .completion import generate_completion_script, install_completion, load_completion_template

__all__ = [
    "generate_completion_script",
    "install_completion",
    "load_completion_template",
]