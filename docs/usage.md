# Promptheus Usage Guide

Promptheus keeps the fun parts of prompt crafting while the AI handles the housekeeping. This guide covers the full command surface so you can stay in flow once you've memorised the quick start from the README.

## Modes at a Glance

### Interactive Loop (REPL)
- Launch with `promptheus`.
- Stay in one colorful session, reuse your provider/model/flags, and cruise through multiple prompts.
- Built-in helpers:
  - `/history`, `/load <n>`, `/clear-history`.
  - Arrow-key recall for previous prompts.
  - Type `exit`, `quit`, or hit `Ctrl+C` when you’re done.

### Single-Shot
- Provide a prompt inline (`promptheus "Write a haiku"`), from a file (`promptheus -f idea.txt` or `promptheus @idea.txt`), or via stdin (`cat idea.txt | promptheus`).
- Perfect when you already know exactly what you want.

## Input Methods
- `-f path/to/prompt.txt` – flag-based file input.
- `@path/to/prompt.txt` – shortcut syntax (alternative to `-f`).
- Standard input piping for scripted flows.

## Interaction Styles

| Mode | Flag | When to use |
| --- | --- | --- |
| Adaptive (default) | – | Promptheus decides whether to ask clarifying questions or perform light refinement. |
| Quick | `-q` / `--quick` | Bypass every AI tweak and ship the original prompt verbatim. |
| Refine | `-r` / `--refine` | Force the full clarifying-question workflow even for analysis tasks. |
| Static | `--static` | Use deterministic, predefined questions instead of AI-generated ones. |

Mix and match with providers, models, and file input as needed, e.g. `promptheus -q -c @brief.md`.

## Provider & Model Selection
- Auto-detects which provider to use based on the API keys you have configured.
- Force a provider: `promptheus --provider gemini "Idea"`, `promptheus --provider anthropic "Idea"`, `promptheus --provider openai "Idea"`, `promptheus --provider groq "Idea"`, `promptheus --provider qwen "Idea"`, `promptheus --provider glm "Idea"`.
- Pin a model: `promptheus --model gemini-1.5-pro "Idea"`, `promptheus --model claude-3-5-sonnet-20241022 "Idea"`, `promptheus --model gpt-4o "Idea"`, `promptheus --model llama-3.1-70b-versatile "Idea"`, etc.
- Available providers: gemini, anthropic, openai, groq, qwen, glm
- List available models: `python get-models.py providers` or `python get-models.py models`

## Output Helpers
- `-c` / `--copy` – copy the refined prompt to the clipboard.
- `-e` / `--edit` – open the result in your `$EDITOR`.
- Combine flags freely: `promptheus -c -e "Pitch deck outline"`.

## Session History
- CLI commands: `promptheus history`, `promptheus history --limit 50`, `promptheus history --clear`.
- Interactive shortcuts: `/history`, `/load <n>`, `/clear-history`, plus ↑/↓ navigation.
- Every refined prompt is saved automatically so you never lose that one perfect phrasing.
- History includes timestamps, task types, and both original and refined prompts for reference.

## Iterative Tweaks
After the main refinement, Promptheus will ask if you want to tweak anything:

```
Tweak? (Enter to accept, or describe your change): make it punchier
```

Use natural language (“make it more formal”, “remove the section on pricing”, “add a call-to-action”). Each tweak is a targeted AI edit. Hit Enter on an empty line to accept the current version.

## Example Workflows

### Creative Brief
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

### Quick Technical Scan
```
$ promptheus -q "Analyze the main.py file and explain the key functions"
✓ Quick mode – using original prompt without modification
╭─ Your Prompt ──────────────────────────────────╮
│ Analyze the main.py file and explain the key   │
│ functions                                      │
╰────────────────────────────────────────────────╯
```

## Editor Preferences

Promptheus opens editors via the `EDITOR` environment variable. Set it once and forget it:

```bash
export EDITOR="code --wait"  # or nano, vim, emacs, etc.
```

## Python 3.14 Compatibility

The `gemini` provider supports Python 3.14 with the unified `google-genai` SDK.
For other providers that may have compatibility issues:
1. Wait for updates as newer provider SDKs support Python 3.14
2. Use Python 3.13 or earlier if compatibility issues arise
3. Consider using virtual environments to manage different Python versions

Happy prompting! 🚀
