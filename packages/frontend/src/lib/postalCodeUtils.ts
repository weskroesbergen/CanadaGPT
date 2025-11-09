/**
 * Canadian Postal Code Utilities
 *
 * Functions for validating, formatting, and handling Canadian postal codes
 * Format: A1A 1A1 (letter-digit-letter space digit-letter-digit)
 */

/**
 * Validates a Canadian postal code
 *
 * Rules:
 * - Format: A1A 1A1 (letter-digit-letter space digit-letter-digit)
 * - First letter cannot be: D, F, I, O, Q, U, W, Z
 * - Other letters cannot be: D, F, I, O, Q, U
 * - Space is optional during input but required for proper format
 *
 * @param postalCode - The postal code to validate
 * @returns true if valid, false otherwise
 *
 * @example
 * validateCanadianPostalCode('K1A 0A9') // true
 * validateCanadianPostalCode('K1A0A9')  // true (space optional)
 * validateCanadianPostalCode('D1A 1A1') // false (D not allowed in first position)
 * validateCanadianPostalCode('123 456') // false (must start with letter)
 */
export function validateCanadianPostalCode(postalCode: string): boolean {
  if (!postalCode) return false;

  // Remove all spaces and convert to uppercase
  const cleaned = postalCode.replace(/\s/g, '').toUpperCase();

  // Must be exactly 6 characters after removing spaces
  if (cleaned.length !== 6) return false;

  // Regex pattern for Canadian postal code
  // First letter cannot be D, F, I, O, Q, U, W, Z
  // Other letters cannot be D, F, I, O, Q, U
  const regex = /^[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z]\d[ABCEGHJ-NPRSTV-Z]\d$/;

  return regex.test(cleaned);
}

/**
 * Formats a Canadian postal code to standard format (A1A 1A1)
 *
 * @param postalCode - The postal code to format
 * @returns Formatted postal code with space, or original if invalid
 *
 * @example
 * formatPostalCode('k1a0a9')  // 'K1A 0A9'
 * formatPostalCode('K1A 0A9') // 'K1A 0A9'
 * formatPostalCode('K1A')     // 'K1A' (incomplete, returns as-is)
 */
export function formatPostalCode(postalCode: string): string {
  if (!postalCode) return '';

  // Remove all spaces and convert to uppercase
  const cleaned = postalCode.replace(/\s/g, '').toUpperCase();

  // If exactly 6 characters, format with space
  if (cleaned.length === 6) {
    return `${cleaned.slice(0, 3)} ${cleaned.slice(3)}`;
  }

  // Return as-is if not 6 characters (incomplete input)
  return cleaned;
}

/**
 * Normalizes a postal code for API calls (removes spaces, uppercase)
 *
 * @param postalCode - The postal code to normalize
 * @returns Normalized postal code (no spaces, uppercase)
 *
 * @example
 * normalizePostalCode('k1a 0a9') // 'K1A0A9'
 * normalizePostalCode('K1A 0A9') // 'K1A0A9'
 */
export function normalizePostalCode(postalCode: string): string {
  if (!postalCode) return '';
  return postalCode.replace(/\s/g, '').toUpperCase();
}

/**
 * Gets a user-friendly error message for invalid postal codes
 *
 * @param postalCode - The postal code that failed validation
 * @returns Error message explaining why it's invalid
 */
export function getPostalCodeError(postalCode: string): string {
  if (!postalCode) {
    return 'Please enter a postal code';
  }

  const cleaned = postalCode.replace(/\s/g, '').toUpperCase();

  if (cleaned.length !== 6) {
    return 'Postal code must be 6 characters (e.g., K1A 0A9)';
  }

  // Check if first character is invalid
  if (!/^[ABCEGHJ-NPRSTVXY]/.test(cleaned)) {
    return 'Invalid postal code format (first letter cannot be D, F, I, O, Q, U, W, or Z)';
  }

  // Check overall format
  if (!/^[A-Z]\d[A-Z]\d[A-Z]\d$/.test(cleaned)) {
    return 'Postal code must follow format: Letter-Number-Letter Number-Letter-Number (e.g., K1A 0A9)';
  }

  return 'Invalid postal code format';
}

/**
 * Extracts the Forward Sortation Area (FSA) from a postal code
 * The FSA is the first 3 characters (A1A) which represents a geographic region
 *
 * @param postalCode - The postal code
 * @returns The FSA portion, or null if invalid
 *
 * @example
 * getForwardSortationArea('K1A 0A9') // 'K1A'
 * getForwardSortationArea('K1A0A9')  // 'K1A'
 */
export function getForwardSortationArea(postalCode: string): string | null {
  if (!postalCode) return null;

  const cleaned = postalCode.replace(/\s/g, '').toUpperCase();

  if (cleaned.length >= 3) {
    return cleaned.slice(0, 3);
  }

  return null;
}
