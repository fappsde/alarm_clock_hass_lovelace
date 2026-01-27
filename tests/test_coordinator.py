"""Tests for the alarm clock coordinator."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.alarm_clock.coordinator import AlarmClockCoordinator
from custom_components.alarm_clock.state_machine import AlarmData, AlarmStateMachine
from custom_components.alarm_clock.const import AlarmState, TRIGGER_SCHEDULED, TRIGGER_MANUAL_TEST


class TestAlarmClockCoordinator:
    """Tests for AlarmClockCoordinator class."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock hass object."""
        hass = MagicMock(spec=HomeAssistant)
        hass.bus = MagicMock()
        hass.bus.async_fire = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.services.async_register = MagicMock()
        hass.states = MagicMock()
        hass.states.get = MagicMock(return_value=None)
        hass.async_create_task = MagicMock(side_effect=lambda x: x)
        return hass

    @pytest.fixture
    def mock_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.title = "Test Alarm Clock"
        return entry

    @pytest.fixture
    def mock_store(self):
        """Create a mock store."""
        store = AsyncMock()
        store.get_all_alarms.return_value = []
        store.get_runtime_state.return_value = None
        store.settings = {}
        store.async_add_alarm = AsyncMock()
        store.async_update_alarm = AsyncMock()
        store.async_remove_alarm = AsyncMock(return_value=True)
        store.async_save_runtime_state = AsyncMock()
        return store

    @pytest.fixture
    def coordinator(self, mock_hass, mock_entry, mock_store):
        """Create a coordinator for testing."""
        return AlarmClockCoordinator(mock_hass, mock_entry, mock_store)

    @pytest.fixture
    def alarm_data(self):
        """Create test alarm data."""
        return AlarmData(
            alarm_id="test_alarm",
            name="Test Alarm",
            time="07:00",
            enabled=True,
            days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        )

    @pytest.mark.asyncio
    async def test_start_with_no_alarms(self, coordinator):
        """Test starting coordinator with no alarms."""
        await coordinator.async_start()

        assert coordinator._running is True
        assert len(coordinator.alarms) == 0

    @pytest.mark.asyncio
    async def test_start_with_alarms(self, coordinator, mock_store, alarm_data):
        """Test starting coordinator with existing alarms."""
        mock_store.get_all_alarms.return_value = [alarm_data]

        await coordinator.async_start()

        assert len(coordinator.alarms) == 1
        assert "test_alarm" in coordinator.alarms

    @pytest.mark.asyncio
    async def test_stop(self, coordinator):
        """Test stopping coordinator."""
        await coordinator.async_start()
        await coordinator.async_stop()

        assert coordinator._running is False

    @pytest.mark.asyncio
    async def test_add_alarm(self, coordinator, alarm_data, mock_store):
        """Test adding a new alarm."""
        await coordinator.async_start()
        await coordinator.async_add_alarm(alarm_data)

        assert "test_alarm" in coordinator.alarms
        mock_store.async_add_alarm.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_alarm(self, coordinator, alarm_data, mock_store):
        """Test removing an alarm."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        result = await coordinator.async_remove_alarm("test_alarm")

        assert result is True
        assert "test_alarm" not in coordinator.alarms
        mock_store.async_remove_alarm.assert_called_once_with("test_alarm")

    @pytest.mark.asyncio
    async def test_remove_nonexistent_alarm(self, coordinator):
        """Test removing an alarm that doesn't exist."""
        await coordinator.async_start()

        result = await coordinator.async_remove_alarm("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_set_enabled(self, coordinator, alarm_data, mock_store):
        """Test enabling/disabling an alarm."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        # Disable
        await coordinator.async_set_enabled("test_alarm", False)
        assert coordinator.alarms["test_alarm"].data.enabled is False

        # Enable
        await coordinator.async_set_enabled("test_alarm", True)
        assert coordinator.alarms["test_alarm"].data.enabled is True

    @pytest.mark.asyncio
    async def test_snooze_when_not_ringing(self, coordinator, alarm_data, mock_store):
        """Test snoozing an alarm that is not ringing."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        result = await coordinator.async_snooze("test_alarm")

        assert result is False

    @pytest.mark.asyncio
    async def test_snooze_when_ringing(self, coordinator, alarm_data, mock_store):
        """Test snoozing a ringing alarm."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        # Trigger alarm
        await coordinator.alarms["test_alarm"].transition_to(AlarmState.RINGING)

        result = await coordinator.async_snooze("test_alarm")

        assert result is True
        assert coordinator.alarms["test_alarm"].state == AlarmState.SNOOZED

    @pytest.mark.asyncio
    async def test_snooze_limit_reached(self, coordinator, alarm_data, mock_store):
        """Test snooze limit enforcement."""
        alarm_data.max_snooze_count = 2
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        alarm = coordinator.alarms["test_alarm"]

        # First snooze
        await alarm.transition_to(AlarmState.RINGING)
        await coordinator.async_snooze("test_alarm")

        # Second snooze
        await alarm.transition_to(AlarmState.RINGING)
        await coordinator.async_snooze("test_alarm")

        # Third snooze should fail
        await alarm.transition_to(AlarmState.RINGING)
        result = await coordinator.async_snooze("test_alarm")

        assert result is False
        assert alarm.snooze_count == 2

    @pytest.mark.asyncio
    async def test_dismiss_when_ringing(self, coordinator, alarm_data, mock_store):
        """Test dismissing a ringing alarm."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        await coordinator.alarms["test_alarm"].transition_to(AlarmState.RINGING)

        result = await coordinator.async_dismiss("test_alarm")

        assert result is True
        assert coordinator.alarms["test_alarm"].state == AlarmState.ARMED

    @pytest.mark.asyncio
    async def test_dismiss_when_not_active(self, coordinator, alarm_data, mock_store):
        """Test dismissing an alarm that is not active."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        result = await coordinator.async_dismiss("test_alarm")

        assert result is False

    @pytest.mark.asyncio
    async def test_skip_next(self, coordinator, alarm_data, mock_store):
        """Test skipping next occurrence."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        result = await coordinator.async_skip_next("test_alarm")

        assert result is True
        assert coordinator.alarms["test_alarm"].data.skip_next is True

    @pytest.mark.asyncio
    async def test_cancel_skip(self, coordinator, alarm_data, mock_store):
        """Test canceling skip."""
        alarm_data.skip_next = True
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        result = await coordinator.async_cancel_skip("test_alarm")

        assert result is True
        assert coordinator.alarms["test_alarm"].data.skip_next is False

    @pytest.mark.asyncio
    async def test_test_alarm(self, coordinator, alarm_data, mock_store):
        """Test triggering a test alarm."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        result = await coordinator.async_test_alarm("test_alarm")

        assert result is True
        assert coordinator.alarms["test_alarm"].state == AlarmState.RINGING
        assert coordinator.alarms["test_alarm"].current_trigger_type == TRIGGER_MANUAL_TEST

    @pytest.mark.asyncio
    async def test_set_time(self, coordinator, alarm_data, mock_store):
        """Test setting alarm time."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        result = await coordinator.async_set_time("test_alarm", "08:30")

        assert result is True
        assert coordinator.alarms["test_alarm"].data.time == "08:30"

    @pytest.mark.asyncio
    async def test_set_time_invalid(self, coordinator, alarm_data, mock_store):
        """Test setting invalid alarm time."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        result = await coordinator.async_set_time("test_alarm", "25:00")

        assert result is False
        assert coordinator.alarms["test_alarm"].data.time == "07:00"

    @pytest.mark.asyncio
    async def test_set_days(self, coordinator, alarm_data, mock_store):
        """Test setting alarm days."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        result = await coordinator.async_set_days("test_alarm", ["saturday", "sunday"])

        assert result is True
        assert coordinator.alarms["test_alarm"].data.days == ["saturday", "sunday"]

    @pytest.mark.asyncio
    async def test_one_time_alarm_disables_after_trigger(self, coordinator, mock_store):
        """Test one-time alarm auto-disables after trigger."""
        alarm_data = AlarmData(
            alarm_id="one_time",
            name="One Time",
            time="07:00",
            enabled=True,
            one_time=True,
            days=["monday"],
        )
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        # Trigger and dismiss
        await coordinator.alarms["one_time"].transition_to(AlarmState.RINGING)
        await coordinator.async_dismiss("one_time")

        assert coordinator.alarms["one_time"].data.enabled is False

    @pytest.mark.asyncio
    async def test_health_status(self, coordinator, alarm_data, mock_store):
        """Test health status reporting."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        status = coordinator.health_status

        assert "healthy" in status
        assert status["healthy"] is True

    @pytest.mark.asyncio
    async def test_events_fired(self, coordinator, alarm_data, mock_store, mock_hass):
        """Test events are fired on state changes."""
        mock_store.get_all_alarms.return_value = [alarm_data]
        await coordinator.async_start()

        await coordinator.alarms["test_alarm"].transition_to(AlarmState.RINGING)
        await coordinator.async_dismiss("test_alarm")

        # Check that events were fired
        assert mock_hass.bus.async_fire.called


class TestCalculateNextTrigger:
    """Tests for next trigger calculation."""

    @pytest.fixture
    def coordinator(self):
        """Create a coordinator for testing."""
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test"
        store = AsyncMock()
        store.get_all_alarms.return_value = []
        return AlarmClockCoordinator(hass, entry, store)

    def test_calculate_next_trigger_weekday(self, coordinator):
        """Test calculating next trigger for weekday alarm."""
        # Monday at 6:00 AM
        with patch.object(dt_util, "now") as mock_now:
            mock_now.return_value = datetime(2024, 1, 15, 6, 0, 0, tzinfo=dt_util.UTC)

            alarm = AlarmData(
                alarm_id="test",
                name="Test",
                time="07:00",
                days=["monday"],
            )

            next_trigger = coordinator._calculate_next_trigger(alarm)

            assert next_trigger is not None
            assert next_trigger.hour == 7
            assert next_trigger.minute == 0

    def test_calculate_next_trigger_time_passed_today(self, coordinator):
        """Test next trigger when today's time has passed."""
        # Monday at 8:00 AM (alarm is 7:00)
        with patch.object(dt_util, "now") as mock_now:
            mock_now.return_value = datetime(2024, 1, 15, 8, 0, 0, tzinfo=dt_util.UTC)

            alarm = AlarmData(
                alarm_id="test",
                name="Test",
                time="07:00",
                days=["monday", "tuesday"],
            )

            next_trigger = coordinator._calculate_next_trigger(alarm)

            assert next_trigger is not None
            # Should be Tuesday
            assert next_trigger.weekday() == 1

    def test_calculate_next_trigger_no_matching_day(self, coordinator):
        """Test next trigger when no matching day in near future."""
        # Monday
        with patch.object(dt_util, "now") as mock_now:
            mock_now.return_value = datetime(2024, 1, 15, 6, 0, 0, tzinfo=dt_util.UTC)

            alarm = AlarmData(
                alarm_id="test",
                name="Test",
                time="07:00",
                days=["saturday"],  # 5 days away
            )

            next_trigger = coordinator._calculate_next_trigger(alarm)

            assert next_trigger is not None
            assert next_trigger.weekday() == 5  # Saturday


class TestScriptExecution:
    """Tests for script execution."""

    @pytest.fixture
    def coordinator(self):
        """Create a coordinator for testing."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        entry = MagicMock()
        entry.entry_id = "test"
        store = AsyncMock()
        store.get_all_alarms.return_value = []
        return AlarmClockCoordinator(hass, entry, store)

    @pytest.mark.asyncio
    async def test_execute_script_success(self, coordinator):
        """Test successful script execution."""
        alarm_data = AlarmData(
            alarm_id="test",
            name="Test",
            time="07:00",
            script_alarm="script.test_script",
        )
        coordinator._alarms["test"] = AlarmStateMachine(
            coordinator.hass, alarm_data
        )

        result = await coordinator._async_execute_script(
            "test", "script.test_script", "alarm"
        )

        assert result is True
        coordinator.hass.services.async_call.assert_called()

    @pytest.mark.asyncio
    async def test_execute_script_none(self, coordinator):
        """Test execution with no script configured."""
        result = await coordinator._async_execute_script(
            "test", None, "alarm"
        )

        assert result is True
        coordinator.hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_script_retry_on_failure(self, coordinator):
        """Test script retry on failure."""
        alarm_data = AlarmData(
            alarm_id="test",
            name="Test",
            time="07:00",
            script_alarm="script.test_script",
            script_retry_count=3,
            script_timeout=1,
        )
        coordinator._alarms["test"] = AlarmStateMachine(
            coordinator.hass, alarm_data
        )

        # Make first two calls fail, third succeed
        coordinator.hass.services.async_call = AsyncMock(
            side_effect=[Exception("Fail"), Exception("Fail"), None]
        )

        result = await coordinator._async_execute_script(
            "test", "script.test_script", "alarm"
        )

        assert result is True
        assert coordinator.hass.services.async_call.call_count == 3
