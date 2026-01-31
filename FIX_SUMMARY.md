# Fix Summary: Script Configuration in Alarm Advanced Settings

## Issues Fixed

### Issue 1: Toggle Visibility Not Working
**Problem**: The "Use Device Default Scripts" toggle in the alarm advanced settings form did not dynamically show/hide the script configuration fields. The script fields were never visible even when the toggle was set to False.

**Root Cause**: The form schema was built once when the form was first shown, using the default value of `use_device_defaults=True`. When the user toggled the switch, the form was not rebuilt with the new schema.

**Solution**: Added logic to detect when the `use_device_defaults` toggle changes and rebuild the form dynamically:
- Compare current toggle value with previous value
- If changed, update stored data and re-show form with new schema
- Preserve other field values to avoid data loss

### Issue 2: Default Scripts Not Applied
**Problem**: When `use_device_defaults` was True, the alarm would still save whatever script values were in the form (which were empty), rather than leaving them as None so the coordinator could use device-level defaults.

**Root Cause**: The alarm creation code was directly reading script fields from the form data without checking the `use_device_defaults` flag.

**Solution**: Added conditional logic when creating the alarm:
- If `use_device_defaults` is True, set all script fields to None
- If `use_device_defaults` is False, use the values from the form
- This allows the coordinator to properly apply device-level defaults when scripts are None

## Code Changes

### File: `custom_components/alarm_clock/config_flow.py`

#### Change 1: Dynamic Form Rebuild (Lines 319-341)
```python
# Check if use_device_defaults toggle was changed
current_use_defaults = user_input.get(CONF_USE_DEVICE_DEFAULTS, True)
previous_use_defaults = self._alarm_data.get(CONF_USE_DEVICE_DEFAULTS, True)

if current_use_defaults != previous_use_defaults:
    # Toggle changed - update stored data and re-show form with new schema
    self._alarm_data[CONF_USE_DEVICE_DEFAULTS] = current_use_defaults
    # Preserve other fields that were filled in
    for key in [CONF_SNOOZE_DURATION, CONF_MAX_SNOOZE_COUNT, ...]:
        if key in user_input:
            self._alarm_data[key] = user_input[key]
    
    # Re-show form with updated schema
    return self.async_show_form(
        step_id="alarm_advanced",
        data_schema=self._build_advanced_schema(current_use_defaults),
    )
```

#### Change 2: Conditional Script Assignment (Lines 401-426)
```python
# Determine if using device defaults
use_device_defaults = alarm_data.get(CONF_USE_DEVICE_DEFAULTS, True)

# If using device defaults, don't set individual scripts
if use_device_defaults:
    script_pre_alarm = None
    script_alarm = None
    # ... all scripts set to None
else:
    # Use alarm-specific scripts from form
    script_pre_alarm = alarm_data.get(CONF_SCRIPT_PRE_ALARM)
    script_alarm = alarm_data.get(CONF_SCRIPT_ALARM)
    # ... use form values
```

## Expected Behavior After Fix

### Before Fix:
1. User creates a new alarm
2. In advanced settings, sees "Use Device Default Scripts" toggle (default: ON)
3. Script fields are never visible, even when toggle is set to OFF
4. When saving with toggle ON, alarm incorrectly stores empty script values

### After Fix:
1. User creates a new alarm
2. In advanced settings, sees "Use Device Default Scripts" toggle (default: ON)
3. Script fields are hidden when toggle is ON
4. User toggles to OFF → Form rebuilds → Script fields become visible
5. User can now configure per-alarm scripts
6. When toggle is ON and user saves, scripts are set to None (coordinator uses device defaults)
7. When toggle is OFF and user saves, specified scripts are saved to the alarm

## Testing Recommendations

### Manual Test Scenario 1: Toggle Visibility
1. Create a new alarm through the UI
2. On the advanced settings page, verify "Use Device Default Scripts" is ON
3. Verify that script fields (Pre-alarm Script, Alarm Script, etc.) are NOT visible
4. Toggle "Use Device Default Scripts" to OFF
5. Verify that script fields become visible
6. Toggle back to ON
7. Verify that script fields are hidden again

### Manual Test Scenario 2: Device Defaults Applied
1. Configure device-level default scripts in Settings → Default Scripts
2. Create a new alarm with "Use Device Default Scripts" ON
3. Save the alarm
4. Verify the alarm uses the device-level default scripts (not empty scripts)
5. Verify the alarm triggers correctly with the default scripts

### Manual Test Scenario 3: Per-Alarm Scripts
1. Create a new alarm
2. Toggle "Use Device Default Scripts" to OFF
3. Select specific scripts for this alarm
4. Save the alarm
5. Verify the alarm uses the per-alarm scripts (not device defaults)
6. Verify the alarm triggers correctly with the per-alarm scripts

## Related Files

- `custom_components/alarm_clock/config_flow.py` - Main fix implementation
- `custom_components/alarm_clock/coordinator.py` - Handles device defaults (lines 971-992)
- `custom_components/alarm_clock/const.py` - Constants for configuration fields
- `custom_components/alarm_clock/strings.json` - UI labels and descriptions

## Version History

- **Issue Introduced**: v1.0.6 - Feature was added but not working correctly
- **Issue Fixed**: Current version - Dynamic form rebuild and proper script handling
