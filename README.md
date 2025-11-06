# Promptheus

AI-powered prompt engineering CLI tool that helps you craft better prompts through intelligent clarification and refinement.

## Overview

Promptheus uses advanced AI (Gemini, Claude, or Z.ai) to analyze your initial prompt and intelligently adapt its behavior based on your task. For creative/generation tasks, it asks clarifying questions to refine your prompt. For analysis/research tasks, it performs an automatic, non-interactive "light refinement" to improve clarity without interrupting your workflow. The result: better prompts with less friction.

## Features

- **Interactive Loop Mode**: REPL-style continuous prompt processing - run without arguments to enter interactive mode
- **Session History**: Automatically saves all refined prompts with arrow key navigation (↑/↓) in interactive mode - never lose a great prompt again! ([Learn more](HISTORY_FEATURE.md))
- **Adaptive Interaction Model**: AI detects whether you're doing analysis (research/exploration) or generation (creating content) and adapts its behavior accordingly
- **Smart Question Generation**: AI generates contextual questions for creative tasks, focuses on scoping for analysis tasks
- **Automatic Light Refinement**: Analysis prompts are automatically improved for clarity without user interaction.
- **Iterative Refinement**: Tweak your prompt iteratively with natural language modifications
- **Multi-Provider Support**: Works with Google Gemini, Anthropic Claude, or Z.ai - auto-detects based on your API keys
- **Multiple Input Methods**: Command line args, file input (`-f`, `@filename`), stdin pipe, or interactive mode
- **Quick & Refine Modes**: `--quick` to bypass all AI refinement, `--refine` to force questions for any task
- **Static Mode (MVP)**: Use predefined questions for predictable processing
- **Interactive CLI**: Beautiful terminal interface with rich formatting and easy copy/paste
- **Clipboard Integration**: Copy refined prompts directly to clipboard
- **Editor Integration**: Open refined prompts in your favorite text editor

## Installation

### Prerequisites

- Python 3.8 or higher
- API key for at least one provider:
  - **Google Gemini** (free tier available) - [Get key](https://makersuite.google.com/app/apikey)
  - **Anthropic Claude** - [Get key](https://console.anthropic.com/)
  - **Z.ai** (GLM models) - [Get token](https://z.ai/)

### Quick Start

1. Clone and install:
```bash
git clone https://github.com/abhichandra21/Promptheus.git
cd Promptheus
pip install -e .
```

2. Configure your API key(s):

**Option A: Using .env file (recommended)**
```bash
# Copy the example
cp .env.example .env

# Edit .env and add your API key
# For Gemini:
GEMINI_API_KEY=your-gemini-api-key-here

# For Claude:
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# For Z.ai:
ANTHROPIC_AUTH_TOKEN=your-zai-token-here
ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
```

**Option B: Environment variables**
```bash
# For Gemini
export GEMINI_API_KEY='your-api-key-here'

# For Claude
export ANTHROPIC_API_KEY='your-api-key-here'

# For Z.ai
export ANTHROPIC_AUTH_TOKEN='your-token-here'
export ANTHROPIC_BASE_URL='https://api.z.ai/api/anthropic'
```

3. Run it:
```bash
promptheus "Your prompt here"
```

Promptheus will auto-detect which provider to use based on available API keys. You can also specify explicitly with `--provider gemini` or `--provider anthropic`.

## Usage

Promptheus is a tool for **refining prompts**. It takes your initial idea and helps you craft a better, more effective prompt that you can then use with any LLM.

It works in two modes:

### Interactive Loop Mode (REPL)

Run without arguments to enter continuous loop mode - perfect for crafting multiple prompts:

```bash
promptheus
```

```
Welcome to Promptheus Interactive Mode!
Using provider: gemini | Model: gemini-1.5-flash
Type 'exit' or 'quit' to exit

promptheus [1]> Write a haiku about coding
# ... (processes prompt, shows refined prompt) ...

promptheus [2]> Analyze the authentication flow in auth.py
# ... (processes prompt, shows refined prompt) ...

promptheus [3]> exit
Goodbye!
```

**Interactive mode features:**
- Process unlimited prompts in one session
- No "continue?" prompts - immediately ready for next input
- **Arrow key history**: Press ↑/↓ to navigate through previous prompts
- **Special commands**:
  - `:history` - View your prompt history
  - `:load <number>` - Load a specific prompt from history
  - `:clear-history` - Clear all history
- Type `exit`, `quit`, or `q` to exit
- Press Ctrl+C to exit at any time
- Provider, model, and flags persist across all prompts in the session

### Single-Shot Mode

Provide a prompt to refine once and exit:

```bash
# Command line argument
promptheus "Write a blog post about AI"

# From file
promptheus -f my-prompt.txt
promptheus @my-prompt.txt

# From stdin
cat my-prompt.txt | promptheus
echo "My prompt" | promptheus
```

**Adaptive behavior**: Promptheus automatically detects your task type:
- **Generation tasks** (e.g., "Write a blog post"): Asks if you want clarifying questions to help refine the prompt.
- **Analysis tasks** (e.g., "Analyze this codebase"): Automatically performs a non-interactive "light refinement" to improve the prompt's clarity.

### File Input

For long or complex prompts, use file input:

**Method 1: Using `-f` flag**
```bash
promptheus -f my-prompt.txt
```

**Method 2: Using `@` syntax**
```bash
promptheus @my-prompt.txt
```

**Method 3: Pipe from stdin**
```bash
cat my-prompt.txt | promptheus
echo "My prompt" | promptheus
```

### Interaction Modes

**Default (Adaptive)**: Let AI decide the best refinement strategy based on your task.
```bash
promptheus "Your prompt"
# or in interactive mode:
promptheus
```

**Quick mode** (`-q` / `--quick`): Bypasses all AI-driven refinement (including light refinement). Outputs the original prompt verbatim, ensuring maximum speed and control.
```bash
# Single-shot
promptheus -q "Analyze this data and tell me what you find"

# Interactive mode with quick flag
promptheus -q
# All prompts in this session will bypass AI refinement
```

**Refine mode** (`-r` / `--refine`): Forces the full, interactive clarifying questions workflow for any task, including analysis.
```bash
# Single-shot
promptheus -r "Explore this codebase"

# Interactive mode with refine flag
promptheus -r
# All prompts in this session will ask clarifying questions
```

**Static mode** (`--static`): Use a predefined, static list of questions instead of AI-generated ones.
```bash
promptheus --static "My prompt"
```

### Provider Selection

**Auto-detect** (default): Uses available API key
```bash
promptheus "Your prompt"
```

**Specify provider**:
```bash
promptheus --provider gemini "Your prompt"
promptheus --provider anthropic "Your prompt"
```

**Specify model**:
```bash
promptheus --model gemini-1.5-pro "Your prompt"
promptheus --model claude-3-5-sonnet-20241022 "Your prompt"
```

### Output Options

**Copy to clipboard**:
```bash
promptheus -c "My prompt"
promptheus --copy "My prompt"
```

**Open in editor**:
```bash
promptheus -e "My prompt"
promptheus --edit "My prompt"
```

**Combine flags**:
```bash
promptheus -c -e "My prompt"              # Copy AND open in editor
promptheus -q -c @prompt.txt              # Quick mode + copy
promptheus --provider anthropic -r -c "Prompt"  # Specific provider + refine + copy
```

### Session History

Promptheus automatically saves all your refined prompts for easy recall:

**View history**:
```bash
promptheus history                        # View recent prompts
promptheus history --limit 50             # View more entries
```

**In interactive mode**:
```bash
promptheus [1]> :history                  # View history table
promptheus [2]> :load 5                   # Load prompt #5 from history
promptheus [3]> # Press ↑ to recall previous prompts
```

**Clear history**:
```bash
promptheus history --clear                # Clear all history
# or in interactive mode:
:clear-history
```

For more details, see [HISTORY_FEATURE.md](HISTORY_FEATURE.md).

### Iterative Refinement

After an initial prompt is generated, you can iteratively tweak it:

```bash
$ promptheus "Write a blog post about AI"

# ... (prompt is generated and displayed) ...

Tweak? (Enter to accept, or describe your change): make it more casual

# ... (tweaked version is displayed) ...

Tweak? (Enter to accept, or describe your change): add a call-to-action

# ... (tweaked version is displayed) ...

Tweak? (Enter to accept, or describe your change): ⏎

✓ Prompt accepted!
```

Common tweaks:
- "make it more formal/casual"
- "make it shorter/longer"
- "add examples"
- "remove the section about X"
- "emphasize Y more"

### Set Default Editor

Promptheus respects your `EDITOR` environment variable:
```bash
export EDITOR=nano  # or vim, emacs, code, etc.
```

## How It Works

### Adaptive Interaction Model

Promptheus uses an intelligent, multi-stage workflow to refine your prompt.

**1. Task Detection**
   - An initial AI call analyzes your prompt to determine the task type.
   - **Analysis tasks**: Research, exploration, investigation, understanding.
     - Example: "Explore this codebase", "Analyze data patterns"
     - **Default Behavior**: Performs an automatic, non-interactive **"light refinement"** to improve the prompt's clarity for an LLM.
   - **Generation tasks**: Creating, writing, producing content.
     - Example: "Write a blog post", "Create a function"
     - **Default Behavior**: Asks if you want to answer clarifying questions to add detail and context.

**2. Clarification Phase** (if applicable)
   - **For generation tasks**: A second AI call generates 3-6 contextual questions about audience, tone, format, and requirements.
   - **For analysis tasks with `--refine`**: The AI may ask 0-3 scoping questions (what to focus on, level of detail).
   - Questions can be text input, multiple choice, or checkbox.

**3. Refinement Phase**
   - **If questions were answered**: A third AI call combines your initial prompt with your answers to generate a final, optimized prompt.
   - **If questions were skipped**: For analysis tasks, the result of the light refinement is used. For generation tasks, the original prompt is used.

**4. Interactive Tweaking**
   - After a prompt is generated and displayed, you can iteratively refine it with simple instructions.
   - Each tweak is a new AI call that modifies the current prompt.
   - Press Enter to accept the prompt when you are satisfied.

**5. Final Output**
   - The final refined prompt is displayed in a formatted panel and as raw text for easy copying.
   - The tool's job is now done. You can take this high-quality prompt and use it with any LLM of your choice.

### Design Philosophy

**"Don't ask the user to make a choice the AI can make for them."**

- **Analysis tasks**: You don't know what you'll find, so questions about tone/format are premature. The tool defaults to improving your prompt automatically and non-interactively.
- **Generation tasks**: You have preferences to specify, so questions add value. The tool offers to ask them, but respects your choice to skip.
- **Power users**: Override the defaults with `--quick` (bypass all AI refinement) or `--refine` (force questions for any task).

## Examples

### Example 1: Interactive Mode Session

```bash
$ promptheus -q

Welcome to Promptheus Interactive Mode!
Using provider: gemini | Model: gemini-1.5-flash
Type 'exit' or 'quit' to exit

promptheus [1]> Analyze the main.py file and explain the key functions

✓ Quick mode - using original prompt without modification

╭─ Your Prompt ────────────────────────────────────────╮
│ Analyze the main.py file and explain the key        │
│ functions                                            │
╰──────────────────────────────────────────────────────╯

━━━ Raw Text (easy to copy) ━━━
Analyze and explain the key functions in the main.py file.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tweak? (Enter to accept, or describe your change): ⏎

✓ Prompt accepted!

promptheus [2]> Write a README section about testing

✓ Quick mode - using original prompt without modification

╭─ Your Prompt ────────────────────────────────────────╮
│ Write a README section about testing                │
╰──────────────────────────────────────────────────────╯

━━━ Raw Text (easy to copy) ━━━
Write a README section about testing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tweak? (Enter to accept, or describe your change): make it more detailed

⟳ Tweaking prompt (v2)...

╭─ Refined Prompt ─────────────────────────────────────╮
│ Write a comprehensive README section about testing  │
│ that includes: testing strategies, how to run       │
│ tests, test coverage expectations, and examples of  │
│ running specific test suites                        │
╰──────────────────────────────────────────────────────╯

Tweak? (Enter to accept, or describe your change): ⏎

✓ Prompt accepted!

promptheus [3]> exit
Goodbye!
```

### Example 2: Generation Task (Blog Post)

```bash
$ promptheus "Write a blog post"

Using provider: gemini | Model: gemini-1.5-flash

✓ Creative task detected with 4 clarifying questions
Ask clarifying questions to refine your prompt? (Y/n): y

Please answer the following questions to refine your prompt:

What is the main topic or subject?: AI ethics
Who is your target audience?: Tech professionals
What tone should the blog post have?: Professional, thought-provoking
Desired length?: 800-1000 words

Generating refined prompt...

╭─ Refined Prompt ─────────────────────────────────────╮
│ Write a thought-provoking blog post exploring AI     │
│ ethics for tech professionals. The post should be    │
│ 800-1000 words, maintain a professional yet          │
│ accessible tone, and address key ethical concerns... │
╰──────────────────────────────────────────────────────╯

━━━ Raw Text (easy to copy) ━━━
Write a thought-provoking blog post exploring AI ethics...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tweak? (Enter to accept, or describe your change): add real-world examples

⟳ Tweaking prompt (v2)...

╭─ Refined Prompt ─────────────────────────────────────╮
│ Write a thought-provoking blog post exploring AI     │
│ ethics for tech professionals, incorporating         │
│ real-world examples like facial recognition bias,    │
│ autonomous vehicle decisions, and content            │
│ moderation challenges. The post should be...         │
╰──────────────────────────────────────────────────────╯

Tweak? (Enter to accept, or describe your change): ⏎

✓ Prompt accepted!
```

### Example 3: Analysis Task (Code Exploration)

```bash
$ promptheus "Explore the authentication system in this codebase"

Using provider: anthropic | Model: claude-3-5-sonnet-20241022

✓ Analysis task detected - performing light refinement
  (Use --quick to skip, or --refine to force questions)


╭─ Refined Prompt ─────────────────────────────────────╮
│ Analyze and explain the authentication system        │
│ within this codebase.                                │
╰──────────────────────────────────────────────────────╯

━━━ Raw Text (easy to copy) ━━━
Analyze and explain the authentication system within this codebase.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tweak? (Enter to accept, or describe your change): ⏎

✓ Prompt accepted!
```

### Example 4: File Input with Quick Mode

```bash
$ cat complex-analysis-prompt.txt
Analyze the performance characteristics of our database queries,
identify slow queries, suggest optimizations, and explain the
impact of current indexing strategies...

$ promptheus -q -c @complex-analysis-prompt.txt

Using provider: gemini | Model: gemini-1.5-flash
Read prompt from file: complex-analysis-prompt.txt

✓ Quick mode - using original prompt without modification
...
✓ Copied to clipboard!
```

### Example 5: Refine Mode with Analysis

```bash
$ promptheus -r "Analyze this API design"

Using provider: gemini | Model: gemini-pro
--refine flag detected for analysis task
✓ Refine mode - 3 scoping questions generated

What aspects should I focus on? [Architecture, Security, Performance]
: Architecture, Security
What level of detail?: Detailed technical analysis

Generating refined prompt...

╭─ Refined Prompt ─────────────────────────────────────╮
│ Conduct a detailed technical analysis of this API    │
│ design, focusing specifically on architecture and    │
│ security aspects. Evaluate...                        │
╰──────────────────────────────────────────────────────╯
...
```

## Project Structure

```
Promptheus/
├── promptheus/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Main application logic
│   ├── config.py            # Configuration management
│   └── providers.py         # LLM provider abstractions
├── .env.example             # Example configuration file
├── README.md                # This file
├── SETUP_UNIFIED.md         # Unified setup guide
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Modern Python packaging
└── setup.py                 # Legacy setup configuration
```

## Dependencies

- `google-generativeai` - Google Gemini API client
- `anthropic` - Anthropic Claude / Z.ai API client
- `python-dotenv` - Environment variable management from .env files
- `questionary` - Interactive CLI prompts
- `pyperclip` - Clipboard functionality
- `rich` - Terminal formatting and styling

## Configuration

Promptheus can be configured via `.env` file or environment variables.

### Environment Variables

**Provider Selection** (auto-detected if not specified):
- `PROMPTHEUS_PROVIDER`: Explicit provider choice (`gemini` or `anthropic`)
- `PROMPTHEUS_MODEL`: Explicit model choice (e.g., `gemini-1.5-pro`, `claude-3-5-sonnet-20241022`)

**Google Gemini**:
- `GEMINI_API_KEY`: Your Gemini API key

**Anthropic Claude**:
- `ANTHROPIC_API_KEY`: Your Claude API key

**Z.ai (GLM models)**:
- `ANTHROPIC_AUTH_TOKEN`: Your Z.ai authentication token
- `ANTHROPIC_BASE_URL`: API base URL (set to `https://api.z.ai/api/anthropic`)

**Other**:
- `EDITOR`: Your preferred text editor (default: `vim`)

### Configuration File (.env)

Create a `.env` file in the project root:

```bash
# Provider and model (optional - auto-detected if omitted)
# PROMPTHEUS_PROVIDER=gemini
# PROMPTHEUS_MODEL=gemini-1.5-pro

# Google Gemini
GEMINI_API_KEY=your-api-key-here

# Anthropic Claude (if using)
# ANTHROPIC_API_KEY=your-api-key-here

# Z.ai (if using)
# ANTHROPIC_AUTH_TOKEN=your-token-here
# ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
```

See `.env.example` for a complete template with all options.

## Troubleshooting

### API Key Issues

**"No valid API key found"**:
```bash
# Check which API keys are set
echo $GEMINI_API_KEY
echo $ANTHROPIC_API_KEY
echo $ANTHROPIC_AUTH_TOKEN

# Set at least one
export GEMINI_API_KEY='your-key-here'
# OR
export ANTHROPIC_API_KEY='your-key-here'
```

**"401 API keys are not supported by this API"**:
- Some models require OAuth instead of API keys
- Promptheus automatically falls back to supported models
- You can explicitly specify a model: `--model gemini-1.5-flash`

### Provider Issues

**Auto-detection not working**:
```bash
# Explicitly specify provider
promptheus --provider gemini "Your prompt"
promptheus --provider anthropic "Your prompt"
```

**Wrong provider being used**:
```bash
# Check your .env file or environment variables
cat .env
env | grep -E '(GEMINI|ANTHROPIC|PROMPTHEUS)'

# Set explicit provider
export PROMPTHEUS_PROVIDER=gemini
```

### Installation Issues

**`promptheus` command not found**:
```bash
# Make sure you installed with pip
pip install -e .

# Or use Python module syntax
python -m promptheus.main "Your prompt"

# Check if it's in your PATH
which promptheus
```

**Module import errors**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or reinstall the package
pip install -e . --force-reinstall
```

### File Input Issues

**"File not found"**:
```bash
# Use absolute path
promptheus -f /full/path/to/prompt.txt

# Or relative to current directory
promptheus -f ./prompts/my-prompt.txt
```

### Clipboard Issues

If clipboard functionality doesn't work:
- **Linux**: Install `xclip` or `xsel`: `sudo apt-get install xclip`
- **macOS**: Should work out of the box
- **Windows**: Should work out of the box
- **WSL**: May require X server for clipboard access

## Development

### Running in Development Mode

```bash
# Install in editable mode
pip install -e .

# Run directly
python -m promptheus.main "Your prompt"
```

### Testing

```bash
# Test with static mode
promptheus --static "Test prompt"

# Test with all flags
promptheus -c -e --static "Test prompt"
```

## Roadmap

**Completed** ✅:
- [x] Support for multiple LLM providers (Gemini, Anthropic/Claude, Z.ai)
- [x] Configuration file support (.env)
- [x] Interactive prompt editing (iterative refinement/tweaking)
- [x] Adaptive interaction model (task type detection)
- [x] File input support (multiple methods)
- [x] Quick and refine modes
- [x] Interactive loop mode (REPL-style continuous processing)

**Planned for Future**:
- [ ] Prompt templates library
- [ ] History and favorites system
- [ ] Prompt validation and scoring
- [ ] Export to various formats (JSON, YAML, Markdown)
- [ ] Batch processing mode
- [ ] Custom system instructions
- [ ] Plugin system for custom providers

## Contributing

Contributions are welcome! Please feel free to submit issues, fork the repository, and create pull requests.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with multiple AI providers: Google Gemini, Anthropic Claude, Z.ai
- Uses the excellent `rich` library for terminal formatting
- Uses `questionary` for interactive CLI prompts
- Inspired by the need for better, more intelligent prompt engineering tools
- Design philosophy: "Don't ask the user to make a choice the AI can make for them"

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review the troubleshooting section

---

**Happy Prompting!** 🚀
