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

# Skip questions mode (improve prompt directly)
promptheus -s "Your prompt"
promptheus --skip-questions "Your prompt"

# Refine mode (force questions)
promptheus -r "Your prompt"

# Different output formats
promptheus -o plain "Your prompt"   # Default: plain text
promptheus -o json "Your prompt"    # JSON output

# Pipe integration examples
promptheus "Write a story" | claude exec           # Chain with other AI tools
claude "$(promptheus 'Create a haiku')"            # Command substitution
promptheus "Explain Docker" | tee output.txt       # Save and display (auto-quiet)
echo "topic" | promptheus | cat > result.txt       # Chain transformations
promptheus -o json "schema" | jq '.prompt'         # JSON processing
```

### Testing
```bash
# Run automated tests
pytest -q

# Manual smoke tests
promptheus --skip-questions "Test prompt"
python -m promptheus.main --skip-questions "Smoke test"

# Test different input methods
promptheus -f test_prompt.txt
promptheus @test_prompt.txt
cat test_prompt.txt | promptheus

# Environment validation
promptheus validate --providers gemini
promptheus validate --test-connection
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
- Supports history commands: `promptheus history`, `/history`, `/load <n>`, `/clear-history`

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

**REPL/Interactive Interface (`src/promptheus/repl.py`)**
- Textual-based TUI for interactive mode with custom key bindings
- Command completer with Tab completion for all `/` commands
- Implements session management commands (`/set`, `/toggle`, `/status`)
- Handles transient messages for non-intrusive user feedback
- Bottom toolbar showing provider/model info and key bindings
- Special commands: `/about`, `/bug`, `/copy`, `/help`, `/history`, `/load`, `/clear-history`

**Supporting Modules**
- `src/promptheus/prompts.py`: System instruction templates for different operations
- `src/promptheus/constants.py`: Shared configuration values (VERSION, GITHUB_REPO, timeouts, token limits)
- `src/promptheus/utils.py`: Common utilities including error sanitization
- `src/promptheus/logging_config.py`: Structured logging configuration
- `src/promptheus/history.py`: Session history management with file persistence
- `src/promptheus/providers.json`: Provider configurations and model definitions
- `src/promptheus/core.py`: Core AI response function for demo/testing purposes
- `src/promptheus/exceptions.py`: Custom exception types (e.g., `PromptCancelled`)
- `src/promptheus/cli.py`: Argument parsing and CLI interface

**Environment Validation**
- Integrated validation through `promptheus validate` subcommand
- Validates API keys and tests provider connections
- Generates environment file templates with `promptheus template` subcommand
- Supports connection testing with actual API calls via `--test-connection`

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
2. Provider-scoped environment variables (`PROMPTHEUS_PROVIDER`, `OPENAI_MODEL`, etc.)
3. `PROMPTHEUS_MODEL` as the global fallback when the provider was auto-detected or injected via `PROMPTHEUS_PROVIDER`
4. Default fallbacks per provider (always used after manual provider switches unless you also specify `--model` or a provider-scoped env var)

### Important Implementation Details

**Environment Variable Loading**
The config system searches upward from current directory for `.env` files, stopping at project root markers (.git, pyproject.toml, setup.py). This allows for flexible configuration placement while preventing directory traversal beyond project boundaries.

**Error Sanitization**
All provider errors are sanitized through `sanitize_error_message()` to prevent leaking API keys or sensitive information in console output.

**Question Mapping**
When AI generates questions, the system maintains a mapping from generic keys (q0, q1, etc.) back to original question text. This ensures the refinement step has full context of what each answer refers to.

**Interactive Mode (Textual TUI)**
The REPL uses a Textual-based TUI with:
- Custom key bindings: Enter to submit, Shift+Enter for newlines, Ctrl+C for cancellation
- Tab completion for all slash commands with descriptions
- Transient messages that disappear after a short duration
- Session state persistence (provider, model, flags) across prompts
- Bottom toolbar showing current provider/model and available key bindings

**History Management**
Prompt history is automatically saved for each refinement and can be accessed via:
- CLI: `promptheus history`, `promptheus history --limit 50`, `promptheus history --clear`
- Interactive: `/history`, `/load <n>`, `/clear-history`

## Development Notes

- The codebase uses structured logging via the `logging` module
- All API calls have configurable timeouts and token limits
- The application supports both single-shot and interactive modes
- Error handling is designed to be user-friendly while logging technical details
- Rich library provides terminal formatting, Textual library provides TUI framework
- Provider libraries are imported lazily to allow optional dependencies
- History is persisted to platform-specific directories (`~/.promptheus` or `%APPDATA%/promptheus`)
- Interactive commands use `/` prefix (e.g., `/history`, `/load`, `/help`)
- Cancellation flow uses `PromptCancelled` exception with exit code 130
- Clipboard operations use `pyperclip` library

## Common Development Patterns

### Adding New Providers
1. Implement `LLMProvider` interface in `providers.py`
2. Add provider configuration to `providers.json`
3. Update `config.py` with API key instructions and detection logic
4. Add provider to factory function in `get_provider()`
5. Update `SUPPORTED_PROVIDER_IDS` in `config.py`
6. Update `__all__` exports

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

### Adding New Interactive Commands
1. Add command to `CommandCompleter.commands` dict in `repl.py`
2. Implement command handler in `interactive_mode()` function
3. Add completion logic in `CommandCompleter.get_completions()` if needed
4. Update `/help` command output in `show_help()` function
5. Test command with Tab completion and execution

### Python 3.14 Compatibility Notes
Some provider libraries may not yet support Python 3.14. For providers experiencing compatibility issues:
1. The `gemini` provider now supports Python 3.14 via the unified `google-genai` SDK
2. For other providers, consider using Python 3.13 or earlier until compatibility is ensured
3. Use virtual environments to isolate different Python versions as needed
4. Pytest warnings are configured in `pyproject.toml` to suppress known deprecation warnings

## MCP Server Architecture

### Overview
The MCP (Model Context Protocol) server exposes Promptheus functionality as standardized tools for integration with MCP-compatible clients.

### Core Components

**MCP Server Implementation (`src/promptheus/mcp_server.py`)**
- **FastMCP Framework**: Provides tool registration and protocol handling
- **Tool Registry**: Five exposed tools with consistent interfaces
- **AskUserQuestion Integration**: Dual-mode support (interactive/structured)
- **Error Sanitization**: Consistent error handling across all tools

**Exposed Tools:**
1. **refine_prompt**: Intelligent prompt refinement with Q&A workflow
2. **tweak_prompt**: Surgical prompt modifications
3. **list_models**: Provider model discovery
4. **list_providers**: Configuration status checking
5. **validate_environment**: Environment validation with connectivity testing

### Response Format Standards

**Success Responses:**
```python
# Refined prompt response
{"type": "refined", "prompt": "...", "next_action": "..."}

# Model/provider list response
{"type": "success", "providers": {...}, "models": {...}}
```

**Clarification Response:**
```python
{
  "type": "clarification_needed",
  "task_type": "analysis" | "generation",
  "questions_for_ask_user_question": [...],
  "answer_mapping": {"q0": "Question text", ...},
  "instructions": "..."
}
```

**Error Response:**
```python
{"type": "error", "error_type": "ConfigurationError", "message": "..."}
```

### AskUserQuestion Integration Modes

**Interactive Mode** (preferred):
- Client injects AskUserQuestion function via `set_ask_user_question()`
- Server automatically collects answers interactively
- Seamless user experience, no client intervention required

**Structured Mode** (fallback):
- Server returns clarification_needed response
- Client responsible for AskUserQuestion tool calls
- Answers mapped back via question IDs (q0, q1, q2, etc.)

### MCP Development Patterns

**Tool Implementation Pattern:**
```python
@mcp.tool()
def tool_name(param: str, optional: Optional[str] = None) -> Dict[str, Any]:
    # Validate inputs
    validation_error = _validate_input(param)
    if validation_error:
        return validation_error
    
    # Initialize provider
    provider, error = _initialize_provider(provider, model)
    if error:
        return error
    
    # Execute tool logic
    try:
        result = execute_tool_logic()
        return {"type": "success", "result": result}
    except Exception as e:
        return {
            "type": "error", 
            "error_type": type(e).__name__,
            "message": sanitize_error_message(str(e))
        }
```

**Question Mapping Pattern:**
```python
def _build_question_mapping(questions: List[Dict[str, Any]]) -> QuestionMapping:
    return {f"q{i}": q.get("question", f"Question {i}") for i, q in enumerate(questions)}
```

### MCP Server Entry Points

**CLI Integration:**
```python
# Subcommand dispatch in main.py
if getattr(args, "command", None) == "mcp":
    from promptheus.mcp_server import run_mcp_server
    run_mcp_server()
```

**Direct Execution:**
```python
# Module entry point
if __name__ == "__main__":
    run_mcp_server()
```

### MCP Testing Strategy

**Unit Testing:**
- Mock provider responses for tool testing
- Validate response format consistency
- Test error handling paths
- Verify question mapping logic

**Integration Testing:**
- Test with actual MCP clients
- Verify AskUserQuestion workflow
- Test provider fallback behavior
- Validate environment requirements

**Manual Testing Workflow:**
1. Start MCP server: `promptheus mcp`
2. Test basic refinement without questions
3. Test clarification workflow with questions
4. Test error conditions (missing keys, invalid providers)
5. Verify both interactive and structured modes

### MCP Error Handling

**Import Validation:**
```python
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None
    # Graceful fallback with informative error
```

**Provider Initialization Errors:**
- Configuration errors (missing API keys)
- Connection test failures
- Provider-specific error sanitization

**Tool Execution Errors:**
- Input validation errors
- Provider API errors
- Question generation failures
- Answer processing errors

### MCP Documentation Standards

**Tool Documentation:**
- Comprehensive docstrings with examples
- Parameter descriptions and types
- Response format specifications
- Usage workflow descriptions

**Integration Documentation:**
- JSON request/response examples
- AskUserQuestion workflow diagrams
- Error handling procedures
- Troubleshooting guides

### MCP Security Considerations

**API Key Protection:**
- Error message sanitization prevents key leakage
- Provider errors are masked before client exposure
- Configuration validation happens server-side

**Input Validation:**
- Prompt length limits (MAX_PROMPT_LENGTH = 50000)
- Answer mapping validation
- Provider/model parameter validation

### MCP Performance Optimization

**Caching Strategy:**
- Model information cached for 24 hours
- Provider validation results cached
- Question generation optimized for reuse

**Error Recovery:**
- Graceful fallback when AskUserQuestion unavailable
- Provider fallback within tool execution
- Retry logic for transient failures
- for 100% of the decisions/questions always ask frontend-developer skill