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

from promptheus.utils import sanitize_error_message

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

    def __init__(self, history_dir: Optional[Path] = None, config=None):
        """
        Initialize history manager.

        Args:
            history_dir: Directory to store history files. Defaults to platform-specific location:
                - Unix/Linux/Mac: ~/.promptheus
                - Windows: %APPDATA%/promptheus
            config: Configuration object to check if history is enabled
        """
        if history_dir is None:
            history_dir = get_default_history_dir()

        self.history_dir = history_dir
        self.history_file = self.history_dir / "history.jsonl"  # JSONL format
        self.prompt_history_file = self.history_dir / "prompt_history.txt"
        self.config = config

        # Create directory if it doesn't exist
        self._ensure_directory()

    @property
    def enabled(self) -> bool:
        """Check if history persistence is enabled."""
        if self.config is None:
            # Fallback to enabled if no config provided (backward compatibility)
            return True
        return self.config.history_enabled

    def _ensure_directory(self) -> None:
        """Create history directory if it doesn't exist."""
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.error(
                "Permission denied when creating history directory at %s",
                self.history_dir,
            )
        except OSError as exc:
            logger.error(
                "Failed to create history directory (%s): %s",
                self.history_dir,
                sanitize_error_message(str(exc)),
            )

    def save_entry(
        self,
        original_prompt: str,
        refined_prompt: str,
        task_type: Optional[str] = None
    ) -> None:
        """
        Save a history entry in O(1) time using append-only JSONL format.

        Args:
            original_prompt: The original user prompt
            refined_prompt: The final refined/accepted prompt
            task_type: Type of task (analysis, generation, etc.)
        """
        # Check if history is enabled
        if not self.enabled:
            logger.debug("History persistence is disabled - skipping save")
            return

        entry = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            original_prompt=original_prompt,
            refined_prompt=refined_prompt,
            task_type=task_type
        )

        try:
            # Append entry to JSONL file (O(1) operation)
            # Use append mode which should be atomic on most systems
            with open(self.history_file, 'a', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f)
                f.write('\n')
                f.flush()  # Ensure data is written immediately

            # Also save to prompt history file for arrow key navigation
            self._append_to_prompt_history(original_prompt)

            logger.debug(f"Saved history entry: {entry.timestamp}")

        except Exception as exc:
            logger.error("Failed to save history entry: %s", sanitize_error_message(str(exc)))

    def _load_history(self) -> List[HistoryEntry]:
        """Load history from JSONL file."""
        if not self.history_file.exists():
            return []

        try:
            history = []
            with open(self.history_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry_data = json.loads(line)
                        history.append(HistoryEntry.from_dict(entry_data))
                    except json.JSONDecodeError as exc:
                        logger.warning(f"Failed to parse history line {line_num}: {exc}")
                        continue
            return history
        except OSError as exc:
            logger.error(
                "Failed to read history file (%s): %s",
                self.history_file,
                sanitize_error_message(str(exc)),
            )
            return []

    def _append_to_prompt_history(self, prompt: str) -> None:
        """Append a prompt to the prompt history file for arrow key navigation."""
        # Check if history is enabled
        if not self.enabled:
            logger.debug("History persistence is disabled - skipping prompt history append")
            return

        try:
            with open(self.prompt_history_file, 'a', encoding='utf-8') as f:
                # Write prompt on a single line with proper escaping
                # Escape control characters that would break the one-line-per-entry format
                sanitized = prompt.replace('\\', '\\\\').replace('\r', '\\r').replace('\n', '\\n')
                f.write(f"{sanitized}\n")
        except OSError as exc:
            logger.error(
                "Failed to append to prompt history file (%s): %s",
                self.prompt_history_file,
                sanitize_error_message(str(exc)),
            )

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
        if not self.history_file.exists():
            return None

        try:
            # For JSONL format, we can read line by line to find the target index
            # We need to read from the beginning and keep track of line count
            current_index = 0
            lines = []

            with open(self.history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    current_index += 1
                    lines.append(line)

                    # Keep only the most recent entries up to the target index
                    if len(lines) > index:
                        lines.pop(0)  # Remove oldest line to maintain size

            if 1 <= index <= len(lines):
                target_line = lines[-index]  # Get the line from end (most recent)
                entry_data = json.loads(target_line)
                return HistoryEntry.from_dict(entry_data)

            return None
        except (OSError, json.JSONDecodeError, IndexError) as exc:
            logger.warning(f"Failed to get history entry by index {index}: {exc}")
            return None

    def clear(self) -> None:
        """Clear all history."""
        try:
            if self.history_file.exists():
                self.history_file.unlink()
            if self.prompt_history_file.exists():
                self.prompt_history_file.unlink()
            logger.info("History cleared")
        except OSError as exc:
            logger.error(
                "Failed to clear history files: %s",
                sanitize_error_message(str(exc)),
            )

    def get_prompt_history_file(self) -> Path:
        """Get the path to the prompt history file for arrow key navigation."""
        return self.prompt_history_file


# Global instance
_history_instance: Optional[PromptHistory] = None


def get_history(config=None) -> PromptHistory:
    """
    Get the global history instance.

    Args:
        config: Optional configuration object to check history settings

    Returns:
        PromptHistory instance with config applied if provided
    """
    global _history_instance
    if _history_instance is None or config is not None:
        _history_instance = PromptHistory(config=config)
    return _history_instance
