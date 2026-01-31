/**
 * Test setup for frontend tests
 * Provides mocks and globals needed for Lovelace card testing
 *
 * IMPORTANT: We use happy-dom which provides customElements, window, HTMLElement, etc.
 * We should NOT override these - just extend them where needed.
 *
 * CRITICAL: ES modules are cached and only evaluated once.
 * This means the alarm-clock-card.js module will only run its top-level code once,
 * not on every test. This is REALISTIC browser behavior.
 * Tests must account for this.
 */

import { beforeAll } from 'vitest';

// Initialize window.customCards array (used by Lovelace cards)
// happy-dom provides window, we just need to ensure customCards exists
if (typeof window !== 'undefined') {
  window.customCards = window.customCards || [];

  // Ensure window has a global reference (some modules expect this)
  if (!window.window) {
    window.window = window;
  }
}

// Import the card once before all tests
// This ensures it's loaded and registered
beforeAll(async () => {
  await import('../../custom_components/alarm_clock/alarm-clock-card.js');
});

// Note: We do NOT clear window.customCards or customElements between tests
// because ES modules are cached (realistic browser behavior)
// Tests must be written to handle already-registered elements and cards
