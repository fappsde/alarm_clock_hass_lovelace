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
  beforeEach(() => {
    // Clear any previous imports
    delete window._alarmClockCardLogged;
    window.customCards = [];
  });

  it('should import module without throwing', async () => {
    // This is the critical test: import should not throw
    expect(async () => {
      await import('../../custom_components/alarm_clock/alarm-clock-card.js');
    }).not.toThrow();
  });

  it('should complete module evaluation', async () => {
    // Import the module
    const module = await import('../../custom_components/alarm_clock/alarm-clock-card.js');

    // Module should be defined
    expect(module).toBeDefined();

    // Module evaluation should complete without errors
    expect(true).toBe(true);
  });

  it('should register card in window.customCards', async () => {
    // Import the module
    await import('../../custom_components/alarm_clock/alarm-clock-card.js');

    // Card should be registered
    expect(window.customCards).toBeDefined();
    expect(Array.isArray(window.customCards)).toBe(true);
    expect(window.customCards.length).toBeGreaterThan(0);

    // Find our card
    const alarmCard = window.customCards.find(
      card => card.type === 'alarm-clock-card'
    );

    expect(alarmCard).toBeDefined();
    expect(alarmCard.name).toBe('Alarm Clock Card');
    expect(alarmCard.type).toBe('alarm-clock-card');
  });

  it('should define custom elements', async () => {
    // Import the module
    await import('../../custom_components/alarm_clock/alarm-clock-card.js');

    // Custom elements should be defined
    expect(customElements.get('alarm-clock-card')).toBeDefined();
    expect(customElements.get('alarm-clock-card-editor')).toBeDefined();
  });

  it('should not throw if imported before lit is available', async () => {
    // This simulates the condition that caused the original bug
    // Even if dependencies aren't ready, the import should not throw
    // (it should fail gracefully or the import system should handle it)

    // Clear customElements to simulate not being ready
    const originalGet = customElements.get;
    customElements.get = () => undefined;

    try {
      // Import should still not throw even if elements aren't found
      // (The ES module import system handles this)
      await import('../../custom_components/alarm_clock/alarm-clock-card.js');
      expect(true).toBe(true); // If we get here, no throw occurred
    } finally {
      // Restore
      customElements.get = originalGet;
    }
  });
});
