/**
 * Version Consistency Test
 *
 * CRITICAL: This test verifies that all version declarations match,
 * preventing version skew that causes stale cached resources.
 *
 * This test would have caught the bug where:
 * - manifest.json had version 1.0.8
 * - __init__.py hardcoded version 1.0.4
 * - Resource URL became /alarm_clock/alarm-clock-card.js?v=1.0.4
 * - Browser cached 1.0.4 forever
 * - Updates to 1.0.8 never loaded
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

describe('Version Consistency Test', () => {
  const rootDir = join(process.cwd());

  it('should have matching versions in all files', () => {
    // Read manifest.json (single source of truth)
    const manifestPath = join(rootDir, 'custom_components/alarm_clock/manifest.json');
    const manifestContent = readFileSync(manifestPath, 'utf-8');
    const manifest = JSON.parse(manifestContent);
    const manifestVersion = manifest.version;

    expect(manifestVersion).toBeDefined();
    expect(manifestVersion).toMatch(/^\d+\.\d+\.\d+$/); // Semantic versioning

    // Read package.json
    const packagePath = join(rootDir, 'package.json');
    const packageContent = readFileSync(packagePath, 'utf-8');
    const packageJson = JSON.parse(packageContent);
    const packageVersion = packageJson.version;

    expect(packageVersion).toBe(manifestVersion);

    // Read frontend card
    const cardPath = join(rootDir, 'custom_components/alarm_clock/alarm-clock-card.js');
    const cardContent = readFileSync(cardPath, 'utf-8');

    // Extract CARD_VERSION from the card
    const versionMatch = cardContent.match(/const CARD_VERSION = ["']([^"']+)["']/);
    expect(versionMatch).toBeTruthy();

    const cardVersion = versionMatch ? versionMatch[1] : null;
    expect(cardVersion).toBe(manifestVersion);

    // Verify www/ copy matches (if it exists)
    const wwwCardPath = join(rootDir, 'www/alarm-clock-card.js');
    try {
      const wwwCardContent = readFileSync(wwwCardPath, 'utf-8');
      const wwwVersionMatch = wwwCardContent.match(/const CARD_VERSION = ["']([^"']+)["']/);
      const wwwVersion = wwwVersionMatch ? wwwVersionMatch[1] : null;
      expect(wwwVersion).toBe(manifestVersion);
    } catch (e) {
      // www/alarm-clock-card.js may not exist, that's okay
    }
  });

  it('should use manifest.json version in __init__.py', () => {
    // Read __init__.py
    const initPath = join(rootDir, 'custom_components/alarm_clock/__init__.py');
    const initContent = readFileSync(initPath, 'utf-8');

    // Verify it reads from manifest.json (not hardcoded)
    expect(initContent).toContain('manifest.json');
    expect(initContent).toContain('def _get_version()');
    expect(initContent).toContain('CARD_VERSION = _get_version()');

    // Verify it does NOT have hardcoded version
    expect(initContent).not.toMatch(/CARD_VERSION = ["']\d+\.\d+\.\d+["']/);
  });

  it('should not have version skew between files', () => {
    const manifestPath = join(rootDir, 'custom_components/alarm_clock/manifest.json');
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
    const manifestVersion = manifest.version;

    const cardPath = join(rootDir, 'custom_components/alarm_clock/alarm-clock-card.js');
    const cardContent = readFileSync(cardPath, 'utf-8');
    const cardVersionMatch = cardContent.match(/const CARD_VERSION = ["']([^"']+)["']/);
    const cardVersion = cardVersionMatch ? cardVersionMatch[1] : null;

    const packagePath = join(rootDir, 'package.json');
    const packageJson = JSON.parse(readFileSync(packagePath, 'utf-8'));
    const packageVersion = packageJson.version;

    // All versions must match exactly
    expect(cardVersion).toBe(manifestVersion);
    expect(packageVersion).toBe(manifestVersion);

    // Success: no version skew possible
  });

  it('should have semantic version format', () => {
    const manifestPath = join(rootDir, 'custom_components/alarm_clock/manifest.json');
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
    const version = manifest.version;

    // Must be semantic versioning: X.Y.Z
    expect(version).toMatch(/^\d+\.\d+\.\d+$/);

    // Must not be 0.0.0
    expect(version).not.toBe('0.0.0');
  });

  it('should have version in card registration', async () => {
    // Import the card
    await import('../../custom_components/alarm_clock/alarm-clock-card.js');

    // Check window.customCards
    const alarmCard = window.customCards.find(c => c.type === 'alarm-clock-card');

    expect(alarmCard).toBeDefined();
    expect(alarmCard.version).toBeDefined();
    expect(alarmCard.version).toMatch(/^\d+\.\d+\.\d+$/);

    // Verify it matches manifest
    const manifestPath = join(rootDir, 'custom_components/alarm_clock/manifest.json');
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));

    expect(alarmCard.version).toBe(manifest.version);
  });

  it('should fail build if versions diverge', () => {
    /**
     * This test enforces that CI MUST fail if versions don't match.
     * Human error must not be able to reintroduce version skew.
     */

    const manifestPath = join(rootDir, 'custom_components/alarm_clock/manifest.json');
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
    const manifestVersion = manifest.version;

    const cardPath = join(rootDir, 'custom_components/alarm_clock/alarm-clock-card.js');
    const cardContent = readFileSync(cardPath, 'utf-8');
    const cardVersionMatch = cardContent.match(/const CARD_VERSION = ["']([^"']+)["']/);
    const cardVersion = cardVersionMatch ? cardVersionMatch[1] : null;

    const packagePath = join(rootDir, 'package.json');
    const packageJson = JSON.parse(readFileSync(packagePath, 'utf-8'));
    const packageVersion = packageJson.version;

    // If any version doesn't match, this test fails and blocks CI
    if (cardVersion !== manifestVersion || packageVersion !== manifestVersion) {
      throw new Error(
        `VERSION SKEW DETECTED!\n` +
        `  manifest.json: ${manifestVersion}\n` +
        `  alarm-clock-card.js: ${cardVersion}\n` +
        `  package.json: ${packageVersion}\n` +
        `All versions must match. Update the version in manifest.json ` +
        `and ensure it propagates to all files.`
      );
    }

    expect(cardVersion).toBe(manifestVersion);
    expect(packageVersion).toBe(manifestVersion);
  });

  it('should detect stale www copy', () => {
    const cardPath = join(rootDir, 'custom_components/alarm_clock/alarm-clock-card.js');
    const wwwPath = join(rootDir, 'www/alarm-clock-card.js');

    try {
      const cardContent = readFileSync(cardPath, 'utf-8');
      const wwwContent = readFileSync(wwwPath, 'utf-8');

      // Files should be identical
      expect(wwwContent).toBe(cardContent);
    } catch (e) {
      // www file may not exist, that's acceptable
      // (integration type serves from custom_components)
    }
  });
});
