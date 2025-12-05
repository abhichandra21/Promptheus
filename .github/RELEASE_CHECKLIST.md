# Release Checklist

**Release Version:** ____________
**Release Type:** [ ] Patch [ ] Minor [ ] Major
**Release Date:** ____________
**Release Manager:** ____________

---

## Phase 1: Pre-Release Preparation

### Environment Check
- [ ] Working directory is clean (`git status`)
- [ ] On `main` branch with latest changes (`git checkout main && git pull`)
- [ ] All dependencies installed (`poetry install --no-root`)
- [ ] All tests passing locally (`poetry run pytest -q`)

### Release Planning
- [ ] Reviewed all commits since last release
  ```bash
  git log $(git describe --tags --abbrev=0)..HEAD --oneline
  ```
- [ ] Determined release type: **____________** (patch/minor/major)
- [ ] Identified all changes for CHANGELOG
- [ ] Reviewed open issues and PRs

---

## Phase 2: Release Branch Creation

### Branch Setup
- [ ] Created release branch: `release/____________`
  ```bash
  git checkout -b release/X.Y.Z
  ```
- [ ] Verified on correct branch (`git branch --show-current`)

### Documentation Updates
- [ ] Updated `CHANGELOG.md` with:
  - [ ] Version number and date
  - [ ] Added section (new features)
  - [ ] Changed section (modifications)
  - [ ] Fixed section (bug fixes)
  - [ ] Environment variables (if any)
  - [ ] Breaking changes (if any)
- [ ] Reviewed CHANGELOG for accuracy and completeness

---

## Phase 3: Version Bump and Testing

### Version Update
- [ ] Bumped version number:
  ```bash
  python scripts/inc_version.py [patch|minor|major] release --commit
  ```
- [ ] Verified version in `src/promptheus/constants.py`: **____________**
- [ ] Verified version in `pyproject.toml`: **____________**
- [ ] Version commit created automatically

### Testing
- [ ] All automated tests passing:
  ```bash
  poetry run pytest -q
  ```
- [ ] Telemetry tests passing (if applicable):
  ```bash
  poetry run pytest tests/test_telemetry_e2e.py -v
  poetry run pytest tests/test_telemetry_summary.py -v
  ```
- [ ] Manual smoke tests completed:
  - [ ] `promptheus --version` shows correct version
  - [ ] `promptheus --help` works
  - [ ] `promptheus --skip-questions "test"` works
  - [ ] Interactive mode works
  - [ ] Web UI works (`promptheus web`)
  - [ ] MCP server works (`promptheus mcp`)
  - [ ] Telemetry commands work (`promptheus telemetry summary`)

### Build Verification
- [ ] Package builds successfully:
  ```bash
  poetry build
  ```
- [ ] Build artifacts exist in `dist/`:
  - [ ] `promptheus-X.Y.Z.tar.gz`
  - [ ] `promptheus-X.Y.Z-py3-none-any.whl`

### Local Installation Test
- [ ] Created test virtual environment
- [ ] Installed from local build successfully
- [ ] Verified installation works
- [ ] Cleaned up test environment

---

## Phase 4: Release PR

### PR Creation
- [ ] Pushed release branch to GitHub:
  ```bash
  git push -u origin release/X.Y.Z
  ```
- [ ] Created Pull Request:
  - [ ] Title: `Release X.Y.Z`
  - [ ] Base: `main`
  - [ ] Compare: `release/X.Y.Z`
  - [ ] Description includes summary and testing checklist
  - [ ] Linked related issues (if any)

### PR Verification
- [ ] CI/CD workflows passing:
  - [ ] Docker tests
  - [ ] Publish workflow (dry-run if applicable)
  - [ ] GitHub Pages deployment (if docs changed)
- [ ] Code review completed (if applicable)
- [ ] All comments addressed
- [ ] PR approved (if team has reviewers)

---

## Phase 5: Merge and Tag

### Merge
- [ ] PR merged into `main`
- [ ] Release branch preserved (not deleted yet)

### Git Tag Creation
- [ ] Switched to main and pulled latest:
  ```bash
  git checkout main && git pull origin main
  ```
- [ ] Verified version is correct in merged code
- [ ] Created annotated tag:
  ```bash
  git tag -a vX.Y.Z -m "Release vX.Y.Z"
  ```
- [ ] Verified tag created:
  ```bash
  git tag -l -n9 vX.Y.Z
  ```
- [ ] Pushed tag to trigger publish:
  ```bash
  git push origin vX.Y.Z
  ```

---

## Phase 6: PyPI Publication

### Automated Publish
- [ ] GitHub Actions "Publish Python Package" workflow triggered
- [ ] Workflow completed successfully
- [ ] All workflow steps passed:
  - [ ] Checkout code
  - [ ] Set up Python
  - [ ] Install Poetry
  - [ ] Install dependencies
  - [ ] Build package
  - [ ] Publish to PyPI

### PyPI Verification
- [ ] Waited 2-3 minutes for PyPI processing
- [ ] Package visible at: https://pypi.org/project/promptheus/
- [ ] Version **____________** is latest on PyPI
- [ ] Package metadata correct (description, links, etc.)

### Installation Test from PyPI
- [ ] Created fresh virtual environment
- [ ] Installed from PyPI:
  ```bash
  pip install promptheus
  ```
- [ ] Verified version:
  ```bash
  promptheus --version  # Should show: X.Y.Z
  ```
- [ ] Tested basic functionality
- [ ] Cleaned up test environment

---

## Phase 7: GitHub Release

### Release Creation
- [ ] Navigated to GitHub Releases
- [ ] Clicked "Draft a new release"
- [ ] Selected tag: `vX.Y.Z`
- [ ] Release title: `Promptheus vX.Y.Z - <Feature Summary>`
- [ ] Release description formatted (copied from CHANGELOG)
- [ ] Checked "Set as the latest release"
- [ ] Published release

### Release Verification
- [ ] Release page displays correctly
- [ ] CHANGELOG visible in release notes
- [ ] Release marked as "Latest"
- [ ] Download links work (if applicable)

---

## Phase 8: Post-Release Tasks

### Documentation
- [ ] Documentation site updated (if needed)
- [ ] GitHub Pages deployed successfully
- [ ] Documentation reflects new version features

### Communication
- [ ] Release announced (if applicable):
  - [ ] GitHub Discussions
  - [ ] README updates
  - [ ] Social media
  - [ ] Email to contributors

### Cleanup
- [ ] Deleted remote release branch:
  ```bash
  git push origin --delete release/X.Y.Z
  ```
- [ ] Deleted local release branch:
  ```bash
  git branch -d release/X.Y.Z
  ```

### Next Development Cycle
- [ ] Bumped to next dev version (optional):
  ```bash
  python scripts/inc_version.py patch dev --commit
  git push origin main
  ```

---

## Rollback Plan (If Needed)

**Issue Discovered:** ____________________________________________

**Severity:** [ ] Critical [ ] Major [ ] Minor

**Action Taken:**
- [ ] Yanked PyPI release
- [ ] Published patch version: ____________
- [ ] Reverted commits
- [ ] Updated documentation

**Resolution:** ____________________________________________

---

## Sign-Off

**Release Manager:** ________________________ **Date:** ____________

**Verification:** All checklist items completed successfully

**Notes:**
_Add any additional notes about this release_

---

## Quick Command Reference

```bash
# Create release branch
git checkout -b release/X.Y.Z

# Bump version
python scripts/inc_version.py [patch|minor|major] release --commit

# Test
poetry run pytest -q

# Build
poetry build

# Push branch
git push -u origin release/X.Y.Z

# After PR merge
git checkout main && git pull origin main
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z

# Cleanup
git push origin --delete release/X.Y.Z
git branch -d release/X.Y.Z
```

---

**Template Version:** 1.0
**Last Updated:** 2025-12-05
