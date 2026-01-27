# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/fappsde/alarm_clock_hass_lovelace/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/fappsde/alarm_clock_hass_lovelace/releases/tag/v1.0.0
