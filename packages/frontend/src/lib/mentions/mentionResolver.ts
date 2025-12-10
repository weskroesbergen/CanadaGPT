/**
 * Mention Resolver - Resolve @mentions to URLs and metadata
 *
 * Converts parsed mentions into navigable URLs and display information.
 */

import type { ParsedMention, MentionType } from './mentionParser';

/**
 * Resolved mention with navigation and display info
 */
export interface ResolvedMention extends ParsedMention {
  /** URL to navigate to */
  url: string;
  /** Display label for the mention */
  label: string;
  /** Whether this mention can have discussions */
  hasDiscussions: boolean;
  /** CSS class for styling based on type */
  colorClass: string;
}

/**
 * Configuration for different locales
 */
interface LocaleConfig {
  bills: string;
  mps: string;
  committees: string;
  votes: string;
  debates: string;
  petitions: string;
}

const LOCALE_PATHS: Record<string, LocaleConfig> = {
  en: {
    bills: 'bills',
    mps: 'mps',
    committees: 'committees',
    votes: 'votes',
    debates: 'debates',
    petitions: 'petitions',
  },
  fr: {
    bills: 'projets-de-loi',
    mps: 'deputes',
    committees: 'comites',
    votes: 'votes',
    debates: 'debats',
    petitions: 'petitions',
  },
};

/**
 * Color classes for each entity type
 */
const TYPE_COLORS: Record<MentionType, string> = {
  bill: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
  mp: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
  committee: 'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/30',
  vote: 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30',
  debate: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
  petition: 'text-teal-600 bg-teal-100 dark:text-teal-400 dark:bg-teal-900/30',
};

/**
 * Entity types that support discussions (Phase 1A: only bills)
 */
const DISCUSSION_ENABLED_TYPES: MentionType[] = ['bill'];

/**
 * Resolve a bill mention to URL and metadata
 */
function resolveBillMention(
  mention: ParsedMention,
  locale: string,
  session: string = '45-1'
): Partial<ResolvedMention> {
  const paths = LOCALE_PATHS[locale] || LOCALE_PATHS.en;
  const billNumber = mention.id.toLowerCase();

  // Build URL with optional section anchor
  let url = `/${locale}/${paths.bills}/${session}/${billNumber}`;
  if (mention.subId) {
    url += `#${mention.subId}`;
  }

  // Build label
  let label = `Bill ${mention.id.toUpperCase()}`;
  if (mention.subId) {
    // Format section reference (e.g., "s2.1.a" -> "Section 2.1.a")
    const sectionRef = mention.subId;
    if (sectionRef.startsWith('s')) {
      label += ` Section ${sectionRef.slice(1)}`;
    } else if (sectionRef.startsWith('part-')) {
      label += ` Part ${sectionRef.replace('part-', '')}`;
    } else {
      label += ` ${sectionRef}`;
    }
  }

  return { url, label };
}

/**
 * Resolve an MP mention to URL and metadata
 */
function resolveMpMention(
  mention: ParsedMention,
  locale: string
): Partial<ResolvedMention> {
  const paths = LOCALE_PATHS[locale] || LOCALE_PATHS.en;

  // Convert slug to display name
  const label = mention.id
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return {
    url: `/${locale}/${paths.mps}/${mention.id}`,
    label,
  };
}

/**
 * Resolve a committee mention to URL and metadata
 */
function resolveCommitteeMention(
  mention: ParsedMention,
  locale: string
): Partial<ResolvedMention> {
  const paths = LOCALE_PATHS[locale] || LOCALE_PATHS.en;
  const code = mention.id.toUpperCase();

  let url = `/${locale}/${paths.committees}/${code.toLowerCase()}`;
  let label = code;

  if (mention.subId) {
    url += `/meetings/${mention.subId}`;
    label += ` Meeting #${mention.subId}`;
  }

  return { url, label };
}

/**
 * Resolve a vote mention to URL and metadata
 */
function resolveVoteMention(
  mention: ParsedMention,
  locale: string
): Partial<ResolvedMention> {
  const paths = LOCALE_PATHS[locale] || LOCALE_PATHS.en;
  const [session, voteNumber] = [mention.id, mention.subId];

  return {
    url: `/${locale}/${paths.votes}/${session}/${voteNumber}`,
    label: locale === 'fr' ? `Vote #${voteNumber}` : `Vote #${voteNumber}`,
  };
}

/**
 * Resolve a debate mention to URL and metadata
 */
function resolveDebateMention(
  mention: ParsedMention,
  locale: string
): Partial<ResolvedMention> {
  const paths = LOCALE_PATHS[locale] || LOCALE_PATHS.en;

  let url = `/${locale}/${paths.debates}/${mention.id}`;
  let label = mention.id;

  if (mention.subId) {
    // Add time anchor
    const time = mention.subId.replace(':', '-');
    url += `#${time}`;
    label += ` at ${mention.subId}`;
  }

  return { url, label };
}

/**
 * Resolve a petition mention to URL and metadata
 */
function resolvePetitionMention(
  mention: ParsedMention,
  locale: string
): Partial<ResolvedMention> {
  const paths = LOCALE_PATHS[locale] || LOCALE_PATHS.en;

  return {
    url: `/${locale}/${paths.petitions}/${mention.id}`,
    label: `Petition ${mention.id.toUpperCase()}`,
  };
}

/**
 * Resolve a parsed mention to full URL and metadata
 *
 * @param mention - Parsed mention object
 * @param locale - Current locale (en/fr)
 * @param options - Additional options (e.g., default session)
 * @returns Resolved mention with URL and display info
 */
export function resolveMention(
  mention: ParsedMention,
  locale: string = 'en',
  options: { session?: string } = {}
): ResolvedMention {
  let resolved: Partial<ResolvedMention> = {};

  switch (mention.type) {
    case 'bill':
      resolved = resolveBillMention(mention, locale, options.session);
      break;
    case 'mp':
      resolved = resolveMpMention(mention, locale);
      break;
    case 'committee':
      resolved = resolveCommitteeMention(mention, locale);
      break;
    case 'vote':
      resolved = resolveVoteMention(mention, locale);
      break;
    case 'debate':
      resolved = resolveDebateMention(mention, locale);
      break;
    case 'petition':
      resolved = resolvePetitionMention(mention, locale);
      break;
  }

  return {
    ...mention,
    url: resolved.url || '#',
    label: resolved.label || mention.raw,
    hasDiscussions: DISCUSSION_ENABLED_TYPES.includes(mention.type),
    colorClass: TYPE_COLORS[mention.type],
  };
}

/**
 * Resolve multiple mentions from text
 *
 * @param mentions - Array of parsed mentions
 * @param locale - Current locale
 * @param options - Additional options
 * @returns Array of resolved mentions
 */
export function resolveMentions(
  mentions: ParsedMention[],
  locale: string = 'en',
  options: { session?: string } = {}
): ResolvedMention[] {
  return mentions.map((mention) => resolveMention(mention, locale, options));
}

/**
 * Convert text with mentions to React elements
 * This is a simplified version - in production you'd use a proper renderer
 *
 * @param text - Text containing mentions
 * @param mentions - Resolved mentions
 * @returns Array of text segments and mention objects
 */
export function segmentTextWithMentions(
  text: string,
  mentions: ResolvedMention[]
): Array<{ type: 'text'; content: string } | { type: 'mention'; mention: ResolvedMention }> {
  if (mentions.length === 0) {
    return [{ type: 'text', content: text }];
  }

  const segments: Array<
    { type: 'text'; content: string } | { type: 'mention'; mention: ResolvedMention }
  > = [];
  let lastIndex = 0;

  for (const mention of mentions) {
    // Add text before this mention
    if (mention.startIndex > lastIndex) {
      segments.push({
        type: 'text',
        content: text.slice(lastIndex, mention.startIndex),
      });
    }

    // Add the mention
    segments.push({
      type: 'mention',
      mention,
    });

    lastIndex = mention.endIndex;
  }

  // Add remaining text after last mention
  if (lastIndex < text.length) {
    segments.push({
      type: 'text',
      content: text.slice(lastIndex),
    });
  }

  return segments;
}

/**
 * Build a mention URL from components (without parsing)
 *
 * @param type - Entity type
 * @param id - Primary identifier
 * @param locale - Current locale
 * @param options - Additional options
 * @returns URL string
 */
export function buildMentionUrl(
  type: MentionType,
  id: string,
  locale: string = 'en',
  options: { session?: string; subId?: string } = {}
): string {
  const paths = LOCALE_PATHS[locale] || LOCALE_PATHS.en;

  switch (type) {
    case 'bill':
      const session = options.session || '45-1';
      let billUrl = `/${locale}/${paths.bills}/${session}/${id.toLowerCase()}`;
      if (options.subId) {
        billUrl += `#${options.subId}`;
      }
      return billUrl;

    case 'mp':
      return `/${locale}/${paths.mps}/${id}`;

    case 'committee':
      let committeeUrl = `/${locale}/${paths.committees}/${id.toLowerCase()}`;
      if (options.subId) {
        committeeUrl += `/meetings/${options.subId}`;
      }
      return committeeUrl;

    case 'vote':
      return `/${locale}/${paths.votes}/${options.session || '45-1'}/${id}`;

    case 'debate':
      let debateUrl = `/${locale}/${paths.debates}/${id}`;
      if (options.subId) {
        debateUrl += `#${options.subId.replace(':', '-')}`;
      }
      return debateUrl;

    case 'petition':
      return `/${locale}/${paths.petitions}/${id.toLowerCase()}`;

    default:
      return '#';
  }
}

/**
 * Check if an entity type supports discussions
 *
 * @param type - Entity type
 * @returns True if discussions are enabled for this type
 */
export function canHaveDiscussions(type: MentionType): boolean {
  return DISCUSSION_ENABLED_TYPES.includes(type);
}

export default {
  resolveMention,
  resolveMentions,
  segmentTextWithMentions,
  buildMentionUrl,
  canHaveDiscussions,
};
