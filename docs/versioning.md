# Version Management

This document explains the version management system for Promptheus development.

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

### For Small Changes (recommended)

```bash
# After making changes
python scripts/inc_version.py patch dev
git push
```

This will:
1. Update version in `src/promptheus/constants.py`
2. Create a git commit with version bump
3. Web UI will show the new version with commit details

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

```bash
# Ensure working directory is clean
git status

# Bump version for release
python scripts/inc_version.py patch release

# Create and push tag
git tag -a v0.2.1 -m "Release v0.2.1"
git push origin v0.2.1

# After release, bump back to dev
python scripts/inc_version.py patch dev
```

## File Locations

- **Version constant**: `src/promptheus/constants.py`
- **Version endpoint**: `src/promptheus/web/server.py` (`/api/version`)
- **Version display**: `src/promptheus/web/static/index.html` (About section)
- **Version fetching**: `src/promptheus/web/static/app.js` (`loadVersion()`)