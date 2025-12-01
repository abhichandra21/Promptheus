#!/usr/bin/env python3
"""
Increment the version number in constants.py for development builds.
Usage: python scripts/inc_version.py [patch|minor|major] [dev|release]

Examples:
- python scripts/inc_version.py patch dev    # 0.2.1 -> 0.2.2-dev
- python scripts/inc_version.py minor release  # 0.2.1 -> 0.3.0
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Get project root (2 levels up from this script)
PROJECT_ROOT = Path(__file__).parent.parent
CONSTANTS_FILE = PROJECT_ROOT / "src" / "promptheus" / "constants.py"
PYPROJECT_FILE = PROJECT_ROOT / "pyproject.toml"


def get_current_version():
    """Read current version from constants.py."""
    content = CONSTANTS_FILE.read_text()
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find VERSION in constants.py")
    return match.group(1)


def update_version(new_version):
    """Update version in both constants.py and pyproject.toml."""
    # Update constants.py
    content = CONSTANTS_FILE.read_text()
    new_content = re.sub(
        r'^(VERSION\s*=\s*["\'])([^"\']+)(["\'])',
        r'\g<1>{}\g<3>'.format(new_version),
        content,
        flags=re.MULTILINE
    )
    CONSTANTS_FILE.write_text(new_content)
    print(f"Updated {CONSTANTS_FILE}: VERSION = '{new_version}'")

    # Update pyproject.toml
    pyproject_content = PYPROJECT_FILE.read_text()
    new_pyproject_content = re.sub(
        r'^(version\s*=\s*["\'])([^"\']+)(["\'])',
        r'\g<1>{}\g<3>'.format(new_version),
        pyproject_content,
        flags=re.MULTILINE
    )
    PYPROJECT_FILE.write_text(new_pyproject_content)
    print(f"Updated {PYPROJECT_FILE}: version = '{new_version}'")


def increment_version(version, bump_type):
    """Increment version based on bump type."""
    # Remove any suffix like -dev
    clean_version = version.split('-')[0]
    parts = clean_version.split('.')

    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")

    major, minor, patch = map(int, parts)

    if bump_type == 'patch':
        patch += 1
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")

    return f"{major}.{minor}.{patch}"


def commit_version_change(old_version, new_version, build_type):
    """Commit the version change to git."""
    try:
        # Add both version files to git
        subprocess.run(
            ["git", "add", "src/promptheus/constants.py", "pyproject.toml"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True
        )

        # Create commit message
        commit_msg = f"Bump version: {old_version} -> {new_version}"
        if build_type == 'dev':
            commit_msg += " (dev build)"

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True
        )

        print(f"Git commit created: {commit_msg}")

    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not commit to git: {e}")
    except FileNotFoundError:
        print("Warning: git not found, skipping commit")


def main():
    parser = argparse.ArgumentParser(
        description="Increment Promptheus version number",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "bump_type",
        choices=["patch", "minor", "major"],
        help="Type of version bump"
    )

    parser.add_argument(
        "build_type",
        choices=["dev", "release"],
        default="dev",
        nargs="?",
        help="Build type (default: dev)"
    )

    parser.add_argument(
        "--commit",
        action="store_true",
        help="Explicitly commit the version bump"
    )

    args = parser.parse_args()

    # Get current version
    current_version = get_current_version()
    print(f"Current version: {current_version}")

    # Increment version
    new_base_version = increment_version(current_version, args.bump_type)

    # Add build suffix if dev
    new_version = new_base_version
    if args.build_type == 'dev':
        new_version += '-dev'

    print(f"New version: {new_version}")

    # Update file
    update_version(new_version)

    # Commit to git only when explicitly requested
    if args.commit:
        commit_version_change(current_version, new_version, args.build_type)
    else:
        print("Skipped git commit (pass --commit to create one).")

    print(f"\n✓ Version incremented successfully!")
    print(f"  {current_version} → {new_version}")

    if args.build_type == 'dev':
        print("\nDev build notes:")
        print("  - Web UI will show commit hash and 'dirty' status")
        print("  - Use 'python scripts/inc_version.py patch release' for stable release")


if __name__ == "__main__":
    main()
