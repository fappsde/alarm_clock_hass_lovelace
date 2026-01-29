"""Validation utilities for alarm clock integration."""
import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


class ValidationError(HomeAssistantError):
    """Validation error exception."""


def validate_time_format(time_value: Any) -> tuple[int, int]:
    """Validate and parse time value.

    Args:
        time_value: Time as dict {'hours': X, 'minutes': Y} or string "HH:MM"

    Returns:
        Tuple of (hours, minutes)

    Raises:
        ValidationError: If time format is invalid
    """
    try:
        if isinstance(time_value, dict):
            hours = int(time_value.get("hours", 0))
            minutes = int(time_value.get("minutes", 0))
        elif isinstance(time_value, str):
            parts = time_value.split(":")
            if len(parts) < 2:
                raise ValueError(f"Invalid time format: {time_value}")
            hours = int(parts[0])
            minutes = int(parts[1])
        else:
            raise ValueError(f"Unsupported time type: {type(time_value)}")

        # Validate ranges
        if not 0 <= hours <= 23:
            raise ValueError(f"Hour must be 0-23, got {hours}")
        if not 0 <= minutes <= 59:
            raise ValueError(f"Minute must be 0-59, got {minutes}")

        return hours, minutes

    except (ValueError, IndexError, KeyError, AttributeError) as e:
        raise ValidationError(f"Invalid time value: {time_value}") from e


def validate_alarm_name(name: str) -> str:
    """Validate and sanitize alarm name.

    Args:
        name: Alarm name to validate

    Returns:
        Sanitized alarm name

    Raises:
        ValidationError: If name is invalid
    """
    if not isinstance(name, str):
        raise ValidationError(f"Name must be string, got {type(name)}")

    # Strip whitespace
    name = name.strip()

    # Check not empty
    if not name:
        raise ValidationError("Alarm name cannot be empty")

    # Check length
    max_length = 50
    if len(name) > max_length:
        _LOGGER.warning(
            "Alarm name too long (%d chars), truncating to %d",
            len(name), max_length
        )
        name = name[:max_length]

    # Remove control characters
    name = "".join(char for char in name if ord(char) >= 32)

    # Ensure valid for entity ID
    # Entity IDs can't have special chars except underscore and hyphen
    if not re.match(r"^[\w\s\-]+$", name):
        _LOGGER.warning(
            "Alarm name contains special characters: %s",
            name
        )
        # Replace special chars with spaces
        name = re.sub(r"[^\w\s\-]", " ", name)

    return name


def validate_duration(
    value: Any,
    field_name: str,
    min_value: int = 0,
    max_value: int = 1440
) -> int:
    """Validate duration value.

    Args:
        value: Duration value to validate
        field_name: Name of field for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        Validated integer value

    Raises:
        ValidationError: If value is invalid
    """
    try:
        int_value = int(value)
    except (ValueError, TypeError) as e:
        raise ValidationError(
            f"{field_name} must be an integer, got {type(value)}"
        ) from e

    if not min_value <= int_value <= max_value:
        raise ValidationError(
            f"{field_name} must be between {min_value} and {max_value}, "
            f"got {int_value}"
        )

    return int_value


def validate_days(days: list[str]) -> list[str]:
    """Validate list of weekdays.

    Args:
        days: List of weekday names

    Returns:
        Validated list of weekdays

    Raises:
        ValidationError: If days list is invalid
    """
    if not isinstance(days, list):
        raise ValidationError(f"Days must be a list, got {type(days)}")

    valid_days = [
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday"
    ]

    # Validate each day
    validated_days = []
    for day in days:
        if not isinstance(day, str):
            raise ValidationError(f"Day must be string, got {type(day)}")

        day_lower = day.lower()
        if day_lower not in valid_days:
            raise ValidationError(f"Invalid day: {day}")

        validated_days.append(day_lower)

    # Check for duplicates
    if len(validated_days) != len(set(validated_days)):
        raise ValidationError("Duplicate days in list")

    # At least one day required (unless one-time alarm)
    # This check is done in coordinator

    return validated_days


async def validate_script_entity(
    hass: HomeAssistant,
    entity_id: str | None
) -> bool:
    """Validate that script entity exists.

    Args:
        hass: Home Assistant instance
        entity_id: Script entity ID to validate

    Returns:
        True if valid or None, False if invalid

    Raises:
        ValidationError: If entity exists but is not a script
    """
    if entity_id is None:
        return True

    if not isinstance(entity_id, str):
        raise ValidationError(
            f"Entity ID must be string, got {type(entity_id)}"
        )

    # Check entity exists
    state = hass.states.get(entity_id)
    if state is None:
        _LOGGER.warning("Script entity does not exist: %s", entity_id)
        return False

    # Check it's a script domain
    if not entity_id.startswith("script."):
        raise ValidationError(
            f"Entity must be a script, got {entity_id}"
        )

    return True


def validate_alarm_data(data: dict[str, Any]) -> dict[str, str]:
    """Validate complete alarm data.

    Args:
        data: Alarm data dictionary

    Returns:
        Dictionary of validation errors (empty if valid)
    """
    errors = {}

    # Validate name
    try:
        if "name" in data:
            data["name"] = validate_alarm_name(data["name"])
    except ValidationError as e:
        errors["name"] = str(e)

    # Validate time
    try:
        if "time" in data:
            validate_time_format(data["time"])
    except ValidationError as e:
        errors["time"] = str(e)

    # Validate days
    try:
        if "days" in data:
            data["days"] = validate_days(data["days"])
    except ValidationError as e:
        errors["days"] = str(e)

    # Validate numeric fields
    numeric_fields = {
        "snooze_duration": (1, 60),
        "max_snooze_count": (0, 10),
        "auto_dismiss_timeout": (1, 180),
        "pre_alarm_duration": (0, 60),
        "script_timeout": (1, 300),
        "script_retry_count": (0, 10),
    }

    for field, (min_val, max_val) in numeric_fields.items():
        if field in data:
            try:
                data[field] = validate_duration(
                    data[field], field, min_val, max_val
                )
            except ValidationError as e:
                errors[field] = str(e)

    return errors


class InputSanitizer:
    """Sanitize user input to prevent issues."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 100) -> str:
        """Sanitize string input.

        Args:
            value: String to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            value = str(value)

        # Remove leading/trailing whitespace
        value = value.strip()

        # Truncate to max length
        if len(value) > max_length:
            value = value[:max_length]

        # Remove control characters
        value = "".join(char for char in value if ord(char) >= 32)

        return value

    @staticmethod
    def sanitize_int(
        value: Any,
        min_value: int | None = None,
        max_value: int | None = None,
        default: int = 0
    ) -> int:
        """Sanitize integer input.

        Args:
            value: Value to sanitize
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            default: Default value if conversion fails

        Returns:
            Sanitized integer
        """
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Invalid integer value: %s, using default %d",
                value, default
            )
            return default

        # Clamp to range
        if min_value is not None and int_value < min_value:
            _LOGGER.warning(
                "Value %d below minimum %d, clamping",
                int_value, min_value
            )
            int_value = min_value

        if max_value is not None and int_value > max_value:
            _LOGGER.warning(
                "Value %d above maximum %d, clamping",
                int_value, max_value
            )
            int_value = max_value

        return int_value
