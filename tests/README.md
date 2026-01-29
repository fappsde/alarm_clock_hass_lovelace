# Testing Guide for Alarm Clock Integration

## Overview
This directory contains tests and validation tools for the alarm clock Home Assistant integration.

## Test Files

### Unit Tests
- `test_config_flow.py` - Config flow tests (prevents infinite loop bug)

### Validation Tools
- `check_versions.py` - Ensures version synchronization across files

### Test Data
- (To be added) Mock data for integration tests

## Running Tests

### Prerequisites
```bash
pip install pytest pytest-homeassistant-custom-component
```

### Run All Tests
```bash
# From project root
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_config_flow.py -v
```

### Run Version Check
```bash
python3 tests/check_versions.py
```

## Pre-Commit Checklist

Before committing any changes:

1. **Run black formatter**:
   ```bash
   black custom_components/alarm_clock/
   ```

2. **Check syntax**:
   ```bash
   find custom_components/alarm_clock -name "*.py" -exec python3 -m py_compile {} \;
   ```

3. **Run version check**:
   ```bash
   python3 tests/check_versions.py
   ```

4. **Run tests**:
   ```bash
   pytest tests/ -v
   ```

5. **Manual testing** (if config flow changed):
   - Create alarm without optional fields
   - Toggle boolean fields
   - Test form submission

## Critical Test Cases

### Config Flow Tests (Prevents v1.0.7 Bug)

**Test 1: Form Submission Without Boolean Field**
- Simulates unchecked checkbox (field not in user_input)
- **Must not** create infinite loop
- **Must** create alarm successfully

**Test 2: Version Synchronization**
- Verifies manifest.json matches card versions
- Verifies both card files are identical

**Test 3: Optional Fields**
- Tests form with all optional fields omitted
- **Must** use default values without crash

## Writing New Tests

### Test Template
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

async def test_my_feature(hass: HomeAssistant):
    """Test my feature."""
    # Arrange
    mock_coordinator = MagicMock()

    # Act
    result = await my_function(mock_coordinator)

    # Assert
    assert result is not None
```

### Mock Home Assistant
```python
@pytest.fixture
def hass():
    """Home Assistant fixture."""
    mock_hass = MagicMock(spec=HomeAssistant)
    mock_hass.data = {DOMAIN: {}}
    return mock_hass
```

## Continuous Integration

### GitHub Actions Workflow
See `.github/workflows/test.yml` for automated testing on push.

### Local CI Simulation
```bash
# Run full CI pipeline locally
./scripts/run_ci_locally.sh
```

## Test Coverage

Current coverage:
- Config flow: 20% (critical paths covered)
- Coordinator: 0%
- State machine: 0%
- Services: 0%

**Goal**: 80% coverage for critical paths

## Known Issues to Test

1. ✅ Config flow infinite loop (v1.0.7) - TESTED
2. ⚠️ Race conditions in alarm scheduling - NEEDS TESTS
3. ⚠️ Memory leaks in event tracking - NEEDS TESTS
4. ⚠️ Script execution error handling - NEEDS TESTS

## Manual Testing Scenarios

### Scenario 1: New Installation
1. Install integration via HACS
2. Add integration through UI
3. Create first alarm
4. Verify all entities created

### Scenario 2: Upgrade from v1.0.7
1. Install v1.0.7
2. Create alarms
3. Upgrade to v1.0.8
4. Verify alarms still work
5. Create new alarm (test fix)

### Scenario 3: Stress Testing
1. Create 10+ alarms
2. Toggle all rapidly
3. Delete and recreate
4. Restart Home Assistant
5. Verify no memory leaks

### Scenario 4: Error Handling
1. Reference non-existent script
2. Set invalid time format
3. Create alarm with very long name
4. Use negative duration values

## Reporting Issues

If tests fail:
1. Check logs: `home-assistant.log`
2. Run diagnostics: Developer Tools → Services → `alarm_clock.diagnostics`
3. Report with:
   - Test output
   - HA version
   - Integration version
   - Steps to reproduce

## Contributing Tests

When adding features:
1. Write tests FIRST (TDD)
2. Ensure tests cover edge cases
3. Update this README
4. Add to CI pipeline

## Resources

- [Home Assistant Testing](https://developers.home-assistant.io/docs/development_testing)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)
