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

## Pipe Integration & Command Substitution

Promptheus supports clean stdout/stderr separation, making it perfect for Unix pipelines and command substitution:

### Basic Piping
```bash
# Auto-quiet mode when piping
promptheus "Write a story" | cat
promptheus "Explain Docker" | less

# Save to file (questions still appear on stderr)
promptheus "Write docs" > output.txt

# Chain with other AI tools
promptheus "Create a haiku" | claude exec
promptheus "Write code" | codex run
```

### Command Substitution
```bash
# Feed refined prompt to another tool
claude "$(promptheus 'Write a technical prompt')"
codex "$(promptheus 'Generate function spec')"

# Use in scripts
REFINED=$(promptheus "Optimize this query")
echo "$REFINED" | mysql -u user -p
```

### Unix Utilities Integration
```bash
# tee: Save and display simultaneously
promptheus "Long explanation" | tee output.txt

# grep: Filter output
promptheus "List best practices" | grep -i "security"

# wc: Count words/lines
promptheus "Write essay" | wc -w

# awk/sed: Transform output
promptheus "Generate list" | sed 's/^/- /' > checklist.md

# cat: Chain multiple files
cat template.txt | promptheus | cat header.txt - footer.txt > final.txt
```

### JSON Processing
```bash
# Use jq to process JSON output
promptheus -o json "Create API schema" | jq '.endpoints'
promptheus -o json "Config template" | jq -r '.settings.database'

# Format and beautify
promptheus -o json "Data structure" | jq '.' > formatted.json
```

### Advanced Patterns
```bash
# Batch processing
cat prompts.txt | while read line; do
  promptheus "$line" >> results.txt
done

# Conditional execution
if promptheus "Check status" | grep -q "success"; then
  echo "All systems operational"
fi

# Multi-stage refinement
promptheus "Draft outline" | \
  promptheus "Expand this outline" | \
  tee expanded.txt

# Parallel processing (GNU parallel)
cat prompts.txt | parallel -j 4 "promptheus {} > output_{#}.txt"

# Error handling
promptheus "Generate code" 2> errors.log > output.txt
```

### Output Format Control
```bash
# Plain text (no markdown)
promptheus -o plain "Write haiku"

# JSON output with metadata
promptheus -o json "Create schema"

# Plain text output (default)
promptheus -o plain "Write story" > story.txt
```

# Subcommand System
Promptheus now uses a subcommand architecture for utility commands:
```bash
# Validate environment and test connections
promptheus validate
promptheus validate --test-connection
promptheus validate --providers openai,gemini

# List available models
promptheus list-models
promptheus list-models --providers openai
promptheus list-models --limit 10

# Generate environment templates
promptheus template openai,gemini
promptheus template --providers openai,anthropic

# Manage history
promptheus history
promptheus history --limit 50
promptheus history --clear
```

**Key Behaviors:**
- **Auto-quiet**: Piping automatically enables quiet mode
- **stderr for UI**: All questions and status go to stderr
- **stdout for output**: Only refined prompt on stdout
- **Non-interactive stdin**: Questions skipped when input is piped

## Interaction Styles

| Mode | Flag | When to use |
| --- | --- | --- |
| Adaptive (default) | – | Promptheus decides whether to ask clarifying questions or perform light refinement. |
| Skip Questions | `-s` / `--skip-questions` | Skip clarifying questions and improve the prompt directly using basic analysis mode. |
| Refine | `-r` / `--refine` | Force the full clarifying-question workflow even for analysis tasks. |

Mix and match with providers, models, and file input as needed, e.g. `promptheus -s -c @brief.md`.

## Provider & Model Selection
- Auto-detects which provider to use based on the API keys you have configured.
- Force a provider: `promptheus --provider gemini "Idea"`, `promptheus --provider anthropic "Idea"`, `promptheus --provider openai "Idea"`, `promptheus --provider groq "Idea"`, `promptheus --provider qwen "Idea"`, `promptheus --provider glm "Idea"`.
- Pin a model: `promptheus --model gemini-1.5-pro "Idea"`, `promptheus --model claude-3-5-sonnet-20241022 "Idea"`, `promptheus --model gpt-4o "Idea"`, `promptheus --model llama-3.1-70b-versatile "Idea"`, etc.
- Available providers: gemini, anthropic, openai, groq, qwen, glm
- List available models: `promptheus list-models` or `promptheus list-models --providers openai,gemini`

## Output Helpers
- `-c` / `--copy` – copy the refined prompt to the clipboard.
- `-o` / `--output-format` – specify output format (`plain` or `json`).
- Combine flags freely: `promptheus -s -c -o json "Pitch deck outline"`.

## Session History
- CLI commands: `promptheus history`, `promptheus history --limit 50`, `promptheus history --clear`.
- Interactive shortcuts: `/history`, `/load <n>`, `/clear-history`, plus ↑/↓ navigation.
- Additional interactive features: `/copy` to copy the last result, `/status` to view current settings.
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

### Skip Questions for Quick Analysis
```
$ promptheus -s "Analyze the main.py file and explain the key functions"
✓ Skip questions mode - improving prompt directly
╭─ Refined Prompt ───────────────────────────────╮
│ [Improved prompt shown here]                   │
╰────────────────────────────────────────────────╯
```

## Environment Template Generation

Generate environment file templates for one or more providers:

```bash
# Single provider
promptheus template openai > .env

# Multiple providers (comma-separated)
promptheus template openai,gemini,anthropic > .env
```

## Python 3.14 Compatibility

The `gemini` provider supports Python 3.14 with the unified `google-genai` SDK.
For other providers that may have compatibility issues:
1. Wait for updates as newer provider SDKs support Python 3.14
2. Use Python 3.13 or earlier if compatibility issues arise
3. Consider using virtual environments to manage different Python versions

## Interactive Features

### Keyboard Shortcuts
- **Enter**: Submit your prompt
- **Shift+Enter**: Add a new line in the prompt (multiline input)
- **Option/Alt+Enter**: Alternative multiline input
- **Ctrl+J**: Another option for multiline input
- **↑/↓ Arrow Keys**: Navigate through previous prompts
- **Tab**: Show command completions when typing `/`

### Enhanced Session Commands
In interactive mode, you can use these slash commands:

**Command Navigation:**
- `/help` - Show all available commands
- `/history` - View recent prompts
- `/load <n>` - Load a specific prompt from history
- `/clear-history` - Clear all history
- `/about` - Show version and configuration info
- `/bug` - Get help with bug reports

**Session Control:**
- `/status` - View current session settings
- `/set provider <name>` - Change AI provider mid-session
- `/set model <name>` - Change model mid-session
- `/toggle refine` - Toggle refine mode on/off
- `/toggle skip-questions` - Toggle skip-questions mode on/off

**Utility:**
- `/copy` - Copy the last refined result to clipboard

Happy prompting! 🚀
