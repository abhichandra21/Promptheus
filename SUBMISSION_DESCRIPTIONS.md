# MCP Registry Submission Descriptions

This file contains all the copy-paste ready descriptions and content for submitting Promptheus to various MCP registries and lists.

---

## Table of Contents

1. [For mcpservers.org Web Form](#for-mcpserversorg-web-form)
2. [For mcp.so (TensorBlock)](#for-mcpso-tensorblock)
3. [GitHub Issue Template for TensorBlock](#github-issue-template-for-tensorblock)
4. [For appcypher/awesome-mcp-servers PR](#for-appcypherawesome-mcp-servers-pr)
5. [For Other Awesome Lists](#for-other-awesome-lists)
6. [Social Media Announcements](#social-media-announcements)

---

## For mcpservers.org Web Form

**URL**: https://mcpservers.org/submit

### Server Name
```
Promptheus
```

### Repository URL
```
https://github.com/abhichandra21/Promptheus
```

### Description (Short - ~250 chars)
```
AI-powered prompt refinement tool with adaptive questioning and multi-provider support. Intelligently refines prompts through clarifying questions, supports 6+ AI providers (Google Gemini, Anthropic Claude, OpenAI, Groq, Alibaba Qwen, Zhipu GLM), and provides comprehensive prompt engineering capabilities.
```

### Description (Long - if requested)
```
Promptheus is an AI-powered prompt refinement tool that helps you craft better prompts for large language models. It uses adaptive questioning to understand your needs and intelligently refines prompts through an interactive workflow.

Key Features:
• 5 MCP Tools: refine_prompt, tweak_prompt, list_models, list_providers, validate_environment
• Multi-provider Support: Google Gemini, Anthropic Claude, OpenAI, Groq, Alibaba Qwen, Zhipu GLM
• Adaptive Task Detection: Automatically detects whether tasks need refinement (generation) or direct optimization (analysis)
• Interactive & Structured Modes: Supports both interactive questioning with users and structured JSON responses
• Session History: Automatic prompt history tracking and reuse
• Privacy-Preserving Telemetry: Anonymous usage metrics (local storage only, can be disabled)

Perfect for developers, researchers, and AI practitioners who want to improve prompt quality and get better results from LLMs.
```

### Installation Instructions
```
pip install promptheus
promptheus mcp
```

### Quick Start / Usage
```
# Install
pip install promptheus

# Start MCP server
promptheus mcp

# Or use CLI directly
promptheus "Your prompt here"

# Requires at least one provider API key:
# GOOGLE_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GROQ_API_KEY, QWEN_API_KEY, or GLM_API_KEY
```

### Categories
```
AI Tools, Developer Productivity, Prompt Engineering, LLM Utilities
```

### Tags/Keywords
```
prompt-engineering, ai, llm, mcp, multi-provider, gemini, claude, openai, groq, refinement, prompt-optimization
```

### License
```
MIT
```

### Additional Links
```
PyPI: https://pypi.org/project/promptheus/
Documentation: https://github.com/abhichandra21/Promptheus#readme
Changelog: https://github.com/abhichandra21/Promptheus/blob/main/CHANGELOG.md
```

---

## For mcp.so (TensorBlock)

**URL**: https://mcp.so (Submit button)

### Server Name
```
Promptheus
```

### GitHub Repository
```
https://github.com/abhichandra21/Promptheus
```

### Description
```
AI-powered prompt refinement tool with adaptive questioning and multi-provider support. Provides 5 MCP tools (refine_prompt, tweak_prompt, list_models, list_providers, validate_environment) for intelligent prompt engineering. Supports Google Gemini, Anthropic Claude, OpenAI, Groq, Alibaba Qwen, and Zhipu GLM. Features adaptive task detection, interactive/structured modes, and session history management.
```

### Installation
```
pip install promptheus && promptheus mcp
```

### Features (bullet points)
```
• 5 MCP tools for prompt refinement and provider management
• Multi-provider support: Google Gemini, Anthropic Claude, OpenAI, Groq, Qwen, GLM
• Adaptive task detection: Automatically determines analysis vs generation workflows
• Interactive questioning mode with AskUserQuestion integration
• Structured JSON response mode for programmatic usage
• Session history tracking and prompt reuse
• Privacy-preserving telemetry (local only, optional)
• CLI and web UI interfaces
```

### Connection Information
```
Transport: stdio
Command: python -m promptheus.mcp_server
Package: promptheus (PyPI)
```

### Required Environment Variables
```
At least one of:
- GOOGLE_API_KEY
- ANTHROPIC_API_KEY
- OPENAI_API_KEY
- GROQ_API_KEY
- QWEN_API_KEY
- GLM_API_KEY

Optional:
- PROMPTHEUS_PROVIDER (override provider)
- PROMPTHEUS_MODEL (override model)
```

### Categories
```
Developer Productivity, AI Tools, Prompt Engineering, LLM Utilities
```

---

## GitHub Issue Template for TensorBlock

**URL**: https://github.com/TensorBlock/awesome-mcp-servers/issues/new

### Title
```
[Submission] Promptheus - AI-powered prompt refinement tool
```

### Body
```markdown
## Server Information

**Name**: Promptheus
**Repository**: https://github.com/abhichandra21/Promptheus
**PyPI Package**: https://pypi.org/project/promptheus/
**Version**: 0.3.0
**License**: MIT

## Description

AI-powered prompt refinement tool with adaptive questioning and multi-provider support. Intelligently refines prompts through clarifying questions, supports 6+ AI providers (Google Gemini, Anthropic Claude, OpenAI, Groq, Alibaba Qwen, Zhipu GLM), and provides comprehensive prompt engineering capabilities via MCP.

## Installation

```bash
pip install promptheus
promptheus mcp
```

## MCP Tools

1. **refine_prompt**: Intelligently refine prompts with adaptive questioning workflow
2. **tweak_prompt**: Make surgical modifications to existing prompts
3. **list_models**: Discover available models for each AI provider
4. **list_providers**: Check provider configuration status
5. **validate_environment**: Validate API keys and test provider connections

## Features

- **Multi-provider support**: Google Gemini, Anthropic Claude, OpenAI, Groq, Alibaba Qwen, Zhipu GLM
- **Adaptive task detection**: Automatically detects analysis vs generation tasks and adjusts workflow
- **Interactive & structured modes**: Supports both interactive questioning (with AskUserQuestion) and structured JSON responses
- **Session history**: Automatic prompt history tracking and reuse
- **Privacy-preserving telemetry**: Anonymous usage metrics stored locally only (can be disabled)
- **CLI and Web UI**: Use from terminal or browser interface

## Connection Information

- **Transport**: stdio
- **Command**: `python -m promptheus.mcp_server`
- **Package Type**: PyPI

## Environment Variables

At least one provider API key required:
- `GOOGLE_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GROQ_API_KEY`
- `QWEN_API_KEY`
- `GLM_API_KEY`

Optional configuration:
- `PROMPTHEUS_PROVIDER` - Override provider selection
- `PROMPTHEUS_MODEL` - Override model selection

## Categories

- AI Tools
- Developer Productivity
- Prompt Engineering
- LLM Utilities

## Additional Links

- **Documentation**: https://github.com/abhichandra21/Promptheus#readme
- **PyPI**: https://pypi.org/project/promptheus/
- **Changelog**: https://github.com/abhichandra21/Promptheus/blob/main/CHANGELOG.md
- **License**: https://github.com/abhichandra21/Promptheus/blob/main/LICENSE

## Why Include This Server?

Promptheus fills a unique niche in the MCP ecosystem by providing intelligent prompt refinement as a service. Unlike most MCP servers that provide data access or API integrations, Promptheus helps users craft better prompts before sending them to LLMs. This meta-capability makes it valuable for any AI workflow that depends on prompt quality.

The multi-provider support (6+ AI backends) and adaptive workflow make it highly flexible and suitable for diverse use cases - from research and analysis to content generation and code writing.
```

---

## For appcypher/awesome-mcp-servers PR

**File to Edit**: README.md

### Entry to Add (Alphabetical Order)

Find the appropriate category (Developer Tools, AI Tools, or Productivity) and add:

```markdown
- [Promptheus](https://github.com/abhichandra21/Promptheus) - AI-powered prompt refinement tool with adaptive questioning and multi-provider support (Google Gemini, Anthropic Claude, OpenAI, Groq, Qwen, GLM). Provides 5 MCP tools for intelligent prompt engineering.
```

### Pull Request Title
```
Add Promptheus - AI-powered prompt refinement tool
```

### Pull Request Description
```markdown
Adding Promptheus, an AI-powered prompt refinement MCP server.

**Repository**: https://github.com/abhichandra21/Promptheus
**PyPI**: https://pypi.org/project/promptheus/
**Version**: 0.3.0
**License**: MIT

## Features:
- 5 MCP tools (refine_prompt, tweak_prompt, list_models, list_providers, validate_environment)
- Multi-provider support (Google Gemini, Anthropic Claude, OpenAI, Groq, Qwen, GLM)
- Adaptive questioning workflow for intelligent prompt refinement
- Interactive and structured modes
- Session history management

## Installation:
```bash
pip install promptheus
promptheus mcp
```

## Why Include:
Promptheus provides meta-capabilities for prompt engineering, helping users craft better prompts before sending them to LLMs. This unique positioning makes it valuable for any AI workflow.

Follows contribution guidelines: alphabetical ordering, clear description, proper formatting, accurate information.
```

---

## For Other Awesome Lists

### Standard Entry Format

```markdown
- [Promptheus](https://github.com/abhichandra21/Promptheus) - AI-powered prompt refinement with adaptive questioning and 6+ provider support. `pip install promptheus`
```

### Detailed Entry Format (if supported)

```markdown
### Promptheus

AI-powered prompt refinement tool with intelligent questioning workflow.

- **Repository**: https://github.com/abhichandra21/Promptheus
- **Installation**: `pip install promptheus`
- **Providers**: Google Gemini, Anthropic Claude, OpenAI, Groq, Qwen, GLM
- **MCP Tools**: refine_prompt, tweak_prompt, list_models, list_providers, validate_environment
- **Features**: Adaptive task detection, interactive/structured modes, session history
- **License**: MIT
```

---

## Social Media Announcements

### Twitter/X Announcement

```
🚀 Just published Promptheus to the official MCP Registry!

🤖 AI-powered prompt refinement
🔧 5 MCP tools for prompt engineering
🌐 6+ provider support (Gemini, Claude, GPT-4, Groq, Qwen, GLM)
💡 Adaptive questioning workflow

Install: pip install promptheus

#MCP #AI #PromptEngineering #LLM

https://github.com/abhichandra21/Promptheus
```

### LinkedIn Announcement

```
I'm excited to announce that Promptheus is now available on the official Model Context Protocol (MCP) Registry!

Promptheus is an AI-powered prompt refinement tool that helps developers and AI practitioners craft better prompts through intelligent questioning and multi-provider support.

Key Highlights:
✅ 5 MCP tools for comprehensive prompt engineering
✅ Support for 6+ AI providers (Google Gemini, Anthropic Claude, OpenAI, Groq, Alibaba Qwen, Zhipu GLM)
✅ Adaptive task detection and workflow optimization
✅ Interactive and structured question modes
✅ Session history management

Whether you're building AI applications, conducting research, or just want better LLM outputs, Promptheus can help optimize your prompts before execution.

Try it out:
pip install promptheus
promptheus mcp

Learn more: https://github.com/abhichandra21/Promptheus

#AI #MachineLearning #PromptEngineering #MCP #LLM #DeveloperTools
```

### Reddit (r/MachineLearning, r/LocalLLaMA)

**Title**: `[P] Promptheus - AI-powered prompt refinement now on MCP Registry`

**Body**:
```
I've just published Promptheus to the official Model Context Protocol (MCP) Registry. It's an AI-powered prompt refinement tool that helps you craft better prompts through intelligent questioning.

**What it does:**
- Analyzes your prompt to determine if refinement is needed
- Asks contextual clarifying questions
- Combines your answers to generate optimized prompts
- Supports 6+ AI providers (Gemini, Claude, GPT-4, Groq, Qwen, GLM)

**MCP Integration:**
Promptheus provides 5 MCP tools that you can use in any MCP-compatible client:
- `refine_prompt` - Main refinement workflow
- `tweak_prompt` - Surgical prompt modifications
- `list_models` - Discover available models
- `list_providers` - Check configuration
- `validate_environment` - Test API connections

**Installation:**
```bash
pip install promptheus
promptheus mcp  # Start MCP server
# Or use CLI: promptheus "Your prompt here"
```

**Why I built this:**
After countless iterations of prompt engineering across different projects, I realized the process could be systematized. Promptheus encodes best practices for prompt refinement into an automated workflow, saving time and improving output quality.

The multi-provider support means you're not locked into a single AI backend - switch between Gemini, Claude, GPT-4, or open models based on your needs.

**Links:**
- GitHub: https://github.com/abhichandra21/Promptheus
- PyPI: https://pypi.org/project/promptheus/
- License: MIT

Happy to answer questions or hear feedback!
```

### Hacker News

**Title**: `Promptheus – AI-powered prompt refinement tool now on MCP Registry`

**URL**: `https://github.com/abhichandra21/Promptheus`

---

## One-Liner Descriptions (Various Lengths)

### Ultra-Short (50 chars)
```
AI prompt refinement with multi-provider support
```

### Short (100 chars)
```
AI-powered prompt refinement tool with adaptive questioning and support for 6+ LLM providers via MCP
```

### Medium (200 chars)
```
AI-powered prompt refinement tool that intelligently refines prompts through clarifying questions. Supports 6+ providers (Gemini, Claude, GPT-4, Groq, Qwen, GLM) with 5 MCP tools for prompt engineering.
```

### Long (500 chars)
```
Promptheus is an AI-powered prompt refinement tool that helps developers and researchers craft better prompts for large language models. It uses adaptive questioning to understand your needs and intelligently refines prompts through an interactive workflow. With support for 6+ AI providers (Google Gemini, Anthropic Claude, OpenAI, Groq, Alibaba Qwen, Zhipu GLM) and 5 specialized MCP tools, Promptheus provides comprehensive prompt engineering capabilities. Features include adaptive task detection, interactive/structured modes, session history, and privacy-preserving telemetry.
```

---

## Elevator Pitch (30 seconds)

```
Promptheus turns prompt engineering from an art into a science. Instead of manually iterating on prompts, it asks intelligent questions to understand your needs, then automatically generates optimized prompts. With support for 6+ AI providers and full MCP integration, it's the missing tool in your AI workflow. Whether you're analyzing data or generating content, Promptheus helps you get better results from LLMs - faster.
```

---

## FAQ Responses

### "What makes Promptheus different from just prompting directly?"

```
Promptheus systematizes prompt engineering best practices. Instead of guessing what details an LLM needs, it asks targeted questions based on task type (analysis vs generation), combines your answers with the original prompt, and generates an optimized version. It's like having a prompt engineering expert guide you through the process automatically.
```

### "Why multi-provider support?"

```
Different LLMs excel at different tasks, and API costs/availability vary. Promptheus lets you switch between Gemini, Claude, GPT-4, Groq, Qwen, and GLM without changing your workflow. You're not locked into a single provider, and you can optimize for cost, quality, or availability as needed.
```

### "What are the MCP tools used for?"

```
The 5 MCP tools (refine_prompt, tweak_prompt, list_models, list_providers, validate_environment) let you integrate Promptheus into any MCP-compatible client. This means you can use prompt refinement directly in Claude Desktop, VSCode extensions, or custom applications - without leaving your workflow.
```

### "Is my data sent anywhere?"

```
No. All prompt refinement happens locally or through the AI provider you configure. Promptheus doesn't store or transmit your prompts to any external service. Optional telemetry (usage metrics only, no prompt content) is stored locally and can be disabled entirely.
```

---

## Copy-Paste Checklist

Before submitting, verify you have:

- [ ] Repository URL: `https://github.com/abhichandra21/Promptheus`
- [ ] PyPI package: `https://pypi.org/project/promptheus/`
- [ ] Installation: `pip install promptheus`
- [ ] MCP command: `promptheus mcp`
- [ ] License: MIT
- [ ] Categories: AI Tools, Developer Productivity, Prompt Engineering
- [ ] Version: 0.3.0
- [ ] 5 MCP tools listed correctly
- [ ] 6+ providers mentioned (Gemini, Claude, OpenAI, Groq, Qwen, GLM)

---

**All content in this file is ready for copy-paste. No modifications needed!**
