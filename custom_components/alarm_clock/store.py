"""Storage for Alarm Clock integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORE_KEY, STORE_VERSION
from .state_machine import AlarmData

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class AlarmClockStore:
    """Class to manage alarm clock data storage."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the store."""
        self.hass = hass
        self.entry = entry
        self._store = Store[dict[str, Any]](
            hass,
            STORE_VERSION,
            f"{STORE_KEY}_{entry.entry_id}",
        )
        self._data: dict[str, Any] = {
            "version": STORE_VERSION,
            "alarms": {},
            "runtime_states": {},
            "settings": {},
        }

    @property
    def alarms(self) -> dict[str, dict[str, Any]]:
        """Get all alarms."""
        return self._data.get("alarms", {})

    @property
    def runtime_states(self) -> dict[str, dict[str, Any]]:
        """Get runtime states for restoration."""
        return self._data.get("runtime_states", {})

    @property
    def settings(self) -> dict[str, Any]:
        """Get global settings."""
        return self._data.get("settings", {})

    async def async_load(self) -> None:
        """Load data from storage."""
        stored = await self._store.async_load()

        if stored is None:
            _LOGGER.debug("No stored data found, using defaults")
            return

        # Handle version migration
        stored_version = stored.get("version", 1)
        if stored_version < STORE_VERSION:
            stored = await self._migrate_data(stored, stored_version)

        self._data = stored
        _LOGGER.debug("Loaded %d alarms from storage", len(self.alarms))

    async def async_save(self) -> None:
        """Save data to storage."""
        await self._store.async_save(self._data)
        _LOGGER.debug("Saved %d alarms to storage", len(self.alarms))

    async def _migrate_data(
        self, data: dict[str, Any], from_version: int
    ) -> dict[str, Any]:
        """Migrate data from older versions."""
        _LOGGER.info("Migrating storage from version %d to %d", from_version, STORE_VERSION)

        # Version 1 -> 2 migration (example for future use)
        if from_version < 2:
            # Add any new fields with defaults
            for alarm_id, alarm_data in data.get("alarms", {}).items():
                if "gradual_volume" not in alarm_data:
                    alarm_data["gradual_volume"] = False
                if "gradual_volume_duration" not in alarm_data:
                    alarm_data["gradual_volume_duration"] = 5

        data["version"] = STORE_VERSION
        return data

    async def async_add_alarm(self, alarm_data: AlarmData) -> None:
        """Add a new alarm."""
        self._data["alarms"][alarm_data.alarm_id] = alarm_data.to_dict()
        await self.async_save()
        _LOGGER.debug("Added alarm: %s", alarm_data.alarm_id)

    async def async_update_alarm(self, alarm_data: AlarmData) -> None:
        """Update an existing alarm."""
        if alarm_data.alarm_id not in self._data["alarms"]:
            _LOGGER.warning("Attempted to update non-existent alarm: %s", alarm_data.alarm_id)
            return

        self._data["alarms"][alarm_data.alarm_id] = alarm_data.to_dict()
        await self.async_save()
        _LOGGER.debug("Updated alarm: %s", alarm_data.alarm_id)

    async def async_remove_alarm(self, alarm_id: str) -> bool:
        """Remove an alarm."""
        if alarm_id not in self._data["alarms"]:
            return False

        del self._data["alarms"][alarm_id]

        # Also remove runtime state
        if alarm_id in self._data.get("runtime_states", {}):
            del self._data["runtime_states"][alarm_id]

        await self.async_save()
        _LOGGER.debug("Removed alarm: %s", alarm_id)
        return True

    async def async_save_runtime_state(
        self, alarm_id: str, state_data: dict[str, Any]
    ) -> None:
        """Save runtime state for an alarm."""
        if "runtime_states" not in self._data:
            self._data["runtime_states"] = {}

        self._data["runtime_states"][alarm_id] = state_data
        await self.async_save()

    def get_runtime_state(self, alarm_id: str) -> dict[str, Any] | None:
        """Get runtime state for an alarm."""
        return self._data.get("runtime_states", {}).get(alarm_id)

    async def async_update_settings(self, settings: dict[str, Any]) -> None:
        """Update global settings."""
        self._data["settings"] = settings
        await self.async_save()

    def get_alarm(self, alarm_id: str) -> AlarmData | None:
        """Get an alarm by ID."""
        alarm_dict = self._data.get("alarms", {}).get(alarm_id)
        if alarm_dict is None:
            return None
        return AlarmData.from_dict(alarm_dict)

    def get_all_alarms(self) -> list[AlarmData]:
        """Get all alarms as AlarmData objects."""
        return [
            AlarmData.from_dict(data)
            for data in self._data.get("alarms", {}).values()
        ]

    async def async_clear_all(self) -> None:
        """Clear all stored data."""
        self._data = {
            "version": STORE_VERSION,
            "alarms": {},
            "runtime_states": {},
            "settings": {},
        }
        await self.async_save()
        _LOGGER.info("Cleared all alarm clock storage")

    def validate_alarms(self) -> dict[str, list[str]]:
        """Validate all alarms and return errors by alarm_id."""
        errors: dict[str, list[str]] = {}

        for alarm_id, alarm_dict in self._data.get("alarms", {}).items():
            try:
                alarm = AlarmData.from_dict(alarm_dict)
                alarm_errors = alarm.validate()
                if alarm_errors:
                    errors[alarm_id] = alarm_errors
            except (KeyError, TypeError, ValueError) as err:
                errors[alarm_id] = [f"Invalid alarm data: {err}"]

        return errors
