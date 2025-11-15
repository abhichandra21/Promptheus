# Promptheus

## Overview

Promptheus is a command-line interface tool for AI-powered prompt engineering. It transforms preliminary prompt concepts into structured, refined inputs suitable for large language model interactions. The tool implements an adaptive workflow that determines task requirements and applies appropriate refinement strategies.

**Core Functionality:**
- Automated prompt analysis and enhancement
- Multi-provider LLM integration with unified interface
- Interactive refinement workflow with contextual questioning
- Session history management and retrieval
- Support for batch processing and pipeline integration

**Primary Use Cases:**
- **Users**: Rapid prompt development for AI-driven tasks without manual optimization overhead
- **Developers**: Programmatic prompt engineering for applications requiring consistent LLM output quality

## Installation

### User Installation

**Standard Installation (PyPI):**
```bash
pip install promptheus
```

**Verification:**
```bash
promptheus --version
```

### Developer Installation

**From Source:**
```bash
git clone https://github.com/abhichandra21/Promptheus.git
cd Promptheus
pip install -e ".[dev]"
```

**Development Dependencies:**
The development installation includes testing frameworks and code quality tools. Execute the test suite to verify installation:
```bash
pytest -q
```

## Configuration

### API Key Setup

Create a `.env` file in your project directory. At minimum, one provider API key is required:

```bash
# Google Gemini
GEMINI_API_KEY=your_gemini_key_here

# Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_key_here

# OpenAI
OPENAI_API_KEY=your_openai_key_here

# Groq
GROQ_API_KEY=your_groq_key_here

# Alibaba Cloud Qwen
DASHSCOPE_API_KEY=your_qwen_key_here

# Zhipu AI GLM
ZAI_API_KEY=your_glm_key_here
```

The system auto-detects available providers. Override detection using `--provider` flag or environment variables.

### Shell Completion (Optional)

**Developer Feature:** Enable command-line completion for improved workflow efficiency.

```bash
# Automatic installation
promptheus completion --install

# Manual installation - Bash
promptheus completion bash > ~/.bash_completion.d/promptheus.bash
source ~/.bash_completion.d/promptheus.bash

# Manual installation - Zsh
promptheus completion zsh > ~/.zsh/completions/_promptheus
source ~/.zshrc
```

**Completion Features:**
- Provider and model name completion
- Subcommand completion
- Flag and option completion
- Context-aware suggestions

## Usage

### Basic Command Patterns

**User-Focused Examples:**
```bash
# Interactive session (REPL mode)
promptheus

# Single prompt execution
promptheus "Write a technical blog post about microservices"

# Skip clarifying questions
promptheus -s "Explain how kubernetes works"

# Force interactive refinement
promptheus -r "Draft a product announcement"

# File input
promptheus -f my-prompt.txt
promptheus @my-prompt.txt

# Standard input
cat idea.txt | promptheus
```

**Developer-Focused Examples:**
```bash
# Specify provider explicitly
promptheus --provider gemini "Analyze this codebase structure"

# Specify model explicitly
promptheus --model gpt-4o "Generate API documentation"

# JSON output for programmatic processing
promptheus -o json "Create OpenAPI schema"

# Pipeline integration
echo "Generate test cases" | promptheus | tee output.txt
```

## Features and Capabilities

### Adaptive Task Detection

**User-Facing:** The system analyzes input prompts to determine task classification and applies appropriate interaction strategies.

**Technical Implementation:**
- **Analysis tasks** (research, code review, data exploration): Bypasses interactive questioning by default
- **Generation tasks** (content creation, code generation, design): Initiates contextual question workflow

Override automatic detection using `-s` (skip-questions) or `-r` (refine) flags.

### Multi-Provider LLM Support

**User-Facing:** Access six major LLM providers through a unified interface.

**Developer-Facing:** Provider abstraction layer ensures consistent behavior across heterogeneous LLM APIs.

**Supported Providers and Models:**
- **Google Gemini**: gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash
- **Anthropic Claude**: claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus
- **OpenAI**: gpt-4o, gpt-4-turbo, gpt-3.5-turbo
- **Groq**: llama-3.3-70b-versatile, llama-3.1-70b-versatile, mixtral-8x7b
- **Alibaba Cloud Qwen**: qwen-max, qwen-plus, qwen-turbo
- **Zhipu AI GLM**: glm-4-plus, glm-4-0520, glm-4-air

Provider selection via `--provider` flag or `PROMPTHEUS_PROVIDER` environment variable. Model selection via `--model` flag or `PROMPTHEUS_MODEL` environment variable.

### Interactive Refinement Workflow

**User-Facing:** The system generates contextual questions based on task analysis to elicit requirements and constraints.

**Developer-Facing:** Question generation utilizes LLM-based analysis of prompt structure and intent. Bypass this workflow using `--skip-questions` for automated processing.

**Post-Refinement Iteration:**
Natural language modification interface enables targeted adjustments to refined output. Users can request specific changes (e.g., "make it more formal", "remove technical jargon") and the system applies targeted modifications iteratively.

### Session History Persistence

**User-Facing:** Automatic storage of refined prompts for retrieval and reuse.

**Command-Line Interface:**
```bash
# View history
promptheus history
promptheus history --limit 50
promptheus history --clear

# Interactive mode commands
/history
/load 3
/clear-history
```

**Developer-Facing:** Privacy and security controls for history management.

**Context-Aware Storage:**
- **Interactive terminal sessions**: History enabled by default
- **Non-interactive usage** (pipelines, scripts, automation): History disabled by default
- **Batch processing**: History disabled to prevent unintended logging

**Programmatic Control:**
```bash
# Enable history explicitly
PROMPTHEUS_ENABLE_HISTORY=1 promptheus "analyze this data"

# Disable history explicitly
PROMPTHEUS_ENABLE_HISTORY=0 promptheus "secret project plan"

# Supported values: 1/0, true/false, yes/no, on/off
```

**Technical Implementation:**
- Local storage: `~/.promptheus/` (Unix) or `%APPDATA%/promptheus` (Windows)
- No external data transmission
- JSONL format with O(1) append complexity
- Escaped special characters for safe storage
- Metadata includes timestamps, task types, original and refined versions

### Pipeline Integration and Output Control

**User-Facing:** Clipboard integration for rapid workflow.
```bash
# Copy refined prompt to clipboard
promptheus -c "Generate API documentation"
```

**Developer-Facing:** Automatic detection of pipeline context with appropriate behavior adjustments.

**Pipeline Behavior:**
```bash
# Automatic quiet mode when stdout is piped
promptheus "Explain Docker" | cat

# Output format control
promptheus -o plain "Write a haiku"        # Plain text (default)
promptheus -o json "Create a function"     # JSON with metadata

# Non-interactive stdin handling
echo "Write a story" | promptheus | cat
```

**Technical Details:**
- **TTY Detection**: Auto-quiet when stdout is not a TTY
- **Stream Separation**: UI messages to stderr, refined output to stdout
- **Non-interactive stdin**: Automatic question bypass when stdin is not a TTY
- **Error Handling**: Errors to stderr with appropriate exit codes
- **Clipboard**: Disabled in quiet mode

**Integration Examples:**
```bash
# Command substitution
claude "$(promptheus 'Create a haiku')"

# Standard utilities
promptheus "Explain Docker" | tee output.txt
echo "topic" | promptheus | cat > result.txt

# JSON processing
promptheus -o json "API schema" | jq '.endpoints'

# Batch processing
cat prompts.txt | while read line; do
  promptheus "$line" >> results.txt
done
```

### Interactive Mode (REPL)

**User-Facing:** Multi-prompt session management with persistent configuration.

Execute `promptheus` without arguments to enter interactive mode.

**Features:**
- **Slash commands**: `/history`, `/load <n>`, `/clear-history`, `/copy`, `/status`, `/set provider <name>`, `/toggle refine`
- **Keyboard shortcuts**: Shift+Enter or Option/Alt+Enter for multiline input
- **Session state**: Provider and model configuration persists across prompts within session
- **Clipboard operations**: `/copy` command for last refined result
- **Command completion**: Tab completion for all slash commands with context-aware suggestions

**Developer-Facing:** Prompt Toolkit-based TUI with custom key bindings, command completion, and session state management.

### Input Method Support

**Supported Input Patterns:**
- **Inline argument**: `promptheus "Your prompt here"`
- **File flag**: `promptheus -f path/to/prompt.txt`
- **@ syntax**: `promptheus @path/to/prompt.txt`
- **Standard input**: `cat prompt.txt | promptheus` or `echo "prompt" | promptheus`

All input methods support flag combinations.

## Command-Line Reference

### Primary Flags

| Flag | Description |
|------|-------------|
| `-s`, `--skip-questions` | Bypass interactive question workflow, apply direct prompt enhancement |
| `-r`, `--refine` | Force interactive refinement workflow regardless of task classification |
| `-o`, `--output-format` | Output format: `plain` (default) or `json` |
| `-c`, `--copy` | Copy refined prompt to system clipboard |

### Provider and Model Selection

| Flag | Description |
|------|-------------|
| `--provider <name>` | Specify LLM provider: gemini, anthropic, openai, groq, qwen, glm |
| `--model <model>` | Specify model identifier (overrides provider default) |

### Input Source Specification

| Method | Syntax | Description |
|--------|--------|-------------|
| Inline | `promptheus "text"` | Direct prompt as command argument |
| File flag | `-f <path>` | Read prompt from specified file path |
| @ syntax | `@<path>` | Shorthand for file input |
| Standard input | (pipe) | Read prompt from stdin |

### History Management

| Command | Description |
|---------|-------------|
| `promptheus history` | Display all stored prompts with metadata |
| `promptheus history --limit N` | Display last N prompts |
| `promptheus history --clear` | Purge all history entries |
| `/history` | View history (interactive mode only) |
| `/load <n>` | Load prompt at index n from history (interactive mode only) |
| `/clear-history` | Clear history (interactive mode only) |

### Interactive Mode Commands

| Command | Description |
|---------|-------------|
| `/history` | Display session history |
| `/load <n>` | Load historical prompt by index |
| `/clear-history` | Purge all history |
| `/copy` | Copy last refined output to clipboard |
| `/about` | Display version and configuration information |
| `/bug` | Open bug report submission interface |
| `/help` | Display command reference |
| `/status` | Display current session configuration |
| `/set provider <name>` | Modify active LLM provider |
| `/set model <name>` | Modify active model |
| `/toggle refine` | Toggle refinement mode |
| `/toggle skip-questions` | Toggle question workflow bypass |

### Utility Subcommands

| Command | Description |
|---------|-------------|
| `promptheus --help` | Display usage information |
| `promptheus --version` | Display version information |
| `promptheus list-models` | Display available providers and models |
| `promptheus validate` | Validate API configuration and connectivity |
| `promptheus template` | Generate environment file template |
| `promptheus completion` | Generate shell completion script |
| `promptheus completion --install` | Install shell completion automatically |
| `promptheus completion bash` | Generate Bash completion script |
| `promptheus completion zsh` | Generate Zsh completion script |

## Advanced Configuration

### Environment Variables

**Provider and Model Control:**
```bash
# Provider selection (overrides auto-detection)
export PROMPTHEUS_PROVIDER=gemini
# Supported: gemini, anthropic, openai, groq, qwen, glm

# Model selection (overrides provider default)
export PROMPTHEUS_MODEL=gemini-2.0-flash-exp
# Examples: claude-3-5-sonnet-20241022, gpt-4o, llama-3.1-405b
```

**History Management:**
```bash
# Enable/disable history persistence
export PROMPTHEUS_ENABLE_HISTORY=1      # Enable
export PROMPTHEUS_ENABLE_HISTORY=0      # Disable
# Supported values: 1/0, true/false, yes/no, on/off
# Default: Context-aware (interactive=enabled, non-interactive=disabled)
```

**Logging Configuration:**
```bash
# Debug mode (verbose output with stack traces)
export PROMPTHEUS_DEBUG=1

# Log level control
export PROMPTHEUS_LOG_LEVEL=INFO
# Supported: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Log format
export PROMPTHEUS_LOG_FORMAT=json
# Values: "json" or custom format string
# Default: "%(asctime)s %(levelname)s [%(name)s] %(message)s"

# Log file output
export PROMPTHEUS_LOG_FILE=app.log
# Accepts any valid file path
```

### Configuration Precedence

**Resolution Order (highest to lowest priority):**
1. Explicit CLI arguments (`--provider gemini`, `--model gpt-4o`)
2. Environment variables (`PROMPTHEUS_PROVIDER`, `PROMPTHEUS_MODEL`)
3. Auto-detection based on available API keys in `.env` file
4. Provider-specific default models

### Environment File Discovery

**Search Pattern:**
The system searches upward from the current working directory for `.env` files, terminating at:
- `.git` directory (repository root)
- `pyproject.toml` (Python project root)
- `setup.py` (Python project root)

This enables project-specific configuration isolation.

### Logging System Configuration

**Developer-Focused:** Comprehensive logging control for debugging and monitoring.

**Debug Mode:**
```bash
# Enable verbose output with stack traces
PROMPTHEUS_DEBUG=1 promptheus "test prompt"

# Granular log level control
PROMPTHEUS_LOG_LEVEL=DEBUG promptheus "analyze this"
```

**Structured Logging:**
```bash
# JSON format for log aggregation
PROMPTHEUS_LOG_FORMAT=json promptheus "generate code"

# Custom format string
PROMPTHEUS_LOG_FORMAT="%(levelname)s: %(message)s" promptheus "task"
```

**File Output:**
```bash
# Write logs to file
PROMPTHEUS_LOG_FILE=/var/log/promptheus.log promptheus "important task"
```

**Behavior Modes:**
- **Default**: Minimal console output
- **Debug**: Verbose output with complete stack traces
- **File logging**: All output to file, console remains clean
- **JSON format**: Structured output for log aggregation systems

**Production Use Cases:**
```bash
# CI/CD with structured logs
PROMPTHEUS_LOG_FORMAT=json PROMPTHEUS_LOG_FILE=ci.log promptheus --version

# Development debugging
PROMPTHEUS_DEBUG=1 PROMPTHEUS_LOG_FILE=debug.log promptheus

# Production monitoring
PROMPTHEUS_LOG_LEVEL=WARNING PROMPTHEUS_LOG_FILE=production.log promptheus
```

## Documentation Resources

**Detailed documentation available in `docs/` directory:**
- **[Architecture](docs/architecture.md)**: System architecture, data flow diagrams, and component interactions
- **[Usage Guide](docs/usage.md)**: Comprehensive workflow examples and integration patterns
- **[Development Guide](docs/development.md)**: Development setup, contribution guidelines, testing procedures
- **[Troubleshooting](docs/troubleshooting.md)**: Diagnostic procedures and common issue resolution

## Use Case Examples

### Content Generation
The system detects creative tasks and offers contextual questions to refine requirements. Example workflow:
1. User provides initial prompt: "Write a blog post"
2. System generates clarifying questions about audience, tone, length, and key topics
3. User provides answers through interactive prompts
4. System generates refined, detailed prompt incorporating all specifications
5. User can iteratively tweak the output using natural language instructions

### Code Analysis
For analysis tasks, the system bypasses unnecessary questions and applies direct enhancement:
1. User provides prompt: "Analyze the main.py file and explain key functions"
2. System detects analysis task type
3. Direct prompt enhancement applied without interactive questions
4. Refined prompt includes specific technical requirements and output format specifications

### Interactive Session
Multi-prompt workflow with persistent configuration:
1. Launch interactive mode with `promptheus`
2. Configure provider and model via `/set` commands
3. Process multiple prompts within single session
4. Access history with `/history` and reload previous prompts with `/load <n>`
5. Toggle modes with `/toggle refine` or `/toggle skip-questions` as needed

## System Requirements

**Runtime Dependencies:**
- Python 3.10 or higher
- At least one configured LLM provider API key

**Supported Providers:**
- Google Gemini
- Anthropic Claude
- OpenAI
- Groq
- Alibaba Cloud Qwen
- Zhipu AI GLM

## Development Environment Setup

**Clone and Install:**
```bash
git clone https://github.com/abhichandra21/Promptheus.git
cd Promptheus
pip install -e ".[dev]"
pytest -q
```

## Python Version Compatibility

**Python 3.14 Support:**
- **Gemini provider**: Full support via `google-genai` SDK
- **Other providers**: Compatibility varies by provider SDK

**Compatibility Notes:**
- For provider-specific issues on Python 3.14, use Python 3.10-3.13
- Manage multiple Python versions via virtual environments
- Provider SDKs are expected to add Python 3.14 support in upcoming releases

## Authentication Management

### Interactive Authentication Setup

**Command:** `promptheus auth`

The authentication system provides an interactive workflow for configuring provider API keys:

```bash
# Interactive provider selection
promptheus auth

# Direct provider specification
promptheus auth gemini
promptheus auth anthropic
promptheus auth openai

# Skip validation for testing
promptheus auth openai --skip-validation
```

**Features:**
- Interactive provider selection with priority ordering
- API key validation before saving (optional)
- Automatic `.env` file management
- Support for all configured providers
- Secure password input (keys not echoed to terminal)

**Workflow:**
1. Select provider from interactive menu or specify via command line
2. System displays provider-specific API key URL when available
3. User enters API key (masked input)
4. System validates key against provider API (unless `--skip-validation` specified)
5. Valid key saved to `.env` file with appropriate environment variable name

## Validation and Diagnostic Utilities

### Configuration Validation

**Test API connectivity and validate configuration:**

```bash
# Basic validation
promptheus validate

# Test live API connections
promptheus validate --test-connection

# Provider-specific validation
promptheus validate --providers gemini,anthropic
```

### Provider and Model Discovery

**List available providers and supported models:**

```bash
# List all available models
promptheus list-models

# Provider-filtered listing
promptheus list-models --providers openai

# Limited output
promptheus list-models --limit 10
```

## Contributing to Promptheus

**Contribution Guidelines:**

1. **Scope**: Maintain focused changes (single feature, refactor, or documentation update per pull request)
2. **Commit messages**: Use imperative mood, concise descriptions
3. **Pull requests**: Include behavior descriptions and test coverage details
4. **Security**: Never log API keys or sensitive credentials
5. **Code formatting**: Execute `black .` before committing
6. **Testing**: Add test files under `tests/` following `test_<module>.py` naming convention

**Detailed contribution procedures:** [docs/development.md](docs/development.md)

## Troubleshooting Common Issues

### Installation Verification

```bash
pip install -e .
which promptheus
python -m promptheus.main "Test prompt"
```

### Provider Configuration Issues

```bash
# Verify API key configuration
cat .env
env | grep -E '(GEMINI|ANTHROPIC|OPENAI|GROQ|DASHSCOPE|ZAI)'

# Test specific provider
promptheus --provider gemini "Test"

# Validate provider configuration
promptheus validate --providers gemini
```

### Clipboard Functionality

**Platform-specific requirements:**
- **Linux**: Install `xclip` or `xsel` via package manager (`sudo apt-get install xclip`)
- **macOS/Windows**: Native clipboard support, no additional installation required
- **WSL**: May require X server configuration for clipboard access

**Comprehensive troubleshooting:** [docs/troubleshooting.md](docs/troubleshooting.md)

## License Information

This project is released under the MIT License. Complete license terms are available in the LICENSE file.

## Contact and Support

**Repository:** https://github.com/abhichandra21/Promptheus

**Issue Tracking:** https://github.com/abhichandra21/Promptheus/issues

**Usage:**
- Bug reports: Submit via GitHub Issues
- Feature requests: Submit via GitHub Issues
- Security vulnerabilities: Report via GitHub Security Advisories

## Acknowledgments

**Core Dependencies:**
- [Rich](https://github.com/Textualize/rich): Terminal rendering and formatting
- [Questionary](https://github.com/tmbo/questionary): Interactive CLI prompts
- [PyPerclip](https://github.com/asweigart/pyperclip): Cross-platform clipboard operations
- [Prompt Toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit): Advanced terminal input handling
- [python-dotenv](https://github.com/theskumar/python-dotenv): Environment configuration management

**LLM Provider SDKs:**
- Google Gemini SDK
- Anthropic SDK
- OpenAI SDK
- Groq SDK
- Alibaba Cloud DashScope SDK
- Zhipu AI SDK
