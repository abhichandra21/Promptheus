"""Essential tests for history management functionality."""

import tempfile
import json
from pathlib import Path
import pytest
from datetime import datetime

from promptheus.history import PromptHistory, HistoryEntry, get_default_history_dir


def test_history_entry_serialization():
    """Test HistoryEntry serialization and deserialization."""
    entry = HistoryEntry(
        timestamp="2023-01-01T12:00:00",
        original_prompt="Original prompt",
        refined_prompt="Refined prompt",
        task_type="generation"
    )
    
    # Test to_dict
    data = entry.to_dict()
    expected = {
        "timestamp": "2023-01-01T12:00:00",
        "original_prompt": "Original prompt", 
        "refined_prompt": "Refined prompt",
        "task_type": "generation"
    }
    assert data == expected
    
    # Test from_dict
    new_entry = HistoryEntry.from_dict(expected)
    assert new_entry.timestamp == "2023-01-01T12:00:00"
    assert new_entry.original_prompt == "Original prompt"
    assert new_entry.refined_prompt == "Refined prompt"
    assert new_entry.task_type == "generation"


def test_prompt_history_initialization():
    """Test PromptHistory initialization with custom directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)
        
        assert history.history_dir == history_dir
        assert history.history_file == history_dir / "history.jsonl"
        assert history.prompt_history_file == history_dir / "prompt_history.txt"
        
        # Directory should be created
        assert history_dir.exists()


def test_save_and_retrieve_entry():
    """Test saving and retrieving a history entry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)
        
        # Save an entry
        history.save_entry(
            original_prompt="Write a blog post",
            refined_prompt="Write a detailed blog post about AI",
            task_type="generation"
        )
        
        # Retrieve entries
        entries = history.get_all()
        
        assert len(entries) == 1
        assert entries[0].original_prompt == "Write a blog post"
        assert entries[0].refined_prompt == "Write a detailed blog post about AI"
        assert entries[0].task_type == "generation"
        
        # Verify the timestamp is valid
        assert entries[0].timestamp is not None
        # Try to parse the timestamp to ensure it's valid ISO format
        datetime.fromisoformat(entries[0].timestamp.replace("Z", "+00:00").split(".")[0])


def test_multiple_entries_order():
    """Test that multiple entries are retrieved in correct order (most recent first)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)
        
        # Save multiple entries
        history.save_entry("Prompt 1", "Refined 1", "generation")
        history.save_entry("Prompt 2", "Refined 2", "analysis")
        history.save_entry("Prompt 3", "Refined 3", "generation")
        
        # Retrieve all (should be most recent first)
        entries = history.get_all()
        
        assert len(entries) == 3
        assert entries[0].original_prompt == "Prompt 3"  # Most recent first
        assert entries[1].original_prompt == "Prompt 2"
        assert entries[2].original_prompt == "Prompt 1"  # Oldest last


def test_get_recent_with_limit():
    """Test getting recent entries with a limit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)
        
        # Save multiple entries
        for i in range(5):
            history.save_entry(f"Prompt {i}", f"Refined {i}", "generation")
        
        # Get only the 3 most recent
        entries = history.get_recent(limit=3)
        
        assert len(entries) == 3
        assert entries[0].original_prompt == "Prompt 4"  # Most recent
        assert entries[1].original_prompt == "Prompt 3"
        assert entries[2].original_prompt == "Prompt 2"


def test_get_by_index():
    """Test getting entry by index (1-based, most recent first)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)
        
        # Save multiple entries
        history.save_entry("Prompt 1", "Refined 1", "generation")
        history.save_entry("Prompt 2", "Refined 2", "analysis")
        history.save_entry("Prompt 3", "Refined 3", "generation")
        
        # Get most recent (index 1)
        entry = history.get_by_index(1)
        assert entry is not None
        assert entry.original_prompt == "Prompt 3"
        
        # Get middle entry (index 2)
        entry = history.get_by_index(2)
        assert entry is not None
        assert entry.original_prompt == "Prompt 2"
        
        # Get oldest (index 3)
        entry = history.get_by_index(3)
        assert entry is not None
        assert entry.original_prompt == "Prompt 1"
        
        # Get out of range
        entry = history.get_by_index(10)
        assert entry is None
        
        # Get negative index
        entry = history.get_by_index(-1)
        assert entry is None


def test_clear_history():
    """Test clearing all history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)
        
        # Add some entries
        history.save_entry("Prompt 1", "Refined 1", "generation")
        history.save_entry("Prompt 2", "Refined 2", "analysis")
        
        # Verify they exist
        entries = history.get_all()
        assert len(entries) == 2
        
        # Clear history
        history.clear()
        
        # Verify it's empty
        entries = history.get_all()
        assert len(entries) == 0
        assert not history.history_file.exists()
        assert not history.prompt_history_file.exists()


def test_history_persistence():
    """Test that history persists across PromptHistory instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        
        # Create first instance and add entries
        history1 = PromptHistory(history_dir=history_dir)
        history1.save_entry("Prompt A", "Refined A", "generation")
        history1.save_entry("Prompt B", "Refined B", "analysis")
        
        # Create second instance and read the same data
        history2 = PromptHistory(history_dir=history_dir)
        entries = history2.get_all()
        
        assert len(entries) == 2
        assert entries[0].original_prompt == "Prompt B"  # Most recent first
        assert entries[1].original_prompt == "Prompt A"


def test_prompt_history_file_creation():
    """Test that prompt history file is created for arrow navigation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)
        
        # Add some entries
        history.save_entry("Prompt 1", "Refined 1", "generation")
        history.save_entry("Prompt 2", "Refined 2", "analysis")
        
        # Check that the prompt history file exists and has content
        prompt_history_file = history.get_prompt_history_file()
        assert prompt_history_file.exists()
        
        with open(prompt_history_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) == 2  # One line per entry
        # The file stores original prompts with newlines escaped
        assert "Prompt 1" in lines[0]
        assert "Prompt 2" in lines[1]


def test_history_file_corruption_handling():
    """Test handling of corrupted history file."""
    from unittest.mock import Mock
    from promptheus.config import Config

    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        # Create a mock config that enables history
        config = Mock()
        config.history_enabled = True
        history = PromptHistory(history_dir=history_dir, config=config)

        # Create a corrupted history file
        with open(history.history_file, 'w', encoding='utf-8') as f:
            f.write("invalid json content\n")

        # Should return empty list instead of crashing
        entries = history.get_all()
        assert entries == []

        # Should still be able to add new entries
        history.save_entry("New Prompt", "Refined New", "generation")
        entries = history.get_all()
        assert len(entries) == 1
        assert entries[0].original_prompt == "New Prompt"


def test_get_default_history_dir():
    """Test getting default history directory path."""
    history_dir = get_default_history_dir()
    
    # The path should be under the home directory
    assert str(history_dir).startswith(str(Path.home()))
    
    # The exact name may vary by platform, but should be reasonable
    assert "promptheus" in str(history_dir).lower()


def test_history_entry_optional_task_type():
    """Test that HistoryEntry works with optional task_type."""
    entry = HistoryEntry(
        timestamp="2023-01-01T12:00:00",
        original_prompt="Test prompt",
        refined_prompt="Refined test prompt"
        # task_type is not provided (should be None)
    )
    
    assert entry.task_type is None
    
    # Save and retrieve with optional task_type
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)
        
        history.save_entry(
            original_prompt="Test prompt",
            refined_prompt="Refined test prompt"
            # task_type is not provided
        )
        
        entries = history.get_all()
        assert len(entries) == 1
        assert entries[0].task_type is None


def test_special_characters_in_prompts():
    """Test history handling with special characters in prompts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)
        
        special_prompt = "Special chars: \n\t\"'\\ and emojis: 🚀🔥"
        special_refined = "Refined with\nnewlines\tand\ttabs"
        
        history.save_entry(special_prompt, special_refined, "generation")
        
        entries = history.get_all()
        assert len(entries) == 1
        assert entries[0].original_prompt == special_prompt
        assert entries[0].refined_prompt == special_refined


def test_empty_history():
    """Test behavior with completely empty history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)
        
        # All operations on empty history should work without errors
        assert history.get_all() == []
        assert history.get_recent(5) == []
        assert history.get_by_index(1) is None
        assert history.get_by_index(10) is None


def test_large_history():
    """Test behavior with a large number of entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        history = PromptHistory(history_dir=history_dir)

        # Add many entries
        num_entries = 100
        for i in range(num_entries):
            history.save_entry(f"Prompt {i}", f"Refined {i}", "generation")

        # Get all entries - should be in reverse order
        all_entries = history.get_all()
        assert len(all_entries) == num_entries
        assert all_entries[0].original_prompt == f"Prompt {num_entries-1}"
        assert all_entries[-1].original_prompt == "Prompt 0"

        # Get recent with reasonable limit
        recent_entries = history.get_recent(10)
        assert len(recent_entries) == 10
        assert recent_entries[0].original_prompt == f"Prompt {num_entries-1}"


def test_prompt_history_escaping():
    """Test that prompts with special characters are properly escaped in prompt history file."""
    from unittest.mock import Mock

    with tempfile.TemporaryDirectory() as tmpdir:
        history_dir = Path(tmpdir)
        config = Mock()
        config.history_enabled = True
        history = PromptHistory(history_dir=history_dir, config=config)

        # Test prompts with various special characters
        test_cases = [
            ("Simple prompt", "Simple prompt"),
            ("Multi-line\nprompt", "Multi-line\\nprompt"),
            ("Prompt with\\backslash", "Prompt with\\\\backslash"),
            ("Mixed\\nand\nreal", "Mixed\\\\nand\\nreal"),
            ("Control chars\r\nhere", "Control chars\\r\\nhere"),
            ("Tab\tand newline\n", "Tab\tand newline\\n"),
        ]

        for original_prompt, expected_escaped in test_cases:
            history.save_entry(original_prompt, f"Refined: {original_prompt}", "test")

        # Verify the prompt history file contains properly escaped content
        with open(history.prompt_history_file, 'r') as f:
            lines = [line.rstrip('\n') for line in f.readlines()]

        assert len(lines) == len(test_cases)
        for i, (original, expected) in enumerate(test_cases):
            assert lines[i] == expected, f"Line {i+1}: expected {expected!r}, got {lines[i]!r}"