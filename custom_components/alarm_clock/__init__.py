"""Alarm Clock integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import AlarmClockCoordinator
from .store import AlarmClockStore

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Alarm Clock component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alarm Clock from a config entry."""
    _LOGGER.debug("Setting up Alarm Clock integration: %s", entry.entry_id)

    # Initialize store for persistent data
    store = AlarmClockStore(hass, entry)
    await store.async_load()

    # Create coordinator
    coordinator = AlarmClockCoordinator(hass, entry, store)

    # Validate referenced entities on startup
    await coordinator.async_validate_entities()

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

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start the coordinator scheduler
    await coordinator.async_start()

    # Register services
    await coordinator.async_register_services()

    _LOGGER.info("Alarm Clock integration setup complete: %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Alarm Clock integration: %s", entry.entry_id)

    coordinator: AlarmClockCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Stop the coordinator
    await coordinator.async_stop()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


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
