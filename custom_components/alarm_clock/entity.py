"""Base entity for Alarm Clock integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import AlarmClockCoordinator
    from .state_machine import AlarmStateMachine

_LOGGER = logging.getLogger(__name__)


class AlarmClockEntity(RestoreEntity):
    """Base class for alarm clock entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: AlarmClockCoordinator,
        entry: ConfigEntry,
        alarm: AlarmStateMachine,
    ) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator
        self.entry = entry
        self._alarm = alarm
        self._alarm_id = alarm.data.alarm_id  # Cache the ID for safety
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or "Alarm Clock",
            manufacturer="Custom Integration",
            model="Smart Alarm Clock",
            sw_version="1.0.0",
        )

    @property
    def alarm(self) -> AlarmStateMachine | None:
        """Return the alarm state machine, or None if no longer available."""
        # Prefer the live version from coordinator if available
        if self._alarm_id in self.coordinator.alarms:
            return self.coordinator.alarms[self._alarm_id]
        # Fall back to cached reference (may be stale but prevents crashes)
        return self._alarm

    @property
    def alarm_id(self) -> str:
        """Return the alarm ID."""
        return self._alarm_id

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._alarm_id in self.coordinator.alarms

    async def async_added_to_hass(self) -> None:
        """Handle entity added to Home Assistant."""
        await super().async_added_to_hass()

        # Register for updates
        self.async_on_remove(self.coordinator.register_update_callback(self.async_write_ha_state))

        # Restore state if available
        if (last_state := await self.async_get_last_state()) is not None:
            await self._async_restore_state(last_state)

    async def _async_restore_state(self, state) -> None:
        """Restore entity state from last known state."""
        # Override in subclasses as needed
        pass


class AlarmClockDeviceEntity(Entity):
    """Base class for device-level alarm clock entities (not per-alarm)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: AlarmClockCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or "Alarm Clock",
            manufacturer="Custom Integration",
            model="Smart Alarm Clock",
            sw_version="1.0.0",
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity added to Home Assistant."""
        await super().async_added_to_hass()

        # Register for updates
        self.async_on_remove(self.coordinator.register_update_callback(self.async_write_ha_state))
