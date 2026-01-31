"""Test script attributes on time and switch entities."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alarm_clock.const import DOMAIN
from custom_components.alarm_clock.coordinator import AlarmClockCoordinator
from custom_components.alarm_clock.state_machine import AlarmData, AlarmStateMachine


class TestScriptAttributes:
    """Test script attributes."""

    @pytest.mark.asyncio
    async def test_get_alarm_scripts_info_with_device_defaults(
        self, hass: HomeAssistant, mock_store
    ):
        """Test getting script info when using device defaults."""
        # Create config entry with options
        config_entry = MockConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Test Alarm Clock",
            data={"name": "Test Alarm Clock"},
            source="user",
            entry_id="test_entry_id",
            unique_id="test_unique_id",
            options={
                "default_script_alarm": "script.wake_up",
                "default_script_pre_alarm": "script.lights_on",
                "default_script_timeout": 45,
                "default_script_retry_count": 5,
            },
        )

        coordinator = AlarmClockCoordinator(hass, config_entry, mock_store)

        # Create an alarm with device defaults
        alarm_data = AlarmData(
            alarm_id="test_alarm",
            name="Test Alarm",
            time="07:00",
            use_device_defaults=True,
        )
        alarm = AlarmStateMachine(hass, alarm_data)

        # Get script info
        scripts_info = coordinator.get_alarm_scripts_info(alarm)

        # Verify device defaults are used
        assert scripts_info["use_device_defaults"] is True
        assert scripts_info["script_alarm"] == "script.wake_up"
        assert scripts_info["script_pre_alarm"] == "script.lights_on"
        assert scripts_info["script_timeout"] == 45
        assert scripts_info["script_retry_count"] == 5

    @pytest.mark.asyncio
    async def test_get_alarm_scripts_info_with_custom_scripts(
        self, hass: HomeAssistant, mock_coordinator: AlarmClockCoordinator
    ):
        """Test getting script info when using custom scripts."""
        # Create an alarm with custom scripts
        alarm_data = AlarmData(
            alarm_id="test_alarm",
            name="Test Alarm",
            time="07:00",
            use_device_defaults=False,
            script_alarm="script.custom_alarm",
            script_pre_alarm="script.custom_pre_alarm",
            script_timeout=60,
            script_retry_count=10,
        )
        alarm = AlarmStateMachine(hass, alarm_data)

        # Get script info
        scripts_info = mock_coordinator.get_alarm_scripts_info(alarm)

        # Verify custom scripts are used
        assert scripts_info["use_device_defaults"] is False
        assert scripts_info["script_alarm"] == "script.custom_alarm"
        assert scripts_info["script_pre_alarm"] == "script.custom_pre_alarm"
        assert scripts_info["script_timeout"] == 60
        assert scripts_info["script_retry_count"] == 10

    @pytest.mark.asyncio
    async def test_get_alarm_scripts_info_returns_all_scripts(
        self, hass: HomeAssistant, mock_coordinator: AlarmClockCoordinator
    ):
        """Test that all script types are included in the info."""
        alarm_data = AlarmData(
            alarm_id="test_alarm",
            name="Test Alarm",
            time="07:00",
            use_device_defaults=False,
            script_pre_alarm="script.pre",
            script_alarm="script.alarm",
            script_post_alarm="script.post",
            script_on_snooze="script.snooze",
            script_on_dismiss="script.dismiss",
            script_on_arm="script.arm",
            script_on_cancel="script.cancel",
            script_on_skip="script.skip",
            script_fallback="script.fallback",
        )
        alarm = AlarmStateMachine(hass, alarm_data)

        # Get script info
        scripts_info = mock_coordinator.get_alarm_scripts_info(alarm)

        # Verify all script types are present
        assert "script_pre_alarm" in scripts_info
        assert "script_alarm" in scripts_info
        assert "script_post_alarm" in scripts_info
        assert "script_on_snooze" in scripts_info
        assert "script_on_dismiss" in scripts_info
        assert "script_on_arm" in scripts_info
        assert "script_on_cancel" in scripts_info
        assert "script_on_skip" in scripts_info
        assert "script_fallback" in scripts_info

        assert scripts_info["script_pre_alarm"] == "script.pre"
        assert scripts_info["script_alarm"] == "script.alarm"
        assert scripts_info["script_post_alarm"] == "script.post"
