"""Config flow for Alarm Clock integration."""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ALARM_NAME,
    CONF_ALARM_TIME,
    CONF_AUTO_DISMISS_TIMEOUT,
    CONF_DAYS,
    CONF_DEFAULT_SCRIPT_ALARM,
    CONF_DEFAULT_SCRIPT_FALLBACK,
    CONF_DEFAULT_SCRIPT_ON_ARM,
    CONF_DEFAULT_SCRIPT_ON_CANCEL,
    CONF_DEFAULT_SCRIPT_ON_DISMISS,
    CONF_DEFAULT_SCRIPT_ON_SKIP,
    CONF_DEFAULT_SCRIPT_ON_SNOOZE,
    CONF_DEFAULT_SCRIPT_POST_ALARM,
    CONF_DEFAULT_SCRIPT_PRE_ALARM,
    CONF_DEFAULT_SCRIPT_RETRY_COUNT,
    CONF_DEFAULT_SCRIPT_TIMEOUT,
    CONF_ENABLED,
    CONF_MAX_SNOOZE_COUNT,
    CONF_MISSED_ALARM_GRACE_PERIOD,
    CONF_ONE_TIME,
    CONF_PRE_ALARM_DURATION,
    CONF_SCRIPT_ALARM,
    CONF_SCRIPT_FALLBACK,
    CONF_SCRIPT_ON_ARM,
    CONF_SCRIPT_ON_CANCEL,
    CONF_SCRIPT_ON_DISMISS,
    CONF_SCRIPT_ON_SKIP,
    CONF_SCRIPT_ON_SNOOZE,
    CONF_SCRIPT_POST_ALARM,
    CONF_SCRIPT_PRE_ALARM,
    CONF_SCRIPT_RETRY_COUNT,
    CONF_SCRIPT_TIMEOUT,
    CONF_SNOOZE_DURATION,
    CONF_USE_DEVICE_DEFAULTS,
    CONF_WATCHDOG_TIMEOUT,
    DEFAULT_AUTO_DISMISS_TIMEOUT,
    DEFAULT_MAX_SNOOZE_COUNT,
    DEFAULT_MISSED_ALARM_GRACE_PERIOD,
    DEFAULT_PRE_ALARM_DURATION,
    DEFAULT_SCRIPT_RETRY_COUNT,
    DEFAULT_SCRIPT_TIMEOUT,
    DEFAULT_SNOOZE_DURATION,
    DEFAULT_WATCHDOG_TIMEOUT,
    DOMAIN,
    WEEKDAYS,
)
from .state_machine import AlarmStateMachine
from .validation import (
    ValidationError,
    validate_alarm_name,
    validate_duration,
    validate_time_format,
)

_LOGGER = logging.getLogger(__name__)


def _weekday_selector() -> selector.SelectSelector:
    """Create weekday selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=day, label=day.capitalize()) for day in WEEKDAYS
            ],
            multiple=True,
            mode=selector.SelectSelectorMode.LIST,
        )
    )


class AlarmClockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alarm Clock."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._alarms: list[dict[str, Any]] = []
        self._current_alarm: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Create the config entry with the name
            return self.async_create_entry(
                title=user_input.get("name", "Alarm Clock"),
                data={"name": user_input.get("name", "Alarm Clock")},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default="Alarm Clock"): cv.string,
                }
            ),
            description_placeholders={
                "name": "Alarm Clock",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AlarmClockOptionsFlow:
        """Create the options flow."""
        return AlarmClockOptionsFlow(config_entry)


class AlarmClockOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Alarm Clock."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        # Note: self.config_entry is automatically set by the base class
        self._alarm_data: dict[str, Any] = {}

    def _build_advanced_schema(self, use_defaults: bool) -> vol.Schema:
        """Build the advanced alarm settings schema."""
        schema_dict = {
            vol.Optional(
                CONF_SNOOZE_DURATION, default=DEFAULT_SNOOZE_DURATION
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=60,
                    step=1,
                    unit_of_measurement="minutes",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_MAX_SNOOZE_COUNT, default=DEFAULT_MAX_SNOOZE_COUNT
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_AUTO_DISMISS_TIMEOUT, default=DEFAULT_AUTO_DISMISS_TIMEOUT
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=180,
                    step=1,
                    unit_of_measurement="minutes",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_PRE_ALARM_DURATION, default=DEFAULT_PRE_ALARM_DURATION
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=60,
                    step=1,
                    unit_of_measurement="minutes",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_USE_DEVICE_DEFAULTS, default=True): selector.BooleanSelector(),
        }

        # Only show individual script fields if NOT using device defaults
        if not use_defaults:
            schema_dict.update(
                {
                    vol.Optional(CONF_SCRIPT_PRE_ALARM): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(CONF_SCRIPT_ALARM): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(CONF_SCRIPT_POST_ALARM): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(CONF_SCRIPT_ON_SNOOZE): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(CONF_SCRIPT_ON_DISMISS): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(CONF_SCRIPT_FALLBACK): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(
                        CONF_SCRIPT_TIMEOUT, default=DEFAULT_SCRIPT_TIMEOUT
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=300,
                            step=1,
                            unit_of_measurement="seconds",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_SCRIPT_RETRY_COUNT, default=DEFAULT_SCRIPT_RETRY_COUNT
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                }
            )

        return vol.Schema(schema_dict)

    def _build_edit_alarm_schema(self, alarm: AlarmStateMachine, use_defaults: bool | None = None) -> vol.Schema:
        """Build the edit alarm schema with current values."""
        # Parse current time
        try:
            hour, minute = map(int, alarm.data.time.split(":"))
            current_time = {"hours": hour, "minutes": minute}
        except (ValueError, AttributeError):
            current_time = {"hours": 7, "minutes": 0}

        # Use provided use_defaults or fall back to alarm's current setting
        if use_defaults is None:
            use_defaults = alarm.data.use_device_defaults

        schema_dict = {
            vol.Required(CONF_ALARM_NAME, default=alarm.data.name): cv.string,
            vol.Required(CONF_ALARM_TIME, default=current_time): selector.TimeSelector(),
            vol.Required(CONF_DAYS, default=alarm.data.days): _weekday_selector(),
            vol.Optional(
                CONF_SNOOZE_DURATION, default=alarm.data.snooze_duration
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=60, step=1, unit_of_measurement="minutes"
                )
            ),
            vol.Optional(
                CONF_MAX_SNOOZE_COUNT, default=alarm.data.max_snooze_count
            ): selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=10, step=1)),
            vol.Optional(
                CONF_AUTO_DISMISS_TIMEOUT, default=alarm.data.auto_dismiss_timeout
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=180, step=1, unit_of_measurement="minutes"
                )
            ),
            vol.Optional(
                CONF_PRE_ALARM_DURATION, default=alarm.data.pre_alarm_duration
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=60, step=1, unit_of_measurement="minutes"
                )
            ),
            vol.Optional(
                CONF_USE_DEVICE_DEFAULTS, default=alarm.data.use_device_defaults
            ): selector.BooleanSelector(),
        }

        # Only show individual script fields if NOT using device defaults
        if not use_defaults:
            schema_dict.update(
                {
                    vol.Optional(
                        CONF_SCRIPT_PRE_ALARM,
                        description={
                            "suggested_value": alarm.data.script_pre_alarm
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(
                        CONF_SCRIPT_ALARM,
                        description={
                            "suggested_value": alarm.data.script_alarm
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(
                        CONF_SCRIPT_POST_ALARM,
                        description={
                            "suggested_value": alarm.data.script_post_alarm
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(
                        CONF_SCRIPT_ON_SNOOZE,
                        description={
                            "suggested_value": alarm.data.script_on_snooze
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(
                        CONF_SCRIPT_ON_DISMISS,
                        description={
                            "suggested_value": alarm.data.script_on_dismiss
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(
                        CONF_SCRIPT_ON_ARM,
                        description={
                            "suggested_value": alarm.data.script_on_arm
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(
                        CONF_SCRIPT_ON_CANCEL,
                        description={
                            "suggested_value": alarm.data.script_on_cancel
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(
                        CONF_SCRIPT_ON_SKIP,
                        description={
                            "suggested_value": alarm.data.script_on_skip
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(
                        CONF_SCRIPT_FALLBACK,
                        description={
                            "suggested_value": alarm.data.script_fallback
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="script")
                    ),
                    vol.Optional(
                        CONF_SCRIPT_TIMEOUT, default=alarm.data.script_timeout
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=300,
                            step=1,
                            unit_of_measurement="seconds",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_SCRIPT_RETRY_COUNT, default=alarm.data.script_retry_count
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                }
            )

        return vol.Schema(schema_dict)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_alarm", "manage_alarms", "default_scripts", "global_settings"],
        )

    async def async_step_add_alarm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle adding a new alarm."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate alarm name
            try:
                user_input[CONF_ALARM_NAME] = validate_alarm_name(user_input[CONF_ALARM_NAME])
            except ValidationError as err:
                _LOGGER.debug("Alarm name validation failed: %s", err)
                errors[CONF_ALARM_NAME] = "invalid_name"

            # Validate time format using validation utility
            try:
                validate_time_format(user_input[CONF_ALARM_TIME])
            except ValidationError as err:
                _LOGGER.debug(
                    "Time validation failed: %s (value: %s)", err, user_input.get(CONF_ALARM_TIME)
                )
                errors[CONF_ALARM_TIME] = "invalid_time"

            if not errors:
                # Store alarm data for advanced settings
                self._alarm_data = user_input
                return await self.async_step_alarm_advanced()

        # Provide default time of 7:00 AM
        default_time = {"hours": 7, "minutes": 0}

        return self.async_show_form(
            step_id="add_alarm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ALARM_NAME): cv.string,
                    vol.Required(CONF_ALARM_TIME, default=default_time): selector.TimeSelector(),
                    vol.Required(CONF_DAYS, default=WEEKDAYS[:5]): _weekday_selector(),
                    vol.Optional(CONF_ONE_TIME, default=False): cv.boolean,
                    vol.Optional(CONF_ENABLED, default=True): cv.boolean,
                }
            ),
            errors=errors,
        )

    async def async_step_alarm_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced alarm settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if use_device_defaults toggle was changed
            current_use_defaults = user_input.get(CONF_USE_DEVICE_DEFAULTS, True)
            previous_use_defaults = self._alarm_data.get(CONF_USE_DEVICE_DEFAULTS, True)

            if current_use_defaults != previous_use_defaults:
                # Toggle changed - update stored data and re-show form with new schema
                self._alarm_data[CONF_USE_DEVICE_DEFAULTS] = current_use_defaults
                # Preserve other fields that were filled in, including script selections
                for key in [
                    CONF_SNOOZE_DURATION,
                    CONF_MAX_SNOOZE_COUNT,
                    CONF_AUTO_DISMISS_TIMEOUT,
                    CONF_PRE_ALARM_DURATION,
                    CONF_SCRIPT_TIMEOUT,
                    CONF_SCRIPT_RETRY_COUNT,
                    CONF_SCRIPT_PRE_ALARM,
                    CONF_SCRIPT_ALARM,
                    CONF_SCRIPT_POST_ALARM,
                    CONF_SCRIPT_ON_SNOOZE,
                    CONF_SCRIPT_ON_DISMISS,
                    CONF_SCRIPT_FALLBACK,
                ]:
                    if key in user_input:
                        self._alarm_data[key] = user_input[key]

                alarm_name = self._alarm_data.get(CONF_ALARM_NAME, "New Alarm")
                return self.async_show_form(
                    step_id="alarm_advanced",
                    description_placeholders={
                        "alarm_name": alarm_name,
                        "info": "Configure advanced alarm settings. If 'Use Device Defaults' is enabled, the alarm will use the device-level default scripts configured in Settings → Default Scripts.",
                    },
                    data_schema=self._build_advanced_schema(current_use_defaults),
                )

            # Validate numeric fields
            numeric_validations = {
                CONF_SNOOZE_DURATION: (1, 60),
                CONF_MAX_SNOOZE_COUNT: (0, 10),
                CONF_AUTO_DISMISS_TIMEOUT: (1, 180),
                CONF_PRE_ALARM_DURATION: (0, 60),
                CONF_SCRIPT_TIMEOUT: (1, 300),
                CONF_SCRIPT_RETRY_COUNT: (0, 10),
            }

            for field, (min_val, max_val) in numeric_validations.items():
                if field in user_input:
                    try:
                        user_input[field] = validate_duration(
                            user_input[field], field, min_val, max_val
                        )
                    except ValidationError as err:
                        _LOGGER.debug("Validation failed for %s: %s", field, err)
                        errors[field] = "invalid_value"

            if errors:
                # Re-show form with errors
                # Read use_defaults from user_input to reflect the current toggle state
                use_defaults = user_input.get(CONF_USE_DEVICE_DEFAULTS, True)
                alarm_name = self._alarm_data.get(CONF_ALARM_NAME, "New Alarm")
                return self.async_show_form(
                    step_id="alarm_advanced",
                    description_placeholders={
                        "alarm_name": alarm_name,
                        "info": "Configure advanced alarm settings. If 'Use Device Defaults' is enabled, the alarm will use the device-level default scripts configured in Settings → Default Scripts.",
                    },
                    data_schema=self._build_advanced_schema(use_defaults),
                    errors=errors,
                )

            # Merge with basic alarm data
            alarm_data = {**self._alarm_data, **user_input}

            # Add the alarm via coordinator
            coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if coordinator:
                import uuid

                from .state_machine import AlarmData

                alarm_id = f"alarm_{uuid.uuid4().hex[:8]}"

                # Convert time selector output to HH:MM string
                time_value = alarm_data[CONF_ALARM_TIME]
                if isinstance(time_value, dict):
                    time_str = (
                        f"{time_value.get('hours', 0):02d}:{time_value.get('minutes', 0):02d}"
                    )
                else:
                    # Handle "HH:MM" or "HH:MM:SS" format - only keep HH:MM
                    time_parts = str(time_value).split(":")
                    time_str = f"{int(time_parts[0]):02d}:{int(time_parts[1]):02d}"

                # Determine if using device defaults
                use_device_defaults = alarm_data.get(CONF_USE_DEVICE_DEFAULTS, True)

                # If using device defaults, don't set individual scripts
                # The coordinator will use device-level defaults instead
                if use_device_defaults:
                    script_pre_alarm = None
                    script_alarm = None
                    script_post_alarm = None
                    script_on_snooze = None
                    script_on_dismiss = None
                    script_fallback = None
                    script_timeout = DEFAULT_SCRIPT_TIMEOUT
                    script_retry_count = DEFAULT_SCRIPT_RETRY_COUNT
                else:
                    # Use alarm-specific scripts from form
                    script_pre_alarm = alarm_data.get(CONF_SCRIPT_PRE_ALARM)
                    script_alarm = alarm_data.get(CONF_SCRIPT_ALARM)
                    script_post_alarm = alarm_data.get(CONF_SCRIPT_POST_ALARM)
                    script_on_snooze = alarm_data.get(CONF_SCRIPT_ON_SNOOZE)
                    script_on_dismiss = alarm_data.get(CONF_SCRIPT_ON_DISMISS)
                    script_fallback = alarm_data.get(CONF_SCRIPT_FALLBACK)
                    script_timeout = alarm_data.get(CONF_SCRIPT_TIMEOUT, DEFAULT_SCRIPT_TIMEOUT)
                    script_retry_count = alarm_data.get(
                        CONF_SCRIPT_RETRY_COUNT, DEFAULT_SCRIPT_RETRY_COUNT
                    )

                new_alarm = AlarmData(
                    alarm_id=alarm_id,
                    name=alarm_data[CONF_ALARM_NAME],
                    time=time_str,
                    days=alarm_data.get(CONF_DAYS, WEEKDAYS[:5]),
                    one_time=alarm_data.get(CONF_ONE_TIME, False),
                    enabled=alarm_data.get(CONF_ENABLED, True),
                    snooze_duration=alarm_data.get(CONF_SNOOZE_DURATION, DEFAULT_SNOOZE_DURATION),
                    max_snooze_count=alarm_data.get(
                        CONF_MAX_SNOOZE_COUNT, DEFAULT_MAX_SNOOZE_COUNT
                    ),
                    auto_dismiss_timeout=alarm_data.get(
                        CONF_AUTO_DISMISS_TIMEOUT, DEFAULT_AUTO_DISMISS_TIMEOUT
                    ),
                    pre_alarm_duration=alarm_data.get(
                        CONF_PRE_ALARM_DURATION, DEFAULT_PRE_ALARM_DURATION
                    ),
                    use_device_defaults=use_device_defaults,
                    script_pre_alarm=script_pre_alarm,
                    script_alarm=script_alarm,
                    script_post_alarm=script_post_alarm,
                    script_on_snooze=script_on_snooze,
                    script_on_dismiss=script_on_dismiss,
                    script_fallback=script_fallback,
                    script_timeout=script_timeout,
                    script_retry_count=script_retry_count,
                )
                try:
                    await coordinator.async_add_alarm(new_alarm)
                except Exception as err:
                    _LOGGER.error("Error adding alarm: %s", err, exc_info=True)
                    return self.async_abort(reason="add_alarm_failed")

            # Clear the alarm data after successful submission
            self._alarm_data = {}

            return self.async_create_entry(title="", data={})

        # Build schema using helper method
        use_defaults = self._alarm_data.get(CONF_USE_DEVICE_DEFAULTS, True)

        alarm_name = self._alarm_data.get(CONF_ALARM_NAME, "New Alarm")
        return self.async_show_form(
            step_id="alarm_advanced",
            description_placeholders={
                "alarm_name": alarm_name,
                "info": "Configure advanced alarm settings. If 'Use Device Defaults' is enabled, the alarm will use the device-level default scripts configured in Settings → Default Scripts.",
            },
            data_schema=self._build_advanced_schema(use_defaults),
        )

    async def async_step_manage_alarms(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle managing existing alarms."""
        coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)

        if not coordinator or not coordinator.alarms:
            return self.async_abort(reason="no_alarms")

        if user_input is not None:
            # User selected an alarm
            self._alarm_data = {"selected_alarm": user_input["alarm"]}
            return await self.async_step_alarm_actions()

        alarm_options = [
            selector.SelectOptionDict(
                value=alarm_id, label=f"{alarm.data.name} ({alarm.data.time})"
            )
            for alarm_id, alarm in coordinator.alarms.items()
        ]

        return self.async_show_form(
            step_id="manage_alarms",
            data_schema=vol.Schema(
                {
                    vol.Required("alarm"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=alarm_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_alarm_actions(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle actions for a selected alarm."""
        if user_input is not None:
            action = user_input["action"]
            alarm_id = self._alarm_data["selected_alarm"]
            coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)

            if action == "delete":
                if coordinator:
                    try:
                        await coordinator.async_remove_alarm(alarm_id)
                    except Exception as err:
                        _LOGGER.error("Error removing alarm: %s", err, exc_info=True)
                        return self.async_abort(reason="remove_alarm_failed")
                return self.async_create_entry(title="", data={})
            elif action == "edit":
                self._alarm_data["alarm_id"] = alarm_id
                return await self.async_step_edit_alarm()

        return self.async_show_form(
            step_id="alarm_actions",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value="edit", label="Edit Alarm"),
                                selector.SelectOptionDict(value="delete", label="Delete Alarm"),
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )

    async def async_step_edit_alarm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle editing an alarm."""
        coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
        alarm_id = self._alarm_data.get("alarm_id")

        if not coordinator or not alarm_id or alarm_id not in coordinator.alarms:
            return self.async_abort(reason="alarm_not_found")

        alarm = coordinator.alarms[alarm_id]
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if use_device_defaults toggle was changed
            current_use_defaults = user_input.get(CONF_USE_DEVICE_DEFAULTS, True)
            previous_use_defaults = alarm.data.use_device_defaults

            if current_use_defaults != previous_use_defaults:
                # Toggle changed - update alarm data temporarily and re-show form with new schema
                # Store current form values to preserve them
                self._alarm_data["form_values"] = user_input
                return self.async_show_form(
                    step_id="edit_alarm",
                    description_placeholders={
                        "alarm_name": alarm.data.name,
                        "info": "Edit alarm settings. If 'Use Device Defaults' is enabled, the alarm will use the device-level default scripts configured in Settings → Default Scripts.",
                    },
                    data_schema=self._build_edit_alarm_schema(alarm, current_use_defaults),
                )

            # Validate alarm name
            try:
                validated_name = validate_alarm_name(user_input[CONF_ALARM_NAME])
            except ValidationError as err:
                _LOGGER.debug("Alarm name validation failed: %s", err)
                errors[CONF_ALARM_NAME] = "invalid_name"

            # Validate time format
            try:
                hours, minutes = validate_time_format(user_input[CONF_ALARM_TIME])
                time_str = f"{hours:02d}:{minutes:02d}"
            except ValidationError as err:
                _LOGGER.debug("Time validation failed: %s", err)
                errors[CONF_ALARM_TIME] = "invalid_time"

            # Validate numeric fields
            numeric_validations = {
                CONF_SNOOZE_DURATION: (1, 60),
                CONF_MAX_SNOOZE_COUNT: (0, 10),
                CONF_AUTO_DISMISS_TIMEOUT: (1, 180),
                CONF_PRE_ALARM_DURATION: (0, 60),
                CONF_SCRIPT_TIMEOUT: (1, 300),
                CONF_SCRIPT_RETRY_COUNT: (0, 10),
            }

            for field, (min_val, max_val) in numeric_validations.items():
                if field in user_input:
                    try:
                        user_input[field] = validate_duration(
                            user_input[field], field, min_val, max_val
                        )
                    except ValidationError as err:
                        _LOGGER.debug("Validation failed for %s: %s", field, err)
                        errors[field] = "invalid_value"

            if errors:
                # Re-show form with errors
                use_defaults = user_input.get(CONF_USE_DEVICE_DEFAULTS, True)
                return self.async_show_form(
                    step_id="edit_alarm",
                    description_placeholders={
                        "alarm_name": alarm.data.name,
                        "info": "Edit alarm settings. If 'Use Device Defaults' is enabled, the alarm will use the device-level default scripts configured in Settings → Default Scripts.",
                    },
                    data_schema=self._build_edit_alarm_schema(alarm, use_defaults),
                    errors=errors,
                )

            # Update alarm with validated values
            alarm.data.name = validated_name
            alarm.data.time = time_str
            alarm.data.days = user_input.get(CONF_DAYS, alarm.data.days)
            alarm.data.snooze_duration = user_input.get(
                CONF_SNOOZE_DURATION, alarm.data.snooze_duration
            )
            alarm.data.max_snooze_count = user_input.get(
                CONF_MAX_SNOOZE_COUNT, alarm.data.max_snooze_count
            )
            alarm.data.auto_dismiss_timeout = user_input.get(
                CONF_AUTO_DISMISS_TIMEOUT, alarm.data.auto_dismiss_timeout
            )
            alarm.data.pre_alarm_duration = user_input.get(
                CONF_PRE_ALARM_DURATION, alarm.data.pre_alarm_duration
            )

            # Update script settings
            use_device_defaults = user_input.get(CONF_USE_DEVICE_DEFAULTS, True)
            alarm.data.use_device_defaults = use_device_defaults

            # If using device defaults, clear individual scripts
            # The coordinator will use device-level defaults instead
            if use_device_defaults:
                alarm.data.script_pre_alarm = None
                alarm.data.script_alarm = None
                alarm.data.script_post_alarm = None
                alarm.data.script_on_snooze = None
                alarm.data.script_on_dismiss = None
                alarm.data.script_on_arm = None
                alarm.data.script_on_cancel = None
                alarm.data.script_on_skip = None
                alarm.data.script_fallback = None
                alarm.data.script_timeout = DEFAULT_SCRIPT_TIMEOUT
                alarm.data.script_retry_count = DEFAULT_SCRIPT_RETRY_COUNT
            else:
                # Update alarm-specific scripts from form
                alarm.data.script_pre_alarm = user_input.get(CONF_SCRIPT_PRE_ALARM)
                alarm.data.script_alarm = user_input.get(CONF_SCRIPT_ALARM)
                alarm.data.script_post_alarm = user_input.get(CONF_SCRIPT_POST_ALARM)
                alarm.data.script_on_snooze = user_input.get(CONF_SCRIPT_ON_SNOOZE)
                alarm.data.script_on_dismiss = user_input.get(CONF_SCRIPT_ON_DISMISS)
                alarm.data.script_on_arm = user_input.get(CONF_SCRIPT_ON_ARM)
                alarm.data.script_on_cancel = user_input.get(CONF_SCRIPT_ON_CANCEL)
                alarm.data.script_on_skip = user_input.get(CONF_SCRIPT_ON_SKIP)
                alarm.data.script_fallback = user_input.get(CONF_SCRIPT_FALLBACK)
                alarm.data.script_timeout = user_input.get(CONF_SCRIPT_TIMEOUT, DEFAULT_SCRIPT_TIMEOUT)
                alarm.data.script_retry_count = user_input.get(
                    CONF_SCRIPT_RETRY_COUNT, DEFAULT_SCRIPT_RETRY_COUNT
                )

            try:
                await coordinator.async_update_alarm(alarm.data)
            except Exception as err:
                _LOGGER.error("Error updating alarm: %s", err, exc_info=True)
                return self.async_abort(reason="update_alarm_failed")
            return self.async_create_entry(title="", data={})

        # Show form with current alarm data
        return self.async_show_form(
            step_id="edit_alarm",
            description_placeholders={
                "alarm_name": alarm.data.name,
                "info": "Edit alarm settings. If 'Use Device Defaults' is enabled, the alarm will use the device-level default scripts configured in Settings → Default Scripts.",
            },
            data_schema=self._build_edit_alarm_schema(alarm),
        )

    async def async_step_default_scripts(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device-level default scripts configuration."""
        if user_input is not None:
            # Build updated options, removing cleared default script fields
            # When a field is cleared, it won't be in user_input, so we need to
            # explicitly remove it from the saved options
            updated_options = {
                k: v
                for k, v in self.config_entry.options.items()
                if not k.startswith("default_script_")
            }
            # Add the new values from user_input, but filter out empty strings and None
            # Empty strings occur when a user clears a previously set script field
            for key, value in user_input.items():
                if value is not None and value != "":
                    updated_options[key] = value

            # Save to config entry options
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=updated_options,
            )
            return self.async_create_entry(title="", data={})

        # Get current defaults from options
        # Filter out empty strings from stored values (legacy data cleanup)
        def get_option(key: str, default: Any = None) -> Any:
            """Get option value, treating empty strings as None."""
            value = self.config_entry.options.get(key, default)
            return None if value == "" else value

        return self.async_show_form(
            step_id="default_scripts",
            description_placeholders={
                "info": "Configure default scripts that will be used by all alarms with 'Use Device Defaults' enabled. These scripts apply automatically to new alarms.",
            },
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_PRE_ALARM,
                        description={
                            "suggested_value": get_option(CONF_DEFAULT_SCRIPT_PRE_ALARM)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ALARM,
                        description={
                            "suggested_value": get_option(CONF_DEFAULT_SCRIPT_ALARM)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_POST_ALARM,
                        description={
                            "suggested_value": get_option(CONF_DEFAULT_SCRIPT_POST_ALARM)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ON_SNOOZE,
                        description={
                            "suggested_value": get_option(CONF_DEFAULT_SCRIPT_ON_SNOOZE)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ON_DISMISS,
                        description={
                            "suggested_value": get_option(CONF_DEFAULT_SCRIPT_ON_DISMISS)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ON_ARM,
                        description={
                            "suggested_value": get_option(CONF_DEFAULT_SCRIPT_ON_ARM)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ON_CANCEL,
                        description={
                            "suggested_value": get_option(CONF_DEFAULT_SCRIPT_ON_CANCEL)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ON_SKIP,
                        description={
                            "suggested_value": get_option(CONF_DEFAULT_SCRIPT_ON_SKIP)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_FALLBACK,
                        description={
                            "suggested_value": get_option(CONF_DEFAULT_SCRIPT_FALLBACK)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_TIMEOUT,
                        description={
                            "suggested_value": get_option(
                                CONF_DEFAULT_SCRIPT_TIMEOUT, DEFAULT_SCRIPT_TIMEOUT
                            )
                        },
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=300,
                            step=1,
                            unit_of_measurement="seconds",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_RETRY_COUNT,
                        description={
                            "suggested_value": get_option(
                                CONF_DEFAULT_SCRIPT_RETRY_COUNT,
                                DEFAULT_SCRIPT_RETRY_COUNT,
                            )
                        },
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                }
            ),
        )

    async def async_step_global_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle global settings."""
        if user_input is not None:
            coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if coordinator:
                await coordinator.store.async_update_settings(user_input)
            return self.async_create_entry(title="", data={})

        coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
        current_settings = coordinator.store.settings if coordinator else {}

        return self.async_show_form(
            step_id="global_settings",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_WATCHDOG_TIMEOUT,
                        default=current_settings.get(
                            CONF_WATCHDOG_TIMEOUT, DEFAULT_WATCHDOG_TIMEOUT
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=10, max=300, step=10, unit_of_measurement="seconds"
                        )
                    ),
                    vol.Optional(
                        CONF_MISSED_ALARM_GRACE_PERIOD,
                        default=current_settings.get(
                            CONF_MISSED_ALARM_GRACE_PERIOD, DEFAULT_MISSED_ALARM_GRACE_PERIOD
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=60, step=1, unit_of_measurement="minutes"
                        )
                    ),
                }
            ),
        )
