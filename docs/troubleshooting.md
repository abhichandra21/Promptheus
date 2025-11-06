# Promptheus Troubleshooting

Need a quick fix? Start here before diving into a rabbit hole.

## Provider & API Keys

**Auto-detect isn’t picking anything up**
```bash
promptheus --provider gemini "Prompt"
promptheus --provider anthropic "Prompt"
```

**Wrong provider keeps showing up**
```bash
cat .env
env | grep -E '(GEMINI|ANTHROPIC|PROMPTHEUS)'
export PROMPTHEUS_PROVIDER=gemini
```

**Unsure whether your keys work?**
```bash
python env_validator.py --provider gemini
python env_validator.py --provider anthropic
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

Still stuck? Open an issue with the command you ran, the flags you used, and any stack trace so we can reproduce it quickly.
