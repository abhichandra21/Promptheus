"""Essential tests for utility functions."""

import pytest
from promptheus.utils import sanitize_error_message, collapse_whitespace


def test_sanitize_error_message_basic():
    """Test basic error message sanitization."""
    message = "API call failed"
    result = sanitize_error_message(message)
    assert result == "API call failed"


def test_sanitize_error_message_with_tokens():
    """Test sanitization of API keys and tokens."""
    message = "Request failed with API key: sk-1234567890abcdef and another key: AIza987654321"
    result = sanitize_error_message(message)
    assert "***" in result  # The actual implementation replaces the entire token with ***
    assert "1234567890abcdef" not in result
    assert "987654321" not in result


def test_sanitize_error_message_with_uuid():
    """Test sanitization of UUID-like tokens."""
    message = "Session token: 550e8400-e29b-41d4-a716-446655440000"
    result = sanitize_error_message(message)
    assert "***" in result
    assert "550e8400-e29b-41d4-a716-446655440000" not in result


def test_sanitize_error_message_long_message():
    """Test sanitization with very long message."""
    long_message = "Error: " + "a" * 200 + " sk-1234567890 " + "b" * 200
    result = sanitize_error_message(long_message)
    
    # Should be truncated to max length (160)
    assert len(result) <= 160
    assert "***" in result


def test_sanitize_error_message_empty():
    """Test sanitization with empty message."""
    result = sanitize_error_message("")
    assert result == ""


def test_sanitize_error_message_none():
    """Test sanitization with None message."""
    result = sanitize_error_message(None)
    assert result == ""


def test_sanitize_error_message_truncated():
    """Test that long messages are properly truncated."""
    # Create a message that is long but doesn't match token pattern
    long_message = "This is a long message " + "with normal words " * 20
    result = sanitize_error_message(long_message, max_length=50)
    
    # Should be truncated to max_length - if adding ... would exceed max_length,
    # it just truncates to max_length
    assert len(result) <= 50  # Either exactly 50 or 53 if ... fits
    # Check if it was actually truncated (doesn't end with original ending)
    assert len(result) < len(long_message)  # Definitely truncated


def test_collapse_whitespace_basic():
    """Test basic whitespace collapsing functionality (right strip only)."""
    lines = ["hello  ", "  world  ", " test"]
    result = collapse_whitespace(lines)
    assert result == "hello\n  world\n test"  # Only right side is stripped


def test_collapse_whitespace_mixed_whitespace():
    """Test collapsing with mixed whitespace (right strip only)."""
    lines = ["  hello\t ", "  \tworld\n", "\ttest  \t"]
    result = collapse_whitespace(lines)
    # Only trailing whitespace is stripped, leading whitespace remains
    assert result == "  hello\n  \tworld\n\ttest"


def test_collapse_whitespace_empty_lines():
    """Test handling of empty lines."""
    lines = ["hello", "", "world", " ", "test"]
    result = collapse_whitespace(lines)
    
    # Empty lines should remain, but lines with just spaces become empty
    expected_lines = result.split("\n")
    assert expected_lines[0] == "hello"
    assert expected_lines[1] == ""  # Empty line remains
    assert expected_lines[2] == "world"
    assert expected_lines[3] == ""  # Space-only line becomes empty
    assert expected_lines[4] == "test"


def test_collapse_whitespace_single_line():
    """Test collapsing with a single line (right strip only)."""
    lines = ["  hello world  "]
    result = collapse_whitespace(lines)
    assert result == "  hello world"  # Only right side is stripped


def test_collapse_whitespace_special_characters():
    """Test collapsing with special characters."""
    lines = ["hello\nworld", "test\twith\ttabs"]
    result = collapse_whitespace(lines)
    assert result == "hello\nworld\ntest\twith\ttabs"


def test_sanitize_error_message_multiple_tokens():
    """Test sanitization with multiple tokens in one message."""
    message = "Keys: sk-1234567890 and AIza0987654321 and secret-abcdef123456"
    result = sanitize_error_message(message)
    assert result.count("***") >= 3  # Should sanitize all three tokens


def test_sanitize_error_message_edge_case_short_token():
    """Test sanitization doesn't affect short strings."""
    message = "Short: abcd"
    result = sanitize_error_message(message)
    assert result == "Short: abcd"  # Should not be sanitized


def test_sanitize_error_message_edge_case_long_token():
    """Test sanitization with very long token."""
    long_token = "x" * 100
    message = f"API key: {long_token}"
    result = sanitize_error_message(message)
    assert "***" in result
    assert long_token not in result


def test_collapse_whitespace_unicode():
    """Test collapsing with Unicode characters (right strip only)."""
    lines = ["héllo  ", "  wørld  ", " tëst"]
    result = collapse_whitespace(lines)
    assert result == "héllo\n  wørld\n tëst"  # Only right side is stripped


def test_collapse_whitespace_with_newlines():
    """Test that existing newlines in content are preserved properly."""
    lines = ["line1\nsubline", "line2", "line3"]
    result = collapse_whitespace(lines)
    # The function joins lines with \n, so the embedded \n becomes part of the content
    assert "\nsubline" in result
    assert "line2" in result