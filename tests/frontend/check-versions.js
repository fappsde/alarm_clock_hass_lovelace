#!/usr/bin/env node

/**
 * Version Consistency Checker
 *
 * This script verifies that all version declarations match across:
 * - manifest.json (single source of truth)
 * - package.json
 * - alarm-clock-card.js
 * - www/alarm-clock-card.js (if exists)
 *
 * Exits with code 1 if any mismatch is found.
 * Used in CI to prevent version skew.
 */

import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '../..');

function main() {
  console.log('🔍 Checking version consistency across all files...\n');

  // Read manifest.json (single source of truth)
  const manifestPath = join(rootDir, 'custom_components/alarm_clock/manifest.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
  const manifestVersion = manifest.version;

  console.log(`✓ manifest.json: ${manifestVersion}`);

  let hasError = false;

  // Check package.json
  const packagePath = join(rootDir, 'package.json');
  const packageJson = JSON.parse(readFileSync(packagePath, 'utf-8'));
  const packageVersion = packageJson.version;

  if (packageVersion !== manifestVersion) {
    console.error(`✗ package.json: ${packageVersion} (MISMATCH!)`);
    hasError = true;
  } else {
    console.log(`✓ package.json: ${packageVersion}`);
  }

  // Check alarm-clock-card.js
  const cardPath = join(rootDir, 'custom_components/alarm_clock/alarm-clock-card.js');
  const cardContent = readFileSync(cardPath, 'utf-8');
  const cardMatch = cardContent.match(/const CARD_VERSION = ["']([^"']+)["']/);
  const cardVersion = cardMatch ? cardMatch[1] : null;

  if (cardVersion !== manifestVersion) {
    console.error(`✗ alarm-clock-card.js: ${cardVersion} (MISMATCH!)`);
    hasError = true;
  } else {
    console.log(`✓ alarm-clock-card.js: ${cardVersion}`);
  }

  // Check www/alarm-clock-card.js (if exists)
  const wwwPath = join(rootDir, 'www/alarm-clock-card.js');
  if (existsSync(wwwPath)) {
    const wwwContent = readFileSync(wwwPath, 'utf-8');
    const wwwMatch = wwwContent.match(/const CARD_VERSION = ["']([^"']+)["']/);
    const wwwVersion = wwwMatch ? wwwMatch[1] : null;

    if (wwwVersion !== manifestVersion) {
      console.error(`✗ www/alarm-clock-card.js: ${wwwVersion} (MISMATCH!)`);
      hasError = true;
    } else {
      console.log(`✓ www/alarm-clock-card.js: ${wwwVersion}`);
    }

    // Also check if files are identical
    if (wwwContent !== cardContent) {
      console.error(`✗ www/alarm-clock-card.js and custom_components version are DIFFERENT!`);
      hasError = true;
    }
  }

  // Check __init__.py uses manifest version
  const initPath = join(rootDir, 'custom_components/alarm_clock/__init__.py');
  const initContent = readFileSync(initPath, 'utf-8');

  if (initContent.includes('_get_version()') && initContent.includes('manifest.json')) {
    console.log(`✓ __init__.py: Uses _get_version() from manifest.json`);
  } else {
    console.error(`✗ __init__.py: Does not read version from manifest.json!`);
    hasError = true;
  }

  // Check for hardcoded versions in __init__.py
  const hardcodedMatch = initContent.match(/CARD_VERSION = ["']\d+\.\d+\.\d+["']/);
  if (hardcodedMatch) {
    console.error(`✗ __init__.py: Contains hardcoded version: ${hardcodedMatch[0]}`);
    hasError = true;
  }

  console.log('');

  if (hasError) {
    console.error('❌ VERSION SKEW DETECTED!');
    console.error('');
    console.error('Please update all versions to match manifest.json:');
    console.error(`  Expected version: ${manifestVersion}`);
    console.error('');
    console.error('Files to update:');
    console.error('  - package.json');
    console.error('  - custom_components/alarm_clock/alarm-clock-card.js (CARD_VERSION)');
    console.error('  - www/alarm-clock-card.js (if exists)');
    console.error('');
    process.exit(1);
  } else {
    console.log('✅ All versions match!');
    console.log(`   Version: ${manifestVersion}`);
    console.log('');
  }
}

main();
