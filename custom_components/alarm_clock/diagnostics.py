"""Diagnostics support for Alarm Clock."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

TO_REDACT = {
    "script_pre_alarm",
    "script_alarm",
    "script_post_alarm",
    "script_on_snooze",
    "script_on_dismiss",
    "script_on_arm",
    "script_on_cancel",
    "script_on_skip",
    "script_fallback",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)

    if not coordinator:
        return {"error": "Coordinator not found"}

    alarms_data = []
    for alarm_id, alarm in coordinator.alarms.items():
        alarm_info = {
            "alarm_id": alarm_id,
            "name": alarm.data.name,
            "time": alarm.data.time,
            "enabled": alarm.data.enabled,
            "days": alarm.data.days,
            "one_time": alarm.data.one_time,
            "skip_next": alarm.data.skip_next,
            "snooze_duration": alarm.data.snooze_duration,
            "max_snooze_count": alarm.data.max_snooze_count,
            "auto_dismiss_timeout": alarm.data.auto_dismiss_timeout,
            "pre_alarm_duration": alarm.data.pre_alarm_duration,
            "state": alarm.state.value,
            "snooze_count": alarm.snooze_count,
            "next_trigger": (alarm.next_trigger.isoformat() if alarm.next_trigger else None),
            "last_triggered": (alarm.last_triggered.isoformat() if alarm.last_triggered else None),
            "scripts": async_redact_data(
                {
                    "script_pre_alarm": alarm.data.script_pre_alarm,
                    "script_alarm": alarm.data.script_alarm,
                    "script_post_alarm": alarm.data.script_post_alarm,
                    "script_on_snooze": alarm.data.script_on_snooze,
                    "script_on_dismiss": alarm.data.script_on_dismiss,
                    "script_on_arm": alarm.data.script_on_arm,
                    "script_on_cancel": alarm.data.script_on_cancel,
                    "script_on_skip": alarm.data.script_on_skip,
                    "script_fallback": alarm.data.script_fallback,
                },
                TO_REDACT,
            ),
        }
        alarms_data.append(alarm_info)

    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "version": entry.version,
        "alarms": alarms_data,
        "health_status": coordinator.health_status,
        "scheduled_callbacks": list(coordinator._scheduled_callbacks.keys()),
        "snooze_callbacks": list(coordinator._snooze_callbacks.keys()),
        "auto_dismiss_callbacks": list(coordinator._auto_dismiss_callbacks.keys()),
    }
