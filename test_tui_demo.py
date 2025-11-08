#!/usr/bin/env python3
"""
Demo script to test the Promptheus TUI without requiring API keys.

This script demonstrates the TUI functionality using a mock AI handler
that simulates network delays and responses.
"""

import time
from promptheus.tui import PromptheusApp


def mock_ai_handler(prompt: str) -> str:
    """
    Mock AI handler that simulates network I/O.

    This is a BLOCKING function that simulates a 2-second API call
    and returns a canned response.
    """
    # Simulate network delay
    time.sleep(2)

    # Return a mock response
    return f"This is a simulated AI response to: '{prompt}'\n\nIn a real scenario, this would be replaced by actual AI-generated content from providers like Gemini, Claude, GPT, etc."


def main():
    """Launch the TUI with a mock AI handler."""
    print("Launching Promptheus TUI Demo...")
    print("This demo uses a mock AI handler (no API keys required)")
    print("Press Ctrl+C to quit, Ctrl+S to toggle dark mode")
    print()

    # Create and run the TUI app
    app = PromptheusApp(ai_handler=mock_ai_handler)
    app.run()


if __name__ == "__main__":
    main()
