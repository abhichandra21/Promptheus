# Promptheus

**Refine and optimize prompts for LLMs**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/downloads/) [![PyPI Version](https://img.shields.io/pypi/v/promptheus)](https://pypi.org/project/promptheus/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![GitHub Stars](https://img.shields.io/github/stars/abhichandra21/Promptheus?style=social)](https://github.com/abhichandra21/Promptheus)

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

## Core Features

**🧠 Adaptive Task Detection**
Automatically detects whether your task needs refinement or direct optimization

**⚡ Interactive Refinement**
Ask targeted questions to elicit requirements and improve outputs

**📝 Pipeline Integration**
Works seamlessly in Unix pipelines and shell scripts

**🔄 Session Management**
Track, load, and reuse past prompts automatically

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
echo "Create a REST API schema" | promptheus | jq '.prompt'
cat prompts.txt | while read line; do promptheus "$line"; done
```

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
