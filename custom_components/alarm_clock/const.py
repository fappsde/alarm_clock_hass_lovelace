"""Constants for the Alarm Clock integration."""
from __future__ import annotations

from enum import StrEnum
from typing import Final

# Domain
DOMAIN: Final = "alarm_clock"

# Configuration keys
CONF_ALARMS: Final = "alarms"
CONF_ALARM_ID: Final = "alarm_id"
CONF_ALARM_NAME: Final = "name"
CONF_ALARM_TIME: Final = "time"
CONF_ENABLED: Final = "enabled"
CONF_DAYS: Final = "days"
CONF_ONE_TIME: Final = "one_time"
CONF_SKIP_NEXT: Final = "skip_next"
CONF_SNOOZE_DURATION: Final = "snooze_duration"
CONF_MAX_SNOOZE_COUNT: Final = "max_snooze_count"
CONF_AUTO_DISMISS_TIMEOUT: Final = "auto_dismiss_timeout"
CONF_PRE_ALARM_DURATION: Final = "pre_alarm_duration"
CONF_GRADUAL_VOLUME: Final = "gradual_volume"
CONF_GRADUAL_VOLUME_DURATION: Final = "gradual_volume_duration"

# Script configuration
CONF_SCRIPT_PRE_ALARM: Final = "script_pre_alarm"
CONF_SCRIPT_ALARM: Final = "script_alarm"
CONF_SCRIPT_POST_ALARM: Final = "script_post_alarm"
CONF_SCRIPT_ON_SNOOZE: Final = "script_on_snooze"
CONF_SCRIPT_ON_DISMISS: Final = "script_on_dismiss"
CONF_SCRIPT_ON_ARM: Final = "script_on_arm"
CONF_SCRIPT_ON_CANCEL: Final = "script_on_cancel"
CONF_SCRIPT_ON_SKIP: Final = "script_on_skip"
CONF_SCRIPT_FALLBACK: Final = "script_fallback"
CONF_SCRIPT_TIMEOUT: Final = "script_timeout"
CONF_SCRIPT_RETRY_COUNT: Final = "script_retry_count"

# Reliability configuration
CONF_WATCHDOG_TIMEOUT: Final = "watchdog_timeout"
CONF_MISSED_ALARM_GRACE_PERIOD: Final = "missed_alarm_grace_period"
CONF_MISSED_ALARM_ACTION: Final = "missed_alarm_action"

# Default values
DEFAULT_SNOOZE_DURATION: Final = 9  # minutes
DEFAULT_MAX_SNOOZE_COUNT: Final = 3
DEFAULT_AUTO_DISMISS_TIMEOUT: Final = 60  # minutes
DEFAULT_PRE_ALARM_DURATION: Final = 5  # minutes
DEFAULT_SCRIPT_TIMEOUT: Final = 30  # seconds
DEFAULT_SCRIPT_RETRY_COUNT: Final = 3
DEFAULT_WATCHDOG_TIMEOUT: Final = 60  # seconds
DEFAULT_MISSED_ALARM_GRACE_PERIOD: Final = 5  # minutes
DEFAULT_GRADUAL_VOLUME_DURATION: Final = 5  # minutes

# Weekdays
WEEKDAYS: Final = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Store
STORE_VERSION: Final = 1
STORE_KEY: Final = f"{DOMAIN}.storage"


class AlarmState(StrEnum):
    """Alarm state enum."""

    DISABLED = "disabled"
    ARMED = "armed"
    PRE_ALARM = "pre_alarm"
    RINGING = "ringing"
    SNOOZED = "snoozed"
    DISMISSED = "dismissed"
    AUTO_DISMISSED = "auto_dismissed"
    MISSED = "missed"


class MissedAlarmAction(StrEnum):
    """Action to take when an alarm is missed."""

    NOTIFY_ONLY = "notify_only"
    TRIGGER_ANYWAY = "trigger_anyway"
    SKIP = "skip"


# Valid state transitions
VALID_STATE_TRANSITIONS: Final[dict[AlarmState, list[AlarmState]]] = {
    AlarmState.DISABLED: [AlarmState.ARMED],
    AlarmState.ARMED: [AlarmState.DISABLED, AlarmState.PRE_ALARM, AlarmState.RINGING, AlarmState.MISSED],
    AlarmState.PRE_ALARM: [AlarmState.RINGING, AlarmState.DISABLED, AlarmState.MISSED],
    AlarmState.RINGING: [
        AlarmState.SNOOZED,
        AlarmState.DISMISSED,
        AlarmState.AUTO_DISMISSED,
        AlarmState.DISABLED,
    ],
    AlarmState.SNOOZED: [AlarmState.RINGING, AlarmState.DISMISSED, AlarmState.DISABLED],
    AlarmState.DISMISSED: [AlarmState.ARMED, AlarmState.DISABLED],
    AlarmState.AUTO_DISMISSED: [AlarmState.ARMED, AlarmState.DISABLED],
    AlarmState.MISSED: [AlarmState.ARMED, AlarmState.DISABLED],
}


# Events
class AlarmEvent(StrEnum):
    """Alarm events."""

    ARMED = f"{DOMAIN}_armed"
    DISARMED = f"{DOMAIN}_disarmed"
    PRE_ALARM = f"{DOMAIN}_pre_alarm"
    TRIGGERED = f"{DOMAIN}_triggered"
    SNOOZED = f"{DOMAIN}_snoozed"
    DISMISSED = f"{DOMAIN}_dismissed"
    AUTO_DISMISSED = f"{DOMAIN}_auto_dismissed"
    MISSED = f"{DOMAIN}_missed"
    SKIPPED = f"{DOMAIN}_skipped"
    SCRIPT_FAILED = f"{DOMAIN}_script_failed"
    HEALTH_WARNING = f"{DOMAIN}_health_warning"
    TIME_CHANGED = f"{DOMAIN}_time_changed"


# Services
SERVICE_SNOOZE: Final = "snooze"
SERVICE_DISMISS: Final = "dismiss"
SERVICE_SKIP_NEXT: Final = "skip_next"
SERVICE_CANCEL_SKIP: Final = "cancel_skip"
SERVICE_TEST_ALARM: Final = "test_alarm"
SERVICE_SET_TIME: Final = "set_time"
SERVICE_SET_DAYS: Final = "set_days"
SERVICE_CREATE_ALARM: Final = "create_alarm"
SERVICE_DELETE_ALARM: Final = "delete_alarm"

# Attributes
ATTR_ALARM_ID: Final = "alarm_id"
ATTR_ALARM_NAME: Final = "alarm_name"
ATTR_ALARM_TIME: Final = "alarm_time"
ATTR_ALARM_STATE: Final = "alarm_state"
ATTR_NEXT_TRIGGER: Final = "next_trigger"
ATTR_SNOOZE_COUNT: Final = "snooze_count"
ATTR_IS_ONE_TIME: Final = "is_one_time"
ATTR_SKIP_NEXT: Final = "skip_next"
ATTR_DAYS: Final = "days"
ATTR_TRIGGER_TYPE: Final = "trigger_type"
ATTR_ERROR_MESSAGE: Final = "error_message"
ATTR_LAST_TRIGGERED: Final = "last_triggered"
ATTR_DURATION: Final = "duration"

# Trigger types
TRIGGER_SCHEDULED: Final = "scheduled"
TRIGGER_MANUAL_TEST: Final = "manual_test"
TRIGGER_MISSED_RECOVERY: Final = "missed_recovery"

# Health check
HEALTH_CHECK_INTERVAL: Final = 60  # seconds
