#!/usr/bin/env python3
"""Test script for the session history feature."""

import sys
import tempfile
from pathlib import Path

# Add the module to path
sys.path.insert(0, str(Path(__file__).parent))

from promptheus.history import PromptHistory

def test_history():
    """Test the history functionality."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        history = PromptHistory(history_dir=Path(tmpdir))

        print("Testing history functionality...")
        print()

        # Test 1: Empty history
        print("Test 1: Check empty history")
        entries = history.get_all()
        assert len(entries) == 0, "History should be empty initially"
        print("✓ Empty history check passed")
        print()

        # Test 2: Save entries
        print("Test 2: Save history entries")
        history.save_entry(
            original_prompt="Write a blog post",
            refined_prompt="Write a comprehensive blog post about AI technology",
            task_type="generation"
        )

        history.save_entry(
            original_prompt="Analyze this data",
            refined_prompt="Perform a thorough analysis of the provided dataset",
            task_type="analysis"
        )

        history.save_entry(
            original_prompt="Create a function",
            refined_prompt="Create a Python function that calculates fibonacci numbers",
            task_type="generation"
        )

        print("✓ Saved 3 history entries")
        print()

        # Test 3: Retrieve all entries
        print("Test 3: Retrieve all entries")
        entries = history.get_all()
        assert len(entries) == 3, f"Expected 3 entries, got {len(entries)}"
        print(f"✓ Retrieved {len(entries)} entries (most recent first)")
        print()

        # Test 4: Check order (most recent first)
        print("Test 4: Verify order (most recent first)")
        assert entries[0].original_prompt == "Create a function", "First entry should be most recent"
        assert entries[2].original_prompt == "Write a blog post", "Last entry should be oldest"
        print("✓ Order is correct (most recent first)")
        print()

        # Test 5: Get recent with limit
        print("Test 5: Get recent entries with limit")
        recent = history.get_recent(limit=2)
        assert len(recent) == 2, f"Expected 2 entries, got {len(recent)}"
        assert recent[0].original_prompt == "Create a function"
        print(f"✓ Retrieved {len(recent)} most recent entries")
        print()

        # Test 6: Get by index
        print("Test 6: Get entry by index")
        entry = history.get_by_index(1)  # Most recent
        assert entry is not None, "Entry should exist"
        assert entry.original_prompt == "Create a function"

        entry = history.get_by_index(3)  # Oldest
        assert entry is not None, "Entry should exist"
        assert entry.original_prompt == "Write a blog post"

        entry = history.get_by_index(10)  # Out of range
        assert entry is None, "Entry should be None for out of range index"
        print("✓ Get by index works correctly")
        print()

        # Test 7: History persistence
        print("Test 7: Test history persistence")
        history2 = PromptHistory(history_dir=Path(tmpdir))
        entries2 = history2.get_all()
        assert len(entries2) == 3, "History should persist"
        print("✓ History persists across instances")
        print()

        # Test 8: Prompt history file
        print("Test 8: Check prompt history file for arrow navigation")
        prompt_file = history.get_prompt_history_file()
        assert prompt_file.exists(), "Prompt history file should exist"
        with open(prompt_file, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"
        print("✓ Prompt history file created for arrow key navigation")
        print()

        # Test 9: Clear history
        print("Test 9: Clear history")
        history.clear()
        entries = history.get_all()
        assert len(entries) == 0, "History should be empty after clear"
        assert not prompt_file.exists(), "Prompt history file should be deleted"
        print("✓ History cleared successfully")
        print()

        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

if __name__ == "__main__":
    test_history()
