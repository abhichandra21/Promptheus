#!/usr/bin/env python3
"""Move each provider's fast/balanced/best tier to the newest matching model on models.dev.

Run by the weekly "Update model tiers" workflow, which opens a PR for a person to review.
Usage: python scripts/update_model_tiers.py [--summary-file PATH]
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

MODELS_DEV_URL = "https://models.dev/api.json"
REPO_ROOT = Path(__file__).resolve().parent.parent
PROVIDERS_JSON = REPO_ROOT / "src" / "promptheus" / "providers.json"
PROVIDERS_PY = REPO_ROOT / "src" / "promptheus" / "providers.py"

# Model ID patterns for each tier. Groq and OpenRouter host other vendors' models
# under no stable naming scheme, so their tiers are maintained by hand.
TIER_RULES = {
    "google": ("google", {
        "fast": r"gemini-\d+(\.\d+)?-flash-lite",
        "balanced": r"gemini-\d+(\.\d+)?-flash",
        "best": r"gemini-\d+(\.\d+)?-pro(-preview)?",
    }),
    "anthropic": ("anthropic", {
        "fast": r"claude-haiku-\d+(-\d{1,2})?",
        "balanced": r"claude-sonnet-\d+(-\d{1,2})?",
        "best": r"claude-opus-\d+(-\d{1,2})?",
    }),
    "openai": ("openai", {
        "fast": r"gpt-\d+(\.\d+)?-luna",
        "balanced": r"gpt-\d+(\.\d+)?-sol",
        "best": r"gpt-\d+(\.\d+)?-astra",
    }),
    "qwen": ("alibaba", {
        "fast": r"qwen\d+(\.\d+)?-flash",
        "balanced": r"qwen\d+(\.\d+)?-plus",
        "best": r"qwen\d+(\.\d+)?-max",
    }),
    "glm": ("zhipuai", {
        "fast": r"glm-\d+(\.\d+)?-flash",
        "balanced": r"glm-\d+(\.\d+)?",
    }),
}


def newest_match(models: dict, pattern: str):
    """Return the newest non-deprecated model whose ID fully matches the pattern."""
    candidates = [
        info for model_id, info in models.items()
        if re.fullmatch(pattern, model_id)
        and info.get("status") != "deprecated"
        and info.get("release_date")
        and "text" in info.get("modalities", {}).get("output", ["text"])
    ]
    if not candidates:
        return None
    # On a tie, prefer the stable release over a preview.
    return max(candidates, key=lambda info: (info["release_date"], "preview" not in info["id"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-file", type=Path, help="Write a markdown list of changes here")
    args = parser.parse_args()

    # models.dev rejects urllib's default User-Agent with a 403.
    request = urllib.request.Request(MODELS_DEV_URL, headers={"User-Agent": "promptheus-model-tiers"})
    with urllib.request.urlopen(request, timeout=60) as response:
        catalog = json.load(response)

    providers_text = PROVIDERS_JSON.read_text()
    providers_py_text = PROVIDERS_PY.read_text()
    providers = json.loads(providers_text)["providers"]
    changes = []

    for provider_id, (models_dev_id, rules) in TIER_RULES.items():
        info = providers[provider_id]
        models = catalog.get(models_dev_id, {}).get("models", {})
        old_tiers = info["tiers"]
        new_tiers = dict(old_tiers)

        for tier, pattern in rules.items():
            newest = newest_match(models, pattern)
            current = models.get(old_tiers.get(tier, ""), {})
            # Only move forward: never replace a model with an older one.
            if newest and newest["id"] != old_tiers.get(tier) and newest["release_date"] > current.get("release_date", ""):
                new_tiers[tier] = newest["id"]
                changes.append(f"- {info['display_name']} {tier}: `{old_tiers.get(tier, 'none')}` -> `{newest['id']}`")

        if new_tiers == old_tiers:
            continue

        # Edit the text in place so the rest of the file keeps its formatting.
        old_line = f'"tiers": {json.dumps(old_tiers)}'
        if providers_text.count(old_line) != 1:
            print(f"Could not find a unique tiers line for {provider_id}", file=sys.stderr)
            return 1
        providers_text = providers_text.replace(old_line, f'"tiers": {json.dumps(new_tiers)}')

        # The default model is always the balanced tier, in providers.json and the constructor.
        old_default, new_default = info["default_model"], new_tiers["balanced"]
        if new_default != old_default:
            block_start = providers_text.index(f'"{provider_id}": {{')
            old_default_line = f'"default_model": "{old_default}"'
            line_at = providers_text.index(old_default_line, block_start)
            providers_text = (
                providers_text[:line_at]
                + f'"default_model": "{new_default}"'
                + providers_text[line_at + len(old_default_line):]
            )
            old_constructor = f'model_name: str = "{old_default}"'
            if providers_py_text.count(old_constructor) != 1:
                print(f"Could not find a unique constructor default for {provider_id}", file=sys.stderr)
                return 1
            providers_py_text = providers_py_text.replace(old_constructor, f'model_name: str = "{new_default}"')

    if not changes:
        print("All model tiers are current.")
        return 0

    PROVIDERS_JSON.write_text(providers_text)
    PROVIDERS_PY.write_text(providers_py_text)
    summary = "\n".join(changes)
    print(summary)
    if args.summary_file:
        args.summary_file.write_text(summary + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
