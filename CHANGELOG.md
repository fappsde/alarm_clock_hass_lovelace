# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.8] - 2026-01-29

### Fixed - CRITICAL Config Flow Bug
- **CRITICAL**: Fixed infinite loop in config flow causing Home Assistant crash
  - Config flow would loop infinitely when boolean fields were unchecked
  - This caused HA to become unresponsive and break HACS integration registry
  - Simplified form submission logic to handle all cases properly
- Updated manifest.json version to match release version (was 1.0.0, now 1.0.8)
- Synchronized version numbers across all files

### Root Cause Analysis
**Bug #1: Infinite Loop in Config Flow**
- **File**: `custom_components/alarm_clock/config_flow.py`
- **Function**: `async_step_alarm_advanced()`
- **Severity**: CRITICAL - Causes HA crash

**Problem**: The config flow logic only handled form submissions when `CONF_USE_DEVICE_DEFAULTS` was present in `user_input`. When this field was absent (which happens with unchecked boolean fields in Home Assistant), the code would:
1. Skip alarm creation
2. Fall through to re-show the form
3. Create an infinite loop
4. Eventually crash Home Assistant

**Original Buggy Code**:
```python
if user_input is not None:
    if CONF_USE_DEVICE_DEFAULTS in user_input:
        # Only handles cases where toggle is present
        if len(user_input) <= 5:
            pass  # Fall through - BUG!
        else:
            # Create alarm
            return self.async_create_entry(title="", data={})
# Falls through to show form again - infinite loop!
```

**Fix**: Simplified the logic to handle ALL form submissions properly:
```python
if user_input is not None:
    # Merge with basic alarm data
    alarm_data = {**self._alarm_data, **user_input}
    # Create alarm
    # ...
    return self.async_create_entry(title="", data={})
```

### Impact Assessment
When an integration crashes during config flow:
- Home Assistant's integration loader gets stuck
- HACS integration registry becomes corrupted
- Other integrations fail to load due to registry lock
- Reinstallation is required to clear the corrupted state

### Recovery Instructions
If you encountered this bug:
1. Stop Home Assistant: `systemctl stop home-assistant`
2. Remove integration configuration from `.storage/core.config_entries`
3. Restart Home Assistant: `systemctl start home-assistant`
4. Reinstall via HACS and reconfigure

### Prevention Measures Implemented
- Test ALL code paths (not just happy path)
- Test with boolean fields both checked and unchecked
- Ensure no infinite loops possible
- Version synchronization checks
- Comprehensive testing protocol

### Technical
- Removed complex conditional logic in `async_step_alarm_advanced`
- Eliminated infinite loop possibility
- Python syntax and formatting validated

## [1.0.x] - Recent Fixes (Technical Details)

### Fixed - Frontend Poisoning Issue
**Problem**: Installing or updating via HACS caused global Lovelace frontend failure, breaking ALL custom cards

**Root Cause**: Unsafe access to Home Assistant internals that threw top-level exceptions, preventing all subsequent custom elements from registering.

**Solution Implemented**:

1. **Use Official ES Module Imports**
   - **Before (UNSAFE)**:
     ```javascript
     const LitElement = Object.getPrototypeOf(
       customElements.get("ha-panel-lovelace")
     );
     const html = LitElement.prototype.html;
     const css = LitElement.prototype.css;
     ```
   - **After (SAFE)**:
     ```javascript
     import { LitElement, html, css } from "lit";
     ```
   - **Why**: `lit` is a peer dependency provided by Home Assistant. No HA internal access required, future-proof against HA changes.

2. **Duplicate Registration Protection**
   - **Before (UNSAFE)**: `customElements.define("alarm-clock-card", AlarmClockCard);`
   - **After (SAFE)**:
     ```javascript
     if (!customElements.get("alarm-clock-card")) {
       customElements.define("alarm-clock-card", AlarmClockCard);
     }
     ```
   - **Why**: Checks for existing registration first. No DOMException on re-import.

3. **Single Source of Truth: manifest.json**
   - **Before**: Version hardcoded in `__init__.py` as `1.0.4` (stale)
   - **After**: Version read dynamically from `manifest.json`
     ```python
     def _get_version() -> str:
         """Get version from manifest.json - single source of truth."""
         manifest_path = Path(__file__).parent / "manifest.json"
         with open(manifest_path, encoding="utf-8") as f:
             manifest = json.load(f)
             return manifest.get("version", "unknown")
     ```
   - **Why**: One file to update, version automatically propagates, proper cache busting, impossible to have version skew.

4. **Fixed HACS Configuration**
   - Added `"type": "integration"` to `hacs.json`
   - Removed `"filename"` field (only needed for plugin types)
   - HACS now correctly handles resource serving

5. **Comprehensive Test Suite**
   - Created 26 frontend tests across 4 test files:
     - `import-safety.test.js` - Verifies module can be imported without throwing
     - `duplicate-registration.test.js` - Tests re-import doesn't throw DOMException
     - `global-safety.test.js` - Tests that broken cards can't break other cards (prevents frontend poisoning)
     - `version-consistency.test.js` - Enforces all versions match
   - Added CI enforcement via GitHub Actions
   - Prevents regressions mechanically

**Files Changed**:
- `custom_components/alarm_clock/alarm-clock-card.js` - Safe imports, duplicate protection
- `www/alarm-clock-card.js` - Same as above (synchronized)
- `custom_components/alarm_clock/__init__.py` - Version from manifest.json
- `hacs.json` - Added integration type
- `.github/workflows/tests.yml` - Updated to include frontend checks

**Impact**:
- ✅ Installing this integration affects ONLY this card (not all cards)
- ✅ Updating properly cache-busts (version from manifest)
- ✅ CI fails if frontend poisoning is reintroduced
- ✅ All cards work even if this one fails
- ✅ Version skew is mechanically impossible

### Fixed - Circular Reference Stack Overflow
**Problem**: `RangeError: Maximum call stack size exceeded` when browser DevTools were open or when HA attempted to log errors

**Root Cause**: The `_getAlarms()` method created alarm objects with circular references. Home Assistant's state objects contain internal circular references. When JavaScript tried to serialize/traverse these objects (console.log, JSON.stringify, error serialization), it entered an infinite loop causing stack overflow.

**Solution**:
- **Before (BROKEN)**:
  ```javascript
  alarms.push({
    entity_id: key,
    state: state,              // Full HA state object (contains circular refs)
    attributes: state.attributes, // Same reference
  });
  ```
- **After (FIXED)**:
  ```javascript
  const attrs = state.attributes;
  alarms.push({
    entity_id: key,
    state: { state: state.state },  // Only the state value
    attributes: {
      // Explicitly list only needed attributes
      alarm_id: attrs.alarm_id,
      alarm_name: attrs.alarm_name,
      alarm_state: attrs.alarm_state,
      alarm_time: attrs.alarm_time,
      days: attrs.days,
      entry_id: attrs.entry_id,
      max_snooze_count: attrs.max_snooze_count,
      next_trigger: attrs.next_trigger,
      skip_next: attrs.skip_next,
      snooze_count: attrs.snooze_count,
      snooze_end_time: attrs.snooze_end_time,
    },
  });
  ```

**Why This Works**:
- Breaks circular references by only copying primitive values and arrays
- Explicit extraction - no hidden nested objects
- Memory efficient - only stores data actually used
- Safe serialization - objects can be safely logged or stringified

**Additional Fixes**:
- Updated all console.log statements to avoid logging full alarm objects
- Only logs safe, minimal data (entity_id, alarm_name, etc.)

**Files Changed**:
- `www/alarm-clock-card.js`
- `custom_components/alarm_clock/alarm-clock-card.js`

**Impact**:
- ✅ Eliminates stack overflow errors
- ✅ Safe to use with browser DevTools open
- ✅ Prevents Home Assistant log errors
- ✅ Reduces memory usage
- ✅ All existing functionality preserved

### Test Infrastructure Improvements
**Summary**: Fixed frontend test infrastructure to run correctly with realistic browser simulation

**Problems Fixed**:
1. **Missing Dependency Lockfile** - Added `package-lock.json` for deterministic CI builds
2. **Unrealistic Test Environment** - Switched to happy-dom's built-in customElements registry
3. **Order-Dependent Tests** - Import module once in `beforeAll` hook (ES modules cache in real browsers)
4. **Template Literal Syntax** - Fixed escaped backticks causing parse errors
5. **CI Missing Guards** - Added explicit lockfile verification to CI

**Test Results**: All 26 tests pass successfully
- ✓ tests/frontend/global-safety.test.js (7 tests)
- ✓ tests/frontend/import-safety.test.js (5 tests)
- ✓ tests/frontend/duplicate-registration.test.js (7 tests)
- ✓ tests/frontend/version-consistency.test.js (7 tests)

**Files Modified**:
- `package-lock.json` (created) - Deterministic dependency resolution
- `tests/frontend/setup.js` (rewritten) - Uses happy-dom properly
- All test files - Account for ES module caching behavior
- `.github/workflows/test-frontend.yml` - Added lockfile verification

**Impact**:
- ✅ Tests run and pass for the right reasons (not false positives)
- ✅ Accurately simulates browser behavior
- ✅ CI enforces all checks
- ✅ Would have caught original bugs before production

### Security Analysis
**CodeQL Scan**: ✅ PASSED (0 vulnerabilities found)

**Security Improvements**:
1. **Data Sanitization** - Only stores explicitly allowed attributes (whitelist approach)
2. **Console Logging Safety** - Prevents accidental exposure of sensitive data in logs
3. **Information Disclosure Prevention** - Reduced attack surface by limiting stored data
4. **Memory Exhaustion Prevention** - Clean objects with no circular refs reduce memory footprint

**Compliance**:
- ✅ Principle of Least Privilege - Only stores needed data
- ✅ Defense in Depth - Whitelisted attributes prevent unknown data exposure
- ✅ Secure Defaults - Safe logging prevents accidental data leakage
- ✅ Minimal Data Retention - Stores only what's necessary

## [1.0.7] - 2026-01-29 [DEPRECATED - Contains Critical Bug]

### Added
- One-time alarm support when all weekdays are unselected
  - Automatically sets alarm for next occurrence (today if time hasn't passed, tomorrow otherwise)
  - Visual "One-time" badge displayed for single-day alarms
  - Date display in countdown for one-time alarms and alarms >24h away

### Changed
- Next alarm display now shows "No next alarm" when all alarms disabled
  - Always visible when `show_next_alarm` is enabled
  - Updates dynamically when alarms are enabled/disabled
- Increased spacing between toggle switch and skip/delete buttons (8px → 12px)

### Fixed
- Next alarm status now properly reflects when alarms are disabled
- Handled "unavailable" state for next alarm sensor

### Known Issues
- ⚠️ **CRITICAL BUG**: Config flow can cause infinite loop and crash Home Assistant
- ⚠️ Use version 1.0.8 instead

## [1.0.6] - 2026-01-29

### Added
- Descriptive section header for default script settings in device options
- Tooltips for skip and delete icon buttons

### Changed
- **UI Improvements**: Skip and delete buttons redesigned as icon buttons
  - Positioned below the alarm toggle switch for better layout
  - Changed from text buttons to icon-only buttons with tooltips
  - More compact and intuitive placement
- **UI Improvements**: Weekday pills now adapt to available space
  - Removed minimum width constraint to prevent overflow
  - Pills now flex proportionally to container width
  - Optimized padding for better space utilization
- Config flow: Individual script fields now hidden when "Use Device Defaults" is enabled
  - Cleaner UI that only shows relevant options
  - Reduces configuration complexity when using device defaults
- Config flow: Enhanced labels and descriptions for all settings
  - Added descriptive text for script timeout and retry count fields
  - Number selectors now use BOX mode for cleaner appearance
  - Used suggested_value instead of default for better UX

### Technical
- Updated alarm header layout to use flexbox column for toggle and icon buttons
- Changed day-pill flex properties from `flex: 1` to `flex: 1 1 0` for better responsiveness
- Reduced day-pill padding and removed min-width constraint
- Conditional schema building in config flow based on use_device_defaults setting

## [1.0.5] - 2026-01-29

### Added
- Device-level default scripts system
  - Configure default scripts once at device level
  - All new alarms automatically use device defaults
  - Per-alarm override with `use_device_defaults` toggle
  - Options flow UI to configure 11 default script settings
  - New service: `set_scripts` to update alarm scripts
- Delete button in alarm cards (both list and editor views)
- Alarm name display in compact horizontal view (editor mode)
- Next alarm display in editor view header
- Service parameter: `use_device_defaults` in `create_alarm` service

### Changed
- **BREAKING**: Alarm naming changed from time-based to count-based
  - Old: "Alarm 15:45" (based on creation time)
  - New: "Alarm 1", "Alarm 2", etc. (sequential numbering)
- Editor view time selection: removed "Set Time" button
  - Time is now clickable like in list view
  - More consistent UX across view modes
- Weekday display optimized to fit in single row
  - Changed from wrapping to nowrap layout
  - Equal-width day pills with centered letters
  - Better use of horizontal space
- Skip button made more compact
  - Text changed from "Skip Next" to "Skip"
  - Reduced padding and font size
  - Shares row with delete button
- Script execution now respects device defaults
  - Automatic resolution between alarm-specific and device-level scripts
  - Applies to all 9 script types and timeout/retry settings

### Fixed
- Entity cleanup when deleting alarms
  - All associated entities now properly removed from entity registry
  - Prevents orphaned unavailable entities
  - Cleans up switches, sensors, binary sensors, and time entities
- Alarm card file synchronization
  - Both `www/` and `custom_components/` versions now identical
  - Version properly tracked and bumped

### Technical
- Added 11 new constants for device-level default scripts
- Added `use_device_defaults` field to AlarmData model
- Script resolution helpers in coordinator
- Enhanced config flow with device defaults step
- Service schema validation for new parameters

## [1.0.0] - 2024-01-15

### Added
- Initial release
- Multiple independent alarms with per-alarm settings
- Per-alarm weekday selection
- One-time alarms with auto-disable
- Skip next occurrence feature
- Configurable snooze duration and max count
- Auto-dismiss after configurable timeout
- Pre-alarm phase with configurable lead time
- Script integration for all alarm phases:
  - Pre-alarm
  - Alarm
  - Post-alarm
  - On-snooze
  - On-dismiss
  - On-arm
  - On-cancel
  - On-skip
- Fallback script on failure
- Script execution with retry and exponential backoff
- Script timeout configuration
- State persistence across restarts (RestoreEntity)
- Missed alarm detection with configurable grace period
- Health check sensor for monitoring
- Atomic state transitions with asyncio locks
- Entity validation on startup
- Auto-disable corrupt alarms with notification
- Config flow for UI-based setup
- Options flow for managing alarms
- Services:
  - snooze
  - dismiss
  - skip_next
  - cancel_skip
  - test_alarm
  - set_time
  - set_days
  - create_alarm
  - delete_alarm
- Events for all state transitions
- Lovelace card with:
  - Compact and expanded modes
  - Quick time adjustments
  - Day toggle pills
  - State-aware UI
  - Large snooze/dismiss buttons
  - Next alarm countdown
  - Mobile-friendly touch targets
  - Theme support
  - Visual card editor
- Full translations (English, German)
- Diagnostics support
- Comprehensive test suite
- GitHub Actions for CI/CD
- HACS compatibility

### Security
- Script entity validation to prevent invalid references
- Atomic state transitions to prevent race conditions

[Unreleased]: https://github.com/fappsde/alarm_clock_hass_lovelace/compare/v1.0.8...HEAD
[1.0.8]: https://github.com/fappsde/alarm_clock_hass_lovelace/compare/v1.0.7...v1.0.8
[1.0.7]: https://github.com/fappsde/alarm_clock_hass_lovelace/compare/v1.0.6...v1.0.7
[1.0.6]: https://github.com/fappsde/alarm_clock_hass_lovelace/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/fappsde/alarm_clock_hass_lovelace/compare/v1.0.0...v1.0.5
[1.0.0]: https://github.com/fappsde/alarm_clock_hass_lovelace/releases/tag/v1.0.0
