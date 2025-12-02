# Version Management

This document explains the version management and release process for Promptheus development.

## Release Process Overview

Promptheus uses semantic versioning (`MAJOR.MINOR.PATCH`) and treats `main` as the integration branch for upcoming releases.

- Regular feature and bugfix PRs merge into `main` without changing the version number.
- Version changes are made only when cutting a release.
- Releases are identified by annotated git tags (`vX.Y.Z`) and the corresponding version constant in code.

High-level flow:

1. Create feature branches from `main`.
2. Open PRs, get them reviewed, and merge into `main` without touching the version.
3. When you are ready to ship, create a short-lived release branch from `main`.
4. Bump the version using `scripts/inc_version.py` (see Release Workflow).
5. Open a `Release X.Y.Z` PR from the release branch into `main`.
6. After merging, create and push an annotated git tag (`vX.Y.Z`).
7. Publish artifacts (PyPI, Docker image, etc.) from the tagged commit.

## Current Version Display

The version is displayed in multiple places:

1. **CLI**: `promptheus --version` shows the current version
2. **Web UI**: Settings → About section shows version with build details:
   - Version number (e.g., `v0.2.1`)
   - Git commit hash (e.g., `(a1b2c3d4-dirty)`)
   - Build type (Development/Clean)
   - Last updated date

## Version Increment Script

Use the `scripts/inc_version.py` script to increment versions:

### Quick Commands

```bash
# Development version (adds -dev suffix)
python scripts/inc_version.py patch dev
python scripts/inc_version.py minor dev

# Release version (no suffix)
python scripts/inc_version.py patch release
python scripts/inc_version.py minor release
```

### Examples

```bash
# Current: 0.2.1
python scripts/inc_version.py patch dev
# New: 0.2.2-dev

# Current: 0.2.2-dev
python scripts/inc_version.py minor dev
# New: 0.3.0-dev

# Current: 0.3.0-dev
python scripts/inc_version.py patch release
# New: 0.3.0
```

### Options

- `patch`: Bump patch version (X.Y.Z+1)
- `minor`: Bump minor version (X.Y+1.0)
- `major`: Bump major version (X+1.0.0)
- `dev`: Add `-dev` suffix for development builds
- `release`: No suffix for stable releases
- `--no-commit`: Skip git commit

## Development Workflow

### Everyday Development

During normal development:

- Create a feature branch from `main`.
- Make changes and open a PR.
- Do not modify the version for regular PRs.
- Merge the PR into `main` after review and checks.

The `main` branch can stay ahead of the last released version; this is expected.

If you want to test a development build locally, you can optionally bump to a `-dev` version using the script, but this should not be done in every PR and should not be committed solely for local testing.

### Version Information in Web UI

The `/api/version` endpoint returns:

```json
{
  "version": "0.2.1",
  "full_version": "v0.2.1",
  "commit_hash": "a1b2c3d4",
  "commit_date": "2024-01-15 10:30:00 +0000",
  "is_dirty": true,
  "build_type": "dev",
  "github_repo": "https://github.com/abhichandra21/Promptheus",
  "timestamp": "2024-01-15T10:35:00.000Z"
}
```

- `commit_hash`: Short 8-character git hash
- `is_dirty`: True if there are uncommitted changes
- `build_type`: "dev" for dirty/dev builds, "clean" for clean releases

### Release Workflow

The release workflow collects multiple merged PRs into a single versioned release.

```bash
# Ensure working directory is clean and up to date
git checkout main
git pull

# Create a release branch
git checkout -b release/x.y.z

# Bump version for release (choose patch/minor/major)
python scripts/inc_version.py patch release

# Commit and push the release branch
git push -u origin release/x.y.z
```

Then:

1. Open a `Release x.y.z` PR from `release/x.y.z` into `main`.
2. After tests pass and the PR is merged, create and push the tag from `main`:

```bash
git checkout main
git pull
git tag -a v0.2.1 -m "Release v0.2.1"
git push origin v0.2.1
```

3. After the release is published, you can bump back to a development version if desired:

```bash
python scripts/inc_version.py patch dev
git push
```

## File Locations

- **Version constant**: `src/promptheus/constants.py`
- **Version endpoint**: `src/promptheus/web/server.py` (`/api/version`)
- **Version display**: `src/promptheus/web/static/index.html` (About section)
- **Version fetching**: `src/promptheus/web/static/app.js` (`loadVersion()`)
