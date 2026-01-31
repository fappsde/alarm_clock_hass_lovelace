"""Tests for alarm_clock config flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.alarm_clock.const import DOMAIN


class TestConfigFlow:
    """Test the alarm_clock config flow."""

    async def test_config_flow_infinite_loop_prevention(self, hass: HomeAssistant):
        """Test that config flow doesn't create infinite loop with boolean fields.

        This tests the critical bug fix from v1.0.8 where unchecked boolean
        fields caused an infinite loop crash.
        """
        # Initialize flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Simulate form submission WITHOUT boolean field
        # (happens when checkbox is unchecked)
        user_input_without_bool = {
            "snooze_duration": 9,
            "max_snooze_count": 3,
            "auto_dismiss_timeout": 60,
            "pre_alarm_duration": 5,
            # Note: CONF_USE_DEVICE_DEFAULTS is NOT present
        }

        with patch.object(hass.config_entries.flow, "_async_create_entry") as mock_create:
            mock_create.return_value = {"type": data_entry_flow.RESULT_TYPE_CREATE_ENTRY}

            # This should complete successfully, not loop
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input_without_bool
            )

            # Verify alarm was created (not looping)
            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert mock_create.called

    async def test_config_flow_with_boolean_field(self, hass: HomeAssistant):
        """Test config flow WITH boolean field present."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        user_input_with_bool = {
            "snooze_duration": 9,
            "max_snooze_count": 3,
            "auto_dismiss_timeout": 60,
            "pre_alarm_duration": 5,
            "use_device_defaults": True,
        }

        with patch.object(hass.config_entries.flow, "_async_create_entry") as mock_create:
            mock_create.return_value = {"type": data_entry_flow.RESULT_TYPE_CREATE_ENTRY}

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input_with_bool
            )

            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert mock_create.called

    async def test_config_flow_all_fields_optional(self, hass: HomeAssistant):
        """Test that all optional fields can be omitted without crash."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Minimal input - all optional fields missing
        minimal_input = {}

        with patch.object(hass.config_entries.flow, "_async_create_entry") as mock_create:
            mock_create.return_value = {"type": data_entry_flow.RESULT_TYPE_CREATE_ENTRY}

            # Should use defaults and not crash
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], minimal_input
            )

            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

    async def test_config_flow_form_not_rerendered_infinitely(self, hass: HomeAssistant):
        """Test that form is not re-rendered after submission."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        initial_flow_id = result["flow_id"]
        user_input = {"snooze_duration": 9}

        with patch.object(hass.config_entries.flow, "_async_create_entry") as mock_create:
            mock_create.return_value = {"type": data_entry_flow.RESULT_TYPE_CREATE_ENTRY}

            result = await hass.config_entries.flow.async_configure(
                initial_flow_id, user_input
            )

            # After submission, should create entry, not show form again
            assert result["type"] != data_entry_flow.RESULT_TYPE_FORM
            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY


class TestErrorHandling:
    """Test error handling in critical code paths."""

    async def test_coordinator_handles_missing_alarm(self, hass: HomeAssistant):
        """Test that coordinator gracefully handles missing alarm."""
        from custom_components.alarm_clock.coordinator import AlarmClockCoordinator

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"

        coordinator = AlarmClockCoordinator(hass, mock_entry)

        # Try to access non-existent alarm
        result = await coordinator.async_set_enabled("non_existent_alarm", True)

        # Should return False, not crash
        assert result is False

    async def test_service_handles_invalid_entity(self, hass: HomeAssistant):
        """Test service calls handle invalid entity IDs gracefully."""
        # Test will be implemented when services are properly mocked
        pass

