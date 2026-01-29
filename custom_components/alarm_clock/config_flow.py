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
    CONF_SCRIPT_ON_DISMISS,
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
            # Validate time format - TimeSelector can return dict, "HH:MM", or "HH:MM:SS"
            try:
                time_value = user_input[CONF_ALARM_TIME]
                if isinstance(time_value, dict):
                    # TimeSelector may return dict with hours and minutes
                    hour = time_value.get("hours", 0)
                    minute = time_value.get("minutes", 0)
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError("Out of range")
                else:
                    # String format validation - handle both "HH:MM" and "HH:MM:SS"
                    time_str = str(time_value)
                    parts = time_str.split(":")
                    if len(parts) < 2:
                        raise ValueError("Invalid format")
                    hour, minute = int(parts[0]), int(parts[1])
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError("Out of range")
            except (ValueError, AttributeError, TypeError) as err:
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
        if user_input is not None:
            # Check if only the toggle was changed - if so, re-show form with updated schema
            if CONF_USE_DEVICE_DEFAULTS in user_input:
                # Update the alarm data with the toggle value
                self._alarm_data[CONF_USE_DEVICE_DEFAULTS] = user_input[CONF_USE_DEVICE_DEFAULTS]

                # If only the toggle was provided (form just toggled, not submitted)
                # Re-show the form with updated schema
                if len(user_input) <= 5:  # Only basic fields + toggle
                    # Re-show form to update visible fields
                    pass  # Fall through to show form again
                else:
                    # Full form submission - proceed with creating alarm
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
                            time_str = f"{time_value.get('hours', 0):02d}:{time_value.get('minutes', 0):02d}"
                        else:
                            # Handle "HH:MM" or "HH:MM:SS" format - only keep HH:MM
                            time_parts = str(time_value).split(":")
                            time_str = f"{int(time_parts[0]):02d}:{int(time_parts[1]):02d}"

                        new_alarm = AlarmData(
                            alarm_id=alarm_id,
                            name=alarm_data[CONF_ALARM_NAME],
                            time=time_str,
                            days=alarm_data.get(CONF_DAYS, WEEKDAYS[:5]),
                            one_time=alarm_data.get(CONF_ONE_TIME, False),
                            enabled=alarm_data.get(CONF_ENABLED, True),
                            snooze_duration=alarm_data.get(
                                CONF_SNOOZE_DURATION, DEFAULT_SNOOZE_DURATION
                            ),
                            max_snooze_count=alarm_data.get(
                                CONF_MAX_SNOOZE_COUNT, DEFAULT_MAX_SNOOZE_COUNT
                            ),
                            auto_dismiss_timeout=alarm_data.get(
                                CONF_AUTO_DISMISS_TIMEOUT, DEFAULT_AUTO_DISMISS_TIMEOUT
                            ),
                            pre_alarm_duration=alarm_data.get(
                                CONF_PRE_ALARM_DURATION, DEFAULT_PRE_ALARM_DURATION
                            ),
                            use_device_defaults=alarm_data.get(CONF_USE_DEVICE_DEFAULTS, True),
                            script_pre_alarm=alarm_data.get(CONF_SCRIPT_PRE_ALARM),
                            script_alarm=alarm_data.get(CONF_SCRIPT_ALARM),
                            script_post_alarm=alarm_data.get(CONF_SCRIPT_POST_ALARM),
                            script_on_snooze=alarm_data.get(CONF_SCRIPT_ON_SNOOZE),
                            script_on_dismiss=alarm_data.get(CONF_SCRIPT_ON_DISMISS),
                            script_fallback=alarm_data.get(CONF_SCRIPT_FALLBACK),
                            script_timeout=alarm_data.get(
                                CONF_SCRIPT_TIMEOUT, DEFAULT_SCRIPT_TIMEOUT
                            ),
                            script_retry_count=alarm_data.get(
                                CONF_SCRIPT_RETRY_COUNT, DEFAULT_SCRIPT_RETRY_COUNT
                            ),
                        )
                        await coordinator.async_add_alarm(new_alarm)

                    # Clear the alarm data after successful submission
                    self._alarm_data = {}

                    return self.async_create_entry(title="", data={})

        # Build schema conditionally based on use_device_defaults
        use_defaults = self._alarm_data.get(CONF_USE_DEVICE_DEFAULTS, True)

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

        alarm_name = self._alarm_data.get(CONF_ALARM_NAME, "New Alarm")
        return self.async_show_form(
            step_id="alarm_advanced",
            description_placeholders={
                "alarm_name": alarm_name,
                "info": "Configure advanced alarm settings. If 'Use Device Defaults' is enabled, the alarm will use the device-level default scripts configured in Settings → Default Scripts.",
            },
            data_schema=vol.Schema(schema_dict),
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
                    await coordinator.async_remove_alarm(alarm_id)
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

        if user_input is not None:
            # Update alarm
            alarm.data.name = user_input[CONF_ALARM_NAME]

            time_value = user_input[CONF_ALARM_TIME]
            if isinstance(time_value, dict):
                alarm.data.time = (
                    f"{time_value.get('hours', 0):02d}:{time_value.get('minutes', 0):02d}"
                )
            else:
                # Handle "HH:MM" or "HH:MM:SS" format - only keep HH:MM
                time_parts = str(time_value).split(":")
                alarm.data.time = f"{int(time_parts[0]):02d}:{int(time_parts[1]):02d}"

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

            await coordinator.async_update_alarm(alarm.data)
            return self.async_create_entry(title="", data={})

        # Parse current time
        try:
            hour, minute = map(int, alarm.data.time.split(":"))
            current_time = {"hours": hour, "minutes": minute}
        except (ValueError, AttributeError):
            current_time = {"hours": 7, "minutes": 0}

        return self.async_show_form(
            step_id="edit_alarm",
            data_schema=vol.Schema(
                {
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
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=0, max=10, step=1)
                    ),
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
                }
            ),
        )

    async def async_step_default_scripts(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device-level default scripts configuration."""
        if user_input is not None:
            # Save to config entry options
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={**self.config_entry.options, **user_input},
            )
            return self.async_create_entry(title="", data={})

        # Get current defaults from options
        current_options = self.config_entry.options

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
                            "suggested_value": current_options.get(CONF_DEFAULT_SCRIPT_PRE_ALARM)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ALARM,
                        description={
                            "suggested_value": current_options.get(CONF_DEFAULT_SCRIPT_ALARM)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_POST_ALARM,
                        description={
                            "suggested_value": current_options.get(CONF_DEFAULT_SCRIPT_POST_ALARM)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ON_SNOOZE,
                        description={
                            "suggested_value": current_options.get(CONF_DEFAULT_SCRIPT_ON_SNOOZE)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ON_DISMISS,
                        description={
                            "suggested_value": current_options.get(CONF_DEFAULT_SCRIPT_ON_DISMISS)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ON_ARM,
                        description={
                            "suggested_value": current_options.get(CONF_DEFAULT_SCRIPT_ON_ARM)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ON_CANCEL,
                        description={
                            "suggested_value": current_options.get(CONF_DEFAULT_SCRIPT_ON_CANCEL)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_ON_SKIP,
                        description={
                            "suggested_value": current_options.get(CONF_DEFAULT_SCRIPT_ON_SKIP)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_FALLBACK,
                        description={
                            "suggested_value": current_options.get(CONF_DEFAULT_SCRIPT_FALLBACK)
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="script",
                        )
                    ),
                    vol.Optional(
                        CONF_DEFAULT_SCRIPT_TIMEOUT,
                        description={
                            "suggested_value": current_options.get(
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
                            "suggested_value": current_options.get(
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
