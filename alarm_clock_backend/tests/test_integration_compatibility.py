"""Test that alarm_clock integration doesn't interfere with other integrations."""

import importlib
import sys
from pathlib import Path

# Add custom_components to path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))


def test_module_imports():
    """Test that our integration modules can be imported without errors."""
    modules = [
        "alarm_clock",
        "alarm_clock.const",
        "alarm_clock.coordinator",
        "alarm_clock.entity",
        "alarm_clock.sensor",
        "alarm_clock.switch",
        "alarm_clock.binary_sensor",
        "alarm_clock.time",
        "alarm_clock.store",
        "alarm_clock.state_machine",
    ]

    errors = []
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            print(f"✓ Successfully imported {module_name}")
        except Exception as e:
            errors.append(f"✗ Failed to import {module_name}: {e}")
            print(errors[-1])

    return errors


def test_no_global_pollution():
    """Test that our integration doesn't pollute global namespace."""
    import alarm_clock

    # Get all attributes of the module
    module_attrs = dir(alarm_clock)

    # Check for unexpected global variables
    unexpected = []
    allowed_prefixes = ["__", "async_", "DOMAIN", "CONFIG_SCHEMA", "PLATFORMS", "CARD_"]

    for attr in module_attrs:
        # Skip private and allowed attributes
        if any(attr.startswith(prefix) for prefix in allowed_prefixes):
            continue

        # Skip standard module attributes
        if attr in ["annotations", "TYPE_CHECKING", "logging", "Path", "cv",
                    "ResourceStorageCollection", "ConfigEntry", "Platform",
                    "HomeAssistant", "dr", "HAS_STATIC_PATH_CONFIG",
                    "AlarmClockCoordinator", "AlarmClockStore", "ConfigType"]:
            continue

        unexpected.append(attr)

    if unexpected:
        print(f"✗ Unexpected global attributes found: {unexpected}")
        return [f"Global namespace pollution: {unexpected}"]
    else:
        print("✓ No global namespace pollution detected")
        return []


def test_no_side_effects_on_import():
    """Test that importing our module doesn't cause side effects."""
    import importlib
    import sys

    # Remove alarm_clock if already imported
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith("alarm_clock")]
    for mod in modules_to_remove:
        del sys.modules[mod]

    # Track initial state
    initial_modules = set(sys.modules.keys())

    # Import our module
    import alarm_clock  # noqa: F401

    # Check what new modules were loaded
    new_modules = set(sys.modules.keys()) - initial_modules
    alarm_clock_modules = {m for m in new_modules if "alarm_clock" in m}
    other_modules = new_modules - alarm_clock_modules

    # Filter out expected core modules
    expected_core = {"homeassistant", "typing", "pathlib", "logging"}
    unexpected_modules = [m for m in other_modules
                          if not any(m.startswith(exp) for exp in expected_core)]

    if unexpected_modules:
        print(f"✗ Unexpected modules loaded on import: {unexpected_modules}")
        return [f"Side effect - unexpected modules: {unexpected_modules}"]
    else:
        print("✓ No unexpected module loading on import")
        return []


def test_domain_isolation():
    """Test that our domain constant is properly isolated."""
    from alarm_clock.const import DOMAIN

    if DOMAIN != "alarm_clock":
        return [f"✗ Domain mismatch: expected 'alarm_clock', got '{DOMAIN}'"]

    print(f"✓ Domain properly set to '{DOMAIN}'")
    return []


def test_no_threading_issues():
    """Test that our thread safety fixes are in place."""
    import inspect
    from alarm_clock import coordinator

    # Get the source code of the coordinator
    source = inspect.getsource(coordinator)

    # Check for proper thread safety patterns
    errors = []

    # Should have call_soon_threadsafe for async_create_task
    if "async_create_task" in source:
        if "call_soon_threadsafe" not in source:
            errors.append("✗ async_create_task used without call_soon_threadsafe")
            print(errors[-1])
        else:
            print("✓ Thread safety pattern (call_soon_threadsafe) found")

    # Should not use deprecated patterns
    deprecated_patterns = [
        ("hass.async_add_job", "async_add_job is deprecated"),
    ]

    for pattern, msg in deprecated_patterns:
        if pattern in source:
            errors.append(f"✗ Deprecated pattern found: {msg}")
            print(errors[-1])

    if not errors:
        print("✓ No threading issues detected")

    return errors


def main():
    """Run all compatibility tests."""
    print("=" * 60)
    print("Testing Alarm Clock Integration Compatibility")
    print("=" * 60)
    print()

    all_errors = []

    print("1. Testing module imports...")
    all_errors.extend(test_module_imports())
    print()

    print("2. Testing global namespace pollution...")
    all_errors.extend(test_no_global_pollution())
    print()

    print("3. Testing side effects on import...")
    all_errors.extend(test_no_side_effects_on_import())
    print()

    print("4. Testing domain isolation...")
    all_errors.extend(test_domain_isolation())
    print()

    print("5. Testing thread safety...")
    all_errors.extend(test_no_threading_issues())
    print()

    print("=" * 60)
    if all_errors:
        print(f"FAILED: {len(all_errors)} issue(s) found:")
        for error in all_errors:
            print(f"  - {error}")
        return 1
    else:
        print("SUCCESS: All compatibility tests passed!")
        print("The integration should not interfere with other HACS integrations.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
