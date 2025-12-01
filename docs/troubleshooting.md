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

## MCP Server Issues

### MCP Package Not Installed

**Symptom:** Error message when starting MCP server
```
Error: The 'mcp' package is not installed. Please install it with 'pip install mcp'.
```

**Resolution:**
```bash
# Install MCP package
pip install mcp

# Or install with development dependencies
pip install -e .[dev]

# Verify installation
python -c "import mcp; print('MCP installed successfully')"
```

### MCP Server Connection Issues

**Symptom:** MCP client cannot connect to Promptheus MCP server

**Diagnostic Steps:**
```bash
# Verify MCP server starts correctly
promptheus mcp

# Check for error messages in server output
# Test with direct Python execution
python -m promptheus.mcp_server

# Verify provider configuration
promptheus validate --test-connection
```

**Common Causes:**
- Missing provider API keys
- MCP package not properly installed
- Port conflicts (MCP uses stdio transport)

### MCP Tool Execution Errors

**Symptom:** MCP tools return error responses

**Diagnostic Commands:**
```bash
# Test individual MCP tools
# Use MCP client to call list_providers
# Use MCP client to call validate_environment

# Check provider status
promptheus list-providers

# Validate environment configuration
promptheus validate --providers google,openai
```

**Common Error Types:**
```json
{
  "type": "error",
  "error_type": "ConfigurationError",
  "message": "No provider configured. Please set API keys in environment."
}
```

**Resolution:**
```bash
# Configure provider API keys
promptheus auth google
promptheus auth openai

# Or manually set in .env file
echo "GOOGLE_API_KEY=your_key_here" >> .env
echo "OPENAI_API_KEY=your_key_here" >> .env
```

### AskUserQuestion Integration Issues

**Symptom:** MCP server not handling clarification questions properly

**Understanding the Integration Modes:**

**Interactive Mode** (when AskUserQuestion is available):
- Server automatically asks questions via injected AskUserQuestion function
- Seamless user experience within supported clients

**Structured Mode** (fallback):
- Server returns `clarification_needed` response with formatted questions
- Client responsible for calling AskUserQuestion tool
- Answers mapped back via `answer_mapping` dictionary

**Debugging AskUserQuestion Issues:**
```bash
# Test refine_prompt workflow
# Step 1: Call with basic prompt that should trigger questions
# Step 2: Verify clarification_needed response format
# Step 3: Check questions_for_ask_user_question array format
# Step 4: Verify answer_mapping structure
```

**Expected Response Format:**
```json
{
  "type": "clarification_needed",
  "questions_for_ask_user_question": [
    {
      "question": "Who is your target audience?",
      "header": "Q1",
      "multiSelect": false,
      "options": [
        {"label": "Technical professionals", "description": "Technical professionals"}
      ]
    }
  ],
  "answer_mapping": {
    "q0": "Who is your target audience?"
  }
}
```

### MCP Client Compatibility Issues

**Symptom:** MCP client cannot properly communicate with Promptheus MCP server

**Resolution:**
```bash
# Ensure MCP client supports:
# - Tool calling capabilities
# - JSON response processing
# - AskUserQuestion tool (for interactive mode)

# Test with basic tool calls first
# Verify response format compatibility
# Check error handling consistency
```

### Performance Issues with MCP Server

**Symptom:** Slow response times from MCP tools

**Diagnostic Steps:**
```bash
# Test provider connectivity
promptheus validate --test-connection

# Check for model fallback behavior
# Monitor API response times
# Verify cache utilization (model cache, etc.)
```

**Optimization Tips:**
- Use specific provider/model parameters to avoid auto-detection overhead
- Ensure provider API keys are valid to prevent retry delays
- Consider using cached model information when available

### MCP Server Logging and Debugging

**Enable Debug Logging:**
```bash
# Set logging level for MCP server
export LOG_LEVEL=DEBUG

# Run MCP server with verbose output
promptheus mcp --verbose  # If supported by client
```

**Common Debug Information:**
- Provider initialization sequence
- Tool execution timing
- Question generation process
- Answer mapping validation
