# Repository Split Summary

This document summarizes the splitting of the Alarm Clock integration into two separate folders, ready to be used as independent repositories.

## Folder Structure

### alarm_clock_backend/
Backend integration for Home Assistant (Python)

**Contents:**
- `custom_components/alarm_clock/` - Main integration code
  - All Python modules (coordinator, state_machine, entities, etc.)
  - manifest.json (backend configuration)
  - services.yaml, strings.json, translations
  - **NOTE**: alarm-clock-card.js has been removed (now in frontend)
- `tests/` - Backend tests (Python/pytest)
  - All integration tests
  - Test configuration and fixtures
- `requirements*.txt` - Python dependencies
- `pyproject.toml` - Project configuration for Python tools
- `README.md` - Backend-specific documentation
- `CHANGELOG.md` - Full changelog (shared)
- `LICENSE` - MIT license (shared)
- `hacs.json` - HACS integration type
- `info.md` - Short description for HACS
- `.github/workflows/` - Backend CI workflows
  - tests.yml - Integration tests
  - validate.yml - Hassfest validation
  - hacs-validation.yml - HACS validation
  - release.yml - Release automation
  - dependabot.yml - Dependency updates

**Key Changes:**
1. Removed frontend/lovelace dependencies from manifest.json
2. Updated __init__.py to remove card registration logic
3. Removed JavaScript card file reference
4. Updated tests to remove card version checks
5. Simplified check_versions.py to only check manifest

### alarm_clock_card/
Frontend Lovelace card for Home Assistant (JavaScript)

**Contents:**
- `alarm-clock-card.js` - Main card implementation
- `tests/` - Frontend tests (JavaScript/Vitest)
  - Version consistency tests
  - Global safety tests
  - Duplicate registration tests
  - Import safety tests
- `package.json` - NPM package configuration
- `package-lock.json` - Locked dependencies
- `vitest.config.js` - Test configuration
- `README.md` - Card-specific documentation
- `CHANGELOG.md` - Full changelog (shared)
- `LICENSE` - MIT license (shared)
- `hacs.json` - HACS plugin type
- `info.md` - Short description for HACS
- `.github/workflows/` - Frontend CI workflows
  - test-frontend.yml - Frontend tests
  - release.yml - Release automation ✨ NEW
  - hacs-validation.yml - HACS validation ✨ NEW
  - dependabot.yml - NPM dependency updates ✨ UPDATED

**Key Changes:**
1. Updated package.json name to "alarm-clock-card"
2. Updated package.json repository URL
3. Updated vitest.config.js to use local paths
4. Updated test-frontend.yml workflow paths
5. Simplified check-versions.js to check package.json vs card file
6. **Added release workflow for automated GitHub releases** ✨
7. **Added HACS validation workflow** ✨
8. **Updated dependabot to use npm instead of pip** ✨
- `package-lock.json` - Locked dependencies
- `vitest.config.js` - Test configuration
- `README.md` - Card-specific documentation
- `CHANGELOG.md` - Full changelog (shared)
- `LICENSE` - MIT license (shared)
- `hacs.json` - HACS plugin type
- `info.md` - Short description for HACS
- `.github/workflows/` - Frontend CI workflows
  - test-frontend.yml - Frontend tests

**Key Changes:**
1. Updated package.json name to "alarm-clock-card"
2. Updated package.json repository URL
3. Updated vitest.config.js to use local paths
4. Updated test-frontend.yml workflow paths
5. Simplified check-versions.js to check package.json vs card file

## File Organization

All files have been preserved from the original repository and organized into appropriate folders:

**Backend-specific files:**
- Python code (*.py)
- Python tests
- Python dependencies
- Backend workflows

**Frontend-specific files:**
- JavaScript card (alarm-clock-card.js)
- Frontend tests
- NPM dependencies
- Frontend workflow

**Shared files (copied to both):**
- LICENSE
- CHANGELOG.md
- .gitignore

**Created/customized for each:**
- README.md (tailored content)
- info.md (tailored content)
- hacs.json (different types)

## Independence

Both folders are now ready to be used as independent repositories:

### Backend (alarm_clock_backend)
- Can be installed via HACS as an Integration
- Provides all backend functionality (alarms, services, events)
- No longer depends on frontend/lovelace for core functionality
- Works independently without the card (entities can be used in any Lovelace card)

### Frontend (alarm_clock_card)
- Can be installed via HACS as a Lovelace Plugin
- Requires the backend integration to be installed separately
- Provides beautiful UI for alarm management
- References backend integration in documentation

## Installation Instructions

Users will now install both components separately:

1. **Backend Installation** (Required)
   - HACS → Integrations → Add Repository
   - Search for "Alarm Clock"
   - Install
   - Settings → Devices & Services → Add Integration

2. **Frontend Installation** (Optional)
   - HACS → Frontend → Add Repository
   - Search for "Alarm Clock Card"
   - Install
   - Add card to Lovelace dashboard

## Testing

### Backend Tests
```bash
cd alarm_clock_backend
pytest tests/
```

### Frontend Tests
```bash
cd alarm_clock_card
npm install
npm test
```

## Version Management

- **Backend**: Version in manifest.json is the source of truth
- **Frontend**: Version in package.json is the source of truth
- Each repository can have independent versioning going forward

## HACS Essentials - Complete ✅

Both folders now include all necessary HACS essentials for independent operation:

### Release Automation
**Backend:**
- `release.yml` workflow creates `alarm_clock.zip` on git tags
- Automatically updates version in manifest.json
- Generates changelog from git commits
- Creates GitHub release with installation instructions

**Frontend:**
- `release.yml` workflow releases `alarm-clock-card.js` on git tags ✨
- Automatically updates version in package.json and card JS file ✨
- Generates changelog from git commits ✨
- Creates GitHub release with installation instructions ✨

### HACS Validation
**Backend:**
- `hacs-validation.yml` validates integration configuration
- Runs weekly and on-demand
- Checks for proper structure and required files

**Frontend:**
- `hacs-validation.yml` validates plugin configuration ✨
- Runs weekly and on-demand ✨
- Checks for proper structure and required files ✨

### Dependency Management
**Backend:**
- Dependabot configured for Python/pip dependencies
- Automatic weekly updates for GitHub Actions

**Frontend:**
- Dependabot configured for NPM dependencies ✨
- Automatic weekly updates for GitHub Actions ✨

### Package Generation
**Backend:**
- Creates `alarm_clock.zip` containing `custom_components/alarm_clock/`
- Ready for manual installation in Home Assistant

**Frontend:**
- Releases `alarm-clock-card.js` file directly
- Ready for manual installation in `www/` folder

### How to Release

**Backend:**
```bash
git tag v1.0.9
git push origin v1.0.9
# Workflow automatically creates release with alarm_clock.zip
```

**Frontend:**
```bash
git tag v1.0.9
git push origin v1.0.9
# Workflow automatically creates release with alarm-clock-card.js
```

## Documentation Updates

Both README files have been updated to:
- Remove references to the other component where appropriate
- Add installation instructions for the separate components
- Link to each other for complete functionality
- Clarify the split architecture

## Migration Path for Users

Users of the current combined repository can:
1. Uninstall the old integration
2. Install both new repositories separately
3. Reconfigure alarms (if needed)

Or continue using the combined repository if it remains available.

## Next Steps

To complete the split:
1. Create two new GitHub repositories:
   - `fappsde/alarm_clock_backend`
   - `fappsde/alarm_clock_card`
2. Copy contents of each folder to its respective repository
3. Update HACS repository URLs in hacs.json files
4. Update documentation links
5. Create initial releases for both
6. Submit to HACS default repository (optional)
