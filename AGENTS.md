# Repository Guidelines

## Project Structure & Module Organization
Promptheus's core logic lives in `src/promptheus/`. `main.py` drives the CLI entry point exposed as `promptheus`, `providers.py` wraps the Gemini, Claude, and Z.ai clients, and `config.py` centralizes runtime settings. Support tools such as `env_validator.py` (for API key checks) and sample prompt assets sit at the repository root. Place new modules under `src/promptheus/` and group provider-specific helpers alongside existing integrations to keep discovery simple.

## Build, Test, and Development Commands
Install dependencies in editable mode before hacking:
```bash
pip install -e .
pip install -r requirements.txt  # optional extras used by env_validator
```
Run the CLI locally with either the console binary or the module:
```bash
promptheus "Draft an onboarding email"
python -m promptheus.main --static "Test prompt"
```
Use `python env_validator.py --provider gemini` to confirm credentials before exercising networked flows.

## Coding Style & Naming Conventions
Follow standard Python 3.8+ conventions: four-space indentation, descriptive snake_case for functions and variables, CapWords for classes, and explicit type hints where practical (mirroring existing signatures in `main.py`). Keep modules under 300 lines by extracting helpers into focused files inside `promptheus/`. Format contributions with `black .` and ensure imports remain sorted; align console output with `rich` styling already in use.

## Testing Guidelines
Automated coverage is still light; new functionality should arrive with `pytest` suites under a top-level `tests/` package (mirror the runtime structure). Name files `test_<module>.py`, use fixtures to stub provider calls, and prefer offline unit tests over live API calls. Run the suite with `pytest -q` and supplement with manual smoke checks via `promptheus --static "Smoke test"` for interactive flows.

## Commit & Pull Request Guidelines
Adopt the existing concise, imperative commit style (e.g., `Fix --refine flag logic`, `Integrate iterative refinement feature`). Each PR should include a brief summary of behavior changes, testing notes, and linked issues. Provide screenshots or terminal transcripts when altering CLI output. Keep PRs focused; split refactors and feature work into separate changesets to ease review.

## Security & Configuration Tips
Store provider secrets in `.env` (see `.env.example`) and never commit them. Run `env_validator.py` before submitting to confirm required keys resolve. Respect the default timeouts and avoid logging full credential values; mask tokens in debug prints just as the validator does.
