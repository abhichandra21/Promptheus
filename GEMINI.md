# Gemini Context: Promptheus Project

This document provides a comprehensive overview of the `Promptheus` project, its architecture, and development conventions to be used as instructional context.

## 1. Project Overview

Promptheus is a sophisticated, AI-powered command-line interface (CLI) tool written in Python. Its primary purpose is to **help users craft and refine prompts**. The tool takes a user's initial prompt and, through a series of AI-driven steps, outputs a better, more effective prompt for the user to then take and use with any Large Language Model (LLM).

### Core Features:
- **Multi-Provider Support**: It uses LLM backends (Google Gemini, Anthropic Claude) for its internal refinement process.
- **Adaptive Interaction**: The tool intelligently detects the user's task type:
  - **Generation Tasks**: It offers to ask clarifying questions to add detail.
  - **Analysis Tasks**: It performs an automatic, non-interactive **"light refinement"** to improve the prompt's clarity.
- **Iterative Refinement**: Users can "tweak" a generated prompt with natural language commands in an interactive loop.
- **Rich Interactive UI**: The interface is built with `rich` and `questionary`, providing a polished and user-friendly experience.
- **Flexible Configuration**: Configuration is handled via a clear hierarchy: CLI arguments (`--quick`, `--refine`), environment variables, and `.env` files.

### Architecture:
The project follows a modular and modern Python architecture:
- **`src/promptheus/main.py`**: The main application entry point. It handles parsing command-line arguments (`argparse`), orchestrates the refinement workflow, and manages the user interface.
- **`src/promptheus/config.py`**: A dedicated configuration manager that detects and validates API keys and settings.
- **`src/promptheus/providers.py`**: The core abstraction layer. It defines an `LLMProvider` abstract base class and concrete implementations (`GeminiProvider`, `AnthropicProvider`).
- **`src/promptheus/prompts.py`**: Stores the system instruction templates that guide the internal LLM calls.
- **`src/promptheus/logging_config.py`**: A centralized module to configure structured logging.

## 2. Building and Running

The project uses standard Python packaging tools (`setuptools`, `pyproject.toml`).

### Installation
To set up the project for development, clone the repository and install it in editable mode.

```bash
# Install dependencies and the tool in editable mode
pip install -e .
```

### Configuration
The application requires at least one API key for an LLM provider to power its internal refinement features.
1.  Copy the example `.env` file: `cp .env.example .env`
2.  Edit the `.env` file to add your API key (e.g., `GEMINI_API_KEY=...`).

### Running the Application
The tool is installed as a command-line script named `promptheus`. Its function is to output a refined prompt.

- **Interactive Mode (REPL):**
  ```bash
  promptheus
  ```
- **Single-Shot Mode:**
  ```bash
  promptheus "Your initial prompt goes here"
  ```
- **Running via Python module (for development):**
  ```bash
  python -m promptheus.main "Your initial prompt goes here"
  ```

## 3. Development Conventions

- **Code Style**: The codebase uses modern Python (3.8+) with type hints, f-strings, and dataclasses.
- **Dependencies**: Project dependencies are managed in `pyproject.toml`.
- **Provider Abstraction**: All provider-specific logic is encapsulated within classes that inherit from `LLMProvider`.
- **UI and Logic Separation**: Core logic does not print to the console. It returns data or uses a `MessageSink` callable that the UI layer in `main.py` implements.
- **Logging**: Use the standard `logging` module for application logs. Do not use `print()` for logging.
- **Workflow for Analysis vs. Generation Tasks**:
    - **Default (Analysis)**: The tool performs a non-interactive "light refinement" using the `light_refine` provider method.
    - **Default (Generation)**: The tool offers to ask clarifying questions.
    - **`--quick`**: This flag bypasses *all* internal AI refinement steps, outputting the original prompt verbatim. It is the fastest mode and gives the user full control.
    - **`--refine`**: This flag forces the full, interactive Q&A workflow for *any* task type.
- **Testing**: The project currently lacks a formal testing suite. New features should be accompanied by tests. **TODO**: Establish a `pytest` suite.
