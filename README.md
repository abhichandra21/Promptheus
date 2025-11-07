# Promptheus

Promptheus is the AI wing-person for prompt engineers, analysts, and creative teams. Drop in a rough prompt and it will adapt to your task, ask smart questions when they add value, lightly polish analysis prompts, and keep every iteration close at hand.

## 🔥 ZSH Tab Completion

Enhance your Promptheus experience with intelligent tab completion!

### Quick Installation
```bash
# Navigate to promptheus directory
cd /path/to/promptheus

# Install completion
./install-completion.sh

# Restart terminal or source .zshrc
source ~/.zshrc
```

### Features
- **Smart Provider & Model Completion**: `promptheus --provider <TAB>`
- **File Completion**: `promptheus -f <TAB>` with .txt priority
- **@filename Syntax**: `promptheus @my_prompt<TAB>`
- **Context-Aware Options**: Different completions based on context
- **History Commands**: `promptheus history <TAB>`

**Example Usage:**
```bash
promptheus --provider gemini --model <TAB>
# → gemini-2.5-pro, gemini-2.5-flash, etc.

promptheus -f my_prompt.txt<TAB>
# → File completion with .txt priority

promptheus history --<TAB>
# → --clear, --limit
```

📖 See [COMPLETION.md](COMPLETION.md) for detailed documentation.

## Known Issues

### Python 3.14 Compatibility
The `gemini` provider now supports Python 3.14 with the unified `google-genai` SDK and automatic API key type detection.
For other providers that may have compatibility issues:

1. **Wait for updates** - newer provider SDKs will eventually support Python 3.14
2. **Downgrade to Python 3.13**:
   ```bash
   pyenv install 3.13
   pyenv local 3.13
   pip install -e .
   ```
3. **Use Python virtual environments** to manage different Python versions for different projects

## Why you'll enjoy it
- Adaptive workflow that knows when to quiz you and when to stay quiet.
- Interactive loop with REPL history, arrow-key recall, and inline tweaks.
- Single-shot mode that plays nicely with stdin, files, and scripts.
- Multi-provider setup (Gemini, Claude, OpenAI, Groq, Qwen, GLM) plus clipboard and editor helpers.
- Natural-language tweak loop so you can say “make it spicier” instead of editing Markdown.

## Quick start
1. Install:
   ```bash
   pip install -e .[dev]
   pip install -r requirements.txt  # optional extras for env_validator
   ```
2. Configure at least one provider key (Gemini, Claude, OpenAI, Groq, Qwen, or GLM):
   ```bash
   cp .env.example .env
   # add GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GROQ_API_KEY,
   # DASHSCOPE_API_KEY, or ZAI_API_KEY (+ optional base URLs)
   ```
3. Sanity check credentials (recommended):
   ```bash
   python env_validator.py --provider gemini
   python env_validator.py --test-connection  # to test actual API connectivity
   ```
4. Prompt away:
   ```bash
   promptheus "Draft an onboarding email"
   ```

## Pick your flow
- **Interactive loop** – run `promptheus`, stay in one colorful session, reuse providers/models/flags, and cruise through prompts. Use `:history`, `:load <n>`, `:clear-history`, or ↑/↓ to revisit earlier ideas.
- **Single shot** – `promptheus "Write a README intro"`, `promptheus -f idea.txt`, or `cat idea.txt | promptheus` when scripting.
- Promptheus detects creative vs analysis work and either asks clarifying questions or performs a light refinement. Override with flags any time.

## Favorite flags

| Flag | What it does |
| --- | --- |
| `-q` / `--quick` | Skip every AI touch-up and ship the original prompt. |
| `-r` / `--refine` | Force the full clarifying-question workflow, even for analysis. |
| `--static` | Use a deterministic set of questions (great for demos). |
| `-c` / `--copy` | Copy the final prompt to your clipboard. |
| `-e` / `--edit` | Pop the result into your `$EDITOR`. |
| `history` | Browse and reuse previous prompts via CLI command. |
| `:history`, `:load <n>` | Interactive shortcuts for history management. |

See `docs/usage.md` for the deep dive, transcripts, and tweak mechanics.

## Providers & models
Promptheus auto-detects whichever provider keys you’ve configured, but you can pin them explicitly:

```bash
promptheus --provider gemini --model gemini-1.5-pro "Pitch deck outline"
promptheus --provider anthropic --model claude-3-5-sonnet-20241022 "Security review"
```

Supports Gemini, Claude, OpenAI, Groq, Qwen, and GLM end-to-end with zero restarts or config edits.

## History Management
Browse and manage your prompt history:
- CLI command: `promptheus history` or `promptheus history --limit 50`
- Interactive commands: `:history`, `:load <n>`, `:clear-history`
- History is automatically saved for each prompt refinement

## Docs & helpful links
- `docs/usage.md` – full command surface, examples, tweak flows.
- `docs/troubleshooting.md` – API key fixes, install tips, clipboard helpers.
- `docs/development.md` – setup, formatting, tests, and contribution guidance.
- `env_validator.py` – run before big demos to ensure keys are live.
- `get-models.py` – helper script to list available providers and models.

## Contributing & support
- Follow the Python 3.8+ style already used in `src/promptheus/`, keep modules focused (<300 LOC), and run `black .`.
- Tests live in `tests/`; run `pytest -q` and add coverage for new behaviors.
- Open issues or PRs with repro steps, transcripts, or screenshots when changing CLI output.

MIT licensed. Built with `rich`, `questionary`, and a lot of prompt perfectionism. Have fun, stay curious, and happy prompting! 🚀
