# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/fappsde/alarm_clock_hass_lovelace/compare/v1.0.6...HEAD
[1.0.6]: https://github.com/fappsde/alarm_clock_hass_lovelace/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/fappsde/alarm_clock_hass_lovelace/compare/v1.0.0...v1.0.5
[1.0.0]: https://github.com/fappsde/alarm_clock_hass_lovelace/releases/tag/v1.0.0
