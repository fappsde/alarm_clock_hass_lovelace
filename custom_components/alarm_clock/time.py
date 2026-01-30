"""Time entities for Alarm Clock integration."""

from __future__ import annotations

import logging
from datetime import time as dt_time
from typing import TYPE_CHECKING

from homeassistant.components.time import TimeEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import AlarmClockEntity

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
    """Set up alarm clock time entities."""
    coordinator: AlarmClockCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Create time entity for each alarm
    for _alarm_id, alarm in coordinator.alarms.items():
        entities.append(AlarmTimeEntity(coordinator, entry, alarm))

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
                AlarmTimeEntity(coordinator, entry, alarm),
            ]
        )

    coordinator.register_entity_adder_callback(add_alarm_entities)


class AlarmTimeEntity(AlarmClockEntity, TimeEntity):
    """Time entity for setting alarm time."""

    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator, entry, alarm) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator, entry, alarm)
        self._attr_unique_id = f"{entry.entry_id}_{alarm.data.alarm_id}_time"
        self._attr_name = f"{alarm.data.name} Time"

    @property
    def native_value(self) -> dt_time | None:
        """Return the current alarm time."""
        alarm = self.alarm
        if alarm is None:
            return None
        try:
            parts = alarm.data.time.split(":")
            if len(parts) >= 2:
                return dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, AttributeError, IndexError):
            pass
        return None

    async def async_set_value(self, value: dt_time) -> None:
        """Set the alarm time."""
        time_str = f"{value.hour:02d}:{value.minute:02d}"
        await self.coordinator.async_set_time(self.alarm_id, time_str)
