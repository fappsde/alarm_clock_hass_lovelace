"""State machine for alarm clock states."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .const import (
    ATTR_ALARM_ID,
    ATTR_ALARM_NAME,
    ATTR_ALARM_STATE,
    ATTR_ALARM_TIME,
    ATTR_IS_ONE_TIME,
    ATTR_SNOOZE_COUNT,
    ATTR_TRIGGER_TYPE,
    VALID_STATE_TRANSITIONS,
    AlarmState,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class InvalidStateTransitionError(Exception):
    """Exception raised when an invalid state transition is attempted."""

    def __init__(self, current_state: AlarmState, target_state: AlarmState) -> None:
        """Initialize the exception."""
        self.current_state = current_state
        self.target_state = target_state
        super().__init__(f"Invalid state transition from {current_state} to {target_state}")


@dataclass
class AlarmData:
    """Data class for alarm configuration."""

    alarm_id: str
    name: str
    time: str  # HH:MM format
    enabled: bool = True
    days: list[str] = field(
        default_factory=lambda: ["monday", "tuesday", "wednesday", "thursday", "friday"]
    )
    one_time: bool = False
    skip_next: bool = False
    snooze_duration: int = 9  # minutes
    max_snooze_count: int = 3
    auto_dismiss_timeout: int = 60  # minutes
    pre_alarm_duration: int = 5  # minutes
    gradual_volume: bool = False
    gradual_volume_duration: int = 5  # minutes

    # Script configuration
    use_device_defaults: bool = True  # Use device-level default scripts

    # Script references (entity_id of script.*)
    script_pre_alarm: str | None = None
    script_alarm: str | None = None
    script_post_alarm: str | None = None
    script_on_snooze: str | None = None
    script_on_dismiss: str | None = None
    script_on_arm: str | None = None
    script_on_cancel: str | None = None
    script_on_skip: str | None = None
    script_fallback: str | None = None
    script_timeout: int = 30  # seconds
    script_retry_count: int = 3

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "alarm_id": self.alarm_id,
            "name": self.name,
            "time": self.time,
            "enabled": self.enabled,
            "days": self.days,
            "one_time": self.one_time,
            "skip_next": self.skip_next,
            "snooze_duration": self.snooze_duration,
            "max_snooze_count": self.max_snooze_count,
            "auto_dismiss_timeout": self.auto_dismiss_timeout,
            "pre_alarm_duration": self.pre_alarm_duration,
            "gradual_volume": self.gradual_volume,
            "gradual_volume_duration": self.gradual_volume_duration,
            "use_device_defaults": self.use_device_defaults,
            "script_pre_alarm": self.script_pre_alarm,
            "script_alarm": self.script_alarm,
            "script_post_alarm": self.script_post_alarm,
            "script_on_snooze": self.script_on_snooze,
            "script_on_dismiss": self.script_on_dismiss,
            "script_on_arm": self.script_on_arm,
            "script_on_cancel": self.script_on_cancel,
            "script_on_skip": self.script_on_skip,
            "script_fallback": self.script_fallback,
            "script_timeout": self.script_timeout,
            "script_retry_count": self.script_retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlarmData:
        """Create from dictionary."""
        return cls(
            alarm_id=data["alarm_id"],
            name=data["name"],
            time=data["time"],
            enabled=data.get("enabled", True),
            days=data.get("days", ["monday", "tuesday", "wednesday", "thursday", "friday"]),
            one_time=data.get("one_time", False),
            skip_next=data.get("skip_next", False),
            snooze_duration=data.get("snooze_duration", 9),
            max_snooze_count=data.get("max_snooze_count", 3),
            auto_dismiss_timeout=data.get("auto_dismiss_timeout", 60),
            pre_alarm_duration=data.get("pre_alarm_duration", 5),
            gradual_volume=data.get("gradual_volume", False),
            gradual_volume_duration=data.get("gradual_volume_duration", 5),
            use_device_defaults=data.get("use_device_defaults", True),
            script_pre_alarm=data.get("script_pre_alarm"),
            script_alarm=data.get("script_alarm"),
            script_post_alarm=data.get("script_post_alarm"),
            script_on_snooze=data.get("script_on_snooze"),
            script_on_dismiss=data.get("script_on_dismiss"),
            script_on_arm=data.get("script_on_arm"),
            script_on_cancel=data.get("script_on_cancel"),
            script_on_skip=data.get("script_on_skip"),
            script_fallback=data.get("script_fallback"),
            script_timeout=data.get("script_timeout", 30),
            script_retry_count=data.get("script_retry_count", 3),
        )

    def validate(self) -> list[str]:
        """Validate alarm data and return list of errors."""
        errors = []

        # Validate time format
        try:
            parts = self.time.split(":")
            if len(parts) != 2:
                raise ValueError("Invalid format")
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Out of range")
        except (ValueError, AttributeError):
            errors.append(f"Invalid time format: {self.time}")

        # Validate days
        valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        for day in self.days:
            if day.lower() not in valid_days:
                errors.append(f"Invalid day: {day}")

        # Validate numeric values
        if self.snooze_duration < 1:
            errors.append("Snooze duration must be at least 1 minute")
        if self.max_snooze_count < 0:
            errors.append("Max snooze count cannot be negative")
        if self.auto_dismiss_timeout < 1:
            errors.append("Auto dismiss timeout must be at least 1 minute")
        if self.pre_alarm_duration < 0:
            errors.append("Pre-alarm duration cannot be negative")

        return errors


@dataclass
class AlarmRuntimeState:
    """Runtime state for an alarm (not persisted)."""

    state: AlarmState = AlarmState.DISABLED
    snooze_count: int = 0
    last_triggered: datetime | None = None
    last_state_change: datetime | None = None
    current_trigger_type: str | None = None
    next_trigger: datetime | None = None
    snooze_end_time: datetime | None = None
    pre_alarm_start_time: datetime | None = None
    ringing_start_time: datetime | None = None


class AlarmStateMachine:
    """State machine for managing alarm states with atomic transitions."""

    def __init__(
        self,
        hass: HomeAssistant,
        alarm_data: AlarmData,
        on_state_change: Callable[[AlarmState, AlarmState], None] | None = None,
    ) -> None:
        """Initialize the state machine."""
        self.hass = hass
        self.data = alarm_data
        self._runtime = AlarmRuntimeState()
        self._lock = asyncio.Lock()
        self._on_state_change = on_state_change

        # Set initial state based on enabled flag
        if alarm_data.enabled:
            self._runtime.state = AlarmState.ARMED
        else:
            self._runtime.state = AlarmState.DISABLED

    @property
    def state(self) -> AlarmState:
        """Get current state."""
        return self._runtime.state

    @property
    def snooze_count(self) -> int:
        """Get current snooze count."""
        return self._runtime.snooze_count

    @property
    def last_triggered(self) -> datetime | None:
        """Get last triggered time."""
        return self._runtime.last_triggered

    @property
    def next_trigger(self) -> datetime | None:
        """Get next trigger time."""
        return self._runtime.next_trigger

    @next_trigger.setter
    def next_trigger(self, value: datetime | None) -> None:
        """Set next trigger time."""
        self._runtime.next_trigger = value

    @property
    def snooze_end_time(self) -> datetime | None:
        """Get snooze end time."""
        return self._runtime.snooze_end_time

    @property
    def current_trigger_type(self) -> str | None:
        """Get current trigger type."""
        return self._runtime.current_trigger_type

    @property
    def ringing_start_time(self) -> datetime | None:
        """Get ringing start time."""
        return self._runtime.ringing_start_time

    def can_transition_to(self, target_state: AlarmState) -> bool:
        """Check if transition to target state is valid."""
        valid_targets = VALID_STATE_TRANSITIONS.get(self._runtime.state, [])
        return target_state in valid_targets

    async def transition_to(
        self,
        target_state: AlarmState,
        trigger_type: str | None = None,
        force: bool = False,
    ) -> bool:
        """
        Attempt to transition to a new state.

        Args:
            target_state: The state to transition to
            trigger_type: The type of trigger (for RINGING state)
            force: Force transition even if invalid (use with caution)

        Returns:
            True if transition was successful, False otherwise
        """
        async with self._lock:
            old_state = self._runtime.state

            if not force and not self.can_transition_to(target_state):
                _LOGGER.warning(
                    "Invalid state transition attempted for alarm %s: %s -> %s",
                    self.data.alarm_id,
                    old_state,
                    target_state,
                )
                return False

            # Update state
            self._runtime.state = target_state
            self._runtime.last_state_change = datetime.now()

            # Handle state-specific logic
            if target_state == AlarmState.RINGING:
                self._runtime.current_trigger_type = trigger_type
                self._runtime.last_triggered = datetime.now()
                self._runtime.ringing_start_time = datetime.now()
            elif target_state == AlarmState.SNOOZED:
                self._runtime.snooze_count += 1
            elif target_state in (
                AlarmState.DISMISSED,
                AlarmState.AUTO_DISMISSED,
                AlarmState.ARMED,
            ):
                # Reset runtime state
                self._runtime.snooze_count = 0
                self._runtime.current_trigger_type = None
                self._runtime.ringing_start_time = None
                self._runtime.snooze_end_time = None
                self._runtime.pre_alarm_start_time = None
            elif target_state == AlarmState.PRE_ALARM:
                self._runtime.pre_alarm_start_time = datetime.now()

            _LOGGER.debug(
                "Alarm %s transitioned: %s -> %s",
                self.data.alarm_id,
                old_state,
                target_state,
            )

            # Notify callback
            if self._on_state_change:
                try:
                    self._on_state_change(old_state, target_state)
                except Exception:
                    _LOGGER.exception("Error in state change callback")

            return True

    async def reset(self) -> None:
        """Reset the state machine to initial state based on enabled flag."""
        async with self._lock:
            self._runtime = AlarmRuntimeState()
            if self.data.enabled:
                self._runtime.state = AlarmState.ARMED
            else:
                self._runtime.state = AlarmState.DISABLED

    def set_snooze_end_time(self, end_time: datetime) -> None:
        """Set the snooze end time."""
        self._runtime.snooze_end_time = end_time

    def get_event_data(self) -> dict[str, Any]:
        """Get data for event firing."""
        return {
            ATTR_ALARM_ID: self.data.alarm_id,
            ATTR_ALARM_NAME: self.data.name,
            ATTR_ALARM_TIME: self.data.time,
            ATTR_ALARM_STATE: self._runtime.state.value,
            ATTR_SNOOZE_COUNT: self._runtime.snooze_count,
            ATTR_IS_ONE_TIME: self.data.one_time,
            ATTR_TRIGGER_TYPE: self._runtime.current_trigger_type,
        }

    def get_script_context(self) -> dict[str, Any]:
        """Get context data for script execution."""
        return {
            "alarm_id": self.data.alarm_id,
            "alarm_name": self.data.name,
            "alarm_time": self.data.time,
            "trigger_type": self._runtime.current_trigger_type,
            "snooze_count": self._runtime.snooze_count,
            "is_one_time": self.data.one_time,
            "days": self.data.days,
        }

    def to_restore_data(self) -> dict[str, Any]:
        """Get data for state restoration."""
        return {
            "state": self._runtime.state.value,
            "snooze_count": self._runtime.snooze_count,
            "last_triggered": (
                self._runtime.last_triggered.isoformat() if self._runtime.last_triggered else None
            ),
            "snooze_end_time": (
                self._runtime.snooze_end_time.isoformat() if self._runtime.snooze_end_time else None
            ),
        }

    def restore_from_data(self, data: dict[str, Any]) -> None:
        """Restore state from saved data."""
        try:
            # Restore state - ensure it's a valid state
            state_value = data.get("state", AlarmState.DISABLED.value)
            try:
                self._runtime.state = AlarmState(state_value)
            except ValueError:
                _LOGGER.warning(
                    "Invalid state value '%s' for alarm %s, defaulting to ARMED/DISABLED",
                    state_value,
                    self.data.alarm_id,
                )
                self._runtime.state = AlarmState.ARMED if self.data.enabled else AlarmState.DISABLED

            self._runtime.snooze_count = data.get("snooze_count", 0)

            # Restore datetime fields with timezone awareness
            if data.get("last_triggered"):
                try:
                    dt = datetime.fromisoformat(data["last_triggered"])
                    # Ensure timezone-aware datetime
                    if dt.tzinfo is None:
                        import homeassistant.util.dt as dt_util

                        dt = dt_util.as_local(dt)
                    self._runtime.last_triggered = dt
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Invalid last_triggered datetime for alarm %s: %s",
                        self.data.alarm_id,
                        err,
                    )

            if data.get("snooze_end_time"):
                try:
                    dt = datetime.fromisoformat(data["snooze_end_time"])
                    # Ensure timezone-aware datetime
                    if dt.tzinfo is None:
                        import homeassistant.util.dt as dt_util

                        dt = dt_util.as_local(dt)
                    self._runtime.snooze_end_time = dt
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Invalid snooze_end_time datetime for alarm %s: %s",
                        self.data.alarm_id,
                        err,
                    )

        except Exception as err:
            _LOGGER.error(
                "Unexpected error restoring state for alarm %s: %s",
                self.data.alarm_id,
                err,
                exc_info=True,
            )
            # Reset to safe state
            self._runtime = AlarmRuntimeState()
            if self.data.enabled:
                self._runtime.state = AlarmState.ARMED
