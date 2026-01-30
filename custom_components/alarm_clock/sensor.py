"""Sensor entities for Alarm Clock integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, AlarmState
from .entity import AlarmClockDeviceEntity, AlarmClockEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .coordinator import AlarmClockCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up alarm clock sensor entities."""
    coordinator: AlarmClockCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Create state and next trigger sensors for each alarm
    for _alarm_id, alarm in coordinator.alarms.items():
        entities.append(AlarmStateSensor(coordinator, entry, alarm))
        entities.append(AlarmNextTriggerSensor(coordinator, entry, alarm))
        entities.append(AlarmSnoozeCountSensor(coordinator, entry, alarm))

    # Create device-level sensors
    entities.append(NextAlarmSensor(coordinator, entry))
    entities.append(ActiveAlarmCountSensor(coordinator, entry))

    async_add_entities(entities)

    # Register callback for dynamically adding entities when new alarms are created
    def add_alarm_entities(alarm_id: str) -> None:
        """Add entities for a new alarm with safety check."""
        # Safety check: ensure alarm still exists (prevents race condition)
        if alarm_id not in coordinator.alarms:
            _LOGGER.warning(
                "Skipping entity creation for alarm %s - alarm no longer exists",
                alarm_id,
            )
            return
        alarm = coordinator.alarms[alarm_id]
        async_add_entities(
            [
                AlarmStateSensor(coordinator, entry, alarm),
                AlarmNextTriggerSensor(coordinator, entry, alarm),
                AlarmSnoozeCountSensor(coordinator, entry, alarm),
            ]
        )

    coordinator.register_entity_adder_callback(add_alarm_entities)


class AlarmStateSensor(AlarmClockEntity, SensorEntity):
    """Sensor showing the current state of an alarm."""

    _attr_icon = "mdi:alarm-check"

    def __init__(self, coordinator, entry, alarm) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, alarm)
        self._attr_unique_id = f"{entry.entry_id}_{alarm.data.alarm_id}_state"
        self._attr_name = f"{alarm.data.name} State"

    @property
    def native_value(self) -> str:
        """Return the current state."""
        alarm = self.alarm
        if alarm is None:
            return AlarmState.DISABLED.value
        return alarm.state.value

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        alarm = self.alarm
        if alarm is None:
            return "mdi:alarm-off"
        icons = {
            AlarmState.DISABLED: "mdi:alarm-off",
            AlarmState.ARMED: "mdi:alarm",
            AlarmState.PRE_ALARM: "mdi:alarm-note",
            AlarmState.RINGING: "mdi:alarm-light",
            AlarmState.SNOOZED: "mdi:alarm-snooze",
            AlarmState.DISMISSED: "mdi:alarm-check",
            AlarmState.AUTO_DISMISSED: "mdi:alarm-check",
            AlarmState.MISSED: "mdi:alarm-multiple",
        }
        return icons.get(alarm.state, "mdi:alarm")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        alarm = self.alarm
        if alarm is None:
            return {}
        return {
            "alarm_id": alarm.data.alarm_id,
            "alarm_time": alarm.data.time,
            "enabled": alarm.data.enabled,
            "trigger_type": alarm.current_trigger_type,
            "ringing_start_time": (
                alarm.ringing_start_time.isoformat() if alarm.ringing_start_time else None
            ),
        }


class AlarmNextTriggerSensor(AlarmClockEntity, SensorEntity):
    """Sensor showing the next trigger time for an alarm."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-alert-outline"

    def __init__(self, coordinator, entry, alarm) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, alarm)
        self._attr_unique_id = f"{entry.entry_id}_{alarm.data.alarm_id}_next_trigger"
        self._attr_name = f"{alarm.data.name} Next Trigger"

    @property
    def native_value(self) -> datetime | None:
        """Return the next trigger time."""
        alarm = self.alarm
        if alarm is None:
            return None
        return alarm.next_trigger

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        alarm = self.alarm
        if alarm is None:
            return {}
        attrs: dict[str, Any] = {
            "skip_next": alarm.data.skip_next,
        }

        # Calculate time until trigger
        if alarm.next_trigger:
            now = dt_util.now()
            if alarm.next_trigger > now:
                delta = alarm.next_trigger - now
                total_minutes = int(delta.total_seconds() / 60)
                hours, minutes = divmod(total_minutes, 60)
                attrs["time_until"] = f"{hours}h {minutes}m"
                attrs["minutes_until"] = total_minutes

        return attrs


class AlarmSnoozeCountSensor(AlarmClockEntity, SensorEntity):
    """Sensor showing the current snooze count for an alarm."""

    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, entry, alarm) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, alarm)
        self._attr_unique_id = f"{entry.entry_id}_{alarm.data.alarm_id}_snooze_count"
        self._attr_name = f"{alarm.data.name} Snooze Count"

    @property
    def native_value(self) -> int:
        """Return the current snooze count."""
        alarm = self.alarm
        if alarm is None:
            return 0
        return alarm.snooze_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        alarm = self.alarm
        if alarm is None:
            return {}
        return {
            "max_snooze_count": alarm.data.max_snooze_count,
            "snoozes_remaining": max(0, alarm.data.max_snooze_count - alarm.snooze_count),
            "snooze_duration": alarm.data.snooze_duration,
            "snooze_end_time": (
                alarm.snooze_end_time.isoformat() if alarm.snooze_end_time else None
            ),
        }


class NextAlarmSensor(AlarmClockDeviceEntity, SensorEntity):
    """Sensor showing the next alarm to trigger across all alarms."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:alarm-bell"

    def __init__(self, coordinator, entry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_alarm"
        self._attr_name = "Next Alarm"

    @property
    def native_value(self) -> datetime | None:
        """Return the next alarm trigger time."""
        next_trigger = None
        for alarm in self.coordinator.alarms.values():
            if alarm.next_trigger:
                if next_trigger is None or alarm.next_trigger < next_trigger:
                    next_trigger = alarm.next_trigger
        return next_trigger

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        next_alarm = None
        next_trigger = None

        for alarm in self.coordinator.alarms.values():
            if alarm.next_trigger:
                if next_trigger is None or alarm.next_trigger < next_trigger:
                    next_trigger = alarm.next_trigger
                    next_alarm = alarm

        attrs: dict[str, Any] = {
            "entry_id": self.entry.entry_id,
            "total_alarms": len(self.coordinator.alarms),
            "enabled_alarms": sum(1 for a in self.coordinator.alarms.values() if a.data.enabled),
        }

        if next_alarm:
            attrs["next_alarm_id"] = next_alarm.data.alarm_id
            attrs["next_alarm_name"] = next_alarm.data.name
            attrs["next_alarm_time"] = next_alarm.data.time

            # Calculate time until
            now = dt_util.now()
            if next_trigger and next_trigger > now:
                delta = next_trigger - now
                total_minutes = int(delta.total_seconds() / 60)
                hours, minutes = divmod(total_minutes, 60)
                attrs["time_until"] = f"{hours}h {minutes}m"
                attrs["minutes_until"] = total_minutes

        return attrs


class ActiveAlarmCountSensor(AlarmClockDeviceEntity, SensorEntity):
    """Sensor showing the count of currently active (ringing/snoozed) alarms."""

    _attr_icon = "mdi:alarm-multiple"

    def __init__(self, coordinator, entry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_active_alarm_count"
        self._attr_name = "Active Alarms"

    @property
    def native_value(self) -> int:
        """Return the count of active alarms."""
        return sum(
            1
            for a in self.coordinator.alarms.values()
            if a.state in (AlarmState.RINGING, AlarmState.SNOOZED, AlarmState.PRE_ALARM)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        active_alarms = [
            {
                "alarm_id": a.data.alarm_id,
                "alarm_name": a.data.name,
                "state": a.state.value,
            }
            for a in self.coordinator.alarms.values()
            if a.state in (AlarmState.RINGING, AlarmState.SNOOZED, AlarmState.PRE_ALARM)
        ]

        return {
            "entry_id": self.entry.entry_id,
            "ringing": sum(
                1 for a in self.coordinator.alarms.values() if a.state == AlarmState.RINGING
            ),
            "snoozed": sum(
                1 for a in self.coordinator.alarms.values() if a.state == AlarmState.SNOOZED
            ),
            "pre_alarm": sum(
                1 for a in self.coordinator.alarms.values() if a.state == AlarmState.PRE_ALARM
            ),
            "active_alarms": active_alarms,
        }
