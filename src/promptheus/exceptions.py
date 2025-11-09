"""Custom exception types for Promptheus."""

class PromptCancelled(KeyboardInterrupt):
    """Raised when the user cancels an in-flight prompt operation."""

    def __init__(self, message: str = "Prompt cancelled by user") -> None:
        super().__init__(message)
