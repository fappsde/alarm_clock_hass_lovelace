"""Binary sensor entities for Alarm Clock integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    """Set up alarm clock binary sensor entities."""
    coordinator: AlarmClockCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # Create ringing sensor for each alarm
    for _alarm_id, alarm in coordinator.alarms.items():
        entities.append(AlarmRingingSensor(coordinator, entry, alarm))

    # Create device-level sensors
    entities.append(AlarmClockHealthSensor(coordinator, entry))
    entities.append(AnyAlarmRingingSensor(coordinator, entry))

    async_add_entities(entities)

    # Register callback for dynamically adding entities when new alarms are created
    coordinator.register_entity_adder_callback(
        lambda alarm_id: async_add_entities(
            [
                AlarmRingingSensor(coordinator, entry, coordinator.alarms[alarm_id]),
            ]
        )
    )


class AlarmRingingSensor(AlarmClockEntity, BinarySensorEntity):
    """Binary sensor that is on when alarm is ringing."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator, entry, alarm) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, alarm)
        self._attr_unique_id = f"{entry.entry_id}_{alarm.data.alarm_id}_ringing"
        self._attr_name = f"{alarm.data.name} Ringing"

    @property
    def is_on(self) -> bool:
        """Return true if alarm is ringing or snoozed."""
        return self.alarm.state in (AlarmState.RINGING, AlarmState.SNOOZED)

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        if self.alarm.state == AlarmState.RINGING:
            return "mdi:alarm-light"
        elif self.alarm.state == AlarmState.SNOOZED:
            return "mdi:alarm-snooze"
        return "mdi:alarm-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "alarm_state": self.alarm.state.value,
            "snooze_count": self.alarm.snooze_count,
            "max_snooze_count": self.alarm.data.max_snooze_count,
        }


class AlarmClockHealthSensor(AlarmClockDeviceEntity, BinarySensorEntity):
    """Binary sensor for alarm clock health status."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:heart-pulse"

    def __init__(self, coordinator, entry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_health"
        self._attr_name = "Health"

    @property
    def is_on(self) -> bool:
        """Return true if there are health issues (problem detected)."""
        return not self.coordinator.health_status.get("healthy", True)

    @property
    def icon(self) -> str:
        """Return icon based on health status."""
        if self.is_on:
            return "mdi:heart-broken"
        return "mdi:heart-pulse"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "last_check": self.coordinator.health_status.get("last_check"),
            "issues": self.coordinator.health_status.get("issues", []),
            "alarm_count": self.coordinator.health_status.get("alarm_count", 0),
            "active_alarms": self.coordinator.health_status.get("active_alarms", 0),
        }


class AnyAlarmRingingSensor(AlarmClockDeviceEntity, BinarySensorEntity):
    """Binary sensor that is on when any alarm is ringing."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:alarm-light"

    def __init__(self, coordinator, entry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_any_ringing"
        self._attr_name = "Any Alarm Ringing"

    @property
    def is_on(self) -> bool:
        """Return true if any alarm is ringing."""
        return any(
            a.state in (AlarmState.RINGING, AlarmState.SNOOZED, AlarmState.PRE_ALARM)
            for a in self.coordinator.alarms.values()
        )

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        if self.is_on:
            return "mdi:alarm-light"
        return "mdi:alarm-check"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        ringing_alarms = [
            {
                "alarm_id": a.data.alarm_id,
                "alarm_name": a.data.name,
                "state": a.state.value,
            }
            for a in self.coordinator.alarms.values()
            if a.state in (AlarmState.RINGING, AlarmState.SNOOZED, AlarmState.PRE_ALARM)
        ]

        return {
            "ringing_alarms": ringing_alarms,
            "count": len(ringing_alarms),
        }
