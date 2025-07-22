/**
 * utils.ts
 * --------
 * Shared utility functions for date formatting and color assignment in the Worker Scheduling Manager frontend.
 * Used by XTaskPage, YTaskPage, CombinedPage, etc.
 */

/**
 * Formats a date string as dd-mm-yyyy for display or filenames.
 * Accepts input in either 'dd/mm/yyyy' or 'yyyy-mm-dd' format.
 *
 * @param {string} date - The date string to format.
 * @returns {string} The formatted date as 'dd-mm-yyyy'.
 *
 * Example:
 *   formatDateDMY('12/01/2025') => '12-01-2025'
 *   formatDateDMY('2025-01-12') => '12-01-2025'
 */
export function formatDateDMY(date: string) {
  // Accepts dd/mm/yyyy or yyyy-mm-dd
  if (date.includes('/')) {
    const [d, m, y] = date.split('/');
    return `${d.padStart(2, '0')}-${m.padStart(2, '0')}-${y}`;
  } else if (date.includes('-')) {
    const [y, m, d] = date.split('-');
    return `${d.padStart(2, '0')}-${m.padStart(2, '0')}-${y}`;
  }
  return date;
}

/**
 * Converts a week range from 'dd/mm/yyyy - dd/mm/yyyy' to 'dd/mm-dd/mm'.
 * If input is not in the expected format, returns the original string.
 *
 * Example:
 *   shortWeekRange('06/07/2025 - 13/07/2025') => '06/07-13/07'
 */
export function shortWeekRange(range: string) {
  const match = range.match(/(\d{2}\/\d{2})\/\d{4} - (\d{2}\/\d{2})\/\d{4}/);
  if (match) {
    return `${match[1]}-${match[2]}`;
  }
  // fallback: if already short or not matching, return as is
  return range;
} 