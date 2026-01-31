/**
 * Test setup for frontend tests
 * Provides mocks and globals needed for Lovelace card testing
 */

// Mock window.customCards
if (typeof window !== 'undefined') {
  window.customCards = window.customCards || [];
}

// Mock customElements if not available
if (typeof customElements === 'undefined') {
  global.customElements = {
    _elements: new Map(),
    define(name, constructor) {
      if (this._elements.has(name)) {
        throw new DOMException(
          `Failed to execute 'define' on 'CustomElementRegistry': the name "${name}" has already been used with this registry`
        );
      }
      this._elements.set(name, constructor);
    },
    get(name) {
      return this._elements.get(name);
    },
    whenDefined(name) {
      return Promise.resolve(this._elements.get(name));
    },
  };
}

// Clean up between tests
afterEach(() => {
  if (typeof window !== 'undefined') {
    delete window._alarmClockCardLogged;
    window.customCards = [];
  }
  if (typeof customElements !== 'undefined' && customElements._elements) {
    customElements._elements.clear();
  }
});
