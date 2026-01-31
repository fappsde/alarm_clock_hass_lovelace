"""Alarm Clock integration for Home Assistant."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import AlarmClockCoordinator
from .store import AlarmClockStore

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

# Config schema for the integration
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Alarm Clock component."""
    hass.data.setdefault(DOMAIN, {})
    
    _LOGGER.info(
        "Alarm Clock backend integration loaded. "
        "Install the Alarm Clock Card from HACS for UI support."
    )
    
    return True


async def _async_cleanup_orphan_entities(
    hass: HomeAssistant, entry: ConfigEntry, valid_alarm_ids: set[str]
) -> None:
    """Remove orphan entities that reference non-existent alarms."""
    entity_registry = er.async_get(hass)
    entities_to_remove = []

    # Find entities belonging to this config entry
    for entity_id, entity_entry in entity_registry.entities.items():
        if entity_entry.config_entry_id != entry.entry_id:
            continue

        # Check if this entity is for a specific alarm (not a device-level entity)
        unique_id = entity_entry.unique_id or ""
        # Device-level entities don't have alarm IDs in their unique_id
        # Alarm-specific entities have format: {entry_id}_{alarm_id}_{entity_type}
        if not unique_id.startswith(entry.entry_id):
            continue

        # Extract potential alarm_id from unique_id
        # Format: {entry_id}_{alarm_id}_{entity_type}
        parts = unique_id.split("_")
        if len(parts) >= 3:
            # Reconstruct the alarm_id (it might contain underscores)
            # The alarm_id is between entry_id and the last part (entity_type)
            potential_alarm_id = "_".join(parts[1:-1])

            # Skip device-level entities (they don't have alarm_ prefix)
            if not potential_alarm_id.startswith("alarm_"):
                continue

            # Check if this alarm still exists
            if potential_alarm_id not in valid_alarm_ids:
                entities_to_remove.append((entity_id, potential_alarm_id))

    # Remove orphan entities
    for entity_id, alarm_id in entities_to_remove:
        _LOGGER.info(
            "Removing orphan entity %s (alarm %s no longer exists)",
            entity_id,
            alarm_id,
        )
        entity_registry.async_remove(entity_id)

    if entities_to_remove:
        _LOGGER.info("Cleaned up %d orphan entities", len(entities_to_remove))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alarm Clock from a config entry."""
    _LOGGER.debug("Setting up Alarm Clock integration: %s", entry.entry_id)

    try:
        # Initialize store for persistent data
        store = AlarmClockStore(hass, entry)
        try:
            await store.async_load()
        except Exception as store_err:
            _LOGGER.error(
                "Error loading alarm clock storage, starting with empty state: %s",
                store_err,
                exc_info=True,
            )
            # Continue with empty store - alarms will need to be recreated

        # Clean up orphan entities before creating new ones
        try:
            valid_alarm_ids = {alarm.alarm_id for alarm in store.get_all_alarms()}
            await _async_cleanup_orphan_entities(hass, entry, valid_alarm_ids)
        except Exception as cleanup_err:
            _LOGGER.warning("Error cleaning up orphan entities: %s", cleanup_err)

        # Create coordinator
        coordinator = AlarmClockCoordinator(hass, entry, store)

        # Store coordinator
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Register device
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or "Alarm Clock",
            manufacturer="Custom Integration",
            model="Smart Alarm Clock",
            sw_version="1.0.0",
        )

        # CRITICAL: Start the coordinator BEFORE setting up platforms
        # This ensures alarms are loaded from storage before entities try to access them
        await coordinator.async_start()

        # Setup platforms with timeout protection - entities can now access coordinator.alarms
        try:
            await asyncio.wait_for(
                hass.config_entries.async_forward_entry_setups(entry, PLATFORMS),
                timeout=30.0,  # 30 second timeout for platform setup
            )
        except TimeoutError:
            _LOGGER.error(
                "Timeout setting up platforms for Alarm Clock integration. "
                "This may indicate a configuration issue."
            )
            # Stop coordinator since setup failed
            await coordinator.async_stop()
            if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
                hass.data[DOMAIN].pop(entry.entry_id)
            return False

        # Validate referenced entities after startup
        await coordinator.async_validate_entities()

        # Register services
        await coordinator.async_register_services()

        _LOGGER.info("Alarm Clock integration setup complete: %s", entry.entry_id)
        return True

    except Exception as err:
        _LOGGER.exception("Error setting up Alarm Clock integration: %s", err)
        # Clean up if setup fails
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Alarm Clock integration: %s", entry.entry_id)

    unload_ok = True

    try:
        coordinator: AlarmClockCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)

        if coordinator is None:
            _LOGGER.warning(
                "Coordinator not found for entry %s, skipping coordinator cleanup",
                entry.entry_id,
            )
        else:
            # Stop the coordinator first (this saves runtime states and unregisters services)
            _LOGGER.debug("Stopping coordinator")
            try:
                await coordinator.async_stop()
            except Exception as err:
                _LOGGER.error("Error stopping coordinator: %s", err, exc_info=True)
                # Continue with unload even if coordinator stop fails

        # Unload platforms (do this even if coordinator stop failed)
        _LOGGER.debug("Unloading platforms")
        try:
            unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        except Exception as err:
            _LOGGER.error("Error unloading platforms: %s", err, exc_info=True)
            unload_ok = False

        # Clean up from hass.data regardless of unload status
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id, None)

        if unload_ok:
            _LOGGER.info("Alarm Clock integration unloaded successfully: %s", entry.entry_id)
        else:
            _LOGGER.warning("Failed to unload some platforms for entry: %s", entry.entry_id)

        return unload_ok

    except Exception as err:
        _LOGGER.error("Error unloading Alarm Clock integration: %s", err, exc_info=True)
        # Try to clean up anyway to prevent lingering state
        try:
            if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
                hass.data[DOMAIN].pop(entry.entry_id, None)
        except Exception:
            pass
        return False


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry to new version."""
    _LOGGER.debug(
        "Migrating from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    if config_entry.version == 1:
        # Future migration logic here
        pass

    _LOGGER.info(
        "Migration to version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )
    return True
