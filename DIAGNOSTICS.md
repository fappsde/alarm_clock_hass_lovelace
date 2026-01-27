# Integration Setup Diagnostics

If you're experiencing setup errors with the Alarm Clock integration, please follow these steps to help diagnose the issue:

## Step 1: Enable Debug Logging

Add the following to your Home Assistant `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.alarm_clock: debug
```

Then restart Home Assistant or reload the logger configuration.

## Step 2: Remove and Re-add the Integration

1. Go to **Settings** → **Devices & Services**
2. Find the "Alarm Clock" integration
3. Click the three dots menu → **Delete**
4. Click **+ ADD INTEGRATION**
5. Search for "Alarm Clock" and add it again
6. Enter a name when prompted

## Step 3: Check the Logs

### Option A: Via Home Assistant UI
1. Go to **Settings** → **System** → **Logs**
2. Look for entries containing `alarm_clock`
3. Copy any ERROR or WARNING messages

### Option B: Via Command Line
If you have SSH access to your Home Assistant instance:

```bash
# View recent logs
docker logs homeassistant 2>&1 | grep -i "alarm_clock"

# Or if running Home Assistant OS:
ha core logs | grep -i "alarm_clock"
```

## Step 4: What to Look For

You're looking for messages like these:

```
ERROR (MainThread) [custom_components.alarm_clock] Error setting up Alarm Clock integration: ...
ERROR (MainThread) [homeassistant.config_entries] Error setting up entry Alarm Clock for alarm_clock
ERROR (MainThread) [homeassistant.components.sensor] Error while setting up alarm_clock platform for sensor
```

## Common Issues and Solutions

### Issue: "No entities" but integration loads

**Symptoms:**
- Integration appears in Devices & Services
- Device shows up but with no entities
- No errors in logs

**Solution:**
This is expected on first setup! The integration creates:
- 4 device-level entities (always present)
- Per-alarm entities (only after you add alarms)

To see entities:
1. Click **CONFIGURE** on the integration
2. Select **Add New Alarm**
3. Fill in alarm details and save
4. Entities should appear automatically

### Issue: "Setup error" message

**Symptoms:**
- Red error icon on device
- Message: "Einrichtungsfehler: Überprüfe die Protokolle" (Setup error: Check the logs)

**Possible Causes:**
1. **Missing dependencies**: Ensure Home Assistant version is 2023.1 or newer
2. **Corrupted storage**: Delete `.storage/alarm_clock.storage_*` file and restart
3. **Platform setup failure**: Check logs for specific platform errors

### Issue: Integration doesn't appear at all

**Possible Causes:**
1. **Installation error**: Ensure files are in `custom_components/alarm_clock/`
2. **Manifest error**: Check that `manifest.json` is valid JSON
3. **Python errors**: Check logs for SyntaxError or ImportError

## Expected Log Output (Successful Setup)

```
DEBUG (MainThread) [custom_components.alarm_clock] Setting up Alarm Clock integration: abc123
INFO (MainThread) [custom_components.alarm_clock.coordinator] Alarm clock coordinator started with 0 alarms
DEBUG (MainThread) [custom_components.alarm_clock.coordinator] Registered alarm clock services
INFO (MainThread) [custom_components.alarm_clock] Alarm Clock integration setup complete: abc123
```

## File Locations

- **Integration files**: `<config>/custom_components/alarm_clock/`
- **Storage file**: `<config>/.storage/alarm_clock.storage_<entry_id>`
- **Logs**: `<config>/home-assistant.log` or via Docker logs

## Still Having Issues?

Please provide:
1. Full error messages from the logs (Step 3)
2. Your Home Assistant version (`Settings` → `About`)
3. Whether you're running:
   - Home Assistant OS
   - Home Assistant Container (Docker)
   - Home Assistant Core (manual install)
   - Home Assistant Supervised

This information will help diagnose the issue more quickly.
