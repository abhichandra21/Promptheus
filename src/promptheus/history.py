"""
Session history management for Promptheus.
Handles saving and retrieving prompt refinement history.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def get_default_history_dir() -> Path:
    """
    Get the default history directory based on platform.

    Returns:
        Path: Platform-appropriate history directory
            - Unix/Linux/Mac: ~/.promptheus
            - Windows: %APPDATA%/promptheus
    """
    if sys.platform == "win32":
        # On Windows, use AppData/Roaming
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "promptheus"
        # Fallback to home directory if APPDATA not set
        return Path.home() / "promptheus"
    else:
        # Unix-like systems: use hidden directory in home
        return Path.home() / ".promptheus"


@dataclass
class HistoryEntry:
    """Represents a single history entry."""
    timestamp: str
    original_prompt: str
    refined_prompt: str
    task_type: Optional[str] = None

    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        """Create from dictionary."""
        return cls(**data)


class PromptHistory:
    """Manages prompt history storage and retrieval."""

    def __init__(self, history_dir: Optional[Path] = None):
        """
        Initialize history manager.

        Args:
            history_dir: Directory to store history files. Defaults to platform-specific location:
                - Unix/Linux/Mac: ~/.promptheus
                - Windows: %APPDATA%/promptheus
        """
        if history_dir is None:
            history_dir = get_default_history_dir()

        self.history_dir = history_dir
        self.history_file = self.history_dir / "history.json"
        self.prompt_history_file = self.history_dir / "prompt_history.txt"

        # Create directory if it doesn't exist
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Create history directory if it doesn't exist."""
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.error(f"Failed to create history directory: {exc}")

    def save_entry(
        self,
        original_prompt: str,
        refined_prompt: str,
        task_type: Optional[str] = None
    ) -> None:
        """
        Save a history entry.

        Args:
            original_prompt: The original user prompt
            refined_prompt: The final refined/accepted prompt
            task_type: Type of task (analysis, generation, etc.)
        """
        entry = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            original_prompt=original_prompt,
            refined_prompt=refined_prompt,
            task_type=task_type
        )

        try:
            # Load existing history
            history = self._load_history()

            # Add new entry
            history.append(entry)

            # Save updated history
            self._save_history(history)

            # Also save to prompt history file for arrow key navigation
            self._append_to_prompt_history(original_prompt)

            logger.debug(f"Saved history entry: {entry.timestamp}")

        except Exception as exc:
            logger.error(f"Failed to save history entry: {exc}")

    def _load_history(self) -> List[HistoryEntry]:
        """Load history from file."""
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [HistoryEntry.from_dict(entry) for entry in data]
        except Exception as exc:
            logger.error(f"Failed to load history: {exc}")
            return []

    def _save_history(self, history: List[HistoryEntry]) -> None:
        """Save history to file."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([entry.to_dict() for entry in history], f, indent=2)
        except Exception as exc:
            logger.error(f"Failed to save history: {exc}")

    def _append_to_prompt_history(self, prompt: str) -> None:
        """Append a prompt to the prompt history file for arrow key navigation."""
        try:
            with open(self.prompt_history_file, 'a', encoding='utf-8') as f:
                # Write prompt on a single line, escaping newlines
                sanitized = prompt.replace('\n', '\\n')
                f.write(f"{sanitized}\n")
        except Exception as exc:
            logger.error(f"Failed to append to prompt history: {exc}")

    def get_recent(self, limit: int = 20) -> List[HistoryEntry]:
        """
        Get recent history entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of history entries, most recent first
        """
        history = self._load_history()
        return list(reversed(history[-limit:]))

    def get_all(self) -> List[HistoryEntry]:
        """Get all history entries, most recent first."""
        history = self._load_history()
        return list(reversed(history))

    def get_by_index(self, index: int) -> Optional[HistoryEntry]:
        """
        Get a history entry by index (1-based, from most recent).

        Args:
            index: 1-based index (1 = most recent)

        Returns:
            History entry or None if index is out of range
        """
        history = self.get_all()
        if 1 <= index <= len(history):
            return history[index - 1]
        return None

    def clear(self) -> None:
        """Clear all history."""
        try:
            if self.history_file.exists():
                self.history_file.unlink()
            if self.prompt_history_file.exists():
                self.prompt_history_file.unlink()
            logger.info("History cleared")
        except Exception as exc:
            logger.error(f"Failed to clear history: {exc}")

    def get_prompt_history_file(self) -> Path:
        """Get the path to the prompt history file for arrow key navigation."""
        return self.prompt_history_file


# Global instance
_history_instance: Optional[PromptHistory] = None


def get_history() -> PromptHistory:
    """Get the global history instance."""
    global _history_instance
    if _history_instance is None:
        _history_instance = PromptHistory()
    return _history_instance
