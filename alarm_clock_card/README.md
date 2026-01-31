# Alarm Clock Card - Lovelace Custom Card for Home Assistant

[![GitHub Release][release-badge]][release-url]
[![License][license-badge]][license-url]
[![Tests][tests-badge]][tests-url]

A beautiful, feature-rich Lovelace custom card for the Alarm Clock integration for Home Assistant.

![Alarm Clock Card](https://raw.githubusercontent.com/fappsde/alarm_clock_hass_lovelace/main/images/card-preview.png)

## Features

- **Compact and expanded modes**
- **Quick time adjustments** (+5m, +10m, +1hr)
- **Day toggle pills** - Quick weekday selection
- **State-aware UI** - Different view when ringing
- **Large touch targets** - Mobile-friendly
- **Theme support** - Respects HA themes
- **Visual card editor** - No YAML needed

## Prerequisites

This card requires the Alarm Clock backend integration to be installed. See the [alarm_clock_backend repository](https://github.com/fappsde/alarm_clock_backend) for installation instructions.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Frontend"
3. Click the three dots menu and select "Custom repositories"
4. Add this repository URL: `https://github.com/fappsde/alarm_clock_card`
5. Select "Lovelace" as the category
6. Click "Add"
7. Find "Alarm Clock Card" and click "Download"
8. Refresh your browser (Ctrl+Shift+R)

### Manual Installation

1. Download the latest `alarm-clock-card.js` from the [releases page][release-url]
2. Copy it to your `www/` folder in your Home Assistant config directory
3. Add the card resource in your Lovelace configuration:

```yaml
# In configuration.yaml or via UI (Settings -> Dashboards -> Resources)
lovelace:
  resources:
    - url: /local/alarm-clock-card.js
      type: module
```

4. Refresh your browser (Ctrl+Shift+R)

## Configuration

### Using the Visual Editor

1. Click "Add Card" in your dashboard
2. Search for "Alarm Clock Card"
3. Select your alarm entity
4. Configure display options
5. Click "Save"

### YAML Configuration

```yaml
type: custom:alarm-clock-card
entity: switch.alarm_clock_morning_alarm
title: My Alarms
show_next_alarm: true
compact_mode: false
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | **Required** | Entity ID of the alarm (switch.alarm_clock_*) |
| `title` | string | Entity name | Card title |
| `show_next_alarm` | boolean | `true` | Show next alarm time |
| `compact_mode` | boolean | `false` | Use compact layout |

### Example Configurations

**Basic Card:**
```yaml
type: custom:alarm-clock-card
entity: switch.alarm_clock_morning_alarm
```

**Multiple Alarms:**
```yaml
type: vertical-stack
cards:
  - type: custom:alarm-clock-card
    entity: switch.alarm_clock_morning_alarm
    title: Morning Alarm
    compact_mode: false
  - type: custom:alarm-clock-card
    entity: switch.alarm_clock_afternoon_nap
    title: Afternoon Nap
    compact_mode: true
```

**With Custom Title:**
```yaml
type: custom:alarm-clock-card
entity: switch.alarm_clock_weekend_alarm
title: Weekend Sleep-In
show_next_alarm: true
```

## Features Details

### Quick Time Adjustments
- Click "+5m" to add 5 minutes to alarm time
- Click "+10m" to add 10 minutes
- Click "+1hr" to add 1 hour
- Great for quick snooze-like adjustments before the alarm goes off

### Weekday Selection
- Click day pills (M, T, W, T, F, S, S) to toggle days
- Selected days are highlighted
- Changes are saved immediately

### State-Aware UI
- **Armed**: Shows next alarm time and standard controls
- **Ringing**: Shows large snooze and dismiss buttons
- **Snoozed**: Shows snooze count and time until next ring
- **Disabled**: Shows disabled state with option to enable

### Compact Mode
- Reduces card height
- Shows essential information only
- Ideal for multiple alarms in a small space

## Troubleshooting

### Card doesn't appear
1. Check that the card resource is loaded (Developer Tools -> Info)
2. Clear browser cache (Ctrl+Shift+R)
3. Verify the file exists at `/local/alarm-clock-card.js`
4. Check browser console for errors (F12)

### Card shows "Custom element doesn't exist"
1. Ensure you've added the resource to Lovelace
2. Refresh your browser completely
3. Check that the file is accessible at `http://your-ha-url:8123/local/alarm-clock-card.js`

### Frontend errors in browser console
If you see errors like "Maximum call stack size exceeded" or "custom element not found":
1. Update to the latest version (1.0.8+)
2. Clear browser cache completely
3. Restart Home Assistant
4. These issues were fixed in recent releases with proper ES module imports

### Changes don't save
1. Verify the backend integration is installed and working
2. Check Home Assistant logs for errors
3. Ensure you have write permissions to the entity

## Version Compatibility

- **Card Version 1.0.8+**: Requires Home Assistant 2024.1.0+
- **Backend Integration**: Must match the card version for best compatibility

## Development

### Building from Source

```bash
# Install dependencies
npm install

# Run tests
npm test

# Run linter
npm run lint

# Check version consistency
npm run check-versions
```

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `npm test`
5. Submit a pull request

## Backend Integration

This card requires the Alarm Clock backend integration. See the [alarm_clock_backend repository](https://github.com/fappsde/alarm_clock_backend) for:
- Backend installation
- Service calls
- Events
- Automations
- Full feature documentation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

[release-badge]: https://img.shields.io/github/v/release/fappsde/alarm_clock_card
[release-url]: https://github.com/fappsde/alarm_clock_card/releases
[license-badge]: https://img.shields.io/github/license/fappsde/alarm_clock_card
[license-url]: https://github.com/fappsde/alarm_clock_card/blob/main/LICENSE
[tests-badge]: https://github.com/fappsde/alarm_clock_card/actions/workflows/test-frontend.yml/badge.svg
[tests-url]: https://github.com/fappsde/alarm_clock_card/actions/workflows/test-frontend.yml
