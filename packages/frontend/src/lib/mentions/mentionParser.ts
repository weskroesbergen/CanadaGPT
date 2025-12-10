/**
 * Mention Parser - Parse @mention syntax from text
 *
 * Supported mention formats:
 * - @bill:c-234 - Bill reference
 * - @bill:c-234:s2.1 - Bill section reference
 * - @mp:pierre-poilievre - MP reference
 * - @committee:fina - Committee reference
 * - @committee:fina:45 - Committee meeting reference
 * - @vote:45-1:234 - Vote reference
 * - @debate:2025-12-09:14:30 - Debate timestamp reference
 * - @petition:e-4823 - Petition reference
 */

/**
 * Entity types that can be mentioned
 */
export type MentionType =
  | 'bill'
  | 'mp'
  | 'committee'
  | 'vote'
  | 'debate'
  | 'petition';

/**
 * Parsed mention data
 */
export interface ParsedMention {
  /** Original matched text (including @) */
  raw: string;
  /** Entity type */
  type: MentionType;
  /** Primary identifier */
  id: string;
  /** Secondary identifier (e.g., section, meeting number) */
  subId?: string;
  /** Third-level identifier (e.g., subsection) */
  subSubId?: string;
  /** Start index in original text */
  startIndex: number;
  /** End index in original text */
  endIndex: number;
}

/**
 * Mention pattern configuration
 */
interface MentionPattern {
  type: MentionType;
  pattern: RegExp;
  /** Extract IDs from regex match groups */
  extract: (match: RegExpMatchArray) => {
    id: string;
    subId?: string;
    subSubId?: string;
  };
}

/**
 * Mention patterns for each entity type
 */
const MENTION_PATTERNS: MentionPattern[] = [
  // Bill with section: @bill:c-234:s2.1.a
  {
    type: 'bill',
    pattern: /@bill:([cs]-?\d+)(?::([a-z0-9.-]+))?/gi,
    extract: (match) => ({
      id: match[1].toLowerCase(),
      subId: match[2] || undefined,
    }),
  },
  // MP: @mp:pierre-poilievre
  {
    type: 'mp',
    pattern: /@mp:([a-z][a-z0-9-]+)/gi,
    extract: (match) => ({
      id: match[1],
    }),
  },
  // Committee with meeting: @committee:fina:45
  {
    type: 'committee',
    pattern: /@committee:([a-z]{4})(?::(\d+))?/gi,
    extract: (match) => ({
      id: match[1].toUpperCase(),
      subId: match[2] || undefined,
    }),
  },
  // Vote: @vote:45-1:234
  {
    type: 'vote',
    pattern: /@vote:(\d+-\d+):(\d+)/gi,
    extract: (match) => ({
      id: match[1],
      subId: match[2],
    }),
  },
  // Debate with timestamp: @debate:2025-12-09:14:30
  {
    type: 'debate',
    pattern: /@debate:(\d{4}-\d{2}-\d{2})(?::(\d{2}[:-]\d{2}))?/gi,
    extract: (match) => ({
      id: match[1],
      subId: match[2]?.replace('-', ':') || undefined,
    }),
  },
  // Petition: @petition:e-4823
  {
    type: 'petition',
    pattern: /@petition:([ea]-?\d+)/gi,
    extract: (match) => ({
      id: match[1].toLowerCase(),
    }),
  },
];

/**
 * Parse all mentions from text
 *
 * @param text - Text to parse
 * @returns Array of parsed mentions with positions
 */
export function parseMentions(text: string): ParsedMention[] {
  const mentions: ParsedMention[] = [];

  for (const { type, pattern, extract } of MENTION_PATTERNS) {
    // Reset regex lastIndex
    pattern.lastIndex = 0;

    let match: RegExpExecArray | null;
    while ((match = pattern.exec(text)) !== null) {
      const { id, subId, subSubId } = extract(match);

      mentions.push({
        raw: match[0],
        type,
        id,
        subId,
        subSubId,
        startIndex: match.index,
        endIndex: match.index + match[0].length,
      });
    }
  }

  // Sort by position in text
  mentions.sort((a, b) => a.startIndex - b.startIndex);

  return mentions;
}

/**
 * Check if text contains any mentions
 *
 * @param text - Text to check
 * @returns True if text contains at least one mention
 */
export function hasMentions(text: string): boolean {
  return MENTION_PATTERNS.some(({ pattern }) => {
    pattern.lastIndex = 0;
    return pattern.test(text);
  });
}

/**
 * Extract the mention being typed at cursor position
 *
 * @param text - Full text
 * @param cursorPosition - Current cursor position
 * @returns Partial mention string if typing a mention, null otherwise
 */
export function getMentionAtCursor(
  text: string,
  cursorPosition: number
): { mention: string; startIndex: number } | null {
  // Look backwards from cursor for @
  const textBeforeCursor = text.slice(0, cursorPosition);
  const lastAtIndex = textBeforeCursor.lastIndexOf('@');

  if (lastAtIndex === -1) return null;

  // Check if there's a space between @ and cursor (would break the mention)
  const textBetween = textBeforeCursor.slice(lastAtIndex);
  if (/\s/.test(textBetween) && textBetween.indexOf(' ') < textBetween.length - 1) {
    return null;
  }

  // Extract the partial mention
  const mention = textBetween;

  return {
    mention,
    startIndex: lastAtIndex,
  };
}

/**
 * Replace a mention in text
 *
 * @param text - Original text
 * @param startIndex - Start position to replace
 * @param endIndex - End position to replace
 * @param replacement - Replacement text
 * @returns Updated text
 */
export function replaceMention(
  text: string,
  startIndex: number,
  endIndex: number,
  replacement: string
): string {
  return text.slice(0, startIndex) + replacement + text.slice(endIndex);
}

/**
 * Generate mention string from components
 *
 * @param type - Entity type
 * @param id - Primary ID
 * @param subId - Secondary ID (optional)
 * @returns Formatted mention string
 */
export function formatMention(
  type: MentionType,
  id: string,
  subId?: string,
  subSubId?: string
): string {
  let mention = `@${type}:${id}`;
  if (subId) {
    mention += `:${subId}`;
    if (subSubId) {
      mention += `.${subSubId}`;
    }
  }
  return mention;
}

/**
 * Validate mention format
 *
 * @param mention - Mention string to validate
 * @returns True if valid mention format
 */
export function isValidMention(mention: string): boolean {
  return MENTION_PATTERNS.some(({ pattern }) => {
    pattern.lastIndex = 0;
    const match = pattern.exec(mention);
    return match !== null && match[0] === mention;
  });
}

/**
 * Get the entity type from a mention string
 *
 * @param mention - Mention string (e.g., "@bill:c-234")
 * @returns Entity type or null if invalid
 */
export function getMentionType(mention: string): MentionType | null {
  const match = mention.match(/@([a-z]+):/i);
  if (!match) return null;

  const type = match[1].toLowerCase();
  const validTypes: MentionType[] = [
    'bill',
    'mp',
    'committee',
    'vote',
    'debate',
    'petition',
  ];

  return validTypes.includes(type as MentionType)
    ? (type as MentionType)
    : null;
}

/**
 * Extract plain text from mentions (for display)
 *
 * @param mention - ParsedMention object
 * @returns Human-readable label
 */
export function getMentionLabel(mention: ParsedMention): string {
  switch (mention.type) {
    case 'bill':
      return mention.subId
        ? `Bill ${mention.id.toUpperCase()} ${mention.subId}`
        : `Bill ${mention.id.toUpperCase()}`;
    case 'mp':
      // Convert slug to name (e.g., "pierre-poilievre" -> "Pierre Poilievre")
      return mention.id
        .split('-')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    case 'committee':
      return mention.subId
        ? `${mention.id} Meeting #${mention.subId}`
        : mention.id;
    case 'vote':
      return `Vote #${mention.subId}`;
    case 'debate':
      return mention.subId
        ? `${mention.id} at ${mention.subId}`
        : mention.id;
    case 'petition':
      return `Petition ${mention.id.toUpperCase()}`;
    default:
      return mention.raw;
  }
}

export default {
  parseMentions,
  hasMentions,
  getMentionAtCursor,
  replaceMention,
  formatMention,
  isValidMention,
  getMentionType,
  getMentionLabel,
};
