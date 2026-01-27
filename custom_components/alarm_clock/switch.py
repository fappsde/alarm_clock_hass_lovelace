"""Switch entities for Alarm Clock integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, AlarmState
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
    """Set up alarm clock switches."""
    coordinator: AlarmClockCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Create enable/disable switch for each alarm
    for _alarm_id, alarm in coordinator.alarms.items():
        entities.append(AlarmEnableSwitch(coordinator, entry, alarm))

        # Create skip next switch
        entities.append(AlarmSkipNextSwitch(coordinator, entry, alarm))

    async_add_entities(entities)

    # Register callback for dynamically adding entities when new alarms are created
    coordinator.register_entity_adder_callback(
        lambda alarm_id: async_add_entities([
            AlarmEnableSwitch(coordinator, entry, coordinator.alarms[alarm_id]),
            AlarmSkipNextSwitch(coordinator, entry, coordinator.alarms[alarm_id]),
        ])
    )


class AlarmEnableSwitch(AlarmClockEntity, SwitchEntity):
    """Switch to enable/disable an alarm."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:alarm"

    def __init__(self, coordinator, entry, alarm) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, alarm)
        self._attr_unique_id = f"{entry.entry_id}_{alarm.data.alarm_id}_enable"
        self._attr_name = f"{alarm.data.name}"

    @property
    def is_on(self) -> bool:
        """Return true if alarm is enabled."""
        return self.alarm.data.enabled

    @property
    def icon(self) -> str:
        """Return the icon based on state."""
        if self.alarm.state == AlarmState.RINGING:
            return "mdi:alarm-light"
        elif self.alarm.state == AlarmState.SNOOZED:
            return "mdi:alarm-snooze"
        elif self.alarm.state == AlarmState.PRE_ALARM:
            return "mdi:alarm-note"
        elif self.alarm.data.enabled:
            return "mdi:alarm"
        return "mdi:alarm-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "alarm_id": self.alarm.data.alarm_id,
            "alarm_name": self.alarm.data.name,
            "alarm_time": self.alarm.data.time,
            "alarm_state": self.alarm.state.value,
            "days": self.alarm.data.days,
            "one_time": self.alarm.data.one_time,
            "skip_next": self.alarm.data.skip_next,
            "snooze_count": self.alarm.snooze_count,
            "max_snooze_count": self.alarm.data.max_snooze_count,
            "next_trigger": (
                self.alarm.next_trigger.isoformat() if self.alarm.next_trigger else None
            ),
            "snooze_end_time": (
                self.alarm.snooze_end_time.isoformat() if self.alarm.snooze_end_time else None
            ),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the alarm."""
        await self.coordinator.async_set_enabled(self.alarm_id, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the alarm."""
        await self.coordinator.async_set_enabled(self.alarm_id, False)


class AlarmSkipNextSwitch(AlarmClockEntity, SwitchEntity):
    """Switch to skip the next occurrence of an alarm."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:debug-step-over"

    def __init__(self, coordinator, entry, alarm) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, alarm)
        self._attr_unique_id = f"{entry.entry_id}_{alarm.data.alarm_id}_skip_next"
        self._attr_name = f"{alarm.data.name} Skip Next"

    @property
    def is_on(self) -> bool:
        """Return true if skip next is enabled."""
        return self.alarm.data.skip_next

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Only available when alarm is enabled
        return super().available and self.alarm.data.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable skip next."""
        await self.coordinator.async_skip_next(self.alarm_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable skip next."""
        await self.coordinator.async_cancel_skip(self.alarm_id)
