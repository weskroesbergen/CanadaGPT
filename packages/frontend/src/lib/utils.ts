import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Parse an ISO date string (YYYY-MM-DD) as local time, not UTC.
 *
 * JavaScript's `new Date("2025-12-10")` parses as midnight UTC,
 * which shifts to the previous day in North American timezones.
 * This function parses the date as local time to avoid that issue.
 */
export function parseLocalDate(dateString: string | null | undefined): Date | null {
  if (!dateString) return null;

  // Handle ISO date strings (YYYY-MM-DD)
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
    const [year, month, day] = dateString.split('-').map(Number);
    return new Date(year, month - 1, day);
  }

  // Fall back to standard Date parsing for other formats
  return new Date(dateString);
}

/**
 * Format an ISO date string as a localized date, treating it as local time.
 */
export function formatLocalDate(
  dateString: string | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  const date = parseLocalDate(dateString);
  if (!date) return '';
  return date.toLocaleDateString(undefined, options);
}
