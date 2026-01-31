# Release Process Documentation

This document describes the release process for both the backend integration and frontend card.

## Overview

Both `alarm_clock_backend/` and `alarm_clock_card/` have automated release workflows that handle version management, changelog generation, and GitHub release creation.

## Quick Release Guide

### For Both Repositories

Creating a release is the same process for both:

```bash
# 1. Ensure all changes are committed
git status

# 2. Update CHANGELOG.md with release notes
vim CHANGELOG.md  # or your preferred editor

# 3. Commit the changelog
git add CHANGELOG.md
git commit -m "Update CHANGELOG for v1.0.10"

# 4. Create and push the tag
git tag v1.0.10
git push origin v1.0.10

# 5. Watch the GitHub Actions workflow create the release
# Visit: https://github.com/[owner]/[repo]/actions
```

## What Happens Automatically

### Backend (alarm_clock_backend)

When you push a tag like `v1.0.10`, the release workflow:

1. **Updates Version**: Modifies `custom_components/alarm_clock/manifest.json`
   ```json
   {
     "version": "1.0.10"
   }
   ```

2. **Creates Package**: Generates `alarm_clock.zip` containing:
   ```
   alarm_clock/
   ├── __init__.py
   ├── manifest.json
   ├── coordinator.py
   └── [all other integration files]
   ```

3. **Generates Changelog**: Extracts commits since last tag

4. **Creates GitHub Release**: With:
   - Release title: "Release 1.0.10"
   - Changelog in description
   - `alarm_clock.zip` attached
   - Installation instructions

### Frontend (alarm_clock_card)

When you push a tag like `v1.0.10`, the release workflow:

1. **Updates Versions**: Modifies both files
   - `package.json`: Updates version field
   - `alarm-clock-card.js`: Updates CARD_VERSION constant

2. **Generates Changelog**: Extracts commits since last tag

3. **Creates GitHub Release**: With:
   - Release title: "Release 1.0.10"
   - Changelog in description
   - `alarm-clock-card.js` attached
   - Installation instructions

## Version Management

### Backend
- **Source of Truth**: `custom_components/alarm_clock/manifest.json`
- **Validation**: `tests/check_versions.py`
- **Format**: Semantic versioning (e.g., "1.0.10")

### Frontend
- **Source of Truth**: `package.json`
- **Also Updated**: `alarm-clock-card.js` (CARD_VERSION constant)
- **Validation**: 
  - `tests/check-versions.js`
  - `tests/version-consistency.test.js`
- **Format**: Semantic versioning (e.g., "1.0.10")

## Semantic Versioning

Follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes (e.g., 1.0.0 → 2.0.0)
- **MINOR**: New features, backwards compatible (e.g., 1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, backwards compatible (e.g., 1.0.0 → 1.0.1)

## Changelog Format

Use this format in CHANGELOG.md:

```markdown
## [1.0.10] - 2026-01-31

### Added
- New feature description
- Another feature

### Changed
- Modified behavior description

### Fixed
- Bug fix description

### Security
- Security vulnerability fix
```

## Pre-Release Checklist

Before creating a release:

- [ ] All tests pass locally
  - Backend: `pytest tests/`
  - Frontend: `npm test`
- [ ] Code quality checks pass
  - Backend: `ruff check`, `black --check`, `isort --check`
  - Frontend: `npm run lint`
- [ ] Version checks pass
  - Backend: `python tests/check_versions.py`
  - Frontend: `npm run check-versions`
- [ ] CHANGELOG.md updated with release notes
- [ ] Documentation updated if needed
- [ ] All changes committed and pushed

## Manual Release (If Workflow Fails)

If the automated workflow fails, you can create a release manually:

### Backend

```bash
# Update version
vim custom_components/alarm_clock/manifest.json

# Create package
cd custom_components
zip -r ../alarm_clock.zip alarm_clock
cd ..

# Create GitHub release manually via web UI
# Upload alarm_clock.zip
```

### Frontend

```bash
# Update versions
vim package.json
vim alarm-clock-card.js  # Update CARD_VERSION

# Create GitHub release manually via web UI
# Upload alarm-clock-card.js
```

## Troubleshooting

### Workflow Doesn't Trigger
- Ensure the tag follows the pattern `v*` (e.g., `v1.0.10`)
- Check you pushed the tag: `git push origin v1.0.10`
- Verify workflow file exists: `.github/workflows/release.yml`

### Version Mismatch Errors
- Backend: Run `python tests/check_versions.py`
- Frontend: Run `npm run check-versions`
- Fix any mismatches and commit

### Release Package Missing Files
- Backend: Ensure all files are in `custom_components/alarm_clock/`
- Frontend: Ensure `alarm-clock-card.js` exists in root

## Release Workflow Files

### Backend: `.github/workflows/release.yml`
- Trigger: Push tag matching `v*`
- Updates: `manifest.json`
- Creates: `alarm_clock.zip`
- Publishes: GitHub release

### Frontend: `.github/workflows/release.yml`
- Trigger: Push tag matching `v*`
- Updates: `package.json`, `alarm-clock-card.js`
- Publishes: GitHub release with card file

## Testing a Release

After creating a release:

### Backend
1. Download `alarm_clock.zip` from GitHub release
2. Extract to test Home Assistant instance
3. Restart Home Assistant
4. Verify integration loads and works

### Frontend
1. Download `alarm-clock-card.js` from GitHub release
2. Copy to test Home Assistant `www/` folder
3. Clear browser cache (Ctrl+Shift+R)
4. Verify card loads and works

## Questions?

If you encounter issues with the release process, please open an issue on GitHub.
