// colors.ts
// Centralized color logic for workers and X/Y tasks

/**
 * Returns a consistent HSL color string for a given worker (by id or name).
 * Used to color-code cells in all tables so each worker has a unique hue.
 *
 * @param {string} idOrName - The worker's id or name.
 * @param {boolean} darkMode - Whether the UI is in dark mode (affects lightness).
 * @returns {string} HSL color string for use in CSS.
 */
export function getWorkerColor(idOrName: string, darkMode: boolean) {
  let hash = 0;
  for (let i = 0; i < idOrName.length; i++) hash = idOrName.charCodeAt(i) + ((hash << 5) - hash);
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 45%, ${darkMode ? '35%' : '70%'})`;
}

/**
 * Centralized color map for X tasks (and custom tasks).
 * Add/modify as needed for consistency across the app.
 */
export const X_TASK_COLORS: Record<string, string> = {
  /**TODO: Make sure that these names can be updated and changed from the client side if need be. */
  'Guarding Duties': '#1976d2',
  'RASAR': '#9c27b0',
  'Kitchen': '#ff8f00',
  'Custom': '#388e3c',
};

/**
 * Centralized color map for Y tasks (with light/dark variants).
 */
export const Y_TASK_COLORS: Record<string, { light: string, dark: string }> = {
    /**TODO: Make sure that these names can be updated and changed from the client side if need be. */
  'Supervisor':      { light: '#9c27b0', dark: '#7b1fa2' },
  'C&N Driver':      { light: '#00838f', dark: '#00695c' },
  'C&N Escort':      { light: '#ff8f00', dark: '#f57f17' },
  'Southern Driver': { light: '#1976d2', dark: '#1565c0' },
  'Southern Escort': { light: '#388e3c', dark: '#2e7d32' },
};

/**
 * Returns the color for a given X task name. Falls back to 'Custom' if not found.
 * @param {string} taskName
 * @returns {string} CSS color
 */
export function getXTaskColor(taskName: string): string {
  return X_TASK_COLORS[taskName] || X_TASK_COLORS['Custom'];
} 