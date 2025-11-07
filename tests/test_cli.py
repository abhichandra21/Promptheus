"""Essential tests for CLI functionality."""

import pytest
from promptheus.cli import build_parser, parse_arguments


def test_build_parser_basic():
    """Test that the argument parser builds correctly."""
    parser = build_parser(include_history=False)
    
    # Should have the basic arguments
    assert parser is not None


def test_parse_args_history_command():
    """Test parsing with history subcommand."""
    parser = build_parser(include_history=True)
    args = parser.parse_args(["history"])
    assert args.command == "history"
    assert not args.clear
    assert args.limit == 20


def test_parse_args_prompt_value_not_treated_as_command():
    """Ensure free-form prompt strings are accepted when no subcommand is used."""
    args = parse_arguments(["Write a blog post"])

    assert args.prompt == "Write a blog post"
    assert args.command is None


def test_parse_args_prompt_allows_options_after_text():
    """Prompt tokens followed by flags should still parse correctly."""
    args = parse_arguments(["Write a blog post", "--copy"])

    assert args.prompt == "Write a blog post"
    assert args.copy is True


def test_parse_args_history_clear():
    """Test parsing with history clear."""
    parser = build_parser(include_history=True)
    args = parser.parse_args(["history", "--clear"])
    assert args.command == "history"
    assert args.clear


def test_parse_args_history_limit():
    """Test parsing with history limit."""
    parser = build_parser(include_history=True)
    args = parser.parse_args(["history", "--limit", "50"])
    assert args.command == "history"
    assert args.limit == 50


def test_parse_args_file_flag():
    """Test parsing with file flag."""
    parser = build_parser(include_history=False)
    args = parser.parse_args(["--file", "test.txt"])
    assert args.file == "test.txt"


def test_parse_args_with_provider():
    """Test parsing with provider flag."""
    parser = build_parser(include_history=False)
    args = parser.parse_args(["--provider", "gemini"])
    assert args.provider == "gemini"


def test_parse_args_with_model():
    """Test parsing with model flag."""
    parser = build_parser(include_history=False)
    args = parser.parse_args(["--model", "gpt-4"])
    assert args.model == "gpt-4"


def test_parse_args_with_flags():
    """Test parsing with various boolean flags."""
    parser = build_parser(include_history=False)
    args = parser.parse_args(["--quick", "--copy", "--edit"])
    assert args.quick
    assert args.copy
    assert args.edit


def test_parse_args_static_flag():
    """Test parsing with static flag variants."""
    parser = build_parser(include_history=False)
    args = parser.parse_args(["--static"])
    assert args.static
    
    # Test the alias
    args = parser.parse_args(["--mvp"])
    assert args.static  # --mvp should be aliased to --static


def test_parse_args_refine_flag():
    """Test parsing with refine flag."""
    parser = build_parser(include_history=False)
    args = parser.parse_args(["--refine"])
    assert args.refine


def test_parse_args_verbose_flag():
    """Test parsing with verbose flag."""
    parser = build_parser(include_history=False)
    args = parser.parse_args(["-v"])
    assert args.verbose


def test_parse_args_file_and_provider():
    """Test that file and provider arguments work together correctly."""
    parser = build_parser(include_history=False)
    args = parser.parse_args(["--file", "test.txt", "--provider", "openai"])
    assert args.file == "test.txt"
    assert args.provider == "openai"


def test_parse_args_multiple_flags():
    """Test parsing with multiple flags."""
    parser = build_parser(include_history=False)
    args = parser.parse_args([
        "--provider", "anthropic",
        "--model", "claude-3",
        "--quick",
        "--copy"
    ])
    assert args.provider == "anthropic"
    assert args.model == "claude-3"
    assert args.quick
    assert args.copy


def test_build_parser_help():
    """Test that help can be generated without errors."""
    parser = build_parser(include_history=True)
    
    # This should not raise an exception
    help_text = parser.format_help()
    assert "Promptheus" in help_text
    assert "AI-powered prompt engineering CLI tool" in help_text
