# Promptheus Troubleshooting

Need a quick fix? Start here before diving into a rabbit hole.

## Provider & API Keys

**Auto-detect isn’t picking anything up**
```bash
promptheus --provider gemini "Prompt"
promptheus --provider anthropic "Prompt"
promptheus --provider openai "Prompt"
promptheus --provider groq "Prompt"
promptheus --provider qwen "Prompt"
promptheus --provider glm "Prompt"
```

**Wrong provider keeps showing up**
```bash
cat .env
env | grep -E '(GEMINI|ANTHROPIC|OPENAI|GROQ|DASHSCOPE|ZAI|PROMPTHEUS)'
export PROMPTHEUS_PROVIDER=gemini
```

**Unsure whether your keys work?**
```bash
python env_validator.py --provider gemini
python env_validator.py --provider anthropic
python env_validator.py --provider openai
python env_validator.py --provider groq
python env_validator.py --provider qwen
python env_validator.py --provider glm
python env_validator.py --test-connection  # to test actual API connectivity
```

## Installation & Runtime

**`promptheus` command not found**
```bash
pip install -e .
python -m promptheus.main "Prompt"
which promptheus
```

**Import errors or missing dependencies**
```bash
pip install -r requirements.txt
pip install -e . --force-reinstall
```

## File Input

**“File not found” errors**
```bash
promptheus -f /absolute/path/to/prompt.txt
promptheus -f ./relative/path/prompt.txt
```

## Clipboard Helpers
- Linux: install `xclip` or `xsel` (`sudo apt-get install xclip`).
- macOS & Windows: should work out of the box.
- WSL: may require an X server for clipboard access.

## Interactive Mode

**Multiline input not working**
- Use Shift+Enter for new lines in prompts
- Alternative: Option/Alt+Enter or Ctrl+J
- If terminal is not responding, try plain mode: `promptheus --plain`

**Slash commands not working**
- All commands start with `/` (not `:` anymore)
- Use `/help` to see all available commands
- Use Tab for command completions

**Session management**
- Use `/status` to see current provider/model settings
- Change provider in session: `/set provider gemini`
- Change model in session: `/set model gpt-4o`
- Toggle modes: `/toggle refine` or `/toggle quick`

Still stuck? Open an issue with the command you ran, the flags you used, and any stack trace so we can reproduce it quickly.
