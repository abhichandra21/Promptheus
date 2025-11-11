"""Custom exception types for Promptheus."""

class PromptCancelled(KeyboardInterrupt):
    """Raised when the user cancels an in-flight prompt operation."""

    def __init__(self, message: str = "Prompt cancelled by user") -> None:
        super().__init__(message)

class ProviderAPIError(Exception):
    """Raised when an LLM provider API call fails."""
    pass


class TemplateError(Exception):
    """Base class for template generation errors."""
    pass


class InvalidProviderError(TemplateError):
    """Raised when an invalid provider is specified for template generation."""
    pass


class FileWriteError(TemplateError):
    """Raised when template file writing fails."""
    pass