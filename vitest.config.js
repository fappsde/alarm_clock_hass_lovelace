import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./tests/frontend/setup.js'],
    include: ['tests/frontend/**/*.test.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['custom_components/alarm_clock/alarm-clock-card.js'],
      exclude: ['tests/**', 'node_modules/**'],
    },
  },
});
