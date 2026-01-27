"""Fixtures for Alarm Clock tests."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.alarm_clock.const import DOMAIN
from custom_components.alarm_clock.coordinator import AlarmClockCoordinator
from custom_components.alarm_clock.state_machine import AlarmData
from custom_components.alarm_clock.store import AlarmClockStore

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    yield


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Alarm Clock",
        data={"name": "Test Alarm Clock"},
        source="user",
        entry_id="test_entry_id",
        unique_id="test_unique_id",
    )


@pytest.fixture
def mock_alarm_data() -> AlarmData:
    """Create mock alarm data."""
    return AlarmData(
        alarm_id="test_alarm_1",
        name="Morning Alarm",
        time="07:00",
        enabled=True,
        days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        one_time=False,
        skip_next=False,
        snooze_duration=9,
        max_snooze_count=3,
        auto_dismiss_timeout=60,
        pre_alarm_duration=5,
    )


@pytest.fixture
def mock_alarm_data_weekend() -> AlarmData:
    """Create mock alarm data for weekend."""
    return AlarmData(
        alarm_id="test_alarm_2",
        name="Weekend Alarm",
        time="09:00",
        enabled=True,
        days=["saturday", "sunday"],
        one_time=False,
        skip_next=False,
        snooze_duration=15,
        max_snooze_count=5,
        auto_dismiss_timeout=90,
        pre_alarm_duration=10,
    )


@pytest.fixture
def mock_alarm_data_one_time() -> AlarmData:
    """Create mock one-time alarm data."""
    return AlarmData(
        alarm_id="test_alarm_3",
        name="One-time Alarm",
        time="06:30",
        enabled=True,
        days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        one_time=True,
        skip_next=False,
        snooze_duration=5,
        max_snooze_count=2,
        auto_dismiss_timeout=30,
        pre_alarm_duration=0,
    )


@pytest.fixture
def mock_store(hass: HomeAssistant, mock_config_entry: ConfigEntry) -> AsyncMock:
    """Create a mock store."""
    from unittest.mock import Mock

    store = AsyncMock(spec=AlarmClockStore)
    store.alarms = {}
    store.runtime_states = {}
    store.settings = {}

    # Synchronous methods should use Mock, not AsyncMock
    store.get_all_alarms = Mock(return_value=[])
    store.get_alarm = Mock(return_value=None)
    store.get_runtime_state = Mock(return_value=None)

    return store


@pytest.fixture
async def mock_coordinator(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_store: AsyncMock,
) -> AlarmClockCoordinator:
    """Create a mock coordinator."""
    coordinator = AlarmClockCoordinator(hass, mock_config_entry, mock_store)
    return coordinator


@pytest.fixture
def mock_now() -> datetime:
    """Return a fixed datetime for testing."""
    return datetime(2024, 1, 15, 6, 0, 0, tzinfo=dt_util.UTC)  # Monday 6:00 AM


@pytest.fixture
def freeze_time(mock_now: datetime) -> Generator[datetime, None, None]:
    """Freeze time for testing."""
    with patch.object(dt_util, "now", return_value=mock_now):
        with patch.object(dt_util, "utcnow", return_value=mock_now):
            yield mock_now
