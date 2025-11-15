# Promptheus Development Guide

This document outlines development environment setup, testing procedures, code standards, and architectural patterns for Promptheus contributors.

## Development Environment Setup

### Installation from Source

```bash
# Clone repository
git clone https://github.com/abhichandra21/Promptheus.git
cd Promptheus

# Install in editable mode with development dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Add provider API keys to .env file
```

### Verification

```bash
# Verify installation
promptheus --version
python -m promptheus.main --version
```

## Testing Procedures

### Manual Testing

**Standard CLI Execution:**
```bash
promptheus "Draft a release note"
```

**Module Entry Point:**
```bash
python -m promptheus.main --skip-questions "Smoke test"
```

**Provider Validation:**
```bash
promptheus validate --providers gemini
promptheus validate --test-connection
```

### Automated Testing

**Execute Test Suite:**
```bash
pytest -q
```

**Test Development Guidelines:**
- Add new tests to `tests/` directory following `test_<module>.py` naming convention
- Implement lightweight unit tests with mocked providers
- Ensure tests execute without network dependencies
- Maintain test coverage for critical paths

## Code Standards

### Python Conventions

**Language Features:**
- Python 3.10+ syntax and features
- Type hints for function signatures
- 4-space indentation
- snake_case naming convention for functions and variables
- PascalCase for class names

**Module Organization:**
- Maximum module length: 300 lines
- Extract utility functions to `src/promptheus/` modules
- Maintain clear separation of concerns

**Code Formatting:**
```bash
# Format code before committing
black .

# Verify import organization
# Imports should be grouped: standard library, third-party, local
```

### Python Version Compatibility

**Python 3.14 Support:**
- Gemini provider: Full support via `google-genai` SDK
- Other providers: Compatibility varies by SDK version

**Development Recommendations:**
- Test with target Python version before committing
- Use virtual environments for version-specific testing
- Document provider-specific compatibility constraints

## Architectural Overview

### Module Structure

**Command-Line Interface Layer:**
- `src/promptheus/cli.py`: Argument parsing and subcommand dispatch

**Core Processing Logic:**
- `src/promptheus/main.py`: Primary prompt processing orchestration

**Interactive Mode (REPL):**
- `src/promptheus/repl/session.py`: Main REPL loop and session state management
- `src/promptheus/repl/commands.py`: Slash command implementation (`/set`, `/toggle`, etc.)
- `src/promptheus/repl/completer.py`: Tab completion for slash commands
- `src/promptheus/repl/history_view.py`: History display functionality

**Provider Integration:**
- `src/promptheus/providers.py`: LLM provider implementations and abstractions
- `src/promptheus/providers.json`: Provider configurations and model definitions

**Configuration and Utilities:**
- `src/promptheus/config.py`: Environment configuration and provider detection
- `src/promptheus/utils.py`: Shared utility functions
- `src/promptheus/history.py`: Session history persistence
- `src/promptheus/logging_config.py`: Logging configuration

## Contribution Guidelines

### Code Changes

**Scope:**
1. Maintain focused changes (single feature, refactor, or documentation update per pull request)
2. Avoid mixing unrelated changes in a single commit

**Commit Messages:**
- Use imperative mood: "Add static mode docs" not "Added static mode docs"
- Keep first line under 72 characters
- Provide detailed explanation in commit body if necessary

**Pull Request Requirements:**
1. Include behavior description
2. Document testing performed
3. Update relevant documentation
4. Add tests for new functionality

### Security Considerations

**API Key Handling:**
- Never log raw API keys
- Use masked output for display (as implemented in validator)
- Sanitize error messages containing credentials

### Adding New Providers

**OpenAI-Compatible Providers:**
If the provider exposes an OpenAI-compatible endpoint, extend the `OpenAICompatibleProvider` base class in `src/promptheus/providers.py` (reference implementations: OpenAI, Groq, Qwen, GLM).

**Provider-Specific Implementations:**
For providers requiring custom integration (e.g., Gemini, Anthropic):
1. Implement provider-specific adapter in `providers.py`
2. Add configuration to `providers.json`
3. Update environment detection in `config.py`
4. Update validation utilities
5. Document provider setup in README.md

## Communication Channels

**Issue Reporting:**
- Open issues at https://github.com/abhichandra21/Promptheus/issues
- Include reproduction steps
- Provide environment details (Python version, provider, OS)

**Pull Request Feedback:**
- Submit draft PRs for early feedback on significant changes
- Request review before marking PR as ready
- Respond to review comments promptly
