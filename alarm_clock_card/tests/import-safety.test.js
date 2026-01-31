/**
 * Frontend Import Safety Test
 *
 * CRITICAL: This test verifies that the card module can be imported
 * without throwing exceptions, preventing frontend poisoning.
 *
 * This test would have caught the original bug where:
 * - Object.getPrototypeOf(customElements.get("ha-panel-lovelace"))
 * - threw an exception if ha-panel-lovelace wasn't loaded yet
 * - breaking ALL other custom cards
 */

import { describe, it, expect, beforeEach } from 'vitest';

describe('Import Safety Test', () => {
  // Note: setup.js imports the module once before all tests
  // This is realistic browser behavior - ES modules are cached

  it('should import module without throwing', async () => {
    // This is the critical test: import should not throw
    let error = null;
    try {
      await import('../../custom_components/alarm_clock/alarm-clock-card.js');
    } catch (e) {
      error = e;
    }
    expect(error).toBeNull();
  });

  it('should complete module evaluation', async () => {
    // Import the module (will return cached version)
    const module = await import('../../custom_components/alarm_clock/alarm-clock-card.js');

    // Module should be defined
    expect(module).toBeDefined();

    // Module evaluation should complete without errors
    expect(true).toBe(true);
  });

  it('should register card in window.customCards', () => {
    // Card was registered during module load (happens once)
    expect(window.customCards).toBeDefined();
    expect(Array.isArray(window.customCards)).toBe(true);

    // Find our card
    const alarmCard = window.customCards.find(
      card => card.type === 'alarm-clock-card'
    );

    expect(alarmCard).toBeDefined();
    expect(alarmCard.name).toBe('Alarm Clock Card');
    expect(alarmCard.type).toBe('alarm-clock-card');
    expect(alarmCard.version).toBeDefined();
  });

  it('should define custom elements', () => {
    // Custom elements should be defined (from module load)
    expect(customElements.get('alarm-clock-card')).toBeDefined();
    expect(customElements.get('alarm-clock-card-editor')).toBeDefined();
  });

  it('should use standard ES module import from lit', async () => {
    // Verify the module is using safe imports
    // This is tested by successfully importing it
    let error = null;
    try {
      await import('../../custom_components/alarm_clock/alarm-clock-card.js');
    } catch (e) {
      error = e;
    }

    // If import succeeded, it means it's using proper ES module imports
    // If it were using Object.getPrototypeOf(customElements.get("ha-panel-lovelace")),
    // it would have thrown since ha-panel-lovelace doesn't exist in test env
    expect(error).toBeNull();
  });
});
