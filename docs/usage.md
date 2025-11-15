# Promptheus Usage Guide

This document provides comprehensive coverage of Promptheus command-line interface patterns, operational modes, and integration workflows.

## Operational Modes

### Interactive Session (REPL)

**Invocation:**
```bash
promptheus
```

**Characteristics:**
- Persistent session maintaining provider, model, and flag configuration across multiple prompt executions
- Command history with arrow-key navigation
- Built-in session management commands: `/history`, `/load <n>`, `/clear-history`
- Session termination via `exit`, `quit`, or `Ctrl+C`

**Use Cases:**
- Multi-prompt workflows requiring consistent configuration
- Exploratory prompt development with iterative refinement
- Rapid prototyping with immediate feedback

### Single Execution Mode

**Invocation Patterns:**
```bash
# Inline argument
promptheus "Write a haiku"

# File input (flag syntax)
promptheus -f idea.txt

# File input (shorthand syntax)
promptheus @idea.txt

# Standard input
cat idea.txt | promptheus
```

**Use Cases:**
- Automated processing pipelines
- Script integration
- Batch operations
- Single-purpose prompt execution

## Input Source Specification

**Available Methods:**

| Method | Syntax | Description |
|--------|--------|-------------|
| File flag | `-f <path>` | Explicit file path specification |
| @ shorthand | `@<path>` | Abbreviated file input syntax |
| Standard input | (pipe) | Stream-based input via stdin |

## Pipeline Integration and Stream Processing

Promptheus implements clean stdout/stderr stream separation for integration with Unix pipelines and command substitution workflows.

### Standard Pipeline Operations

**Basic Patterns:**
```bash
# Automatic quiet mode activation when stdout is piped
promptheus "Write a story" | cat
promptheus "Explain Docker" | less

# File redirection (interactive prompts on stderr)
promptheus "Write docs" > output.txt

# Integration with external AI toolchains
promptheus "Create a haiku" | claude exec
promptheus "Write code" | codex run
```

### Command Substitution Patterns

**Shell Integration:**
```bash
# Feed refined output to external tools
claude "$(promptheus 'Write a technical prompt')"
codex "$(promptheus 'Generate function spec')"

# Variable capture for scripting
REFINED=$(promptheus "Optimize this query")
echo "$REFINED" | mysql -u user -p
```

### Unix Utility Integration

**Standard Utility Patterns:**
```bash
# Simultaneous file save and display
promptheus "Long explanation" | tee output.txt

# Output filtering
promptheus "List best practices" | grep -i "security"

# Metrics extraction
promptheus "Write essay" | wc -w

# Stream transformation
promptheus "Generate list" | sed 's/^/- /' > checklist.md

# Multi-file composition
cat template.txt | promptheus | cat header.txt - footer.txt > final.txt
```

### JSON Output Processing

**Structured Data Manipulation:**
```bash
# Extract specific fields
promptheus -o json "Create API schema" | jq '.endpoints'
promptheus -o json "Config template" | jq -r '.settings.database'

# Format and persist
promptheus -o json "Data structure" | jq '.' > formatted.json
```

### Advanced Integration Patterns

**Complex Workflow Examples:**
```bash
# Batch processing
cat prompts.txt | while read line; do
  promptheus "$line" >> results.txt
done

# Conditional execution
if promptheus "Check status" | grep -q "success"; then
  echo "All systems operational"
fi

# Multi-stage processing pipeline
promptheus "Draft outline" | \
  promptheus "Expand this outline" | \
  tee expanded.txt

# Parallel execution (GNU parallel)
cat prompts.txt | parallel -j 4 "promptheus {} > output_{#}.txt"

# Stream-specific error handling
promptheus "Generate code" 2> errors.log > output.txt
```

### Output Format Specification

**Format Control:**
```bash
# Plain text output (default)
promptheus -o plain "Write haiku"

# Structured JSON output with metadata
promptheus -o json "Create schema"

# Explicit plain text specification
promptheus -o plain "Write story" > story.txt
```

## Authentication Management

### Interactive Authentication Setup

The `auth` subcommand provides an interactive workflow for configuring provider API keys:

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

**Authentication Workflow:**

1. **Provider Selection**: If no provider specified, displays interactive menu with priority ordering
2. **API Key URL**: System displays provider-specific API key acquisition URL when available
3. **Key Input**: User enters API key via secure password prompt (input masked)
4. **Validation**: System validates key against provider API (unless `--skip-validation` flag used)
5. **Storage**: Valid key saved to `.env` file with appropriate environment variable

**Features:**
- Automatic `.env` file creation and management
- API key format validation
- Live API connectivity testing
- Support for all configured providers
- Recommended providers highlighted in selection menu

## Subcommand Architecture

Promptheus implements a subcommand-based interface for utility operations:

### Environment Validation
```bash
# Basic validation
promptheus validate

# Test live API connectivity
promptheus validate --test-connection

# Provider-specific validation
promptheus validate --providers openai,gemini
```

### Model Discovery
```bash
# List all available models
promptheus list-models

# Provider-filtered listing
promptheus list-models --providers openai

# Limited output
promptheus list-models --limit 10
```

### Environment Template Generation
```bash
# Generate multi-provider template
promptheus template openai,gemini

# Alternative syntax
promptheus template --providers openai,anthropic
```

### History Management
```bash
# Display history
promptheus history

# Limited history display
promptheus history --limit 50

# Purge history
promptheus history --clear
```

### Shell Completion Installation
```bash
# Bash completion script generation
promptheus completion bash

# Zsh completion script generation
promptheus completion zsh

# Automatic installation
promptheus completion --install
```

### Stream Behavior Characteristics

**Automatic Adjustments:**
- **Auto-quiet**: Quiet mode activation when stdout is piped
- **stderr routing**: UI elements (questions, status messages) directed to stderr
- **stdout isolation**: Refined output exclusively on stdout
- **Non-interactive detection**: Question workflow bypass when stdin is piped

## Refinement Workflow Modes

| Mode | Flag | Behavior |
| --- | --- | --- |
| Adaptive (default) | None | Automatic task classification determines question workflow activation |
| Skip Questions | `-s` / `--skip-questions` | Bypass interactive questions, apply direct enhancement |
| Refine | `-r` / `--refine` | Force interactive question workflow regardless of task type |

**Flag Composition:**
Flags may be combined. Example: `promptheus -s -c @brief.md`

## Provider and Model Selection

### Auto-Detection
The system auto-detects available providers based on configured API keys in the `.env` file.

### Manual Override

**Provider Selection:**
```bash
promptheus --provider gemini "Idea"
promptheus --provider anthropic "Idea"
promptheus --provider openai "Idea"
promptheus --provider groq "Idea"
promptheus --provider qwen "Idea"
promptheus --provider glm "Idea"
```

**Model Selection:**
```bash
promptheus --model gemini-1.5-pro "Idea"
promptheus --model claude-3-5-sonnet-20241022 "Idea"
promptheus --model gpt-4o "Idea"
promptheus --model llama-3.1-70b-versatile "Idea"
```

**Supported Providers:** gemini, anthropic, openai, groq, qwen, glm

**Model Discovery:**
```bash
promptheus list-models
promptheus list-models --providers openai,gemini
```

## Output Control Flags

| Flag | Function |
|------|----------|
| `-c` / `--copy` | Copy refined output to system clipboard |
| `-o` / `--output-format` | Specify format: `plain` or `json` |

**Composite Usage:**
```bash
promptheus -s -c -o json "Pitch deck outline"
```

## History Management System

### Command-Line Interface
```bash
promptheus history                 # Display all history
promptheus history --limit 50      # Display last 50 entries
promptheus history --clear         # Purge history
```

### Interactive Mode Commands
- `/history` - Display session history
- `/load <n>` - Load entry at index n
- `/clear-history` - Purge all history
- Arrow key navigation (↑/↓) for recent prompts
- `/copy` - Copy last refined result to clipboard
- `/status` - Display current session configuration

### Storage Characteristics
- Automatic persistence of refined prompts
- Metadata includes timestamps, task classifications, original and refined versions
- Local storage with no external transmission

## Iterative Refinement Interface

Post-refinement, the system offers an iterative modification workflow:

```
Tweak? (Enter to accept, or describe your change): make it punchier
```

**Modification Commands:**
- Natural language instructions: "make it more formal", "remove the section on pricing", "add a call-to-action"
- Each modification applies targeted AI-based editing
- Empty input (Enter) accepts current version

## Command Reference Summary

### Authentication Commands

| Command | Description |
|---------|-------------|
| `promptheus auth` | Interactive provider selection and API key configuration |
| `promptheus auth <provider>` | Configure specific provider |
| `promptheus auth <provider> --skip-validation` | Skip API key validation |

### Utility Commands

| Command | Description |
|---------|-------------|
| `promptheus --help` | Display usage information |
| `promptheus --version` | Display version information |
| `promptheus list-models` | Display available providers and models |
| `promptheus validate` | Validate API configuration |
| `promptheus validate --test-connection` | Test live API connectivity |
| `promptheus template <providers>` | Generate environment template |

### History Commands

| Command | Description |
|---------|-------------|
| `promptheus history` | Display all history |
| `promptheus history --limit N` | Display last N entries |
| `promptheus history --clear` | Purge history |

## Workflow Examples

### Content Generation with Interactive Refinement
```
$ promptheus "Write a blog post"
✓ Creative task detected with clarifying questions
Ask clarifying questions to refine your prompt? (Y/n): y
...
╭─ Refined Prompt ───────────────────────────────╮
│ Write a thought-provoking blog post on AI ethics│
│ ... include real-world examples ...             │
╰─────────────────────────────────────────────────╯
```

### Analysis Task with Question Bypass
```
$ promptheus -s "Analyze the main.py file and explain the key functions"
✓ Skip questions mode - improving prompt directly
╭─ Refined Prompt ───────────────────────────────╮
│ [Improved prompt shown here]                   │
╰────────────────────────────────────────────────╯
```

## Environment Configuration Template Generation

Generate `.env` file templates for provider configuration:

```bash
# Single provider template
promptheus template openai > .env

# Multi-provider template
promptheus template openai,gemini,anthropic > .env
```

## Python Version Compatibility

### Python 3.14 Support Status

**Gemini Provider:** Full support via unified `google-genai` SDK

**Other Providers:** Compatibility status varies by SDK version

**Mitigation Strategies:**
1. Monitor provider SDK updates for Python 3.14 compatibility
2. Use Python 3.10-3.13 for providers without Python 3.14 support
3. Utilize virtual environments for version management

## Interactive Mode Features

### Keyboard Bindings

| Key Combination | Function |
|----------------|----------|
| Enter | Submit prompt |
| Shift+Enter | Insert newline (multiline mode) |
| Option/Alt+Enter | Insert newline (alternative) |
| Ctrl+J | Insert newline (alternative) |
| ↑/↓ Arrow Keys | Navigate command history |
| Tab | Display command completion suggestions |

### Slash Command Reference

**Information and Navigation:**

| Command | Function |
|---------|----------|
| `/help` | Display available commands |
| `/history` | Display recent prompts |
| `/load <n>` | Load prompt at index n |
| `/clear-history` | Purge history |
| `/about` | Display version and configuration |
| `/bug` | Access bug report interface |

**Session Configuration:**

| Command | Function |
|---------|----------|
| `/status` | Display current settings |
| `/set provider <name>` | Modify active provider |
| `/set model <name>` | Modify active model |
| `/toggle refine` | Toggle refinement mode |
| `/toggle skip-questions` | Toggle question bypass mode |

**Utility Operations:**

| Command | Function |
|---------|----------|
| `/copy` | Copy last refined result to clipboard |
