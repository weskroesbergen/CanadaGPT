/**
 * Input validation utilities for GraphQL resolvers
 *
 * Provides validation and sanitization for user-provided parameters
 * to prevent DoS attacks and ensure data integrity.
 */

/**
 * Maximum allowed limit value for any query
 * This prevents excessive memory usage and expensive database queries
 */
export const MAX_LIMIT = 1000;

/**
 * Minimum allowed limit value
 */
export const MIN_LIMIT = 1;

/**
 * Default limits for different query types
 */
export const DEFAULT_LIMITS = {
  random: 12,
  top: 10,
  search: 50,
  list: 20,
};

/**
 * Validates and clamps a limit parameter to safe bounds
 *
 * @param value - The user-provided limit value
 * @param defaultValue - The default value to use if limit is not provided
 * @param maxValue - Maximum allowed value (defaults to MAX_LIMIT)
 * @returns A safe, validated limit value
 *
 * @example
 * ```typescript
 * const limit = validateLimit(args.limit, 10); // Clamps between 1 and 1000
 * const limit = validateLimit(args.limit, 10, 100); // Clamps between 1 and 100
 * ```
 */
export function validateLimit(
  value: number | null | undefined,
  defaultValue: number = DEFAULT_LIMITS.list,
  maxValue: number = MAX_LIMIT
): number {
  // Use default if not provided
  if (value === null || value === undefined || isNaN(value)) {
    return defaultValue;
  }

  // Convert to integer and clamp to valid range
  const intValue = Math.floor(value);

  // Clamp between MIN_LIMIT and maxValue
  return Math.max(MIN_LIMIT, Math.min(intValue, maxValue));
}

/**
 * Validates and sanitizes an offset parameter
 *
 * @param value - The user-provided offset value
 * @param defaultValue - The default value to use if offset is not provided
 * @returns A safe, validated offset value
 */
export function validateOffset(
  value: number | null | undefined,
  defaultValue: number = 0
): number {
  if (value === null || value === undefined || isNaN(value)) {
    return defaultValue;
  }

  const intValue = Math.floor(value);

  // Offset must be non-negative
  return Math.max(0, intValue);
}

/**
 * Validates a fiscal year parameter
 *
 * @param value - The user-provided fiscal year
 * @returns A valid fiscal year or null
 */
export function validateFiscalYear(
  value: number | null | undefined
): number | null {
  if (value === null || value === undefined || isNaN(value)) {
    return null;
  }

  const year = Math.floor(value);

  // Fiscal years should be reasonable (between 2000 and 2100)
  if (year < 2000 || year > 2100) {
    return null;
  }

  return year;
}

/**
 * Validates a year parameter for general use
 *
 * @param value - The user-provided year
 * @param minYear - Minimum valid year (default: 1900)
 * @param maxYear - Maximum valid year (default: current year + 10)
 * @returns A valid year or null
 */
export function validateYear(
  value: number | null | undefined,
  minYear: number = 1900,
  maxYear: number = new Date().getFullYear() + 10
): number | null {
  if (value === null || value === undefined || isNaN(value)) {
    return null;
  }

  const year = Math.floor(value);

  if (year < minYear || year > maxYear) {
    return null;
  }

  return year;
}

/**
 * Sanitizes a string parameter by trimming and limiting length
 *
 * @param value - The user-provided string
 * @param maxLength - Maximum allowed length (default: 1000)
 * @returns A safe, sanitized string
 */
export function validateString(
  value: string | null | undefined,
  maxLength: number = 1000
): string | null {
  if (!value || typeof value !== 'string') {
    return null;
  }

  const trimmed = value.trim();

  if (trimmed.length === 0) {
    return null;
  }

  // Truncate if too long
  return trimmed.substring(0, maxLength);
}

/**
 * Validates an array of strings
 *
 * @param value - The user-provided array
 * @param maxItems - Maximum number of items allowed (default: 100)
 * @param maxLength - Maximum length of each string (default: 200)
 * @returns A safe, validated array
 */
export function validateStringArray(
  value: string[] | null | undefined,
  maxItems: number = 100,
  maxLength: number = 200
): string[] | null {
  if (!value || !Array.isArray(value) || value.length === 0) {
    return null;
  }

  // Limit number of items
  const limitedArray = value.slice(0, maxItems);

  // Validate and sanitize each item
  const validatedArray = limitedArray
    .filter(item => typeof item === 'string')
    .map(item => item.trim().substring(0, maxLength))
    .filter(item => item.length > 0);

  return validatedArray.length > 0 ? validatedArray : null;
}

/**
 * Validation error class for better error handling
 */
export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}
