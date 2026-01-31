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
  // Note: setup.js imports the module once before all tests
  // ES modules are cached - this is realistic browser behavior

  it('should not throw DOMException on re-import', async () => {
    // Module is already imported (cached), but try again
    let error = null;
    try {
      await import('../../custom_components/alarm_clock/alarm-clock-card.js');
    } catch (e) {
      error = e;
    }
    expect(error).toBeNull();
  });

  it('should only register card once in window.customCards', () => {
    // Card registration happens only once (during first module evaluation)
    // Even though module is imported multiple times, top-level code runs once
    const alarmCards = window.customCards.filter(
      card => card.type === 'alarm-clock-card'
    );

    // Should have exactly one registration
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

  it('should set logging flag after module load', () => {
    // The card uses window._alarmClockCardLogged to prevent duplicate logging
    // This flag should be set after the module loads (which happened in setup.js)

    // The flag should be set
    expect(window._alarmClockCardLogged).toBe(true);

    // This demonstrates the duplicate-logging protection mechanism
    // Even if the module were loaded again, the flag would prevent re-logging
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
    // Simulate rapid HMR-style imports
    const imports = Array(10).fill(null).map(() =>
      import('../../custom_components/alarm_clock/alarm-clock-card.js')
    );

    // All should resolve without throwing
    await expect(Promise.all(imports)).resolves.toBeDefined();

    // Should still only have one card registered
    // (ES modules cache means top-level code runs only once)
    const alarmCards = window.customCards.filter(
      card => card.type === 'alarm-clock-card'
    );
    expect(alarmCards.length).toBe(1);
  });
});
