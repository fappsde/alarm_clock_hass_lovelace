"""Alarm Clock integration for Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.resources import ResourceStorageCollection
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

# Path to the card JavaScript file
CARD_JS_URL = f"/{DOMAIN}/alarm-clock-card.js"
CARD_JS_PATH = Path(__file__).parent / "alarm-clock-card.js"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Alarm Clock component."""
    hass.data.setdefault(DOMAIN, {})

    # Register the static path for the card JavaScript file
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_JS_URL, str(CARD_JS_PATH), cache_headers=False)]
    )
    _LOGGER.debug("Registered static path for alarm clock card: %s", CARD_JS_URL)

    # Register the Lovelace resource
    await _async_register_lovelace_resource(hass)

    return True


async def _async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Register the alarm clock card as a Lovelace resource."""
    resource_url = CARD_JS_URL

    # Check if lovelace resources component is available
    if "lovelace" not in hass.data:
        _LOGGER.debug("Lovelace not yet loaded, will register resource later")
        # Store flag to register resource when first entry is set up
        hass.data[DOMAIN]["_register_resource"] = True
        return

    try:
        # Get the resources collection
        resources: ResourceStorageCollection | None = hass.data["lovelace"].get(
            "resources"
        )

        if resources is None:
            _LOGGER.debug("Lovelace resources not available (YAML mode?)")
            return

        # Check if resource is already registered
        for resource in resources.async_items():
            if resource.get("url") == resource_url:
                _LOGGER.debug("Alarm clock card resource already registered")
                return

        # Register the resource
        await resources.async_create_item({"res_type": "module", "url": resource_url})
        _LOGGER.info("Registered alarm clock card as Lovelace resource: %s", resource_url)

    except Exception as err:
        _LOGGER.warning("Could not auto-register Lovelace resource: %s", err)
        _LOGGER.info(
            "Please manually add the following to your Lovelace resources: "
            "URL: %s, Type: JavaScript Module",
            resource_url,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alarm Clock from a config entry."""
    _LOGGER.debug("Setting up Alarm Clock integration: %s", entry.entry_id)

    # Try to register Lovelace resource if not done during async_setup
    if hass.data[DOMAIN].get("_register_resource"):
        hass.data[DOMAIN].pop("_register_resource", None)
        await _async_register_lovelace_resource(hass)

    try:
        # Initialize store for persistent data
        store = AlarmClockStore(hass, entry)
        await store.async_load()

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

        # Setup platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Start the coordinator scheduler
        await coordinator.async_start()

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
