#!/usr/bin/env python3
"""Version checker for backend integration.

This script ensures the manifest.json version is valid.

Exit code 0 if valid, 1 if invalid.
"""
import json
import sys
from pathlib import Path


def get_manifest_version() -> str:
    """Get version from manifest.json."""
    manifest_path = Path("custom_components/alarm_clock/manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    return manifest.get("version", "unknown")


def main() -> int:
    """Check version in manifest.json."""
    print("Checking backend integration version...")
    
    manifest_version = get_manifest_version()
    
    if manifest_version == "unknown":
        print("❌ FAILED: Could not read version from manifest.json")
        return 1
    
    print(f"✅ manifest.json version: {manifest_version}")
    print("\nNote: The Alarm Clock Card is now in a separate repository.")
    print("      Install it separately from HACS (Frontend section).")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
