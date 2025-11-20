# Repository Guidelines

## Project Structure & Module Organization
Runtime code lives under `src/promptheus/`. `main.py` owns the CLI entry point, `providers.py` wraps the adapters for multiple LLM providers (Gemini, Claude, OpenAI, Groq, Qwen, GLM), `config.py` manages environment-driven settings, and `history.py` persists prompt sessions. Shared assets (e.g., `models.json`, `logging_config.py`, `utils.py`) sit alongside. Tests mirror this layout in `tests/`, while helper tools such as `sample_prompts.txt` remain at the repository root. Add new runtime modules inside `src/promptheus/` and keep provider-specific helpers beside existing integrations to simplify discovery.

## Build, Test, and Development Commands
Install dependencies in editable mode before contributing:
```bash
pip install -e .[dev]
pip install -r requirements.txt  # extras for env_validator
```
Run the CLI locally with either binary or module syntax:
```bash
promptheus "Draft an onboarding email"
python -m promptheus.main --skip-questions "Smoke test"

# Quiet mode for scripting (clean stdout/stderr separation)
promptheus "Generate a report" > output.txt  # Auto-quiet when piping
promptheus "Write code" | cat  # Auto-quiet when piping

# Different output formats
promptheus -o json "Create function" | jq .
promptheus -o plain "Write haiku"
```
Validate credentials before hitting remote APIs:
```bash
promptheus validate --providers google
promptheus validate --test-connection  # to test actual API connectivity
```

## Coding Style & Naming Conventions
Target Python 3.8+ with four-space indentation, `snake_case` for functions/variables, and `CapWords` for classes. Mirror existing type hints (see `main.py`) and keep modules under ~300 lines by extracting helpers where needed. Format with `black .`, keep imports sorted, and align terminal output with the `rich` styles already used in the CLI panels/table helpers.

## Testing Guidelines
Tests live in `tests/` and follow the `test_<module>.py` naming pattern. Prefer fast, offline unit tests that stub provider calls rather than exercising live APIs. Run `pytest -q` before sending a PR, and supplement with a manual CLI smoke test (`promptheus --skip-questions "Smoke test"`) when you touch interactive flows or history features.

## Commit & Pull Request Guidelines
Use concise, imperative commit messages (e.g., `Add OpenAI provider guard`, `Tighten question validation`). PRs should summarize behavioral changes, reference related issues, list tests run, and include CLI transcripts or screenshots whenever user-facing output changes. Keep changes focused—split feature work and refactors into separate PRs for easier review.

## Security & Configuration Tips
Store provider secrets in `.env` (bootstrap from `.env.example`) and never log raw tokens. Run `promptheus validate` after updating credentials to ensure required keys are present. Honor the default timeout settings in `constants.py`, and mask sensitive values when printing exceptions (use `sanitize_error_message` to stay consistent).

## Supported Providers
Promptheus supports 6 major LLM providers:
- **Google** (formerly Gemini) - using `GOOGLE_API_KEY`
- **Claude** (Anthropic) - using `ANTHROPIC_API_KEY`
- **OpenAI** - using `OPENAI_API_KEY`
- **Groq** - using `GROQ_API_KEY`
- **Qwen** (Alibaba/DashScope) - using `DASHSCOPE_API_KEY`
- **GLM** (Zhipu) - using `ZHIPUAI_API_KEY`

Each provider has its own configuration in `models.json` and respective adapter in `providers.py`.

## History Management
The system automatically tracks all prompt refinements in a local history file. Users can access:
- CLI command: `promptheus history`
- Interactive commands: `/history`, `/load <n>`, `/clear-history`
- History includes timestamps, task types, and both original and refined prompts.

## Quiet Mode & Piping
Promptheus supports clean stdout/stderr separation for scripting and piping:
- **Auto-quiet mode**: Automatically enabled when stdout is not a TTY (e.g., when piping)
- **Prompt processing unchanged**: Questions are still asked based on LLM's decision, regardless of output mode
- **Output formats**: `-o/--output-format` supports `plain` (default) and `json`
- **Behavior**: In quiet mode, all UI (status, warnings, spinners, questions) goes to stderr, only the refined prompt goes to stdout
- **Limitations**: Interactive tweaks and clipboard (`--copy`) are disabled in quiet mode
