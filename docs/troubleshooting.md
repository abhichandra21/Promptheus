# Promptheus Troubleshooting Guide

This document provides diagnostic procedures and resolution strategies for common issues encountered during Promptheus operation.

## Provider Configuration Issues

### Provider Auto-Detection Failure

**Symptom:** System fails to detect configured providers

**Resolution:**
```bash
# Explicitly specify provider
promptheus --provider google "Prompt"
promptheus --provider anthropic "Prompt"
promptheus --provider openai "Prompt"
promptheus --provider groq "Prompt"
promptheus --provider qwen "Prompt"
promptheus --provider glm "Prompt"
```

### Incorrect Provider Selection

**Symptom:** System selects unexpected provider

**Diagnostic Steps:**
```bash
# Verify environment configuration
cat .env

# Check environment variables
env | grep -E '(GOOGLE|ANTHROPIC|OPENAI|GROQ|DASHSCOPE|ZHIPUAI|PROMPTHEUS)'

# Override provider selection
export PROMPTHEUS_PROVIDER=google
```

### API Key Validation

**Verification Commands:**
```bash
# Validate specific provider configuration
promptheus validate --providers google
promptheus validate --providers anthropic
promptheus validate --providers openai
promptheus validate --providers groq
promptheus validate --providers qwen
promptheus validate --providers glm

# Test live API connectivity
promptheus validate --test-connection
```

## Installation and Runtime Issues

### Command Not Found Error

**Symptom:** Shell reports `promptheus` command not found

**Resolution:**
```bash
# Reinstall in editable mode
pip install -e .

# Execute via Python module
python -m promptheus.main "Prompt"

# Verify installation
which promptheus
```

### Dependency Resolution Errors

**Symptom:** Import errors or missing module exceptions

**Resolution:**
```bash
# Install required dependencies
pip install -r requirements.txt

# Force reinstallation
pip install -e . --force-reinstall
```

## File Input Issues

### File Not Found Errors

**Symptom:** File input fails with path resolution errors

**Resolution:**
```bash
# Use absolute path
promptheus -f /absolute/path/to/prompt.txt

# Use relative path from current directory
promptheus -f ./relative/path/prompt.txt
```

## Clipboard Integration Issues

### Platform-Specific Requirements

**Linux:**
- Install `xclip` or `xsel`: `sudo apt-get install xclip`

**macOS:**
- Native clipboard support (no additional installation required)

**Windows:**
- Native clipboard support (no additional installation required)

**WSL (Windows Subsystem for Linux):**
- May require X server configuration for clipboard access
- Verify X server is running and DISPLAY variable is set

## Interactive Mode Issues

### Multiline Input Problems

**Symptom:** Unable to insert newlines in prompt input

**Resolution:**
- Use `Shift+Enter` for newline insertion
- Alternative: `Option/Alt+Enter` or `Ctrl+J`
- Fallback: Use plain mode if terminal is unresponsive

### Slash Command Failures

**Common Issues:**
- Commands must begin with `/` prefix (not `:`)
- Use `/help` to display available commands
- Use Tab key for command completion suggestions

### Session Configuration Management

**Commands:**
```bash
# Display current session configuration
/status

# Modify provider
/set provider google

# Modify model
/set model gpt-4o

# Toggle modes
/toggle refine
/toggle skip-questions
```

## Shell Completion Issues

### Completion Script Not Functional

**Symptom:** Tab completion does not work after installation

**Diagnostic Steps:**
```bash
# Verify completion script generation
promptheus completion bash  # Should output script

# Verify promptheus is in PATH
which promptheus

# Reload shell configuration
source ~/.bashrc   # Bash
source ~/.zshrc    # Zsh

# For Poetry environments, create alias
alias promptheus='poetry run promptheus'
```

## Model Discovery Issues

### Model List Not Updating

**Symptom:** Model lists appear outdated or do not include newly available models

**Resolution:**
```bash
# Manually refresh model cache
promptheus validate --test-connection  # This will also refresh cache

# Or, in Web UI:
# Go to Settings and click "Refresh Model Cache" button
```

**Cache Location:**
- On Unix: `~/.promptheus/models_cache.json`
- On Windows: `%APPDATA%/promptheus/models_cache.json`

## Reporting Issues

When reporting issues, include the following information:

1. **Command executed:** Full command with all flags
2. **Error output:** Complete error message and stack trace
3. **Environment details:**
   - Python version (`python --version`)
   - Operating system and version
   - Provider and model in use
   - Installation method (pip, source, Poetry)
4. **Reproduction steps:** Minimal steps to reproduce the issue
5. **Current model cache status:** If issue related to model discovery

**Issue Tracker:** https://github.com/abhichandra21/Promptheus/issues
