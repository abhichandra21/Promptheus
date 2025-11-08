# Promptheus Developer Guide

This file provides guidance for AI assistants (including Claude Code) when working with code in this repository.

## Development Commands

### Installation and Setup
```bash
# Install in development mode
pip install -e .

# Or use the traditional setup.py approach
python setup.py develop
```

### Running the Application
```bash
# Run the CLI tool
promptheus "Your prompt here"

# Run via Python module
python -m promptheus.main "Your prompt here"

# Interactive mode (REPL-style)
promptheus

# Quick mode (skip questions)
promptheus -q "Your prompt"

# Refine mode (force questions)
promptheus -r "Your prompt"
```

### Testing
```bash
# Run automated tests
pytest -q

# Manual smoke tests
promptheus --static "Test prompt"
python -m promptheus.main --static "Smoke test"

# Test different input methods
promptheus -f test_prompt.txt
promptheus @test_prompt.txt
cat test_prompt.txt | promptheus

# Environment validation
python env_validator.py --provider gemini
python env_validator.py --test-connection
```

### Development Utilities
```bash
# Code formatting
black .

# Check for linting issues (if available)
python -m flake8 src/promptheus/ --ignore=E501,W503

# Type checking (if available)
python -m mypy src/promptheus/
```

## Architecture Overview

### Core Components

**Main Application (`src/promptheus/main.py`)**
- Entry point and CLI interface using argparse
- Implements adaptive interaction model that detects task types (analysis vs generation)
- Handles interactive loop mode (REPL) for continuous prompt processing
- Manages the question-answer-refinement workflow
- Contains the core `process_single_prompt()` orchestrator function
- Supports history commands: `promptheus history`, `:history`, `:load <n>`, `:clear-history`

**Provider Abstraction (`src/promptheus/providers.py`)**
- Abstract `LLMProvider` base class defining the interface for AI providers
- Multiple provider implementations: `GeminiProvider`, `AnthropicProvider`, `OpenAIProvider`, `GroqProvider`, `QwenProvider`, `GLMProvider`
- Provider factory pattern via `get_provider()` function
- Handles model fallbacks, retries, and error sanitization
- Each provider implements `_generate_text()` for raw API calls
- JSON mode support where available (OpenAI, Groq, Qwen, Gemini)
- Consistent `generate_questions()` method across all providers

**Configuration System (`src/promptheus/config.py`)**
- Auto-detects available providers based on API keys in environment
- Secure `.env` file loading with upward search from current directory
- Provider-specific configuration and model selection
- Handles validation and setup of API credentials
- Supports environment variable overrides for provider and model selection

**Supporting Modules**
- `src/promptheus/prompts.py`: System instruction templates for different operations
- `src/promptheus/constants.py`: Shared configuration values (timeouts, token limits)
- `src/promptheus/utils.py`: Common utilities including error sanitization
- `src/promptheus/logging_config.py`: Structured logging configuration
- `src/promptheus/history.py`: Session history management with file persistence
- `src/promptheus/models.json`: Provider configurations and model definitions
- `src/promptheus/core.py`: Core AI response function for demo/testing purposes

**Environment Validator (`env_validator.py`)**
- Standalone utility for testing provider configurations
- Validates API keys and tests provider connections
- Generates environment file templates for each provider
- Supports connection testing with actual API calls

**Model Information Helper (`get-models.py`)**
- Helper script to list all available providers and their supported models
- Used for tab completion and provider discovery

### Key Architectural Patterns

**Adaptive Interaction Model**
The system intelligently detects task types:
- **Analysis tasks** (research, exploration): Skip questions by default
- **Generation tasks** (writing, creating): Offer clarifying questions
- Uses AI to classify prompts and adapt behavior accordingly

**Question-Answer-Refinement Workflow**
1. AI analyzes prompt and determines if questions are needed
2. Generates contextual clarifying questions (or uses static fallback questions)
3. User answers questions via questionary-based CLI interface
4. AI combines original prompt + answers to generate refined prompt
5. Interactive tweaking allows iterative refinement

**Provider Abstraction**
- All providers implement the same `LLMProvider` interface
- Supports 6 AI backends (Gemini, Claude, OpenAI, Groq, Qwen, GLM)
- Automatic fallback between models within each provider
- Consistent error handling and response formatting
- Provider-specific capabilities (JSON mode, custom endpoints, etc.)

**Configuration Hierarchy**
1. Explicit CLI arguments (`--provider`, `--model`)
2. Environment variables (`PROMPTHEUS_PROVIDER`, `PROMPTHEUS_MODEL`)
3. Auto-detection based on available API keys
4. Default fallbacks per provider

### Important Implementation Details

**Environment Variable Loading**
The config system searches upward from current directory for `.env` files, stopping at project root markers (.git, pyproject.toml, setup.py). This allows for flexible configuration placement while preventing directory traversal beyond project boundaries.

**Error Sanitization**
All provider errors are sanitized through `sanitize_error_message()` to prevent leaking API keys or sensitive information in console output.

**Question Mapping**
When AI generates questions, the system maintains a mapping from generic keys (q0, q1, etc.) back to original question text. This ensures the refinement step has full context of what each answer refers to.

**Interactive Mode**
The REPL-style interactive mode persists provider, model, and flag settings across multiple prompts in a session, providing a seamless workflow for batch processing.

**History Management**
Prompt history is automatically saved for each refinement and can be accessed via:
- CLI: `promptheus history`, `promptheus history --limit 50`, `promptheus history --clear`
- Interactive: `:history`, `:load <n>`, `:clear-history`

## Development Notes

- The codebase uses structured logging via the `logging` module
- All API calls have configurable timeouts and token limits
- The application supports both single-shot and interactive modes
- Error handling is designed to be user-friendly while logging technical details
- The Rich library provides terminal formatting for a polished CLI experience
- Provider libraries are imported lazily to allow optional dependencies
- History is persisted to platform-specific directories (`~/.promptheus` or `%APPDATA%/promptheus`)

## Common Development Patterns

### Adding New Providers
1. Implement `LLMProvider` interface in `providers.py`
2. Add provider configuration to `models.json`
3. Update `config.py` with API key instructions
4. Add provider to factory function in `get_provider()`
5. Update `__all__` exports

### Error Handling Pattern
```python
try:
    # API call
    response = client.generate_content(prompt)
except Exception as exc:
    sanitized = sanitize_error_message(str(exc))
    logger.warning("Provider call failed: %s", sanitized)
    raise RuntimeError(f"Provider API call failed: {sanitized}") from exc
```

### Question Generation Pattern
All providers must implement `generate_questions()` that returns:
```python
{
    "task_type": "analysis|generation",
    "questions": [
        {
            "question": "Question text",
            "type": "text|radio|checkbox",
            "options": ["option1", "option2"],  # for radio/checkbox
            "required": True|False,
            "default": "default_value"
        }
    ]
}
```

### Python 3.14 Compatibility Notes
Some provider libraries may not yet support Python 3.14. For providers experiencing compatibility issues:
1. The `gemini` provider now supports Python 3.14 via the unified `google-genai` SDK
2. For other providers, consider using Python 3.13 or earlier until compatibility is ensured
3. Use virtual environments to isolate different Python versions as needed
