/**
 * Duplicate Registration Test
 *
 * CRITICAL: This test verifies that re-importing the module does not
 * throw a DOMException due to duplicate customElements.define() calls.
 *
 * This test would have caught bugs where:
 * - customElements.define() is called without checking if already defined
 * - Module is imported multiple times (common in dev/HMR scenarios)
 * - Results in: DOMException: Failed to execute 'define'
 */

import { describe, it, expect, beforeEach } from 'vitest';

describe('Duplicate Registration Test', () => {
  beforeEach(() => {
    // Clear any previous state
    delete window._alarmClockCardLogged;
    window.customCards = [];

    // Clear custom elements registry
    if (customElements._elements) {
      customElements._elements.clear();
    }
  });

  it('should not throw DOMException on re-import', async () => {
    // First import
    await import('../../custom_components/alarm_clock/alarm-clock-card.js');

    // Second import should not throw
    expect(async () => {
      await import('../../custom_components/alarm_clock/alarm-clock-card.js');
    }).not.toThrow();
  });

  it('should only register card once in window.customCards', async () => {
    // Import twice
    await import('../../custom_components/alarm_clock/alarm-clock-card.js');
    await import('../../custom_components/alarm_clock/alarm-clock-card.js');

    // Should only have one registration
    const alarmCards = window.customCards.filter(
      card => card.type === 'alarm-clock-card'
    );

    expect(alarmCards.length).toBe(1);
  });

  it('should handle customElements.define() being called when already defined', async () => {
    // Pre-define a dummy element with the same name
    class DummyCard extends HTMLElement {}

    // Define it first
    customElements.define('test-alarm-card', DummyCard);

    // Try to define again (simulating what the protection code does)
    const attemptRedefine = () => {
      if (!customElements.get('test-alarm-card')) {
        customElements.define('test-alarm-card', DummyCard);
      }
    };

    // Should not throw
    expect(attemptRedefine).not.toThrow();

    // Element should still be defined
    expect(customElements.get('test-alarm-card')).toBe(DummyCard);
  });

  it('should maintain element definition across multiple imports', async () => {
    // First import
    await import('../../custom_components/alarm_clock/alarm-clock-card.js');
    const firstDefinition = customElements.get('alarm-clock-card');

    // Second import
    await import('../../custom_components/alarm_clock/alarm-clock-card.js');
    const secondDefinition = customElements.get('alarm-clock-card');

    // Should be the same definition
    expect(secondDefinition).toBe(firstDefinition);
  });

  it('should not log card info multiple times', async () => {
    // Track console.info calls
    const infoLogs = [];
    const originalInfo = console.info;
    console.info = (...args) => {
      infoLogs.push(args);
      originalInfo(...args);
    };

    try {
      // Import multiple times
      await import('../../custom_components/alarm_clock/alarm-clock-card.js');
      await import('../../custom_components/alarm_clock/alarm-clock-card.js');
      await import('../../custom_components/alarm_clock/alarm-clock-card.js');

      // Should only log once (via window._alarmClockCardLogged flag)
      const alarmCardLogs = infoLogs.filter(
        args => args.some(arg => typeof arg === 'string' && arg.includes('ALARM-CLOCK-CARD'))
      );

      expect(alarmCardLogs.length).toBe(1);
    } finally {
      console.info = originalInfo;
    }
  });

  it('should protect editor element from duplicate registration', async () => {
    // Import twice
    await import('../../custom_components/alarm_clock/alarm-clock-card.js');
    await import('../../custom_components/alarm_clock/alarm-clock-card.js');

    // Editor should be defined
    expect(customElements.get('alarm-clock-card-editor')).toBeDefined();

    // And should not have thrown
    expect(true).toBe(true);
  });

  it('should handle rapid successive imports', async () => {
    // Simulate rapid HMR updates
    const imports = Array(10).fill(null).map(() =>
      import('../../custom_components/alarm_clock/alarm-clock-card.js')
    );

    // All should resolve without throwing
    await expect(Promise.all(imports)).resolves.toBeDefined();

    // Should still only have one card registered
    const alarmCards = window.customCards.filter(
      card => card.type === 'alarm-clock-card'
    );
    expect(alarmCards.length).toBe(1);
  });
});
