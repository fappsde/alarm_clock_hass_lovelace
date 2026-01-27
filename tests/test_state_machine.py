"""Tests for the alarm clock state machine."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from custom_components.alarm_clock.state_machine import (
    AlarmData,
    AlarmStateMachine,
    AlarmRuntimeState,
    InvalidStateTransitionError,
)
from custom_components.alarm_clock.const import AlarmState, VALID_STATE_TRANSITIONS


class TestAlarmData:
    """Tests for AlarmData class."""

    def test_create_alarm_data(self):
        """Test creating alarm data."""
        alarm = AlarmData(
            alarm_id="test_1",
            name="Test Alarm",
            time="07:30",
        )

        assert alarm.alarm_id == "test_1"
        assert alarm.name == "Test Alarm"
        assert alarm.time == "07:30"
        assert alarm.enabled is True
        assert alarm.one_time is False
        assert alarm.snooze_duration == 9

    def test_alarm_data_to_dict(self):
        """Test converting alarm data to dict."""
        alarm = AlarmData(
            alarm_id="test_1",
            name="Test Alarm",
            time="07:30",
            days=["monday", "friday"],
        )

        data = alarm.to_dict()

        assert data["alarm_id"] == "test_1"
        assert data["name"] == "Test Alarm"
        assert data["time"] == "07:30"
        assert data["days"] == ["monday", "friday"]

    def test_alarm_data_from_dict(self):
        """Test creating alarm data from dict."""
        data = {
            "alarm_id": "test_1",
            "name": "Test Alarm",
            "time": "08:00",
            "enabled": False,
            "days": ["saturday", "sunday"],
            "one_time": True,
        }

        alarm = AlarmData.from_dict(data)

        assert alarm.alarm_id == "test_1"
        assert alarm.enabled is False
        assert alarm.one_time is True
        assert "saturday" in alarm.days

    def test_alarm_data_validation_valid(self):
        """Test validating valid alarm data."""
        alarm = AlarmData(
            alarm_id="test_1",
            name="Test Alarm",
            time="07:30",
            days=["monday"],
        )

        errors = alarm.validate()

        assert len(errors) == 0

    def test_alarm_data_validation_invalid_time(self):
        """Test validating alarm data with invalid time."""
        alarm = AlarmData(
            alarm_id="test_1",
            name="Test Alarm",
            time="25:00",  # Invalid
        )

        errors = alarm.validate()

        assert len(errors) > 0
        assert any("time" in e.lower() for e in errors)

    def test_alarm_data_validation_invalid_time_format(self):
        """Test validating alarm data with invalid time format."""
        alarm = AlarmData(
            alarm_id="test_1",
            name="Test Alarm",
            time="7:30:00",  # Invalid format
        )

        errors = alarm.validate()

        assert len(errors) > 0

    def test_alarm_data_validation_invalid_day(self):
        """Test validating alarm data with invalid day."""
        alarm = AlarmData(
            alarm_id="test_1",
            name="Test Alarm",
            time="07:30",
            days=["monday", "invalid_day"],
        )

        errors = alarm.validate()

        assert len(errors) > 0
        assert any("day" in e.lower() for e in errors)

    def test_alarm_data_validation_negative_snooze(self):
        """Test validating alarm data with negative snooze duration."""
        alarm = AlarmData(
            alarm_id="test_1",
            name="Test Alarm",
            time="07:30",
            snooze_duration=0,  # Invalid
        )

        errors = alarm.validate()

        assert len(errors) > 0


class TestAlarmStateMachine:
    """Tests for AlarmStateMachine class."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock hass object."""
        return MagicMock()

    @pytest.fixture
    def alarm_data(self):
        """Create test alarm data."""
        return AlarmData(
            alarm_id="test_1",
            name="Test Alarm",
            time="07:00",
            enabled=True,
        )

    @pytest.fixture
    def state_machine(self, mock_hass, alarm_data):
        """Create a state machine for testing."""
        return AlarmStateMachine(mock_hass, alarm_data)

    def test_initial_state_enabled(self, mock_hass):
        """Test initial state when enabled."""
        alarm_data = AlarmData(
            alarm_id="test_1",
            name="Test",
            time="07:00",
            enabled=True,
        )
        sm = AlarmStateMachine(mock_hass, alarm_data)

        assert sm.state == AlarmState.ARMED

    def test_initial_state_disabled(self, mock_hass):
        """Test initial state when disabled."""
        alarm_data = AlarmData(
            alarm_id="test_1",
            name="Test",
            time="07:00",
            enabled=False,
        )
        sm = AlarmStateMachine(mock_hass, alarm_data)

        assert sm.state == AlarmState.DISABLED

    @pytest.mark.asyncio
    async def test_valid_transition_armed_to_ringing(self, state_machine):
        """Test valid transition from armed to ringing."""
        result = await state_machine.transition_to(AlarmState.RINGING)

        assert result is True
        assert state_machine.state == AlarmState.RINGING

    @pytest.mark.asyncio
    async def test_valid_transition_ringing_to_snoozed(self, state_machine):
        """Test valid transition from ringing to snoozed."""
        await state_machine.transition_to(AlarmState.RINGING)

        result = await state_machine.transition_to(AlarmState.SNOOZED)

        assert result is True
        assert state_machine.state == AlarmState.SNOOZED
        assert state_machine.snooze_count == 1

    @pytest.mark.asyncio
    async def test_valid_transition_ringing_to_dismissed(self, state_machine):
        """Test valid transition from ringing to dismissed."""
        await state_machine.transition_to(AlarmState.RINGING)

        result = await state_machine.transition_to(AlarmState.DISMISSED)

        assert result is True
        assert state_machine.state == AlarmState.DISMISSED

    @pytest.mark.asyncio
    async def test_invalid_transition_disabled_to_ringing(self, mock_hass):
        """Test invalid transition from disabled to ringing."""
        alarm_data = AlarmData(
            alarm_id="test_1",
            name="Test",
            time="07:00",
            enabled=False,
        )
        sm = AlarmStateMachine(mock_hass, alarm_data)

        result = await sm.transition_to(AlarmState.RINGING)

        assert result is False
        assert sm.state == AlarmState.DISABLED

    @pytest.mark.asyncio
    async def test_invalid_transition_armed_to_snoozed(self, state_machine):
        """Test invalid transition from armed to snoozed."""
        result = await state_machine.transition_to(AlarmState.SNOOZED)

        assert result is False
        assert state_machine.state == AlarmState.ARMED

    @pytest.mark.asyncio
    async def test_force_transition(self, state_machine):
        """Test forced transition bypasses validation."""
        # This should normally fail
        result = await state_machine.transition_to(AlarmState.SNOOZED, force=True)

        assert result is True
        assert state_machine.state == AlarmState.SNOOZED

    @pytest.mark.asyncio
    async def test_snooze_count_increments(self, state_machine):
        """Test snooze count increments on each snooze."""
        await state_machine.transition_to(AlarmState.RINGING)
        await state_machine.transition_to(AlarmState.SNOOZED)

        assert state_machine.snooze_count == 1

        # Snooze again (through ringing)
        await state_machine.transition_to(AlarmState.RINGING)
        await state_machine.transition_to(AlarmState.SNOOZED)

        assert state_machine.snooze_count == 2

    @pytest.mark.asyncio
    async def test_snooze_count_resets_on_dismiss(self, state_machine):
        """Test snooze count resets when alarm is dismissed."""
        await state_machine.transition_to(AlarmState.RINGING)
        await state_machine.transition_to(AlarmState.SNOOZED)
        await state_machine.transition_to(AlarmState.DISMISSED)

        assert state_machine.snooze_count == 0

    @pytest.mark.asyncio
    async def test_last_triggered_set_on_ringing(self, state_machine):
        """Test last triggered time is set when alarm starts ringing."""
        assert state_machine.last_triggered is None

        await state_machine.transition_to(AlarmState.RINGING)

        assert state_machine.last_triggered is not None

    def test_can_transition_to_valid(self, state_machine):
        """Test can_transition_to returns True for valid transitions."""
        assert state_machine.can_transition_to(AlarmState.RINGING) is True
        assert state_machine.can_transition_to(AlarmState.DISABLED) is True
        assert state_machine.can_transition_to(AlarmState.PRE_ALARM) is True

    def test_can_transition_to_invalid(self, state_machine):
        """Test can_transition_to returns False for invalid transitions."""
        assert state_machine.can_transition_to(AlarmState.SNOOZED) is False
        assert state_machine.can_transition_to(AlarmState.DISMISSED) is False

    @pytest.mark.asyncio
    async def test_reset(self, state_machine):
        """Test reset returns state machine to initial state."""
        await state_machine.transition_to(AlarmState.RINGING)
        await state_machine.transition_to(AlarmState.SNOOZED)

        await state_machine.reset()

        assert state_machine.state == AlarmState.ARMED
        assert state_machine.snooze_count == 0

    def test_get_event_data(self, state_machine):
        """Test get_event_data returns correct data."""
        data = state_machine.get_event_data()

        assert data["alarm_id"] == "test_1"
        assert data["alarm_name"] == "Test Alarm"
        assert data["alarm_time"] == "07:00"
        assert data["alarm_state"] == "armed"

    def test_get_script_context(self, state_machine):
        """Test get_script_context returns correct context."""
        context = state_machine.get_script_context()

        assert context["alarm_id"] == "test_1"
        assert context["alarm_name"] == "Test Alarm"
        assert context["is_one_time"] is False

    @pytest.mark.asyncio
    async def test_state_change_callback(self, mock_hass, alarm_data):
        """Test state change callback is called."""
        callback = MagicMock()
        sm = AlarmStateMachine(mock_hass, alarm_data, on_state_change=callback)

        await sm.transition_to(AlarmState.RINGING)

        callback.assert_called_once_with(AlarmState.ARMED, AlarmState.RINGING)

    def test_to_restore_data(self, state_machine):
        """Test to_restore_data returns serializable data."""
        data = state_machine.to_restore_data()

        assert "state" in data
        assert "snooze_count" in data
        assert data["state"] == "armed"

    def test_restore_from_data(self, state_machine):
        """Test restore_from_data restores state correctly."""
        restore_data = {
            "state": "snoozed",
            "snooze_count": 2,
        }

        state_machine.restore_from_data(restore_data)

        assert state_machine.state == AlarmState.SNOOZED
        assert state_machine.snooze_count == 2


class TestValidStateTransitions:
    """Tests for state transition validation."""

    def test_all_states_have_transitions(self):
        """Test all states have defined transitions."""
        for state in AlarmState:
            assert state in VALID_STATE_TRANSITIONS

    def test_disabled_can_only_arm(self):
        """Test disabled state can only transition to armed."""
        valid = VALID_STATE_TRANSITIONS[AlarmState.DISABLED]
        assert valid == [AlarmState.ARMED]

    def test_armed_transitions(self):
        """Test armed state valid transitions."""
        valid = VALID_STATE_TRANSITIONS[AlarmState.ARMED]
        assert AlarmState.DISABLED in valid
        assert AlarmState.PRE_ALARM in valid
        assert AlarmState.RINGING in valid
        assert AlarmState.SNOOZED not in valid

    def test_ringing_transitions(self):
        """Test ringing state valid transitions."""
        valid = VALID_STATE_TRANSITIONS[AlarmState.RINGING]
        assert AlarmState.SNOOZED in valid
        assert AlarmState.DISMISSED in valid
        assert AlarmState.AUTO_DISMISSED in valid
        assert AlarmState.ARMED not in valid
