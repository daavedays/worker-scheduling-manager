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
  return `hsl(${hue}, 60%, ${darkMode ? '32%' : '82%'})`;
}

/**
 * Centralized color map for X tasks (and custom tasks).
 * Add/modify as needed for consistency across the app.
 */
export const X_TASK_COLORS: Record<string, string> = {
  /**TODO: Make sure that these names can be updated and changed from the client side if need be. */
  'Guarding Duties': '#2e7dbe',
  'RASAR': '#8e24aa',
  'Kitchen': '#fbc02d',
  'Custom': '#43a047',
};

/**
 * Centralized color map for Y tasks (with light/dark variants).
 */
export const Y_TASK_COLORS: Record<string, { light: string, dark: string }> = {
    /**TODO: Make sure that these names can be updated and changed from the client side if need be. */
  'Supervisor':      { light: '#b39ddb', dark: '#5e35b1' },
  'C&N Driver':      { light: '#80cbc4', dark: '#00897b' },
  'C&N Escort':      { light: '#ffe082', dark: '#fbc02d' },
  'Southern Driver': { light: '#90caf9', dark: '#1976d2' },
  'Southern Escort': { light: '#a5d6a7', dark: '#388e3c' },
};

/**
 * Returns the color for a given X task name. Falls back to 'Custom' if not found.
 * @param {string} taskName
 * @returns {string} CSS color
 */
export function getXTaskColor(taskName: string): string {
  return X_TASK_COLORS[taskName] || X_TASK_COLORS['Custom'];
} 