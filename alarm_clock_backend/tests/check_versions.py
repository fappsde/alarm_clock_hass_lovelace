#!/usr/bin/env python3
"""Version synchronization checker.

This script ensures that all version numbers are synchronized across:
- manifest.json
- www/alarm-clock-card.js
- custom_components/alarm_clock/alarm-clock-card.js

Exit code 0 if all versions match, 1 if mismatch found.
"""
import json
import re
import sys
from pathlib import Path


def get_manifest_version() -> str:
    """Get version from manifest.json."""
    manifest_path = Path("custom_components/alarm_clock/manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    return manifest.get("version", "unknown")


def get_card_version(card_path: Path) -> str:
    """Get version from card JS file."""
    with open(card_path) as f:
        content = f.read()

    # Extract: const CARD_VERSION = "X.X.X";
    match = re.search(r'const CARD_VERSION = "([^"]+)"', content)
    if match:
        return match.group(1)
    return "unknown"


def check_card_files_identical() -> bool:
    """Check if both card files are identical."""
    www_path = Path("www/alarm-clock-card.js")
    cc_path = Path("custom_components/alarm_clock/alarm-clock-card.js")

    with open(www_path) as f:
        www_content = f.read()

    with open(cc_path) as f:
        cc_content = f.read()

    return www_content == cc_content


def main():
    """Main version check."""
    print("Checking version synchronization...")

    # Get versions
    manifest_version = get_manifest_version()
    www_card_version = get_card_version(Path("www/alarm-clock-card.js"))
    cc_card_version = get_card_version(
        Path("custom_components/alarm_clock/alarm-clock-card.js")
    )

    print(f"Manifest version:              {manifest_version}")
    print(f"WWW card version:              {www_card_version}")
    print(f"Custom components card version: {cc_card_version}")

    # Check for mismatches
    errors = []

    if manifest_version != www_card_version:
        errors.append(
            f"Manifest ({manifest_version}) doesn't match WWW card ({www_card_version})"
        )

    if manifest_version != cc_card_version:
        errors.append(
            f"Manifest ({manifest_version}) doesn't match CC card ({cc_card_version})"
        )

    if www_card_version != cc_card_version:
        errors.append(
            f"WWW card ({www_card_version}) doesn't match CC card ({cc_card_version})"
        )

    # Check if card files are identical
    print("\nChecking if card files are identical...")
    if not check_card_files_identical():
        errors.append("Card files (www/ and custom_components/) are not identical!")
    else:
        print("✓ Card files are identical")

    # Report results
    if errors:
        print("\n❌ VERSION MISMATCH DETECTED:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease synchronize versions before committing!")
        return 1
    else:
        print("\n✓ All versions are synchronized!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
