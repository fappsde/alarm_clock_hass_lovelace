"""Coordinator for Alarm Clock integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import CALLBACK_TYPE, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ALARM_ID,
    ATTR_ALARM_TIME,
    ATTR_DAYS,
    ATTR_DURATION,
    ATTR_ERROR_MESSAGE,
    CONF_ALARM_ID,
    CONF_ALARM_NAME,
    CONF_ALARM_TIME,
    CONF_DAYS,
    CONF_ENABLED,
    CONF_MAX_SNOOZE_COUNT,
    CONF_ONE_TIME,
    CONF_SCRIPT_ALARM,
    CONF_SCRIPT_FALLBACK,
    CONF_SCRIPT_ON_ARM,
    CONF_SCRIPT_ON_CANCEL,
    CONF_SCRIPT_ON_DISMISS,
    CONF_SCRIPT_ON_SKIP,
    CONF_SCRIPT_ON_SNOOZE,
    CONF_SCRIPT_POST_ALARM,
    CONF_SCRIPT_PRE_ALARM,
    CONF_SCRIPT_RETRY_COUNT,
    CONF_SCRIPT_TIMEOUT,
    CONF_SNOOZE_DURATION,
    CONF_USE_DEVICE_DEFAULTS,
    DEFAULT_MISSED_ALARM_GRACE_PERIOD,
    DEFAULT_SNOOZE_DURATION,
    DOMAIN,
    HEALTH_CHECK_INTERVAL,
    SERVICE_CANCEL_SKIP,
    SERVICE_CREATE_ALARM,
    SERVICE_DELETE_ALARM,
    SERVICE_DISMISS,
    SERVICE_SET_DAYS,
    SERVICE_SET_SCRIPTS,
    SERVICE_SET_TIME,
    SERVICE_SKIP_NEXT,
    SERVICE_SNOOZE,
    SERVICE_TEST_ALARM,
    TRIGGER_MANUAL_TEST,
    TRIGGER_MISSED_RECOVERY,
    TRIGGER_SCHEDULED,
    WEEKDAYS,
    AlarmEvent,
    AlarmState,
)
from .state_machine import AlarmData, AlarmStateMachine

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .store import AlarmClockStore

_LOGGER = logging.getLogger(__name__)


class AlarmClockCoordinator:
    """Coordinator for managing all alarms."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: AlarmClockStore,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.store = store

        self._alarms: dict[str, AlarmStateMachine] = {}
        self._scheduled_callbacks: dict[str, CALLBACK_TYPE | None] = {}
        self._snooze_callbacks: dict[str, CALLBACK_TYPE | None] = {}
        self._auto_dismiss_callbacks: dict[str, CALLBACK_TYPE | None] = {}
        self._pre_alarm_callbacks: dict[str, CALLBACK_TYPE | None] = {}
        self._health_check_callback: CALLBACK_TYPE | None = None

        self._update_callbacks: list[Callable] = []
        self._entity_adder_callbacks: list[Callable[[str], None]] = []
        self._running = False
        self._health_status: dict[str, Any] = {
            "healthy": True,
            "last_check": None,
            "issues": [],
        }

        # Rate limiting for idempotent triggers
        self._last_trigger_times: dict[str, datetime] = {}

        # Watchdog for script execution
        self._script_watchdog_tasks: dict[str, asyncio.Task] = {}

        # Lock for thread-safe alarm scheduling
        self._schedule_lock = asyncio.Lock()

        # Track if this coordinator registered the services
        self._services_registered = False

    @property
    def alarms(self) -> dict[str, AlarmStateMachine]:
        """Get all alarms."""
        return self._alarms

    @property
    def health_status(self) -> dict[str, Any]:
        """Get health status."""
        return self._health_status

    async def async_start(self) -> None:
        """Start the coordinator."""
        _LOGGER.info("Starting alarm clock coordinator")
        self._running = True

        try:
            # Load alarms from store
            alarms_to_load = self.store.get_all_alarms()
            _LOGGER.debug("Loading %d alarms from storage", len(alarms_to_load))

            for alarm_data in alarms_to_load:
                try:
                    await self._async_setup_alarm(alarm_data)
                    _LOGGER.debug("Successfully loaded alarm: %s", alarm_data.alarm_id)
                except Exception as err:
                    _LOGGER.error(
                        "Failed to setup alarm %s: %s. Skipping this alarm.",
                        alarm_data.alarm_id,
                        err,
                        exc_info=True,
                    )
                    # Continue loading other alarms even if one fails

            # Check for missed alarms
            _LOGGER.debug("Checking for missed alarms")
            await self._async_check_missed_alarms()

            # Start health check
            _LOGGER.debug("Starting health check")
            self._schedule_health_check()

            _LOGGER.info(
                "Alarm clock coordinator started successfully with %d alarms", len(self._alarms)
            )

        except Exception as err:
            _LOGGER.error("Critical error during coordinator startup: %s", err, exc_info=True)
            # Mark as not running to prevent further issues
            self._running = False
            raise

    async def async_stop(self) -> None:
        """Stop the coordinator."""
        _LOGGER.debug("Stopping alarm clock coordinator")
        self._running = False

        # Cancel all scheduled callbacks
        for alarm_id in list(self._scheduled_callbacks.keys()):
            self._cancel_scheduled_callback(alarm_id)

        for alarm_id in list(self._snooze_callbacks.keys()):
            self._cancel_snooze_callback(alarm_id)

        for alarm_id in list(self._auto_dismiss_callbacks.keys()):
            self._cancel_auto_dismiss_callback(alarm_id)

        for alarm_id in list(self._pre_alarm_callbacks.keys()):
            self._cancel_pre_alarm_callback(alarm_id)

        # Cancel health check
        if self._health_check_callback:
            self._health_check_callback()
            self._health_check_callback = None

        # Cancel watchdog tasks
        for task in self._script_watchdog_tasks.values():
            task.cancel()
        self._script_watchdog_tasks.clear()

        # Save runtime states
        for alarm_id, alarm in self._alarms.items():
            await self.store.async_save_runtime_state(alarm_id, alarm.to_restore_data())

        # Unregister services if this is the last entry
        await self.async_unregister_services()

        # Clear update callbacks to prevent memory leaks
        self._update_callbacks.clear()
        self._entity_adder_callbacks.clear()

        _LOGGER.info("Alarm clock coordinator stopped")

    async def _async_setup_alarm(self, alarm_data: AlarmData) -> None:
        """Set up a single alarm."""
        try:
            # Validate alarm data
            errors = alarm_data.validate()
            if errors:
                _LOGGER.error(
                    "Invalid alarm data for %s: %s. Disabling alarm.",
                    alarm_data.alarm_id,
                    errors,
                )
                alarm_data.enabled = False
                await self.store.async_update_alarm(alarm_data)
                self._fire_event(
                    AlarmEvent.HEALTH_WARNING,
                    {
                        ATTR_ALARM_ID: alarm_data.alarm_id,
                        ATTR_ERROR_MESSAGE: f"Alarm disabled due to invalid data: {errors}",
                    },
                )

            # Create state machine
            alarm = AlarmStateMachine(
                self.hass,
                alarm_data,
                on_state_change=lambda old, new: self._on_alarm_state_change(
                    alarm_data.alarm_id, old, new
                ),
            )

            # Restore runtime state if available
            runtime_state = self.store.get_runtime_state(alarm_data.alarm_id)
            if runtime_state:
                try:
                    alarm.restore_from_data(runtime_state)
                    _LOGGER.debug(
                        "Restored state for alarm %s: %s",
                        alarm_data.alarm_id,
                        alarm.state,
                    )
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to restore runtime state for alarm %s: %s. Using default state.",
                        alarm_data.alarm_id,
                        err,
                    )
                    # State machine will use default state

            self._alarms[alarm_data.alarm_id] = alarm

            # Schedule if armed
            if alarm.state == AlarmState.ARMED:
                await self._schedule_alarm(alarm_data.alarm_id)

            # Handle restored snooze state
            if alarm.state == AlarmState.SNOOZED and alarm.snooze_end_time:
                now = dt_util.now()
                if alarm.snooze_end_time > now:
                    self._schedule_snooze_end(alarm_data.alarm_id, alarm.snooze_end_time)
                else:
                    # Snooze expired, trigger alarm
                    await self._async_trigger_alarm(alarm_data.alarm_id, TRIGGER_SCHEDULED)

        except Exception as err:
            _LOGGER.error(
                "Failed to setup alarm %s: %s",
                alarm_data.alarm_id,
                err,
                exc_info=True,
            )
            raise

    async def async_add_alarm(self, alarm_data: AlarmData) -> None:
        """Add a new alarm."""
        try:
            await self.store.async_add_alarm(alarm_data)
            await self._async_setup_alarm(alarm_data)
            self._notify_entity_adders(alarm_data.alarm_id)
            self._notify_update()
            _LOGGER.info("Added new alarm: %s", alarm_data.alarm_id)
        except Exception as err:
            _LOGGER.error("Error adding alarm %s: %s", alarm_data.alarm_id, err, exc_info=True)
            raise

    async def async_update_alarm(self, alarm_data: AlarmData) -> None:
        """Update an existing alarm."""
        alarm_id = alarm_data.alarm_id

        if alarm_id not in self._alarms:
            _LOGGER.warning("Attempted to update non-existent alarm: %s", alarm_id)
            return

        try:
            old_alarm = self._alarms[alarm_id]
            old_state = old_alarm.state

            # Cancel existing schedules
            self._cancel_scheduled_callback(alarm_id)

            # Update store
            await self.store.async_update_alarm(alarm_data)

            # Update state machine
            old_alarm.data = alarm_data

            # Re-schedule if needed
            if alarm_data.enabled and old_state in (AlarmState.ARMED, AlarmState.DISABLED):
                await old_alarm.transition_to(AlarmState.ARMED)
                await self._schedule_alarm(alarm_id)
            elif not alarm_data.enabled:
                await old_alarm.transition_to(AlarmState.DISABLED)

            self._notify_update()
            _LOGGER.debug("Updated alarm: %s", alarm_id)
        except Exception as err:
            _LOGGER.error("Error updating alarm %s: %s", alarm_id, err, exc_info=True)
            raise

    async def async_remove_alarm(self, alarm_id: str) -> bool:
        """Remove an alarm."""
        if alarm_id not in self._alarms:
            return False

        try:
            # Cancel all callbacks
            self._cancel_scheduled_callback(alarm_id)
            self._cancel_snooze_callback(alarm_id)
            self._cancel_auto_dismiss_callback(alarm_id)
            self._cancel_pre_alarm_callback(alarm_id)

            # Clean up tracking dicts to prevent memory leaks
            self._last_trigger_times.pop(alarm_id, None)

            # Cancel and remove any script watchdog tasks
            if alarm_id in self._script_watchdog_tasks:
                self._script_watchdog_tasks[alarm_id].cancel()
                del self._script_watchdog_tasks[alarm_id]

            # Remove from store
            await self.store.async_remove_alarm(alarm_id)

            # Remove associated entities from entity registry
            try:
                entity_registry = er.async_get(self.hass)
                entities_to_remove = []

                # Find all entities with this alarm_id in their unique_id
                for entity_id, entity_entry in entity_registry.entities.items():
                    if entity_entry.unique_id and alarm_id in entity_entry.unique_id:
                        entities_to_remove.append(entity_id)

                # Remove found entities
                for entity_id in entities_to_remove:
                    _LOGGER.debug("Removing entity %s for alarm %s", entity_id, alarm_id)
                    entity_registry.async_remove(entity_id)
            except Exception as entity_err:
                _LOGGER.warning("Error removing entities for alarm %s: %s", alarm_id, entity_err)

            # Remove from memory
            del self._alarms[alarm_id]

            self._notify_update()
            _LOGGER.info(
                "Removed alarm %s and %d associated entities", alarm_id, len(entities_to_remove)
            )
            return True
        except Exception as err:
            _LOGGER.error("Error removing alarm %s: %s", alarm_id, err, exc_info=True)
            return False

    async def _schedule_alarm(self, alarm_id: str) -> None:
        """Schedule the next trigger for an alarm.

        Thread-safe using asyncio.Lock to prevent race conditions when
        cancelling and creating callbacks.
        """
        if alarm_id not in self._alarms:
            return

        alarm = self._alarms[alarm_id]

        if not alarm.data.enabled or alarm.data.skip_next:
            async with self._schedule_lock:
                alarm.next_trigger = None
                self._cancel_scheduled_callback(alarm_id)
            return

        # Calculate next trigger time
        next_trigger = self._calculate_next_trigger(alarm.data)

        if next_trigger is None:
            async with self._schedule_lock:
                alarm.next_trigger = None
                self._cancel_scheduled_callback(alarm_id)
            return

        alarm.next_trigger = next_trigger

        # Schedule pre-alarm if configured (outside lock - independent operation)
        if alarm.data.pre_alarm_duration > 0:
            pre_alarm_time = next_trigger - timedelta(minutes=alarm.data.pre_alarm_duration)
            if pre_alarm_time > dt_util.now():
                self._schedule_pre_alarm(alarm_id, pre_alarm_time)

        # Critical section: Cancel existing and schedule new callback
        async with self._schedule_lock:
            # Cancel existing callback
            self._cancel_scheduled_callback(alarm_id)

            # Schedule new callback
            self._scheduled_callbacks[alarm_id] = async_track_point_in_time(
                self.hass,
                lambda now, aid=alarm_id: self.hass.loop.call_soon_threadsafe(
                    lambda: self.hass.async_create_task(self._async_handle_alarm_trigger(aid))
                ),
                next_trigger,
            )

        _LOGGER.debug(
            "Scheduled alarm %s for %s",
            alarm_id,
            next_trigger.isoformat(),
        )

    def _calculate_next_trigger(self, alarm_data: AlarmData) -> datetime | None:
        """Calculate the next trigger time for an alarm."""
        now = dt_util.now()

        # Parse alarm time
        try:
            hour, minute = map(int, alarm_data.time.split(":"))
        except (ValueError, AttributeError):
            _LOGGER.error("Invalid alarm time: %s", alarm_data.time)
            return None

        # Check each day starting from today
        for days_ahead in range(8):  # Check up to 7 days ahead
            check_date = now.date() + timedelta(days=days_ahead)
            day_name = WEEKDAYS[check_date.weekday()]

            if day_name not in [d.lower() for d in alarm_data.days]:
                continue

            trigger_time = dt_util.now().replace(
                year=check_date.year,
                month=check_date.month,
                day=check_date.day,
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )

            # If today, check if time hasn't passed
            if days_ahead == 0 and trigger_time <= now:
                continue

            return trigger_time

        return None

    async def _async_handle_alarm_trigger(self, alarm_id: str) -> None:
        """Handle alarm trigger."""
        if alarm_id not in self._alarms:
            return

        # Idempotent check - prevent double triggers within same minute
        now = dt_util.now()
        last_trigger = self._last_trigger_times.get(alarm_id)
        if last_trigger and (now - last_trigger).total_seconds() < 60:
            _LOGGER.debug(
                "Ignoring duplicate trigger for alarm %s (last trigger: %s)",
                alarm_id,
                last_trigger,
            )
            return

        self._last_trigger_times[alarm_id] = now

        await self._async_trigger_alarm(alarm_id, TRIGGER_SCHEDULED)

    async def _async_trigger_alarm(self, alarm_id: str, trigger_type: str) -> None:
        """Trigger an alarm."""
        if alarm_id not in self._alarms:
            return

        alarm = self._alarms[alarm_id]

        # Transition to ringing
        if not await alarm.transition_to(AlarmState.RINGING, trigger_type=trigger_type):
            _LOGGER.warning(
                "Failed to transition alarm %s to ringing state",
                alarm_id,
            )
            return

        _LOGGER.info("Alarm %s triggered (%s)", alarm_id, trigger_type)

        # Fire event
        self._fire_event(AlarmEvent.TRIGGERED, alarm.get_event_data())

        # Execute alarm script
        await self._async_execute_script(
            alarm_id,
            self._get_effective_script(alarm, "script_alarm"),
            "alarm",
        )

        # Schedule auto-dismiss
        auto_dismiss_time = dt_util.now() + timedelta(minutes=alarm.data.auto_dismiss_timeout)
        self._schedule_auto_dismiss(alarm_id, auto_dismiss_time)

        self._notify_update()

    def _schedule_pre_alarm(self, alarm_id: str, trigger_time: datetime) -> None:
        """Schedule pre-alarm callback."""
        self._cancel_pre_alarm_callback(alarm_id)

        self._pre_alarm_callbacks[alarm_id] = async_track_point_in_time(
            self.hass,
            lambda now, aid=alarm_id: self.hass.loop.call_soon_threadsafe(
                lambda: self.hass.async_create_task(self._async_handle_pre_alarm(aid))
            ),
            trigger_time,
        )

    async def _async_handle_pre_alarm(self, alarm_id: str) -> None:
        """Handle pre-alarm trigger."""
        if alarm_id not in self._alarms:
            return

        alarm = self._alarms[alarm_id]

        if alarm.state != AlarmState.ARMED:
            return

        await alarm.transition_to(AlarmState.PRE_ALARM)

        _LOGGER.debug("Pre-alarm triggered for %s", alarm_id)

        # Fire event
        self._fire_event(AlarmEvent.PRE_ALARM, alarm.get_event_data())

        # Execute pre-alarm script
        await self._async_execute_script(
            alarm_id,
            self._get_effective_script(alarm, "script_pre_alarm"),
            "pre_alarm",
        )

        self._notify_update()

    def _schedule_snooze_end(self, alarm_id: str, end_time: datetime) -> None:
        """Schedule snooze end callback."""
        self._cancel_snooze_callback(alarm_id)

        if alarm_id in self._alarms:
            self._alarms[alarm_id].set_snooze_end_time(end_time)

        self._snooze_callbacks[alarm_id] = async_track_point_in_time(
            self.hass,
            lambda now, aid=alarm_id: self.hass.loop.call_soon_threadsafe(
                lambda: self.hass.async_create_task(self._async_handle_snooze_end(aid))
            ),
            end_time,
        )

    async def _async_handle_snooze_end(self, alarm_id: str) -> None:
        """Handle snooze end - re-trigger alarm."""
        if alarm_id not in self._alarms:
            return

        alarm = self._alarms[alarm_id]

        if alarm.state != AlarmState.SNOOZED:
            return

        _LOGGER.debug("Snooze ended for alarm %s", alarm_id)

        await self._async_trigger_alarm(alarm_id, TRIGGER_SCHEDULED)

    def _schedule_auto_dismiss(self, alarm_id: str, dismiss_time: datetime) -> None:
        """Schedule auto-dismiss callback."""
        self._cancel_auto_dismiss_callback(alarm_id)

        self._auto_dismiss_callbacks[alarm_id] = async_track_point_in_time(
            self.hass,
            lambda now, aid=alarm_id: self.hass.loop.call_soon_threadsafe(
                lambda: self.hass.async_create_task(self._async_handle_auto_dismiss(aid))
            ),
            dismiss_time,
        )

    async def _async_handle_auto_dismiss(self, alarm_id: str) -> None:
        """Handle auto-dismiss timeout."""
        if alarm_id not in self._alarms:
            return

        alarm = self._alarms[alarm_id]

        if alarm.state not in (AlarmState.RINGING, AlarmState.SNOOZED):
            return

        _LOGGER.info("Auto-dismissing alarm %s after timeout", alarm_id)

        await alarm.transition_to(AlarmState.AUTO_DISMISSED)

        # Fire event
        self._fire_event(AlarmEvent.AUTO_DISMISSED, alarm.get_event_data())

        # Execute post-alarm script
        await self._async_execute_script(
            alarm_id,
            self._get_effective_script(alarm, "script_post_alarm"),
            "post_alarm",
        )

        # Handle one-time alarm
        if alarm.data.one_time:
            alarm.data.enabled = False
            await self.store.async_update_alarm(alarm.data)
            await alarm.transition_to(AlarmState.DISABLED)
        else:
            # Re-arm and schedule next
            await alarm.transition_to(AlarmState.ARMED)
            await self._schedule_alarm(alarm_id)

        self._notify_update()

    async def async_snooze(self, alarm_id: str, duration_minutes: int | None = None) -> bool:
        """Snooze an alarm."""
        if alarm_id not in self._alarms:
            return False

        alarm = self._alarms[alarm_id]

        if alarm.state != AlarmState.RINGING:
            _LOGGER.warning(
                "Cannot snooze alarm %s - not ringing (state: %s)",
                alarm_id,
                alarm.state,
            )
            return False

        # Check snooze limit
        if alarm.snooze_count >= alarm.data.max_snooze_count:
            _LOGGER.warning(
                "Cannot snooze alarm %s - max snooze count (%d) reached",
                alarm_id,
                alarm.data.max_snooze_count,
            )
            return False

        duration = duration_minutes or alarm.data.snooze_duration
        snooze_end = dt_util.now() + timedelta(minutes=duration)

        await alarm.transition_to(AlarmState.SNOOZED)

        # Cancel auto-dismiss
        self._cancel_auto_dismiss_callback(alarm_id)

        # Schedule snooze end
        self._schedule_snooze_end(alarm_id, snooze_end)

        _LOGGER.info(
            "Alarm %s snoozed for %d minutes (snooze %d/%d)",
            alarm_id,
            duration,
            alarm.snooze_count,
            alarm.data.max_snooze_count,
        )

        # Fire event
        event_data = alarm.get_event_data()
        event_data[ATTR_DURATION] = duration
        self._fire_event(AlarmEvent.SNOOZED, event_data)

        # Execute on-snooze script
        await self._async_execute_script(
            alarm_id,
            self._get_effective_script(alarm, "script_on_snooze"),
            "on_snooze",
        )

        # Save runtime state
        await self.store.async_save_runtime_state(alarm_id, alarm.to_restore_data())

        self._notify_update()
        return True

    async def async_dismiss(self, alarm_id: str) -> bool:
        """Dismiss an alarm."""
        if alarm_id not in self._alarms:
            return False

        alarm = self._alarms[alarm_id]

        if alarm.state not in (AlarmState.RINGING, AlarmState.SNOOZED, AlarmState.PRE_ALARM):
            _LOGGER.warning(
                "Cannot dismiss alarm %s - not active (state: %s)",
                alarm_id,
                alarm.state,
            )
            return False

        await alarm.transition_to(AlarmState.DISMISSED)

        # Cancel callbacks
        self._cancel_auto_dismiss_callback(alarm_id)
        self._cancel_snooze_callback(alarm_id)

        _LOGGER.info("Alarm %s dismissed", alarm_id)

        # Fire event
        self._fire_event(AlarmEvent.DISMISSED, alarm.get_event_data())

        # Execute on-dismiss script
        await self._async_execute_script(
            alarm_id,
            self._get_effective_script(alarm, "script_on_dismiss"),
            "on_dismiss",
        )

        # Execute post-alarm script
        await self._async_execute_script(
            alarm_id,
            self._get_effective_script(alarm, "script_post_alarm"),
            "post_alarm",
        )

        # Handle one-time alarm
        if alarm.data.one_time:
            alarm.data.enabled = False
            await self.store.async_update_alarm(alarm.data)
            await alarm.transition_to(AlarmState.DISABLED)
        else:
            # Re-arm and schedule next
            await alarm.transition_to(AlarmState.ARMED)
            await self._schedule_alarm(alarm_id)

        self._notify_update()
        return True

    async def async_skip_next(self, alarm_id: str) -> bool:
        """Skip the next occurrence of an alarm."""
        if alarm_id not in self._alarms:
            return False

        alarm = self._alarms[alarm_id]
        alarm.data.skip_next = True

        await self.store.async_update_alarm(alarm.data)

        # Cancel scheduled trigger
        self._cancel_scheduled_callback(alarm_id)
        self._cancel_pre_alarm_callback(alarm_id)

        _LOGGER.info("Alarm %s - next occurrence will be skipped", alarm_id)

        # Fire event
        self._fire_event(AlarmEvent.SKIPPED, alarm.get_event_data())

        # Execute on-skip script
        await self._async_execute_script(
            alarm_id,
            self._get_effective_script(alarm, "script_on_skip"),
            "on_skip",
        )

        self._notify_update()
        return True

    async def async_cancel_skip(self, alarm_id: str) -> bool:
        """Cancel skip for the next occurrence."""
        if alarm_id not in self._alarms:
            return False

        alarm = self._alarms[alarm_id]
        alarm.data.skip_next = False

        await self.store.async_update_alarm(alarm.data)

        # Re-schedule
        if alarm.state == AlarmState.ARMED:
            await self._schedule_alarm(alarm_id)

        self._notify_update()
        return True

    async def async_test_alarm(self, alarm_id: str) -> bool:
        """Trigger an alarm for testing."""
        if alarm_id not in self._alarms:
            return False

        alarm = self._alarms[alarm_id]

        if alarm.state in (AlarmState.RINGING, AlarmState.SNOOZED):
            _LOGGER.warning("Cannot test alarm %s - already active", alarm_id)
            return False

        _LOGGER.info("Testing alarm %s", alarm_id)

        await self._async_trigger_alarm(alarm_id, TRIGGER_MANUAL_TEST)
        return True

    async def async_set_enabled(self, alarm_id: str, enabled: bool) -> bool:
        """Enable or disable an alarm."""
        if alarm_id not in self._alarms:
            return False

        alarm = self._alarms[alarm_id]
        alarm.data.enabled = enabled

        await self.store.async_update_alarm(alarm.data)

        if enabled:
            await alarm.transition_to(AlarmState.ARMED, force=True)
            await self._schedule_alarm(alarm_id)

            # Fire event
            self._fire_event(AlarmEvent.ARMED, alarm.get_event_data())

            # Execute on-arm script
            await self._async_execute_script(
                alarm_id,
                self._get_effective_script(alarm, "script_on_arm"),
                "on_arm",
            )
        else:
            # Cancel callbacks
            self._cancel_scheduled_callback(alarm_id)
            self._cancel_pre_alarm_callback(alarm_id)

            # If currently active, execute cancel script
            if alarm.state in (AlarmState.RINGING, AlarmState.SNOOZED, AlarmState.PRE_ALARM):
                self._cancel_auto_dismiss_callback(alarm_id)
                self._cancel_snooze_callback(alarm_id)

                await self._async_execute_script(
                    alarm_id,
                    self._get_effective_script(alarm, "script_on_cancel"),
                    "on_cancel",
                )

            await alarm.transition_to(AlarmState.DISABLED, force=True)

            # Fire event
            self._fire_event(AlarmEvent.DISARMED, alarm.get_event_data())

        self._notify_update()
        return True

    async def async_set_time(self, alarm_id: str, time: str) -> bool:
        """Set alarm time."""
        if alarm_id not in self._alarms:
            return False

        alarm = self._alarms[alarm_id]
        old_time = alarm.data.time
        alarm.data.time = time

        # Validate
        errors = alarm.data.validate()
        if errors:
            alarm.data.time = old_time
            return False

        await self.store.async_update_alarm(alarm.data)

        # Reschedule
        if alarm.state == AlarmState.ARMED:
            await self._schedule_alarm(alarm_id)

        # Fire event
        event_data = alarm.get_event_data()
        event_data["old_time"] = old_time
        self._fire_event(AlarmEvent.TIME_CHANGED, event_data)

        self._notify_update()
        return True

    async def async_set_days(self, alarm_id: str, days: list[str]) -> bool:
        """Set alarm days."""
        if alarm_id not in self._alarms:
            return False

        alarm = self._alarms[alarm_id]
        alarm.data.days = days

        await self.store.async_update_alarm(alarm.data)

        # Reschedule
        if alarm.state == AlarmState.ARMED:
            await self._schedule_alarm(alarm_id)

        self._notify_update()
        return True

    async def async_set_scripts(
        self,
        alarm_id: str,
        script_pre_alarm: str | None = None,
        script_alarm: str | None = None,
        script_post_alarm: str | None = None,
        script_on_snooze: str | None = None,
        script_on_dismiss: str | None = None,
        script_on_arm: str | None = None,
        script_on_cancel: str | None = None,
        script_on_skip: str | None = None,
        script_fallback: str | None = None,
        script_timeout: int | None = None,
        script_retry_count: int | None = None,
    ) -> bool:
        """Set alarm scripts."""
        if alarm_id not in self._alarms:
            return False

        alarm = self._alarms[alarm_id]

        # Setting individual scripts disables device defaults
        alarm.data.use_device_defaults = False

        # Update only the provided scripts
        if script_pre_alarm is not None:
            alarm.data.script_pre_alarm = script_pre_alarm
        if script_alarm is not None:
            alarm.data.script_alarm = script_alarm
        if script_post_alarm is not None:
            alarm.data.script_post_alarm = script_post_alarm
        if script_on_snooze is not None:
            alarm.data.script_on_snooze = script_on_snooze
        if script_on_dismiss is not None:
            alarm.data.script_on_dismiss = script_on_dismiss
        if script_on_arm is not None:
            alarm.data.script_on_arm = script_on_arm
        if script_on_cancel is not None:
            alarm.data.script_on_cancel = script_on_cancel
        if script_on_skip is not None:
            alarm.data.script_on_skip = script_on_skip
        if script_fallback is not None:
            alarm.data.script_fallback = script_fallback
        if script_timeout is not None:
            alarm.data.script_timeout = script_timeout
        if script_retry_count is not None:
            alarm.data.script_retry_count = script_retry_count

        await self.store.async_update_alarm(alarm.data)
        self._notify_update()
        return True

    def _get_effective_script(self, alarm: AlarmStateMachine, script_attr: str) -> str | None:
        """Get the effective script for an alarm based on device defaults setting."""
        if not alarm.data.use_device_defaults:
            # Use alarm-specific scripts
            return getattr(alarm.data, script_attr)

        # Use device-level defaults from config entry options
        options = self.entry.options
        default_attr = f"default_{script_attr}"
        return options.get(default_attr)

    def _get_effective_script_timeout(self, alarm: AlarmStateMachine) -> int:
        """Get the effective script timeout."""
        if not alarm.data.use_device_defaults:
            return alarm.data.script_timeout
        return self.entry.options.get("default_script_timeout", 30)

    def _get_effective_script_retry_count(self, alarm: AlarmStateMachine) -> int:
        """Get the effective script retry count."""
        if not alarm.data.use_device_defaults:
            return alarm.data.script_retry_count
        return self.entry.options.get("default_script_retry_count", 3)

    async def _async_execute_script(
        self,
        alarm_id: str,
        script_entity_id: str | None,
        script_type: str,
    ) -> bool:
        """Execute a script with retry and timeout."""
        if not script_entity_id:
            return True

        alarm = self._alarms.get(alarm_id)
        if not alarm:
            return False

        timeout = self._get_effective_script_timeout(alarm)
        max_retries = self._get_effective_script_retry_count(alarm)
        context = alarm.get_script_context()

        for attempt in range(max_retries):
            try:
                _LOGGER.debug(
                    "Executing %s script %s for alarm %s (attempt %d/%d)",
                    script_type,
                    script_entity_id,
                    alarm_id,
                    attempt + 1,
                    max_retries,
                )

                # Execute with timeout
                await asyncio.wait_for(
                    self.hass.services.async_call(
                        "script",
                        script_entity_id.replace("script.", ""),
                        {
                            "alarm_context": context,
                        },
                        blocking=True,
                    ),
                    timeout=timeout,
                )

                _LOGGER.debug(
                    "Successfully executed %s script for alarm %s",
                    script_type,
                    alarm_id,
                )
                return True

            except TimeoutError:
                _LOGGER.warning(
                    "Timeout executing %s script %s for alarm %s (attempt %d/%d)",
                    script_type,
                    script_entity_id,
                    alarm_id,
                    attempt + 1,
                    max_retries,
                )

            except Exception as err:
                _LOGGER.warning(
                    "Error executing %s script %s for alarm %s (attempt %d/%d): %s",
                    script_type,
                    script_entity_id,
                    alarm_id,
                    attempt + 1,
                    max_retries,
                    err,
                )

            # Exponential backoff
            if attempt < max_retries - 1:
                backoff = 2**attempt
                await asyncio.sleep(backoff)

        # All retries failed
        _LOGGER.error(
            "Failed to execute %s script %s for alarm %s after %d attempts",
            script_type,
            script_entity_id,
            alarm_id,
            max_retries,
        )

        # Fire script failed event
        self._fire_event(
            AlarmEvent.SCRIPT_FAILED,
            {
                ATTR_ALARM_ID: alarm_id,
                "script_entity_id": script_entity_id,
                "script_type": script_type,
                ATTR_ERROR_MESSAGE: f"Script failed after {max_retries} attempts",
            },
        )

        # Execute fallback if available
        if alarm.data.script_fallback and script_entity_id != alarm.data.script_fallback:
            _LOGGER.info(
                "Executing fallback script for alarm %s",
                alarm_id,
            )
            return await self._async_execute_script(
                alarm_id,
                self._get_effective_script(alarm, "script_fallback"),
                "fallback",
            )

        return False

    async def _async_check_missed_alarms(self) -> None:
        """Check for alarms that might have been missed during downtime."""
        now = dt_util.now()
        grace_period = timedelta(minutes=DEFAULT_MISSED_ALARM_GRACE_PERIOD)

        for alarm_id, alarm in self._alarms.items():
            if alarm.state != AlarmState.ARMED:
                continue

            if not alarm.data.enabled:
                continue

            # Calculate what the trigger time would have been
            expected_trigger = self._calculate_next_trigger(alarm.data)

            if expected_trigger is None:
                continue

            # Check if we missed a trigger within the grace period
            # This would happen if the expected next trigger is in the past
            # but within the grace period
            if expected_trigger < now:
                time_missed = now - expected_trigger
                if time_missed <= grace_period:
                    _LOGGER.warning(
                        "Detected missed alarm %s (was due %s ago)",
                        alarm_id,
                        time_missed,
                    )

                    # Fire missed event
                    self._fire_event(
                        AlarmEvent.MISSED,
                        {
                            **alarm.get_event_data(),
                            "missed_by_seconds": time_missed.total_seconds(),
                        },
                    )

                    # Trigger the missed alarm
                    await self._async_trigger_alarm(alarm_id, TRIGGER_MISSED_RECOVERY)

    def _schedule_health_check(self) -> None:
        """Schedule periodic health check."""
        if self._health_check_callback:
            self._health_check_callback()

        next_check = dt_util.now() + timedelta(seconds=HEALTH_CHECK_INTERVAL)

        self._health_check_callback = async_track_point_in_time(
            self.hass,
            lambda now: self.hass.loop.call_soon_threadsafe(
                lambda: self.hass.async_create_task(self._async_run_health_check())
            ),
            next_check,
        )

    async def _async_run_health_check(self) -> None:
        """Run health check."""
        issues = []

        # Check for inconsistent states
        for alarm_id, alarm in self._alarms.items():
            # Enabled but not scheduled
            if (
                alarm.data.enabled
                and alarm.state == AlarmState.ARMED
                and alarm_id not in self._scheduled_callbacks
            ):
                issues.append(f"Alarm {alarm_id} is armed but not scheduled")
                # Try to fix
                await self._schedule_alarm(alarm_id)

            # Snoozed without callback
            if alarm.state == AlarmState.SNOOZED and alarm_id not in self._snooze_callbacks:
                issues.append(f"Alarm {alarm_id} is snoozed but no wake callback")
                # Try to fix by re-triggering
                await self._async_trigger_alarm(alarm_id, TRIGGER_SCHEDULED)

            # Ringing without auto-dismiss
            if alarm.state == AlarmState.RINGING and alarm_id not in self._auto_dismiss_callbacks:
                issues.append(f"Alarm {alarm_id} is ringing but no auto-dismiss scheduled")
                # Schedule auto-dismiss
                auto_dismiss_time = dt_util.now() + timedelta(
                    minutes=alarm.data.auto_dismiss_timeout
                )
                self._schedule_auto_dismiss(alarm_id, auto_dismiss_time)

        # Update health status
        self._health_status = {
            "healthy": len(issues) == 0,
            "last_check": dt_util.now().isoformat(),
            "issues": issues,
            "alarm_count": len(self._alarms),
            "active_alarms": sum(
                1
                for a in self._alarms.values()
                if a.state in (AlarmState.RINGING, AlarmState.SNOOZED)
            ),
        }

        if issues:
            _LOGGER.warning("Health check found issues: %s", issues)
            self._fire_event(
                AlarmEvent.HEALTH_WARNING,
                {"issues": issues},
            )

        # Schedule next check
        if self._running:
            self._schedule_health_check()

        self._notify_update()

    async def async_validate_entities(self) -> None:
        """Validate that all referenced entities exist."""
        entity_registry = er.async_get(self.hass)
        missing_entities = []

        for alarm_id, alarm in self._alarms.items():
            for script_field in [
                "script_pre_alarm",
                "script_alarm",
                "script_post_alarm",
                "script_on_snooze",
                "script_on_dismiss",
                "script_on_arm",
                "script_on_cancel",
                "script_on_skip",
                "script_fallback",
            ]:
                script_id = getattr(alarm.data, script_field, None)
                if script_id:
                    # Check if entity exists
                    entity = entity_registry.async_get(script_id)
                    if entity is None:
                        # Also check by state
                        state = self.hass.states.get(script_id)
                        if state is None:
                            missing_entities.append((alarm_id, script_field, script_id))

        if missing_entities:
            for alarm_id, field, entity_id in missing_entities:
                _LOGGER.warning(
                    "Alarm %s references missing entity %s (%s)",
                    alarm_id,
                    entity_id,
                    field,
                )
            self._fire_event(
                AlarmEvent.HEALTH_WARNING,
                {
                    "message": "Some referenced scripts do not exist",
                    "missing_entities": [
                        {"alarm_id": a, "field": f, "entity_id": e} for a, f, e in missing_entities
                    ],
                },
            )

    def _fire_event(self, event_type: AlarmEvent, data: dict[str, Any]) -> None:
        """Fire an event."""
        event_data = {
            **data,
            "timestamp": dt_util.now().isoformat(),
        }
        self.hass.bus.async_fire(event_type, event_data)
        _LOGGER.debug("Fired event %s: %s", event_type, event_data)

    def _on_alarm_state_change(
        self, alarm_id: str, old_state: AlarmState, new_state: AlarmState
    ) -> None:
        """Handle alarm state change."""
        _LOGGER.debug(
            "Alarm %s state changed: %s -> %s",
            alarm_id,
            old_state,
            new_state,
        )

    def _cancel_scheduled_callback(self, alarm_id: str) -> None:
        """Cancel scheduled alarm callback."""
        if alarm_id in self._scheduled_callbacks:
            callback = self._scheduled_callbacks.pop(alarm_id)
            if callback:
                callback()

    def _cancel_snooze_callback(self, alarm_id: str) -> None:
        """Cancel snooze callback."""
        if alarm_id in self._snooze_callbacks:
            callback = self._snooze_callbacks.pop(alarm_id)
            if callback:
                callback()

    def _cancel_auto_dismiss_callback(self, alarm_id: str) -> None:
        """Cancel auto-dismiss callback."""
        if alarm_id in self._auto_dismiss_callbacks:
            callback = self._auto_dismiss_callbacks.pop(alarm_id)
            if callback:
                callback()

    def _cancel_pre_alarm_callback(self, alarm_id: str) -> None:
        """Cancel pre-alarm callback."""
        if alarm_id in self._pre_alarm_callbacks:
            callback = self._pre_alarm_callbacks.pop(alarm_id)
            if callback:
                callback()

    def register_update_callback(self, callback: Callable) -> Callable:
        """Register a callback for updates."""
        self._update_callbacks.append(callback)

        def remove_callback() -> None:
            if callback in self._update_callbacks:
                self._update_callbacks.remove(callback)

        return remove_callback

    def register_entity_adder_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for when new alarms are added."""
        self._entity_adder_callbacks.append(callback)

    def _notify_update(self) -> None:
        """Notify all registered callbacks of an update."""
        for update_callback in self._update_callbacks:
            try:
                # Use call_soon_threadsafe to ensure thread safety when scheduling callbacks
                # This is necessary because _notify_update can be called from timer callbacks
                if asyncio.iscoroutinefunction(update_callback):
                    # For async callbacks, wrap the task creation in call_soon_threadsafe
                    self.hass.loop.call_soon_threadsafe(
                        lambda cb=update_callback: self.hass.async_create_task(cb())
                    )
                else:
                    # For sync callbacks like async_write_ha_state
                    self.hass.loop.call_soon_threadsafe(update_callback)
            except Exception:
                _LOGGER.exception("Error in update callback")

    def _notify_entity_adders(self, alarm_id: str) -> None:
        """Notify all entity adder callbacks of a new alarm."""
        # Verify alarm exists before notifying (defensive check)
        if alarm_id not in self._alarms:
            _LOGGER.warning("Skipping entity adder notification - alarm %s not found", alarm_id)
            return

        # Use a copy of the list to avoid issues if callbacks modify the list
        callbacks = list(self._entity_adder_callbacks)
        for adder_callback in callbacks:
            try:
                # Double-check alarm still exists before each callback
                if alarm_id not in self._alarms:
                    _LOGGER.warning(
                        "Alarm %s was removed during entity creation, stopping", alarm_id
                    )
                    break
                adder_callback(alarm_id)
            except Exception:
                _LOGGER.exception("Error in entity adder callback for alarm %s", alarm_id)

    async def async_register_services(self) -> None:
        """Register services."""
        # Service schemas
        snooze_schema = vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): cv.entity_id,
                vol.Optional(ATTR_DURATION): vol.Coerce(int),
            }
        )

        entity_schema = vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): cv.entity_id,
            }
        )

        set_time_schema = vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): cv.entity_id,
                vol.Required(ATTR_ALARM_TIME): cv.string,
            }
        )

        set_days_schema = vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): cv.entity_id,
                vol.Required(ATTR_DAYS): vol.All(cv.ensure_list, [cv.string]),
            }
        )

        create_alarm_schema = vol.Schema(
            {
                vol.Required(CONF_ALARM_NAME): cv.string,
                vol.Required(CONF_ALARM_TIME): cv.string,
                vol.Optional(CONF_DAYS, default=WEEKDAYS[:5]): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_ENABLED, default=True): cv.boolean,
                vol.Optional(CONF_ONE_TIME, default=False): cv.boolean,
                vol.Optional(CONF_SNOOZE_DURATION, default=DEFAULT_SNOOZE_DURATION): vol.Coerce(
                    int
                ),
                vol.Optional(CONF_MAX_SNOOZE_COUNT, default=3): vol.Coerce(int),
                vol.Optional(CONF_USE_DEVICE_DEFAULTS, default=True): cv.boolean,
                vol.Optional("entry_id"): cv.string,
            }
        )

        delete_alarm_schema = vol.Schema(
            {
                vol.Required(CONF_ALARM_ID): cv.string,
            }
        )

        set_scripts_schema = vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): cv.entity_id,
                vol.Optional(CONF_SCRIPT_PRE_ALARM): cv.entity_id,
                vol.Optional(CONF_SCRIPT_ALARM): cv.entity_id,
                vol.Optional(CONF_SCRIPT_POST_ALARM): cv.entity_id,
                vol.Optional(CONF_SCRIPT_ON_SNOOZE): cv.entity_id,
                vol.Optional(CONF_SCRIPT_ON_DISMISS): cv.entity_id,
                vol.Optional(CONF_SCRIPT_ON_ARM): cv.entity_id,
                vol.Optional(CONF_SCRIPT_ON_CANCEL): cv.entity_id,
                vol.Optional(CONF_SCRIPT_ON_SKIP): cv.entity_id,
                vol.Optional(CONF_SCRIPT_FALLBACK): cv.entity_id,
                vol.Optional(CONF_SCRIPT_TIMEOUT): vol.Coerce(int),
                vol.Optional(CONF_SCRIPT_RETRY_COUNT): vol.Coerce(int),
            }
        )

        async def handle_snooze(call: ServiceCall) -> None:
            """Handle snooze service call."""
            try:
                entity_id = call.data[ATTR_ENTITY_ID]
                duration = call.data.get(ATTR_DURATION)
                _LOGGER.debug(
                    "handle_snooze called: entity_id=%s, duration=%s", entity_id, duration
                )
                alarm_id = self._entity_id_to_alarm_id(entity_id)
                if alarm_id:
                    _LOGGER.debug("Resolved to alarm_id=%s, calling async_snooze", alarm_id)
                    await self.async_snooze(alarm_id, duration)
                else:
                    _LOGGER.error(
                        "Failed to resolve entity_id %s to alarm_id. Available alarms: %s",
                        entity_id,
                        list(self._alarms.keys()),
                    )
            except Exception as err:
                _LOGGER.error("Error in snooze service: %s", err, exc_info=True)

        async def handle_dismiss(call: ServiceCall) -> None:
            """Handle dismiss service call."""
            try:
                entity_id = call.data[ATTR_ENTITY_ID]
                _LOGGER.debug("handle_dismiss called: entity_id=%s", entity_id)
                alarm_id = self._entity_id_to_alarm_id(entity_id)
                if alarm_id:
                    _LOGGER.debug("Resolved to alarm_id=%s, calling async_dismiss", alarm_id)
                    await self.async_dismiss(alarm_id)
                else:
                    _LOGGER.error(
                        "Failed to resolve entity_id %s to alarm_id. Available alarms: %s",
                        entity_id,
                        list(self._alarms.keys()),
                    )
            except Exception as err:
                _LOGGER.error("Error in dismiss service: %s", err, exc_info=True)

        async def handle_skip_next(call: ServiceCall) -> None:
            """Handle skip next service call."""
            try:
                entity_id = call.data[ATTR_ENTITY_ID]
                _LOGGER.debug("handle_skip_next called: entity_id=%s", entity_id)
                alarm_id = self._entity_id_to_alarm_id(entity_id)
                if alarm_id:
                    _LOGGER.debug("Resolved to alarm_id=%s, calling async_skip_next", alarm_id)
                    await self.async_skip_next(alarm_id)
                else:
                    _LOGGER.error(
                        "Failed to resolve entity_id %s to alarm_id. Available alarms: %s",
                        entity_id,
                        list(self._alarms.keys()),
                    )
            except Exception as err:
                _LOGGER.error("Error in skip_next service: %s", err, exc_info=True)

        async def handle_cancel_skip(call: ServiceCall) -> None:
            """Handle cancel skip service call."""
            try:
                entity_id = call.data[ATTR_ENTITY_ID]
                _LOGGER.debug("handle_cancel_skip called: entity_id=%s", entity_id)
                alarm_id = self._entity_id_to_alarm_id(entity_id)
                if alarm_id:
                    _LOGGER.debug("Resolved to alarm_id=%s, calling async_cancel_skip", alarm_id)
                    await self.async_cancel_skip(alarm_id)
                else:
                    _LOGGER.error(
                        "Failed to resolve entity_id %s to alarm_id. Available alarms: %s",
                        entity_id,
                        list(self._alarms.keys()),
                    )
            except Exception as err:
                _LOGGER.error("Error in cancel_skip service: %s", err, exc_info=True)

        async def handle_test_alarm(call: ServiceCall) -> None:
            """Handle test alarm service call."""
            try:
                entity_id = call.data[ATTR_ENTITY_ID]
                _LOGGER.debug("handle_test_alarm called: entity_id=%s", entity_id)
                alarm_id = self._entity_id_to_alarm_id(entity_id)
                if alarm_id:
                    _LOGGER.debug("Resolved to alarm_id=%s, calling async_test_alarm", alarm_id)
                    await self.async_test_alarm(alarm_id)
                else:
                    _LOGGER.error(
                        "Failed to resolve entity_id %s to alarm_id. Available alarms: %s",
                        entity_id,
                        list(self._alarms.keys()),
                    )
            except Exception as err:
                _LOGGER.error("Error in test_alarm service: %s", err, exc_info=True)

        async def handle_set_time(call: ServiceCall) -> None:
            """Handle set time service call."""
            try:
                entity_id = call.data[ATTR_ENTITY_ID]
                time = call.data[ATTR_ALARM_TIME]
                _LOGGER.debug("handle_set_time called: entity_id=%s, time=%s", entity_id, time)
                alarm_id = self._entity_id_to_alarm_id(entity_id)
                if alarm_id:
                    _LOGGER.debug("Resolved to alarm_id=%s, calling async_set_time", alarm_id)
                    await self.async_set_time(alarm_id, time)
                else:
                    _LOGGER.error(
                        "Failed to resolve entity_id %s to alarm_id. Available alarms: %s",
                        entity_id,
                        list(self._alarms.keys()),
                    )
            except Exception as err:
                _LOGGER.error("Error in set_time service: %s", err, exc_info=True)

        async def handle_set_days(call: ServiceCall) -> None:
            """Handle set days service call."""
            try:
                entity_id = call.data[ATTR_ENTITY_ID]
                days = call.data[ATTR_DAYS]
                _LOGGER.debug("handle_set_days called: entity_id=%s, days=%s", entity_id, days)
                alarm_id = self._entity_id_to_alarm_id(entity_id)
                if alarm_id:
                    _LOGGER.debug("Resolved to alarm_id=%s, calling async_set_days", alarm_id)
                    await self.async_set_days(alarm_id, days)
                else:
                    _LOGGER.error(
                        "Failed to resolve entity_id %s to alarm_id. Available alarms: %s",
                        entity_id,
                        list(self._alarms.keys()),
                    )
            except Exception as err:
                _LOGGER.error("Error in set_days service: %s", err, exc_info=True)

        async def handle_set_scripts(call: ServiceCall) -> None:
            """Handle set scripts service call."""
            try:
                entity_id = call.data[ATTR_ENTITY_ID]
                _LOGGER.debug("handle_set_scripts called: entity_id=%s", entity_id)
                alarm_id = self._entity_id_to_alarm_id(entity_id)
                if alarm_id:
                    _LOGGER.debug("Resolved to alarm_id=%s, calling async_set_scripts", alarm_id)
                    await self.async_set_scripts(
                        alarm_id,
                        script_pre_alarm=call.data.get(CONF_SCRIPT_PRE_ALARM),
                        script_alarm=call.data.get(CONF_SCRIPT_ALARM),
                        script_post_alarm=call.data.get(CONF_SCRIPT_POST_ALARM),
                        script_on_snooze=call.data.get(CONF_SCRIPT_ON_SNOOZE),
                        script_on_dismiss=call.data.get(CONF_SCRIPT_ON_DISMISS),
                        script_on_arm=call.data.get(CONF_SCRIPT_ON_ARM),
                        script_on_cancel=call.data.get(CONF_SCRIPT_ON_CANCEL),
                        script_on_skip=call.data.get(CONF_SCRIPT_ON_SKIP),
                        script_fallback=call.data.get(CONF_SCRIPT_FALLBACK),
                        script_timeout=call.data.get(CONF_SCRIPT_TIMEOUT),
                        script_retry_count=call.data.get(CONF_SCRIPT_RETRY_COUNT),
                    )
                else:
                    _LOGGER.error(
                        "Failed to resolve entity_id %s to alarm_id. Available alarms: %s",
                        entity_id,
                        list(self._alarms.keys()),
                    )
            except Exception as err:
                _LOGGER.error("Error in set_scripts service: %s", err, exc_info=True)

        async def handle_create_alarm(call: ServiceCall) -> None:
            """Handle create alarm service call."""
            try:
                # Check if entry_id is provided and matches this coordinator
                target_entry_id = call.data.get("entry_id")
                if target_entry_id and target_entry_id != self.entry.entry_id:
                    # This call is not for this coordinator
                    return

                # If no entry_id provided and there are multiple coordinators,
                # only the first one will handle it (backward compatibility)
                if not target_entry_id and len(self.hass.data[DOMAIN]) > 2:
                    # Check if this is the first coordinator (excluding _register_resource)
                    coordinators = [
                        k for k in self.hass.data[DOMAIN].keys() if k != "_register_resource"
                    ]
                    if coordinators and coordinators[0] != self.entry.entry_id:
                        return

                import uuid

                alarm_id = f"alarm_{uuid.uuid4().hex[:8]}"
                alarm_data = AlarmData(
                    alarm_id=alarm_id,
                    name=call.data[CONF_ALARM_NAME],
                    time=call.data[CONF_ALARM_TIME],
                    days=call.data.get(CONF_DAYS, WEEKDAYS[:5]),
                    enabled=call.data.get(CONF_ENABLED, True),
                    one_time=call.data.get(CONF_ONE_TIME, False),
                    snooze_duration=call.data.get(CONF_SNOOZE_DURATION, DEFAULT_SNOOZE_DURATION),
                    max_snooze_count=call.data.get(CONF_MAX_SNOOZE_COUNT, 3),
                    use_device_defaults=call.data.get(CONF_USE_DEVICE_DEFAULTS, True),
                )
                await self.async_add_alarm(alarm_data)
            except Exception as err:
                _LOGGER.error("Error in create_alarm service: %s", err, exc_info=True)

        async def handle_delete_alarm(call: ServiceCall) -> None:
            """Handle delete alarm service call."""
            try:
                alarm_id = call.data[CONF_ALARM_ID]
                await self.async_remove_alarm(alarm_id)
            except Exception as err:
                _LOGGER.error("Error in delete_alarm service: %s", err, exc_info=True)

        # Register services (only if not already registered)
        if not self.hass.services.has_service(DOMAIN, SERVICE_SNOOZE):
            self.hass.services.async_register(
                DOMAIN, SERVICE_SNOOZE, handle_snooze, schema=snooze_schema
            )
        if not self.hass.services.has_service(DOMAIN, SERVICE_DISMISS):
            self.hass.services.async_register(
                DOMAIN, SERVICE_DISMISS, handle_dismiss, schema=entity_schema
            )
        if not self.hass.services.has_service(DOMAIN, SERVICE_SKIP_NEXT):
            self.hass.services.async_register(
                DOMAIN, SERVICE_SKIP_NEXT, handle_skip_next, schema=entity_schema
            )
        if not self.hass.services.has_service(DOMAIN, SERVICE_CANCEL_SKIP):
            self.hass.services.async_register(
                DOMAIN, SERVICE_CANCEL_SKIP, handle_cancel_skip, schema=entity_schema
            )
        if not self.hass.services.has_service(DOMAIN, SERVICE_TEST_ALARM):
            self.hass.services.async_register(
                DOMAIN, SERVICE_TEST_ALARM, handle_test_alarm, schema=entity_schema
            )
        if not self.hass.services.has_service(DOMAIN, SERVICE_SET_TIME):
            self.hass.services.async_register(
                DOMAIN, SERVICE_SET_TIME, handle_set_time, schema=set_time_schema
            )
        if not self.hass.services.has_service(DOMAIN, SERVICE_SET_DAYS):
            self.hass.services.async_register(
                DOMAIN, SERVICE_SET_DAYS, handle_set_days, schema=set_days_schema
            )
        if not self.hass.services.has_service(DOMAIN, SERVICE_SET_SCRIPTS):
            self.hass.services.async_register(
                DOMAIN, SERVICE_SET_SCRIPTS, handle_set_scripts, schema=set_scripts_schema
            )
        if not self.hass.services.has_service(DOMAIN, SERVICE_CREATE_ALARM):
            self.hass.services.async_register(
                DOMAIN, SERVICE_CREATE_ALARM, handle_create_alarm, schema=create_alarm_schema
            )
        if not self.hass.services.has_service(DOMAIN, SERVICE_DELETE_ALARM):
            self.hass.services.async_register(
                DOMAIN, SERVICE_DELETE_ALARM, handle_delete_alarm, schema=delete_alarm_schema
            )

        self._services_registered = True
        _LOGGER.debug("Registered alarm clock services")

    async def async_unregister_services(self) -> None:
        """Unregister services if this coordinator registered them."""
        if not self._services_registered:
            return

        # Check if there are other config entries still using this domain
        # Only unregister services if this is the last entry
        other_entries = [
            entry_id
            for entry_id in self.hass.data.get(DOMAIN, {})
            if entry_id != self.entry.entry_id and entry_id != "_register_resource"
        ]

        if other_entries:
            _LOGGER.debug(
                "Not unregistering services - other entries still active: %s",
                other_entries,
            )
            return

        # Unregister all services
        services_to_remove = [
            SERVICE_SNOOZE,
            SERVICE_DISMISS,
            SERVICE_SKIP_NEXT,
            SERVICE_CANCEL_SKIP,
            SERVICE_TEST_ALARM,
            SERVICE_SET_TIME,
            SERVICE_SET_DAYS,
            SERVICE_SET_SCRIPTS,
            SERVICE_CREATE_ALARM,
            SERVICE_DELETE_ALARM,
        ]

        for service_name in services_to_remove:
            if self.hass.services.has_service(DOMAIN, service_name):
                self.hass.services.async_remove(DOMAIN, service_name)

        self._services_registered = False
        _LOGGER.debug("Unregistered alarm clock services")

    def _entity_id_to_alarm_id(self, entity_id: str) -> str | None:
        """Convert entity ID to alarm ID."""
        _LOGGER.debug("_entity_id_to_alarm_id: Looking up entity_id=%s", entity_id)

        # Try to get the alarm_id from the entity's attributes
        entity = self.hass.states.get(entity_id)
        if entity and hasattr(entity, "attributes"):
            alarm_id = entity.attributes.get("alarm_id")
            _LOGGER.debug("Found alarm_id=%s in entity attributes", alarm_id)
            if alarm_id and alarm_id in self._alarms:
                _LOGGER.debug("alarm_id %s found in self._alarms, returning", alarm_id)
                return alarm_id
            elif alarm_id:
                _LOGGER.warning(
                    "alarm_id %s found in entity but NOT in self._alarms. Available: %s",
                    alarm_id,
                    list(self._alarms.keys()),
                )
        else:
            _LOGGER.debug("Entity %s not found or has no attributes", entity_id)

        # Fallback: try to match by entity_id ending
        _LOGGER.debug("Trying fallback: checking if entity_id ends with any alarm_id")
        for alarm_id in self._alarms:
            if entity_id.endswith(alarm_id):
                _LOGGER.debug("Fallback match: entity_id ends with alarm_id %s", alarm_id)
                return alarm_id

        _LOGGER.warning(
            "Could not resolve entity_id %s to any alarm_id. Available alarms: %s",
            entity_id,
            list(self._alarms.keys()),
        )
        return None
