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
    CONF_SNOOZE_DURATION,
    CONF_WATCHDOG_TIMEOUT,
    DEFAULT_AUTO_DISMISS_TIMEOUT,
    DEFAULT_MAX_SNOOZE_COUNT,
    DEFAULT_MISSED_ALARM_GRACE_PERIOD,
    DEFAULT_PRE_ALARM_DURATION,
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
            menu_options=["add_alarm", "manage_alarms", "global_settings"],
        )

    async def async_step_add_alarm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle adding a new alarm."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate time format
            try:
                parts = user_input[CONF_ALARM_TIME].split(":")
                if len(parts) != 2:
                    raise ValueError("Invalid format")
                hour, minute = int(parts[0]), int(parts[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Out of range")
            except (ValueError, AttributeError):
                errors[CONF_ALARM_TIME] = "invalid_time"

            if not errors:
                # Store alarm data for advanced settings
                self._alarm_data = user_input
                return await self.async_step_alarm_advanced()

        return self.async_show_form(
            step_id="add_alarm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ALARM_NAME): cv.string,
                    vol.Required(CONF_ALARM_TIME): selector.TimeSelector(),
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
            # Merge with basic alarm data
            alarm_data = {**self._alarm_data, **user_input}

            # Add the alarm via coordinator
            coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if coordinator:
                import uuid

                from .state_machine import AlarmData

                alarm_id = f"alarm_{uuid.uuid4().hex[:8]}"

                # Convert time selector output to string
                time_value = alarm_data[CONF_ALARM_TIME]
                if isinstance(time_value, dict):
                    time_str = (
                        f"{time_value.get('hours', 0):02d}:{time_value.get('minutes', 0):02d}"
                    )
                else:
                    time_str = str(time_value)

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
                    script_pre_alarm=alarm_data.get(CONF_SCRIPT_PRE_ALARM),
                    script_alarm=alarm_data.get(CONF_SCRIPT_ALARM),
                    script_post_alarm=alarm_data.get(CONF_SCRIPT_POST_ALARM),
                    script_on_snooze=alarm_data.get(CONF_SCRIPT_ON_SNOOZE),
                    script_on_dismiss=alarm_data.get(CONF_SCRIPT_ON_DISMISS),
                    script_fallback=alarm_data.get(CONF_SCRIPT_FALLBACK),
                )
                await coordinator.async_add_alarm(new_alarm)

            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="alarm_advanced",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SNOOZE_DURATION, default=DEFAULT_SNOOZE_DURATION
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=60, step=1, unit_of_measurement="minutes"
                        )
                    ),
                    vol.Optional(
                        CONF_MAX_SNOOZE_COUNT, default=DEFAULT_MAX_SNOOZE_COUNT
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=0, max=10, step=1)
                    ),
                    vol.Optional(
                        CONF_AUTO_DISMISS_TIMEOUT, default=DEFAULT_AUTO_DISMISS_TIMEOUT
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=180, step=1, unit_of_measurement="minutes"
                        )
                    ),
                    vol.Optional(
                        CONF_PRE_ALARM_DURATION, default=DEFAULT_PRE_ALARM_DURATION
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=60, step=1, unit_of_measurement="minutes"
                        )
                    ),
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
                }
            ),
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
                alarm.data.time = str(time_value)

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
