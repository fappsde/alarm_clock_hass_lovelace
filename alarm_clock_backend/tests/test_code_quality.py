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
                    line_num = content[: match.start()].count("\n") + 1
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


def test_callback_thread_safety():
    """Test that callback list operations are thread-safe."""
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

    # Check that threading.Lock is imported
    if "import threading" not in content:
        errors.append(
            "coordinator.py: Missing 'import threading' - needed for callback thread safety"
        )
        return errors

    # Check that _callback_lock is defined
    if "_callback_lock" not in content:
        errors.append(
            "coordinator.py: Missing '_callback_lock' - needed for thread-safe callback operations"
        )

    # Check that _update_callbacks operations use the lock
    # Look for patterns that modify _update_callbacks without lock
    unsafe_patterns = [
        (
            r"self\._update_callbacks\.append\(",
            "append to _update_callbacks",
        ),
        (
            r"self\._update_callbacks\.remove\(",
            "remove from _update_callbacks",
        ),
        (
            r"self\._update_callbacks\.clear\(",
            "clear _update_callbacks",
        ),
        (
            r"self\._entity_adder_callbacks\.append\(",
            "append to _entity_adder_callbacks",
        ),
        (
            r"self\._entity_adder_callbacks\.clear\(",
            "clear _entity_adder_callbacks",
        ),
    ]

    for pattern, operation in unsafe_patterns:
        matches = list(re.finditer(pattern, content))
        for match in matches:
            # Check if this is within a 'with self._callback_lock:' block
            # Look backwards for the lock context
            start = max(0, match.start() - 300)
            context_before = content[start : match.start()]

            # Count 'with self._callback_lock:' vs closing of blocks
            if "with self._callback_lock:" not in context_before:
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    f"coordinator.py:{line_num}: {operation} without _callback_lock protection"
                )

    # Check that _notify_update copies the list before iteration
    notify_update_match = re.search(
        r"def _notify_update\(self\).*?(?=\n    def |\nclass |\Z)",
        content,
        re.DOTALL,
    )
    if notify_update_match:
        notify_content = notify_update_match.group()
        if "list(self._update_callbacks)" not in notify_content:
            if "callbacks = list(" not in notify_content:
                errors.append(
                    "coordinator.py: _notify_update should copy callback list before iteration"
                )

    return errors


def test_entity_null_checks():
    """Test that entity properties have null checks for self.alarm."""
    errors = []
    entity_files = [
        "switch.py",
        "sensor.py",
        "binary_sensor.py",
        "time.py",
    ]

    base_path = Path(__file__).parent.parent / "custom_components" / "alarm_clock"

    # Properties that access self.alarm and need null checks
    properties_needing_checks = [
        "is_on",
        "native_value",
        "icon",
        "extra_state_attributes",
        "available",
    ]

    for filename in entity_files:
        file_path = base_path / filename
        if not file_path.exists():
            continue

        content = file_path.read_text()

        # Find all property definitions that access self.alarm
        for prop_name in properties_needing_checks:
            # Find property definition
            prop_pattern = rf"@property\s+def {prop_name}\(self\).*?(?=@property|\n    async def |\n    def |\nclass |\Z)"
            matches = re.finditer(prop_pattern, content, re.DOTALL)

            for match in matches:
                prop_content = match.group()

                # Check if it accesses self.alarm
                if "self.alarm" in prop_content:
                    # Check for null check pattern: "alarm = self.alarm" followed by "if alarm is None"
                    has_null_check = (
                        "alarm = self.alarm" in prop_content
                        and "if alarm is None" in prop_content
                    )

                    # Also accept direct pattern with early return
                    has_direct_check = "if self.alarm is None" in prop_content

                    if not has_null_check and not has_direct_check:
                        line_num = content[: match.start()].count("\n") + 1
                        errors.append(
                            f"{filename}:{line_num}: Property '{prop_name}' accesses self.alarm without null check"
                        )

    return errors


def test_service_handler_exception_handling():
    """Test that service handlers have exception handling."""
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

    # Find all service handler definitions
    handler_pattern = r"async def (handle_\w+)\(call: ServiceCall\).*?(?=\n        async def |\n    async def |\n    def |\n        # Register|\Z)"
    matches = re.finditer(handler_pattern, content, re.DOTALL)

    for match in matches:
        handler_name = match.group(1)
        handler_content = match.group()

        # Check for try/except block
        if "try:" not in handler_content or "except" not in handler_content:
            line_num = content[: match.start()].count("\n") + 1
            errors.append(
                f"coordinator.py:{line_num}: Service handler '{handler_name}' missing exception handling"
            )

    return errors


def test_no_blocking_service_calls():
    """Test that service calls don't use blocking=True (can block event loop)."""
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

    # Find blocking=True in service calls
    blocking_pattern = r"async_call\([^)]*blocking\s*=\s*True"
    matches = list(re.finditer(blocking_pattern, content, re.DOTALL))

    for match in matches:
        line_num = content[: match.start()].count("\n") + 1
        errors.append(
            f"coordinator.py:{line_num}: Service call with blocking=True can block event loop during startup"
        )

    return errors


def test_module_level_imports():
    """Test that commonly used modules are imported at module level (not inline)."""
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

    # Check for inline imports that should be at module level
    inline_imports = [
        ("uuid", r"(?<!^)import uuid\b"),
    ]

    for module_name, pattern in inline_imports:
        # First check if it's imported at module level (in first 50 lines)
        first_50_lines = "\n".join(content.split("\n")[:50])
        if f"import {module_name}" in first_50_lines:
            # Good, it's at module level - now check for duplicate inline imports
            matches = list(re.finditer(pattern, content, re.MULTILINE))
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                if line_num > 50:  # Skip module-level import
                    errors.append(
                        f"coordinator.py:{line_num}: Inline 'import {module_name}' - already imported at module level"
                    )
        else:
            # Check if it's used but not imported at module level
            if module_name in content:
                errors.append(
                    f"coordinator.py: Module '{module_name}' used but not imported at module level"
                )

    return errors


def test_async_method_exception_handling():
    """Test that critical async methods have exception handling."""
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

    # Critical async methods that should have try/except
    critical_methods = [
        "async_add_alarm",
        "async_update_alarm",
        "async_remove_alarm",
    ]

    for method_name in critical_methods:
        # Find method definition
        method_pattern = rf"async def {method_name}\(self.*?(?=\n    async def |\n    def |\nclass |\Z)"
        match = re.search(method_pattern, content, re.DOTALL)

        if match:
            method_content = match.group()
            if "try:" not in method_content or "except" not in method_content:
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    f"coordinator.py:{line_num}: Async method '{method_name}' missing exception handling"
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


def test_config_flow_exception_handling():
    """Test that config flow has exception handling for coordinator calls."""
    errors = []
    config_flow_file = (
        Path(__file__).parent.parent
        / "custom_components"
        / "alarm_clock"
        / "config_flow.py"
    )

    if not config_flow_file.exists():
        return ["config_flow.py not found"]

    content = config_flow_file.read_text()

    # Find coordinator calls that should have exception handling
    coordinator_calls = [
        r"await coordinator\.async_add_alarm\(",
        r"await coordinator\.async_remove_alarm\(",
        r"await coordinator\.async_update_alarm\(",
    ]

    for pattern in coordinator_calls:
        matches = list(re.finditer(pattern, content))
        for match in matches:
            # Check if this call is within a try block
            start = max(0, match.start() - 500)
            context_before = content[start : match.start()]

            # Simple check: count try vs except in context
            if context_before.count("try:") <= context_before.count("except"):
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    f"config_flow.py:{line_num}: Coordinator call without exception handling"
                )

    return errors


def test_store_load_exception_handling():
    """Test that store.async_load has exception handling."""
    errors = []
    init_file = (
        Path(__file__).parent.parent
        / "custom_components"
        / "alarm_clock"
        / "__init__.py"
    )

    if not init_file.exists():
        return ["__init__.py not found"]

    content = init_file.read_text()

    # Find store.async_load call
    if "await store.async_load()" in content:
        # Check if it's within a try block
        match = re.search(r"await store\.async_load\(\)", content)
        if match:
            start = max(0, match.start() - 300)
            context_before = content[start : match.start()]

            if "try:" not in context_before:
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    f"__init__.py:{line_num}: store.async_load() should have exception handling"
                )

    return errors


def test_timezone_aware_datetime():
    """Test that state_machine.py uses dt_util.now() instead of datetime.now()."""
    errors = []
    state_machine_file = (
        Path(__file__).parent.parent
        / "custom_components"
        / "alarm_clock"
        / "state_machine.py"
    )

    if not state_machine_file.exists():
        return ["state_machine.py not found"]

    content = state_machine_file.read_text()

    # Check that datetime.now() is not used (should use dt_util.now() for timezone awareness)
    datetime_now_pattern = r"datetime\.now\(\)"
    matches = list(re.finditer(datetime_now_pattern, content))
    for match in matches:
        line_num = content[: match.start()].count("\n") + 1
        errors.append(
            f"state_machine.py:{line_num}: Use dt_util.now() instead of datetime.now() for timezone awareness"
        )

    # Check that dt_util is imported at module level
    if "from homeassistant.util import dt as dt_util" not in content:
        errors.append(
            "state_machine.py: Missing module-level import 'from homeassistant.util import dt as dt_util'"
        )

    return errors


def test_variable_scope_in_exception_handling():
    """Test that variables used after try blocks are defined before them."""
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

    # Check async_remove_alarm: entities_removed_count should be defined before try block
    remove_alarm_pattern = r"async def async_remove_alarm\(self.*?(?=\n    async def |\n    def |\nclass |\Z)"
    match = re.search(remove_alarm_pattern, content, re.DOTALL)
    if match:
        method_content = match.group()

        # Check that entities_removed_count is initialized before try block
        if "entities_removed_count" in method_content:
            # Find first occurrence of entities_removed_count
            first_use = method_content.find("entities_removed_count")
            try_pos = method_content.find("try:")

            if try_pos != -1 and first_use > try_pos:
                # Check if it's an assignment before try
                pre_try = method_content[:try_pos]
                if "entities_removed_count" not in pre_try:
                    line_num = content[: match.start()].count("\n") + 1
                    errors.append(
                        f"coordinator.py: async_remove_alarm should initialize entities_removed_count before try block"
                    )

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
        ("Callback thread safety", test_callback_thread_safety),
        ("Entity null checks", test_entity_null_checks),
        ("Service handler exceptions", test_service_handler_exception_handling),
        ("No blocking service calls", test_no_blocking_service_calls),
        ("Module level imports", test_module_level_imports),
        ("Async method exceptions", test_async_method_exception_handling),
        ("Entity base classes", test_entity_base_classes),
        ("JavaScript version", test_javascript_version),
        ("Domain consistency", test_domain_consistency),
        ("Service definitions", test_service_definitions),
        ("Config flow exceptions", test_config_flow_exception_handling),
        ("Store load exceptions", test_store_load_exception_handling),
        ("Timezone aware datetime", test_timezone_aware_datetime),
        ("Variable scope in exceptions", test_variable_scope_in_exception_handling),
    ]

    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        errors = test_func()
        if errors:
            all_errors.extend(errors)
            for error in errors:
                print(f"  ✗ {error}")
        else:
            print("  ✓ Passed")
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
        print("  ✓ Callback operations are thread-safe")
        print("  ✓ Entity properties have null checks")
        print("  ✓ Service handlers have exception handling")
        print("  ✓ No blocking service calls")
        print("  ✓ Module imports at top level")
        print("  ✓ Async methods have exception handling")
        print("  ✓ Entity base classes correct")
        print("  ✓ JavaScript versioning in place")
        print("  ✓ Domain constants consistent")
        print("  ✓ Service definitions valid")
        print("  ✓ Config flow has exception handling")
        print("  ✓ Store loading has exception handling")
        print("  ✓ Timezone-aware datetime usage")
        print("  ✓ Variable scope in exception handling")
        print()
        print("This integration should not interfere with other HACS integrations.")
        return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
