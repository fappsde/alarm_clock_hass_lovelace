# Alarm Clock for Home Assistant

[![HACS][hacs-badge]][hacs-url]
[![GitHub Release][release-badge]][release-url]
[![License][license-badge]][license-url]
[![Validate][validate-badge]][validate-url]
[![Tests][tests-badge]][tests-url]

A robust, feature-rich alarm clock integration for Home Assistant with a beautiful Lovelace card.

![Alarm Clock Card](https://raw.githubusercontent.com/fappsde/alarm_clock_hass_lovelace/main/images/card-preview.png)

## Features

### Core Features
- **Multiple independent alarms** - Like a smartphone, create as many alarms as you need
- **Per-alarm weekday selection** - Different schedules for different days
- **One-time alarms** - Auto-disable after trigger
- **Skip next occurrence** - Sleep in without disabling the alarm
- **Snooze** - Configurable duration and maximum count
- **Auto-dismiss** - Timeout after configurable duration

### Script Integration
| Phase | Timing | Example Use |
|-------|--------|-------------|
| Pre-alarm | N minutes before | Dim up lights, open blinds |
| Alarm | At alarm time | Play sound, full lights |
| Post-alarm | After dismiss/timeout | Stop sound, keep lights |
| On-snooze | When snoozed | Pause sound, dim lights |
| On-dismiss | When dismissed | Cleanup actions |
| On-arm | When enabled | Confirmation |
| On-cancel | When disabled while active | Emergency stop |
| On-skip | When skip next activated | Notification |

### Reliability Features
- **State persistence** - Survives restarts, even mid-snooze
- **Missed alarm detection** - Triggers if HA was down at alarm time
- **Script retry with backoff** - Automatic retry on failure
- **Fallback mechanism** - Alternative script if primary fails
- **Health monitoring** - Built-in health check sensor
- **Atomic state transitions** - No race conditions
- **Entity validation** - Warns about missing scripts on startup

### Lovelace Card
- **Compact and expanded modes**
- **Quick time adjustments** (+5m, +10m, +1hr)
- **Day toggle pills** - Quick weekday selection
- **State-aware UI** - Different view when ringing
- **Large touch targets** - Mobile-friendly
- **Theme support** - Respects HA themes
- **Visual card editor** - No YAML needed

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu and select "Custom repositories"
4. Add this repository URL: `https://github.com/fappsde/alarm_clock_hass_lovelace`
5. Select "Integration" as the category
6. Click "Add"
7. Find "Alarm Clock" and click "Download"
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page][release-url]
2. Extract the `alarm_clock` folder to `custom_components/` in your HA config directory
3. Copy `www/alarm-clock-card.js` to your `www/` folder
4. Restart Home Assistant

## Configuration

### Adding the Integration

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for "Alarm Clock"
4. Follow the setup wizard

### Adding Alarms

1. Go to the Alarm Clock device
2. Click **Configure**
3. Select **Add New Alarm**
4. Configure:
   - Name
   - Time
   - Days
   - Snooze settings
   - Scripts (optional)

### Adding the Lovelace Card

Add the card resource (if not auto-discovered):

```yaml
# In configuration.yaml or via UI
lovelace:
  resources:
    - url: /local/alarm-clock-card.js
      type: module
```

Add the card to your dashboard:

```yaml
type: custom:alarm-clock-card
entity: switch.alarm_clock_morning_alarm
title: My Alarms
show_next_alarm: true
compact_mode: false
```

## Services

| Service | Description |
|---------|-------------|
| `alarm_clock.snooze` | Snooze a ringing alarm |
| `alarm_clock.dismiss` | Dismiss an alarm |
| `alarm_clock.skip_next` | Skip next occurrence |
| `alarm_clock.cancel_skip` | Cancel skip |
| `alarm_clock.test_alarm` | Trigger alarm for testing |
| `alarm_clock.set_time` | Change alarm time |
| `alarm_clock.set_days` | Change alarm days |
| `alarm_clock.create_alarm` | Create new alarm |
| `alarm_clock.delete_alarm` | Delete an alarm |

### Example Automations

```yaml
# Snooze alarm from phone notification
automation:
  - alias: "Snooze Alarm from Notification"
    trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: SNOOZE_ALARM
    action:
      - service: alarm_clock.snooze
        data:
          entity_id: switch.alarm_clock_morning_alarm
          duration: 10

# Play music when alarm triggers
automation:
  - alias: "Play Morning Music"
    trigger:
      - platform: event
        event_type: alarm_clock_triggered
    action:
      - service: media_player.play_media
        target:
          entity_id: media_player.bedroom_speaker
        data:
          media_content_id: "spotify:playlist:37i9dQZF1DX0UrRvztWcAU"
          media_content_type: playlist
```

## Events

| Event | Description |
|-------|-------------|
| `alarm_clock_armed` | Alarm enabled |
| `alarm_clock_disarmed` | Alarm disabled |
| `alarm_clock_pre_alarm` | Pre-alarm phase started |
| `alarm_clock_triggered` | Alarm started ringing |
| `alarm_clock_snoozed` | User hit snooze |
| `alarm_clock_dismissed` | User dismissed |
| `alarm_clock_auto_dismissed` | Timeout dismissed |
| `alarm_clock_missed` | Alarm was missed |
| `alarm_clock_skipped` | Next occurrence skipped |
| `alarm_clock_script_failed` | Script execution failed |
| `alarm_clock_health_warning` | Health issue detected |

## Entities

Each alarm creates:
- `switch.alarm_clock_<name>` - Enable/disable
- `switch.alarm_clock_<name>_skip_next` - Skip next toggle
- `time.alarm_clock_<name>_time` - Alarm time
- `sensor.alarm_clock_<name>_state` - Current state
- `sensor.alarm_clock_<name>_next_trigger` - Next trigger time
- `sensor.alarm_clock_<name>_snooze_count` - Snooze count
- `binary_sensor.alarm_clock_<name>_ringing` - Is ringing?

Device-level entities:
- `sensor.alarm_clock_next_alarm` - Next alarm across all
- `sensor.alarm_clock_active_alarms` - Count of active alarms
- `binary_sensor.alarm_clock_any_alarm_ringing` - Any alarm ringing
- `binary_sensor.alarm_clock_health` - Health status

## Troubleshooting

### Alarm doesn't trigger
1. Check the alarm is enabled (switch is on)
2. Verify the day is selected
3. Check `skip_next` is not enabled
4. Look at the `next_trigger` sensor

### Scripts not running
1. Verify the script entity exists
2. Check Home Assistant logs for errors
3. Look for `alarm_clock_script_failed` events
4. Ensure script doesn't have a longer timeout than configured

### State not persisting
1. Check `binary_sensor.alarm_clock_health`
2. Look at diagnostics for issues
3. Verify `.storage` files exist

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs-url]: https://github.com/hacs/integration
[release-badge]: https://img.shields.io/github/v/release/fappsde/alarm_clock_hass_lovelace
[release-url]: https://github.com/fappsde/alarm_clock_hass_lovelace/releases
[license-badge]: https://img.shields.io/github/license/fappsde/alarm_clock_hass_lovelace
[license-url]: https://github.com/fappsde/alarm_clock_hass_lovelace/blob/main/LICENSE
[validate-badge]: https://github.com/fappsde/alarm_clock_hass_lovelace/actions/workflows/validate.yml/badge.svg
[validate-url]: https://github.com/fappsde/alarm_clock_hass_lovelace/actions/workflows/validate.yml
[tests-badge]: https://github.com/fappsde/alarm_clock_hass_lovelace/actions/workflows/tests.yml/badge.svg
[tests-url]: https://github.com/fappsde/alarm_clock_hass_lovelace/actions/workflows/tests.yml
