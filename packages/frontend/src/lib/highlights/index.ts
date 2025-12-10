/**
 * Text highlight utilities for URL-based text selection sharing
 */

export {
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
} from './highlightUrl';

export type { HighlightParams, MultiHighlightParams } from './highlightUrl';
