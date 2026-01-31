# Testing Guide for Alarm Clock Integration

## Overview
This directory contains comprehensive tests and validation tools for the alarm clock Home Assistant integration, covering both backend (Python) and frontend (JavaScript) components.

## Test Files

### Backend Tests (Python)
- `test_config_flow.py` - Config flow tests (prevents infinite loop bug)
- Additional pytest tests for integration components

### Frontend Tests (JavaScript)
- `frontend/import-safety.test.js` - Module import safety verification
- `frontend/duplicate-registration.test.js` - Custom element registration protection
- `frontend/global-safety.test.js` - Frontend poisoning prevention (CRITICAL)
- `frontend/version-consistency.test.js` - Version synchronization enforcement

### Validation Tools
- `check_versions.py` - Ensures version synchronization across files
- `frontend/check-versions.js` - JavaScript version checker

## Running Tests

### Prerequisites

**Backend (Python):**
```bash
pip install pytest pytest-homeassistant-custom-component
```

**Frontend (JavaScript):**
```bash
npm install
```

### Run All Tests

**Backend:**
```bash
# From project root
pytest tests/ -v
```

**Frontend:**
```bash
# From project root
npm test

# Run specific test suite
npx vitest run tests/frontend/global-safety.test.js

# Run with coverage
npm test -- --coverage
```

### Version Consistency Check
```bash
# Python version checker
python3 tests/check_versions.py

# JavaScript version checker
npm run check-versions
```

## Test Coverage

### Current Coverage
- **Config flow**: 20% (critical paths covered)
- **Frontend safety**: 100% (26 tests, all passing)
- **Coordinator**: Partial coverage
- **State machine**: Partial coverage
- **Services**: Partial coverage

**Goal**: 80% coverage for all critical paths

## Critical Test Cases

### Frontend Tests (Prevents Production Bugs)

#### Test 1: Import Safety ⭐ CRITICAL
**Purpose**: Verifies module can be imported without throwing top-level exceptions

**What it prevents**:
- Frontend poisoning (original v1.0.x bug)
- Broken HA internals access
- Module evaluation failures

**Test scenario**:
```javascript
// Module must import without throwing
import './alarm-clock-card.js';
// Custom elements must be registered
expect(customElements.get('alarm-clock-card')).toBeDefined();
```

#### Test 2: Duplicate Registration Protection
**Purpose**: Ensures re-importing module doesn't cause DOMException

**What it prevents**:
- DOMException on HMR (Hot Module Replacement)
- Crashes during development
- Multiple registration attempts

**Test scenario**:
```javascript
// First import - should work
import './alarm-clock-card.js';
// Second import - should NOT throw
import './alarm-clock-card.js';
expect(customElements.get('alarm-clock-card')).toBeDefined();
```

#### Test 3: Global Safety ⭐ MOST CRITICAL
**Purpose**: Verifies this card cannot break other cards (frontend poisoning prevention)

**What it prevents**:
- ALL custom cards failing after installing this integration
- "Konfigurationsfehler: custom element not found" errors
- HACS breaking globally

**Test scenario**:
```javascript
// Import alarm card
import './alarm-clock-card.js';

// Try to register 10 other fake cards
for (let i = 0; i < 10; i++) {
  class TestCard extends HTMLElement {}
  customElements.define(`test-card-${i}`, TestCard);
}

// All 10 cards should register successfully
// If alarm card poisoned frontend, these would fail
```

**This test would have caught the original production bug!**

#### Test 4: Version Consistency
**Purpose**: Enforces all versions match (manifest, package, card)

**What it prevents**:
- Stale cached versions (original v1.0.4 cache bug)
- Version skew between components
- Browser caching wrong version

**Test scenario**:
```javascript
const manifestVersion = require('../custom_components/alarm_clock/manifest.json').version;
const packageVersion = require('../package.json').version;
const cardVersion = extractCardVersion('./alarm-clock-card.js');

expect(manifestVersion).toBe(packageVersion);
expect(packageVersion).toBe(cardVersion);
```

### Backend Tests (Config Flow)

#### Test 1: Form Submission Without Boolean Field ⭐ CRITICAL
**Purpose**: Prevents infinite loop when checkboxes are unchecked

**What it prevents**:
- Infinite config flow loop (v1.0.7 critical bug)
- Home Assistant crashes
- HACS registry corruption

**Test scenario**:
```python
# Simulate unchecked checkbox (field not in user_input)
user_input = {
    "alarm_name": "Test",
    "alarm_time": "07:00",
    # use_device_defaults NOT present (unchecked)
}

result = await flow.async_step_alarm_advanced(user_input)

# Must NOT loop - must create entry successfully
assert result["type"] == "create_entry"
```

**This test prevents HA crashes!**

## Pre-Commit Checklist

Before committing any changes:

1. **Run black formatter**:
   ```bash
   black custom_components/alarm_clock/
   ```

2. **Check Python syntax**:
   ```bash
   find custom_components/alarm_clock -name "*.py" -exec python3 -m py_compile {} \;
   ```

3. **Run version check**:
   ```bash
   python3 tests/check_versions.py
   npm run check-versions
   ```

4. **Run all tests**:
   ```bash
   pytest tests/ -v
   npm test
   ```

5. **Manual testing** (if config flow changed):
   - Create alarm without optional fields
   - Toggle boolean fields (check and uncheck)
   - Test form submission with various combinations
   - Monitor HA logs for errors

## Breaking the Tests Intentionally (Verification)

To verify tests catch real problems:

### Break Import Safety
```javascript
// In alarm-clock-card.js, change line 9 to:
const LitElement = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace")
);
```
**Expected**: ✅ Import safety test FAILS (module throws during import)

### Break Duplicate Registration Protection
```javascript
// In alarm-clock-card.js, remove the check:
customElements.define("alarm-clock-card", AlarmClockCard);  // No if guard
```
**Expected**: ✅ Duplicate registration test FAILS (DOMException on re-import)

### Break Version Consistency
```bash
# Change manifest.json version to 1.0.9
# Don't update package.json
```
**Expected**: ✅ Version consistency test FAILS with clear error message

### Break Config Flow
```python
# In config_flow.py, restore buggy logic:
if user_input is not None:
    if CONF_USE_DEVICE_DEFAULTS in user_input:
        # Only handle when field present
```
**Expected**: ✅ Config flow test FAILS (infinite loop detected)

## Test Infrastructure Details

### Frontend Test Environment
- **Test Runner**: Vitest (fast, modern)
- **DOM Simulation**: happy-dom (realistic browser behavior)
- **Module System**: ES modules (matches production)
- **Caching**: Enabled (ES modules cache in real browsers)

### Why happy-dom?
- Built-in customElements registry (realistic)
- Fast execution (faster than jsdom)
- Modern web standards support
- Used by Home Assistant frontend team

### ES Module Caching
Tests correctly simulate browser behavior:
- Modules imported once and cached
- Top-level code runs exactly once
- `customElements` and `window.customCards` persist
- Matches real-world behavior

## Known Issues and Testing

### ✅ Config flow infinite loop (v1.0.7) - TESTED & FIXED
**Test**: `test_config_flow.py::test_form_without_boolean_field`
**Status**: Passes - bug cannot reoccur

### ✅ Frontend poisoning (v1.0.x) - TESTED & FIXED
**Test**: `frontend/global-safety.test.js`
**Status**: Passes - poisoning mechanically impossible

### ✅ Circular reference stack overflow - TESTED & FIXED
**Test**: Implicit via import-safety tests
**Status**: Passes - safe object construction

### ✅ Version skew causing stale cache - TESTED & FIXED
**Test**: `frontend/version-consistency.test.js`
**Status**: Passes - versions must match

### ⚠️ NEEDS TESTS (Future Work)
- Race conditions in alarm scheduling
- Memory leaks in event tracking
- Script execution error handling edge cases
- State restoration after HA restart

## Manual Testing Scenarios

### Scenario 1: New Installation
1. Install integration via HACS
2. Add integration through UI
3. Create first alarm
4. Verify all entities created
5. Check no console errors in browser

### Scenario 2: Upgrade from v1.0.7 (Critical)
1. Install v1.0.7 (deprecated)
2. Note any issues
3. Upgrade to v1.0.8+
4. Verify alarms still work
5. Create new alarm (test fix)
6. Monitor HA logs for errors

### Scenario 3: Frontend Poisoning Prevention
1. Install this integration
2. Install other custom cards (mushroom, mini-graph, etc.)
3. Verify all cards load correctly
4. Check browser console for errors
5. Confirm no "custom element not found" errors

### Scenario 4: Stress Testing
1. Create 10+ alarms
2. Toggle all rapidly
3. Delete and recreate
4. Restart Home Assistant
5. Verify no memory leaks
6. Check all alarms still functional

### Scenario 5: Error Handling
1. Reference non-existent script
2. Set invalid time format
3. Create alarm with very long name
4. Use negative duration values
5. Verify graceful error handling

## Continuous Integration

### GitHub Actions Workflows
- `.github/workflows/tests.yml` - Backend Python tests
- `.github/workflows/test-frontend.yml` - Frontend JavaScript tests

### What CI Checks
1. ✅ All Python tests pass
2. ✅ All JavaScript tests pass (26 tests)
3. ✅ Version consistency enforced
4. ✅ No frontend poisoning possible
5. ✅ Code formatting (black, prettier)
6. ✅ Syntax validation
7. ✅ Import safety verified

### CI Enforcement
- **Blocks PR merge** if tests fail
- **No human discipline required** - mechanical enforcement
- **Catches bugs before production**

## Reporting Issues

If tests fail:

1. **Check logs**:
   ```bash
   # Home Assistant logs
   tail -f home-assistant.log | grep alarm_clock
   
   # Test output
   npm test -- --reporter=verbose
   pytest tests/ -vv
   ```

2. **Run diagnostics**:
   - Developer Tools → Services → `alarm_clock.diagnostics`

3. **Report with**:
   - Test output (full trace)
   - Home Assistant version
   - Integration version
   - Browser version (for frontend issues)
   - Steps to reproduce
   - Expected vs actual behavior

## Contributing Tests

When adding features:

1. **Write tests FIRST** (TDD - Test Driven Development)
2. **Ensure tests cover edge cases**:
   - Happy path (normal usage)
   - Error conditions
   - Boundary conditions
   - Invalid input
   - Race conditions (if applicable)
3. **Update this README** with new test descriptions
4. **Add to CI pipeline** if new test category
5. **Verify tests fail** when feature is broken
6. **Verify tests pass** when feature is correct

### Test Template

**Backend (Python):**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

async def test_my_feature(hass: HomeAssistant):
    """Test my feature does X correctly."""
    # Arrange - Setup test data
    mock_coordinator = MagicMock()
    
    # Act - Execute the feature
    result = await my_function(mock_coordinator)
    
    # Assert - Verify expected behavior
    assert result is not None
    assert result.some_property == expected_value
```

**Frontend (JavaScript):**
```javascript
import { describe, it, expect } from 'vitest';

describe('My Feature', () => {
  it('should do X correctly', () => {
    // Arrange
    const input = createTestInput();
    
    // Act
    const result = myFunction(input);
    
    // Assert
    expect(result).toBeDefined();
    expect(result.someProperty).toBe(expectedValue);
  });
});
```

## Resources

- [Home Assistant Testing Guide](https://developers.home-assistant.io/docs/development_testing)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)
- [Vitest Documentation](https://vitest.dev/)
- [happy-dom Documentation](https://github.com/capricorn86/happy-dom)
- [Web Components Testing Best Practices](https://open-wc.org/guides/developing-components/testing/)

## Summary

This test suite prevents the following critical bugs from reaching production:

1. ⭐ **Config flow infinite loop** → Would crash Home Assistant
2. ⭐ **Frontend poisoning** → Would break ALL custom cards
3. ⭐ **Circular reference stack overflow** → Would crash browser DevTools
4. ⭐ **Version skew** → Would cause stale cache issues

**All 26 frontend tests pass** + Backend tests = Production-ready code

**Testing is not optional** - it's what keeps this integration stable and safe for all users.
