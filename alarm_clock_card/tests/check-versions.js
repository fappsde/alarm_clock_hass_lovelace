#!/usr/bin/env node

/**
 * Version Consistency Checker for Alarm Clock Card
 *
 * This script verifies that all version declarations match across:
 * - package.json (single source of truth for frontend)
 * - alarm-clock-card.js (CARD_VERSION constant)
 *
 * Exits with code 1 if any mismatch is found.
 * Used in CI to prevent version skew.
 */

import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..');

function main() {
  console.log('🔍 Checking version consistency across card files...\n');

  // Read package.json (single source of truth)
  const packagePath = join(rootDir, 'package.json');
  const packageJson = JSON.parse(readFileSync(packagePath, 'utf-8'));
  const packageVersion = packageJson.version;

  console.log(`✓ package.json: ${packageVersion}`);

  let hasError = false;

  // Check alarm-clock-card.js
  const cardPath = join(rootDir, 'alarm-clock-card.js');
  const cardContent = readFileSync(cardPath, 'utf-8');
  const cardMatch = cardContent.match(/const CARD_VERSION = ["']([^"']+)["']/);
  const cardVersion = cardMatch ? cardMatch[1] : null;

  if (cardVersion !== packageVersion) {
    console.error(`✗ alarm-clock-card.js: ${cardVersion} (MISMATCH!)`);
    hasError = true;
  } else {
    console.log(`✓ alarm-clock-card.js: ${cardVersion}`);
  }

  console.log('');

  if (hasError) {
    console.error('❌ VERSION SKEW DETECTED!');
    console.error('');
    console.error('Please update all versions to match package.json:');
    console.error(`  Expected version: ${packageVersion}`);
    console.error('');
    console.error('Files to update:');
    console.error('  - alarm-clock-card.js (CARD_VERSION)');
    console.error('');
    process.exit(1);
  } else {
    console.log('✅ All versions match!');
    console.log(`   Version: ${packageVersion}`);
    console.log('');
  }
}

main();
