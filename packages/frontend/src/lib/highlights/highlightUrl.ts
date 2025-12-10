/**
 * Highlight URL Utilities
 *
 * Handles encoding/decoding of text highlight data in URLs
 * for Substack-style shareable text selections.
 *
 * URL format: /bills/{session}/{number}?hl={section}:{start}-{end}
 * Example: /bills/45-1/c-234?hl=s2.1.a:15-47
 */

/**
 * Parsed highlight data
 */
export interface HighlightParams {
  /** Section anchor ID (e.g., "s2.1.a") */
  section: string;
  /** Start character offset within section */
  start: number;
  /** End character offset within section */
  end: number;
}

/**
 * Multiple highlights (for future extension)
 */
export interface MultiHighlightParams {
  highlights: HighlightParams[];
}

/**
 * Parse highlight parameter from URL
 *
 * @param hlParam - The ?hl= query parameter value
 * @returns Parsed highlight data or null if invalid
 *
 * @example
 * parseHighlightParam("s2.1.a:15-47")
 * // { section: "s2.1.a", start: 15, end: 47 }
 */
export function parseHighlightParam(
  hlParam: string | null | undefined
): HighlightParams | null {
  if (!hlParam) return null;

  // Decode URI component
  const decoded = decodeURIComponent(hlParam);

  // Parse format: section:start-end
  const match = decoded.match(/^([a-z0-9.-]+):(\d+)-(\d+)$/i);
  if (!match) return null;

  const [, section, startStr, endStr] = match;
  const start = parseInt(startStr, 10);
  const end = parseInt(endStr, 10);

  // Validate
  if (isNaN(start) || isNaN(end) || start < 0 || end <= start) {
    return null;
  }

  return { section, start, end };
}

/**
 * Parse multiple highlights from URL (comma-separated)
 *
 * @param hlParam - The ?hl= query parameter value
 * @returns Array of highlight params
 *
 * @example
 * parseMultipleHighlights("s2.1.a:15-47,s2.2:0-30")
 * // [{ section: "s2.1.a", start: 15, end: 47 }, { section: "s2.2", start: 0, end: 30 }]
 */
export function parseMultipleHighlights(
  hlParam: string | null | undefined
): HighlightParams[] {
  if (!hlParam) return [];

  const decoded = decodeURIComponent(hlParam);
  const parts = decoded.split(',');

  return parts
    .map((part) => parseHighlightParam(part))
    .filter((hl): hl is HighlightParams => hl !== null);
}

/**
 * Encode highlight data for URL
 *
 * @param highlight - Highlight data to encode
 * @returns URL-safe encoded string
 *
 * @example
 * encodeHighlightParam({ section: "s2.1.a", start: 15, end: 47 })
 * // "s2.1.a:15-47"
 */
export function encodeHighlightParam(highlight: HighlightParams): string {
  const param = `${highlight.section}:${highlight.start}-${highlight.end}`;
  return encodeURIComponent(param);
}

/**
 * Encode multiple highlights for URL
 *
 * @param highlights - Array of highlights
 * @returns URL-safe encoded string
 */
export function encodeMultipleHighlights(highlights: HighlightParams[]): string {
  if (highlights.length === 0) return '';

  const params = highlights
    .map((hl) => `${hl.section}:${hl.start}-${hl.end}`)
    .join(',');

  return encodeURIComponent(params);
}

/**
 * Build a full URL with highlight parameter
 *
 * @param baseUrl - Base URL without query params
 * @param highlight - Highlight data
 * @returns Full URL with highlight parameter
 *
 * @example
 * buildHighlightUrl("/en/bills/45-1/c-234", { section: "s2.1.a", start: 15, end: 47 })
 * // "/en/bills/45-1/c-234?hl=s2.1.a%3A15-47"
 */
export function buildHighlightUrl(
  baseUrl: string,
  highlight: HighlightParams
): string {
  const encoded = encodeHighlightParam(highlight);
  const separator = baseUrl.includes('?') ? '&' : '?';
  return `${baseUrl}${separator}hl=${encoded}`;
}

/**
 * Build URL with section anchor and optional highlight
 *
 * @param baseUrl - Base URL
 * @param section - Section to anchor to
 * @param highlight - Optional highlight within section
 * @returns Full URL with anchor and optional highlight
 */
export function buildSectionUrl(
  baseUrl: string,
  section: string,
  highlight?: Omit<HighlightParams, 'section'>
): string {
  let url = `${baseUrl}#${section}`;

  if (highlight) {
    const hlParam = encodeHighlightParam({
      section,
      start: highlight.start,
      end: highlight.end,
    });
    url += `?hl=${hlParam}`;
  }

  return url;
}

/**
 * Extract highlight from current URL search params
 *
 * @param searchParams - URLSearchParams object
 * @returns Parsed highlight or null
 */
export function getHighlightFromSearchParams(
  searchParams: URLSearchParams
): HighlightParams | null {
  return parseHighlightParam(searchParams.get('hl'));
}

/**
 * Extract highlight from URL string
 *
 * @param url - Full URL or just query string
 * @returns Parsed highlight or null
 */
export function getHighlightFromUrl(url: string): HighlightParams | null {
  try {
    const urlObj = new URL(url, window.location.origin);
    return parseHighlightParam(urlObj.searchParams.get('hl'));
  } catch {
    // Try parsing as just query string
    if (url.includes('hl=')) {
      const match = url.match(/[?&]hl=([^&]+)/);
      if (match) {
        return parseHighlightParam(match[1]);
      }
    }
    return null;
  }
}

/**
 * Remove highlight parameter from URL
 *
 * @param url - URL with highlight param
 * @returns URL without highlight param
 */
export function removeHighlightFromUrl(url: string): string {
  try {
    const urlObj = new URL(url, window.location.origin);
    urlObj.searchParams.delete('hl');
    return urlObj.pathname + urlObj.search + urlObj.hash;
  } catch {
    return url.replace(/[?&]hl=[^&]+/, '');
  }
}

/**
 * Validate highlight params against section content
 *
 * @param highlight - Highlight params to validate
 * @param sectionLength - Total length of section text
 * @returns True if highlight is valid for the section
 */
export function isValidHighlight(
  highlight: HighlightParams,
  sectionLength: number
): boolean {
  return (
    highlight.start >= 0 &&
    highlight.end > highlight.start &&
    highlight.end <= sectionLength
  );
}

/**
 * Normalize highlight params to valid ranges
 *
 * @param highlight - Highlight params to normalize
 * @param sectionLength - Total length of section text
 * @returns Normalized highlight or null if invalid
 */
export function normalizeHighlight(
  highlight: HighlightParams,
  sectionLength: number
): HighlightParams | null {
  const start = Math.max(0, highlight.start);
  const end = Math.min(sectionLength, highlight.end);

  if (end <= start) return null;

  return {
    section: highlight.section,
    start,
    end,
  };
}

/**
 * Generate social share URL with highlight
 *
 * @param platform - Social platform
 * @param url - URL with highlight
 * @param text - Text to share (optional, for quote)
 * @returns Platform-specific share URL
 */
export function getSocialShareUrl(
  platform: 'twitter' | 'facebook' | 'linkedin',
  url: string,
  text?: string
): string {
  const encodedUrl = encodeURIComponent(url);

  switch (platform) {
    case 'twitter':
      const twitterText = text
        ? `"${text.slice(0, 200)}${text.length > 200 ? '...' : ''}"`
        : '';
      return `https://twitter.com/intent/tweet?text=${encodeURIComponent(twitterText)}&url=${encodedUrl}`;

    case 'facebook':
      return `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`;

    case 'linkedin':
      return `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`;

    default:
      return url;
  }
}

export default {
  parseHighlightParam,
  parseMultipleHighlights,
  encodeHighlightParam,
  encodeMultipleHighlights,
  buildHighlightUrl,
  buildSectionUrl,
  getHighlightFromSearchParams,
  getHighlightFromUrl,
  removeHighlightFromUrl,
  isValidHighlight,
  normalizeHighlight,
  getSocialShareUrl,
};
