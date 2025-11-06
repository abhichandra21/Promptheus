# Promptheus Development Guide

## Local Setup
```bash
pip install -e .
pip install -r requirements.txt   # optional helpers for env_validator, etc.
cp .env.example .env              # drop in provider keys
```

## Manual Smoke Tests
- Standard CLI: `promptheus "Draft a release note"`.
- Module entry point: `python -m promptheus.main --static "Smoke test"`.
- Provider sanity checks: `python env_validator.py --provider gemini`.

## Automated Tests
```bash
pytest -q
```
Add new tests under `tests/` as `test_<module>.py`. Prefer lightweight unit tests with mocked providers so the suite stays offline-friendly.

## Formatting & Style
- Python 3.8+ conventions, 4-space indent, descriptive snake_case.
- Type hints where practical (mirror `main.py` signatures).
- Keep modules under 300 lines; factor helpers into `src/promptheus/`.
- Run `black .` before committing and keep imports sorted.

## Contribution Tips
1. Keep changes focused (feature vs refactor vs docs).
2. Use short, imperative commit messages (`Add static mode docs`).
3. Include behavior notes and testing details when raising a PR.
4. Never log raw API keys; stick to masked output like the validator.

Questions? Open an issue with repro steps or drop a PR draft for early feedback. 🎯
