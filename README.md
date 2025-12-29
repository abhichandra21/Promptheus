# Promptheus

**Refine and optimize prompts for LLMs**

<!-- mcp-name: io.github.abhichandra21/promptheus -->

[![Python Version](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/downloads/) [![PyPI Version](https://img.shields.io/pypi/v/promptheus)](https://pypi.org/project/promptheus/) [![Release Version](https://img.shields.io/badge/release-v0.3.1-brightgreen)](CHANGELOG.md) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![GitHub Stars](https://img.shields.io/github/stars/abhichandra21/Promptheus?style=social)](https://github.com/abhichandra21/Promptheus)

[![Deploy GitHub Pages](https://github.com/abhichandra21/Promptheus/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/abhichandra21/Promptheus/actions/workflows/deploy-pages.yml) [![Docker Build & Test](https://github.com/abhichandra21/Promptheus/actions/workflows/docker-test.yml/badge.svg)](https://github.com/abhichandra21/Promptheus/actions/workflows/docker-test.yml) [![Publish Python Package](https://github.com/abhichandra21/Promptheus/actions/workflows/publish.yml/badge.svg)](https://github.com/abhichandra21/Promptheus/actions/workflows/publish.yml)

## Quick Start

```bash
pip install promptheus
```

```bash
# Interactive session
promptheus

# Single prompt
promptheus "Write a technical blog post"

# Skip clarifying questions
promptheus -s "Explain Kubernetes"

# Use web UI
promptheus web
```

### Python library usage

```python
from promptheus import refine_prompt

result = refine_prompt("Write a technical blog post", skip_questions=True)
print(result["refined_prompt"])
```

If you're already in an async application (e.g., FastAPI), call `refine_prompt_async` instead of the sync helper.

## What is Promptheus?

Promptheus analyzes your prompts and refines them with:
- **Adaptive questioning**: Smart detection of what information you need to provide
- **Multi-provider support**: Works with Google, OpenAI, Anthropic, Groq, Qwen, and more
- **Interactive refinement**: Iteratively improve outputs through natural conversation
- **Session history**: Automatically track and reuse past prompts
- **CLI and Web UI**: Use from terminal or browser

## Supported Providers

| Provider | Models | Setup |
|----------|--------|-------|
| **Google Gemini** | gemini-2.0-flash, gemini-1.5-pro | [API Key](https://aistudio.google.com) |
| **Anthropic Claude** | claude-3-5-sonnet, claude-3-opus | [Console](https://console.anthropic.com) |
| **OpenAI** | gpt-4o, gpt-4-turbo | [API Key](https://platform.openai.com/api-keys) |
| **Groq** | llama-3.3-70b, mixtral-8x7b | [Console](https://console.groq.com) |
| **Alibaba Qwen** | qwen-max, qwen-plus | [DashScope](https://dashscope.aliyun.com) |
| **Zhipu GLM** | glm-4-plus, glm-4-air | [Console](https://open.bigmodel.cn) |
| **OpenRouter** | openrouter/auto (auto-routing) | [Dashboard](https://openrouter.ai) |

OpenRouter integration in Promptheus is optimized around the `openrouter/auto` routing model:
- Model listing is intentionally minimal: Promptheus does not expose your full OpenRouter account catalog.
- You can still specify a concrete model manually with `OPENROUTER_MODEL` or `--model` if your key has access.

## Core Features

**🧠 Adaptive Task Detection**
Automatically detects whether your task needs refinement or direct optimization

**⚡ Interactive Refinement**
Ask targeted questions to elicit requirements and improve outputs

**📝 Pipeline Integration**
Works seamlessly in Unix pipelines and shell scripts

**🔄 Session Management**
Track, load, and reuse past prompts automatically

**📊 Telemetry & Analytics**
Anonymous usage and performance metrics tracking for insights (local storage only, can be disabled)

**🌐 Web Interface**
Beautiful UI for interactive prompt refinement and history management

## Configuration

Create a `.env` file with at least one provider API key:

```bash
GOOGLE_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

Or run the interactive setup:

```bash
promptheus auth
```

## Examples

**Content Generation**
```bash
promptheus "Write a blog post about async programming"
# System asks: audience, tone, length, key topics
# Generates refined prompt with all specifications
```

**Code Analysis**
```bash
promptheus -s "Review this function for security issues"
# Skips questions, applies direct enhancement
```

**Interactive Session**
```bash
promptheus
/set provider anthropic
/set model claude-3-5-sonnet
# Process multiple prompts, switch providers/models with /commands
```

**Pipeline Integration**
```bash
echo "Create a REST API schema" | promptheus | jq '.refined_prompt'
cat prompts.txt | while read line; do promptheus "$line"; done
```

**Testing & Examples**: See [sample_prompts.md](sample_prompts.md) for test prompts demonstrating adaptive task detection (analysis vs generation).

**Telemetry & Analytics**
```bash
# View telemetry summary (anonymous metrics about usage and performance)
promptheus telemetry summary

# Disable telemetry if desired
export PROMPTHEUS_TELEMETRY_ENABLED=0

# Customize history storage location
export PROMPTHEUS_HISTORY_DIR=~/.custom_promptheus
```

## MCP Server

Promptheus includes a **Model Context Protocol (MCP) server** that exposes prompt refinement capabilities as standardized tools for integration with MCP-compatible clients.

### What the MCP Server Does

The Promptheus MCP server provides:
- **Prompt refinement with Q&A**: Intelligent prompt optimization through adaptive questioning
- **Prompt tweaking**: Surgical modifications to existing prompts  
- **Model/provider inspection**: Discovery and validation of available AI providers
- **Environment validation**: Configuration checking and connectivity testing

### Starting the MCP Server

```bash
# Start the MCP server
promptheus mcp

# Or run directly with Python
python -m promptheus.mcp_server
```

**Prerequisites:**
- MCP package installed: `pip install mcp` (included in requirements.txt)
- At least one provider API key configured (see [Configuration](#configuration))

### Available MCP Tools

#### `refine_prompt`
Intelligent prompt refinement with optional clarification questions.

**Inputs:**
- `prompt` (required): The initial prompt to refine
- `answers` (optional): Dictionary mapping question IDs to answers `{q0: "answer", q1: "answer"}`
- `answer_mapping` (optional): Maps question IDs to original question text
- `provider` (optional): Override provider (e.g., "google", "openai")
- `model` (optional): Override model name

**Response Types:**
- `{"type": "refined", "prompt": "...", "next_action": "..."}`: Success with refined prompt
- `{"type": "clarification_needed", "questions_for_ask_user_question": [...], "answer_mapping": {...}}`: Questions needed
- `{"type": "error", "error_type": "...", "message": "..."}`: Error occurred

#### `tweak_prompt`
Apply targeted modifications to existing prompts.

**Inputs:**
- `prompt` (required): Current prompt to modify
- `modification` (required): Description of changes (e.g., "make it shorter")
- `provider`, `model` (optional): Provider/model overrides

**Returns:**
- `{"type": "refined", "prompt": "..."}`: Modified prompt

#### `list_models`
Discover available models from configured providers.

**Inputs:**
- `providers` (optional): List of provider names to query
- `limit` (optional): Max models per provider (default: 20)
- `include_nontext` (optional): Include vision/embedding models

**Returns:**
- `{"type": "success", "providers": {"google": {"available": true, "models": [...]}}}`

#### `list_providers`
Check provider configuration status.

**Returns:**
- `{"type": "success", "providers": {"google": {"configured": true, "model": "..."}}}`

#### `validate_environment`
Test environment configuration and API connectivity.

**Inputs:**
- `providers` (optional): Specific providers to validate
- `test_connection` (optional): Test actual API connectivity

**Returns:**
- `{"type": "success", "validation": {"google": {"configured": true, "connection_test": "passed"}}}`

### Prompt Refinement Workflow with Q&A

The MCP server supports a structured clarification workflow for optimal prompt refinement:

#### Step 1: Initial Refinement Request
```json
{
  "tool": "refine_prompt",
  "arguments": {
    "prompt": "Write a blog post about machine learning"
  }
}
```

#### Step 2: Handle Clarification Response
```json
{
  "type": "clarification_needed",
  "task_type": "generation",
  "message": "To refine this prompt effectively, I need to ask...",
  "questions_for_ask_user_question": [
    {
      "question": "Who is your target audience?",
      "header": "Q1",
      "multiSelect": false,
      "options": [
        {"label": "Technical professionals", "description": "Technical professionals"},
        {"label": "Business executives", "description": "Business executives"}
      ]
    }
  ],
  "answer_mapping": {
    "q0": "Who is your target audience?"
  }
}
```

#### Step 3: Collect User Answers
Use your MCP client's `AskUserQuestion` tool with the provided questions, then map answers to question IDs.

#### Step 4: Final Refinement with Answers
```json
{
  "tool": "refine_prompt", 
  "arguments": {
    "prompt": "Write a blog post about machine learning",
    "answers": {"q0": "Technical professionals"},
    "answer_mapping": {"q0": "Who is your target audience?"}
  }
}
```

**Response:**
```json
{
  "type": "refined",
  "prompt": "Write a comprehensive technical blog post about machine learning fundamentals targeted at software engineers and technical professionals. Include practical code examples and architectural patterns...",
  "next_action": "This refined prompt is now ready to use. If the user asked you to execute/run the prompt, use this refined prompt directly with your own capabilities..."
}
```

### AskUser Integration Contract

The MCP server operates in two modes:

**Interactive Mode** (when AskUserQuestion is available):
- Automatically asks clarification questions via injected AskUserQuestion function
- Returns refined prompt immediately after collecting answers
- Seamless user experience within supported clients

**Structured Mode** (fallback for all clients):
- Returns `clarification_needed` response with formatted questions
- Client responsible for calling AskUserQuestion tool
- Answers mapped back via `answer_mapping` dictionary

**Question Format:**
Each question in `questions_for_ask_user_question` includes:
- `question`: The question text to display
- `header`: Short identifier (Q1, Q2, etc.)
- `multiSelect`: Boolean for multi-select options
- `options`: Array of `{label, description}` for radio/checkbox questions

**Answer Mapping:**
- Question IDs follow pattern: `q0`, `q1`, `q2`, etc.
- Answers dictionary uses these IDs as keys: `{"q0": "answer", "q1": "answer"}`
- `answer_mapping` preserves original question text for provider context

### Troubleshooting MCP

**MCP Package Not Installed**
```
Error: The 'mcp' package is not installed. Please install it with 'pip install mcp'.
```
**Fix:** `pip install mcp` or install Promptheus with dev dependencies: `pip install -e .[dev]`

**Missing Provider API Keys**
```json
{
  "type": "error",
  "error_type": "ConfigurationError", 
  "message": "No provider configured. Please set API keys in environment."
}
```
**Diagnosis:** Use `list_providers` or `validate_environment` tools to check configuration status

**Provider Misconfiguration**
```json
{
  "type": "success",
  "providers": {
    "google": {"configured": false, "error": "GOOGLE_API_KEY not found"},
    "openai": {"configured": true, "model": "gpt-4o"}
  }
}
```
**Fix:** Set missing API keys in `.env` file or environment variables

**Connection Test Failures**
```json
{
  "type": "success", 
  "validation": {
    "google": {
      "configured": true,
      "connection_test": "failed: Authentication error"
    }
  }
}
```
**Fix:** Verify API keys are valid and have necessary permissions

## Full Documentation

**Quick reference**: `promptheus --help`

**Comprehensive guides**:
- 📖 [Installation & Setup](docs/documentation.html#installation)
- 🚀 [Usage Guide](docs/documentation.html#quick-start)
- 🔧 [Configuration](docs/documentation.html#configuration)
- ⌨️ [CLI Reference](docs/documentation.html#cli-basics)
- 🌐 [Web UI Guide](docs/documentation.html#web-overview)
- 🔌 [Provider Setup](docs/documentation.html#providers)

## Development

```bash
git clone https://github.com/abhichandra21/Promptheus.git
cd Promptheus
pip install -e ".[dev]"
pytest -q
```

See [CLAUDE.md](CLAUDE.md) for detailed development guidance.

## License

MIT License - see [LICENSE](LICENSE) for details

## Contributing

Contributions welcome! Please see our [development guide](docs/documentation.html) for contribution guidelines.

---

**Questions?** [Open an issue](https://github.com/abhichandra21/Promptheus/issues) | **Live demo**: `promptheus web`
