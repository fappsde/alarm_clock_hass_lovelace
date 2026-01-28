"""Static code quality tests for alarm_clock integration."""

import re
from pathlib import Path


def test_no_deprecated_patterns():
    """Test that code doesn't use deprecated Home Assistant patterns."""
    errors = []
    base_path = Path(__file__).parent.parent / "custom_components" / "alarm_clock"

    # Patterns to check
    checks = [
        {
            "pattern": r"lovelace_data\.get\(['\"]resources['\"]\)",
            "message": "Deprecated: Use getattr(lovelace_data, 'resources', None) instead",
            "files": ["__init__.py"],
        },
        {
            "pattern": r"hass\.async_add_job\(",
            "message": "Deprecated: Use call_soon_threadsafe + async_create_task instead",
            "files": ["*.py"],
        },
        {
            "pattern": r"async_create_task\([^)]+\)(?!\s*\))",
            "message": "Warning: async_create_task should be wrapped in call_soon_threadsafe",
            "files": ["coordinator.py"],
            "ignore_if_has": "call_soon_threadsafe",
        },
    ]

    for check in checks:
        pattern = check["pattern"]
        message = check["message"]
        file_patterns = check["files"]

        for file_pattern in file_patterns:
            if "*" in file_pattern:
                files = base_path.glob(file_pattern)
            else:
                files = [base_path / file_pattern]

            for file_path in files:
                if not file_path.exists():
                    continue

                content = file_path.read_text()

                # Skip if ignore condition is met
                if "ignore_if_has" in check and check["ignore_if_has"] in content:
                    continue

                matches = re.finditer(pattern, content)
                for match in matches:
                    # Calculate line number
                    line_num = content[:match.start()].count("\n") + 1
                    errors.append(
                        f"{file_path.name}:{line_num}: {message}\n  Found: {match.group()}"
                    )

    return errors


def test_thread_safety():
    """Test that thread safety patterns are properly implemented."""
    errors = []
    coordinator_file = (
        Path(__file__).parent.parent
        / "custom_components"
        / "alarm_clock"
        / "coordinator.py"
    )

    if not coordinator_file.exists():
        return ["coordinator.py not found"]

    content = coordinator_file.read_text()

    # Check for async_create_task usage
    async_create_task_pattern = r"async_create_task\s*\("
    matches = list(re.finditer(async_create_task_pattern, content))

    if matches:
        # Ensure all are wrapped in call_soon_threadsafe
        for match in matches:
            # Get context around the match
            start = max(0, match.start() - 200)
            end = min(len(content), match.end() + 100)
            context = content[start:end]

            if "call_soon_threadsafe" not in context:
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    f"coordinator.py:{line_num}: async_create_task not wrapped in call_soon_threadsafe"
                )

    return errors


def test_entity_base_classes():
    """Test that entities use correct base classes."""
    errors = []
    entity_files = [
        "switch.py",
        "sensor.py",
        "binary_sensor.py",
        "time.py",
    ]

    base_path = Path(__file__).parent.parent / "custom_components" / "alarm_clock"

    for filename in entity_files:
        file_path = base_path / filename
        if not file_path.exists():
            continue

        content = file_path.read_text()

        # Check that RestoreEntity is imported if needed
        if "async_get_last_state" in content and "RestoreEntity" not in content:
            errors.append(
                f"{filename}: Uses async_get_last_state but doesn't import RestoreEntity"
            )

    # Check entity.py uses RestoreEntity
    entity_file = base_path / "entity.py"
    if entity_file.exists():
        content = entity_file.read_text()
        if "class AlarmClockEntity(Entity)" in content:
            if "RestoreEntity" not in content:
                errors.append("entity.py: AlarmClockEntity should extend RestoreEntity")

    return errors


def test_javascript_version():
    """Test that JavaScript card has version identifier."""
    errors = []
    js_files = [
        Path(__file__).parent.parent
        / "custom_components"
        / "alarm_clock"
        / "alarm-clock-card.js",
        Path(__file__).parent.parent / "www" / "alarm-clock-card.js",
    ]

    for js_file in js_files:
        if not js_file.exists():
            errors.append(f"{js_file.name} not found")
            continue

        content = js_file.read_text()

        # Check for version constant
        if "CARD_VERSION" not in content:
            errors.append(f"{js_file.name}: Missing CARD_VERSION constant")
        else:
            # Extract version
            version_match = re.search(r'CARD_VERSION\s*=\s*["\']([^"\']+)["\']', content)
            if version_match:
                print(f"  {js_file.name}: Version {version_match.group(1)}")
            else:
                errors.append(f"{js_file.name}: CARD_VERSION format invalid")

        # Check that removed methods don't exist
        if "_setViewMode" in content:
            errors.append(
                f"{js_file.name}: Found deprecated _setViewMode method (should be removed)"
            )

    return errors


def test_domain_consistency():
    """Test that DOMAIN constant is consistent across files."""
    errors = []
    const_file = (
        Path(__file__).parent.parent / "custom_components" / "alarm_clock" / "const.py"
    )

    if not const_file.exists():
        return ["const.py not found"]

    content = const_file.read_text()
    domain_match = re.search(r'DOMAIN\s*(?::\s*Final\s*)?=\s*["\']([^"\']+)["\']', content)

    if not domain_match:
        return ["DOMAIN not found in const.py"]

    expected_domain = domain_match.group(1)

    if expected_domain != "alarm_clock":
        errors.append(f"DOMAIN should be 'alarm_clock', found '{expected_domain}'")

    return errors


def test_service_definitions():
    """Test that services.yaml is valid."""
    errors = []
    services_file = (
        Path(__file__).parent.parent
        / "custom_components"
        / "alarm_clock"
        / "services.yaml"
    )

    if not services_file.exists():
        return ["services.yaml not found"]

    content = services_file.read_text()

    # Check for required services
    required_services = [
        "snooze",
        "dismiss",
        "skip_next",
        "test_alarm",
        "set_time",
        "create_alarm",
        "delete_alarm",
    ]

    for service in required_services:
        if f"{service}:" not in content:
            errors.append(f"services.yaml: Missing service '{service}'")

    return errors


def main():
    """Run all code quality tests."""
    print("=" * 70)
    print("Static Code Quality Tests for Alarm Clock Integration")
    print("=" * 70)
    print()

    all_errors = []

    tests = [
        ("Deprecated patterns", test_no_deprecated_patterns),
        ("Thread safety", test_thread_safety),
        ("Entity base classes", test_entity_base_classes),
        ("JavaScript version", test_javascript_version),
        ("Domain consistency", test_domain_consistency),
        ("Service definitions", test_service_definitions),
    ]

    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        errors = test_func()
        if errors:
            all_errors.extend(errors)
            for error in errors:
                print(f"  ✗ {error}")
        else:
            print(f"  ✓ Passed")
        print()

    print("=" * 70)
    if all_errors:
        print(f"FAILED: {len(all_errors)} issue(s) found")
        return 1
    else:
        print("SUCCESS: All code quality tests passed!")
        print()
        print("Summary:")
        print("  ✓ No deprecated patterns found")
        print("  ✓ Thread safety properly implemented")
        print("  ✓ Entity base classes correct")
        print("  ✓ JavaScript versioning in place")
        print("  ✓ Domain constants consistent")
        print("  ✓ Service definitions valid")
        print()
        print("This integration should not interfere with other HACS integrations.")
        return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
