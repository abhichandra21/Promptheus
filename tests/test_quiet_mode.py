"""Tests for output format functionality."""

import pytest
from promptheus.cli import parse_arguments


def test_output_format_flag_parsing():
    """Test that -o/--output-format flag is parsed correctly."""
    # Test plain (default)
    args = parse_arguments(["test prompt"])
    assert args.output_format == "plain"

    # Test plain explicitly
    args = parse_arguments(["-o", "plain", "test prompt"])
    assert args.output_format == "plain"

    # Test json
    args = parse_arguments(["--output-format", "json", "test prompt"])
    assert args.output_format == "json"


def test_output_format_default_value():
    """Test that output format has correct default."""
    args = parse_arguments(["test prompt"])
    assert args.output_format == "plain"
