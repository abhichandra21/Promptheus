"""Tests for quiet mode functionality."""

import pytest
from promptheus.cli import parse_arguments


def test_quiet_output_flag_parsing():
    """Test that --quiet-output flag is parsed correctly."""
    args = parse_arguments(["--quiet-output", "test prompt"])
    assert args.quiet_output is True
    assert args.prompt == "test prompt"


def test_output_format_flag_parsing():
    """Test that -o/--output-format flag is parsed correctly."""
    # Test markdown (default)
    args = parse_arguments(["test prompt"])
    assert args.output_format == "markdown"

    # Test plain
    args = parse_arguments(["-o", "plain", "test prompt"])
    assert args.output_format == "plain"

    # Test json
    args = parse_arguments(["--output-format", "json", "test prompt"])
    assert args.output_format == "json"

    # Test yaml
    args = parse_arguments(["--output-format", "yaml", "test prompt"])
    assert args.output_format == "yaml"


def test_quiet_with_output_format():
    """Test that --quiet-output works with different output formats."""
    args = parse_arguments(["--quiet-output", "-o", "json", "test prompt"])
    assert args.quiet_output is True
    assert args.output_format == "json"


def test_quiet_mode_default_values():
    """Test that quiet mode flags have correct defaults."""
    args = parse_arguments(["test prompt"])
    assert not hasattr(args, "quiet_output") or args.quiet_output is False
