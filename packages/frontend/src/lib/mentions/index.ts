/**
 * Mention utilities for @mention parsing and resolution
 */

export {
  parseMentions,
  hasMentions,
  getMentionAtCursor,
  replaceMention,
  formatMention,
  isValidMention,
  getMentionType,
  getMentionLabel,
} from './mentionParser';

export type { ParsedMention, MentionType } from './mentionParser';

export {
  resolveMention,
  resolveMentions,
  segmentTextWithMentions,
  buildMentionUrl,
  canHaveDiscussions,
} from './mentionResolver';

export type { ResolvedMention } from './mentionResolver';
