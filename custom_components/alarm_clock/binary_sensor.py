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
                AlarmRingingSensor(coordinator, entry, alarm),
            ]
        )

    coordinator.register_entity_adder_callback(add_alarm_entities)


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
        alarm = self.alarm
        if alarm is None:
            return False
        return alarm.state in (AlarmState.RINGING, AlarmState.SNOOZED)

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        alarm = self.alarm
        if alarm is None:
            return "mdi:alarm-off"
        if alarm.state == AlarmState.RINGING:
            return "mdi:alarm-light"
        elif alarm.state == AlarmState.SNOOZED:
            return "mdi:alarm-snooze"
        return "mdi:alarm-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        alarm = self.alarm
        if alarm is None:
            return {}
        return {
            "alarm_state": alarm.state.value,
            "snooze_count": alarm.snooze_count,
            "max_snooze_count": alarm.data.max_snooze_count,
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
