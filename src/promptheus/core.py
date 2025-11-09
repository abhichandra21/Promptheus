"""
Core AI response wrapper.
This file contains the core logic for getting AI responses.
"""

import time


def get_ai_response(prompt: str) -> str:
    """
    This is a BLOCKING function that takes a user prompt,
    calls an AI API, and returns the string response.
    Simulating a network call.

    Args:
        prompt: The user's input prompt

    Returns:
        The AI's response as a string with markdown formatting
    """
    # Simulate network delay
    time.sleep(1.5)

    # Return a formatted response with markdown
    response = f"This is the **AI's response** to your prompt about: '{prompt}'.\n\n"
    response += "Here are some bullet points:\n* Point 1\n* Point 2\n* Point 3"

    return response
