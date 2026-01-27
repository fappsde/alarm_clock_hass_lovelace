# Repository Setup Guide

This document outlines the GitHub repository settings that need to be configured for full functionality of this Home Assistant custom component.

## Required GitHub Repository Settings

### 1. Repository Description
Set a clear description for your repository:
1. Go to your GitHub repository
2. Click on the gear icon (⚙️) next to "About" on the right side
3. Add a description, for example: "Home Assistant custom component for managing alarm clocks"
4. Click "Save changes"

### 2. Repository Topics
Add the required topics for HACS discovery:
1. In the same "About" section settings
2. Add the following topics:
   - `home-assistant`
   - `hacs`
   - `home-assistant-component` (optional but recommended)
   - `alarm-clock` (optional but recommended)
3. Click "Save changes"

### 3. Branch Protection Rules

Once the workflows are passing, you can enable branch protection:

1. Go to **Settings** → **Branches** → **Branch protection rules**
2. Click "Add rule"
3. Branch name pattern: `main`
4. Enable the following:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
   - Select these required status checks:
     - `Validate / Hassfest Validation`
     - `Validate / Lint`
     - `Tests / Run Tests (3.11)`
     - `Tests / Run Tests (3.12)`
     - `Tests / Test Minimum HA Version`
5. Optionally enable:
   - ✅ Require conversation resolution before merging
   - ✅ Do not allow bypassing the above settings
6. Click "Create" or "Save changes"

## Verification

After configuring the repository settings:

1. **Verify HACS Validation**: Go to the Actions tab and manually run the "HACS Validation (Optional)" workflow
2. **Check Status Checks**: Create a test PR to verify all status checks appear and pass

## Troubleshooting

### HACS Validation Still Failing
- Ensure both description and topics are set
- Wait a few minutes for GitHub to update
- Manually trigger the HACS validation workflow

### Status Checks Not Appearing
- Ensure workflows have run at least once on the main branch
- Check the Actions tab for any workflow failures
- Verify the workflow files are in `.github/workflows/`

### Dependabot Issues
- Ensure Dependabot is enabled in **Settings** → **Security** → **Dependabot**
- Check that `dependabot.yml` exists in `.github/`
