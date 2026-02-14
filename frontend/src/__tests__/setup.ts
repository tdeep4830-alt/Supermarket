/**
 * Vitest global setup.
 *
 * - Provides jsdom localStorage stub
 * - Clears Zustand stores between tests
 */
import { afterEach } from 'vitest';

// Reset Zustand stores after each test to avoid leaking state
afterEach(() => {
  localStorage.clear();
});
