# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
# Test with static mode
promptheus --static "Test prompt"

# Test different input methods
promptheus -f test_prompt.txt
cat test_prompt.txt | promptheus
```

### Development Utilities
```bash
# Check for linting issues (if available)
python -m flake8 src/promptheus/ --ignore=E501,W503

# Type checking (if available)
python -m mypy src/promptheus/

# Run specific test modules
python test_modes.py
python test_file_input.py
```

## Architecture Overview

### Core Components

**Main Application (`src/promptheus/main.py`)**
- Entry point and CLI interface using argparse
- Implements adaptive interaction model that detects task types (analysis vs generation)
- Handles interactive loop mode (REPL) for continuous prompt processing
- Manages the question-answer-refinement workflow
- Contains the core `process_single_prompt()` orchestrator function

**Provider Abstraction (`src/promptheus/providers.py`)**
- Abstract `LLMProvider` base class defining the interface for AI providers
- `GeminiProvider` and `AnthropicProvider` implementations
- Provider factory pattern via `get_provider()` function
- Handles model fallbacks, retries, and error sanitization
- Each provider implements `_generate_text()` for raw API calls

**Configuration System (`src/promptheus/config.py`)**
- Auto-detects available providers based on API keys in environment
- Secure `.env` file loading with upward search from current directory
- Provider-specific configuration and model selection
- Handles validation and setup of API credentials

**Supporting Modules**
- `src/promptheus/prompts.py`: System instruction templates for different operations
- `src/promptheus/constants.py`: Shared configuration values (timeouts, token limits)
- `src/promptheus/utils.py`: Common utilities including error sanitization
- `src/promptheus/logging_config.py`: Structured logging configuration

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
- Supports multiple AI backends (Gemini, Claude, Z.ai)
- Automatic fallback between models within each provider
- Consistent error handling and response formatting

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

## Development Notes

- The codebase uses structured logging via the `logging` module
- All API calls have configurable timeouts and token limits
- The application supports both single-shot and interactive modes
- Error handling is designed to be user-friendly while logging technical details
- The Rich library provides terminal formatting for a polished CLI experience
