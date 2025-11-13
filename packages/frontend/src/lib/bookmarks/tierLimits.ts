/**
 * Bookmark Tier Limits and Enforcement
 *
 * FREE: 10 bookmarks
 * BASIC: 100 bookmarks + 10 collections + notes (5000 char limit)
 * PRO: Unlimited bookmarks + unlimited collections + notes (unlimited) + AI prompts
 */

export type SubscriptionTier = 'FREE' | 'BASIC' | 'PRO';

export interface TierLimits {
  maxBookmarks: number | null; // null = unlimited
  maxCollections: number | null;
  maxFavorites: number | null;
  hasAIFeatures: boolean;
  hasSidebar: boolean;
  hasExport: boolean;
  hasBulkOperations: boolean;
  hasSharing: boolean;
  // Notes features
  hasNotes: boolean; // Can add notes to bookmarks
  maxNoteLength: number | null; // null = unlimited, 0 = disabled
  hasAIPrompts: boolean; // Can add AI context prompts (PRO only)
  hasVoiceNotes: boolean; // Can record voice notes (PRO only)
  hasNoteHistory: boolean; // Can access note version history (PRO only)
  hasNoteLinks: boolean; // Can link notes to other bookmarks (PRO only)
  maxWorkspaces: number | null; // Number of workspaces (PRO only)
}

export const TIER_LIMITS: Record<SubscriptionTier, TierLimits> = {
  FREE: {
    maxBookmarks: 10,
    maxCollections: 0, // No collections for FREE tier
    maxFavorites: 3, // Quick menu can show 3 favorites
    hasAIFeatures: false,
    hasSidebar: false,
    hasExport: false,
    hasBulkOperations: false,
    hasSharing: false,
    // Notes - locked for FREE tier
    hasNotes: false,
    maxNoteLength: 0,
    hasAIPrompts: false,
    hasVoiceNotes: false,
    hasNoteHistory: false,
    hasNoteLinks: false,
    maxWorkspaces: 0,
  },
  BASIC: {
    maxBookmarks: 100,
    maxCollections: 10,
    maxFavorites: 10,
    hasAIFeatures: false,
    hasSidebar: false,
    hasExport: true, // Can export to CSV/PDF
    hasBulkOperations: false,
    hasSharing: false,
    // Notes - basic features
    hasNotes: true,
    maxNoteLength: 5000, // 5000 character limit
    hasAIPrompts: false,
    hasVoiceNotes: false,
    hasNoteHistory: false,
    hasNoteLinks: false,
    maxWorkspaces: 0,
  },
  PRO: {
    maxBookmarks: null, // Unlimited
    maxCollections: null, // Unlimited
    maxFavorites: null, // Unlimited
    hasAIFeatures: true, // AI suggestions, connections, summaries, alerts
    hasSidebar: true, // Sidebar panel on all pages
    hasExport: true,
    hasBulkOperations: true,
    hasSharing: true, // Share collections publicly
    // Notes - all features unlocked
    hasNotes: true,
    maxNoteLength: null, // Unlimited
    hasAIPrompts: true, // Can add AI context prompts
    hasVoiceNotes: true, // Can record voice notes
    hasNoteHistory: true, // Can access note version history
    hasNoteLinks: true, // Can link notes with [[notation]]
    maxWorkspaces: null, // Unlimited workspaces
  },
};

/**
 * Get tier limits for a user
 */
export function getTierLimits(tier?: string | null): TierLimits {
  const normalizedTier = (tier?.toUpperCase() || 'FREE') as SubscriptionTier;
  return TIER_LIMITS[normalizedTier] || TIER_LIMITS.FREE;
}

/**
 * Check if user can create more bookmarks
 */
export function canCreateBookmark(
  currentCount: number,
  tier?: string | null
): boolean {
  const limits = getTierLimits(tier);
  if (limits.maxBookmarks === null) return true; // Unlimited
  return currentCount < limits.maxBookmarks;
}

/**
 * Check if user can create more collections
 */
export function canCreateCollection(
  currentCount: number,
  tier?: string | null
): boolean {
  const limits = getTierLimits(tier);
  if (limits.maxCollections === null) return true; // Unlimited
  if (limits.maxCollections === 0) return false; // Not allowed for this tier
  return currentCount < limits.maxCollections;
}

/**
 * Check if user can create more favorites
 */
export function canCreateFavorite(
  currentCount: number,
  tier?: string | null
): boolean {
  const limits = getTierLimits(tier);
  if (limits.maxFavorites === null) return true; // Unlimited
  return currentCount < limits.maxFavorites;
}

/**
 * Get user-friendly limit message
 */
export function getLimitMessage(
  type: 'bookmark' | 'collection' | 'favorite',
  tier?: string | null
): string {
  const limits = getTierLimits(tier);
  const tierName = tier || 'FREE';

  switch (type) {
    case 'bookmark':
      if (limits.maxBookmarks === null) {
        return `You have unlimited bookmarks with ${tierName} tier`;
      }
      return `You've reached your bookmark limit (${limits.maxBookmarks} for ${tierName} tier)`;

    case 'collection':
      if (limits.maxCollections === 0) {
        return `Collections are not available on ${tierName} tier. Upgrade to BASIC or PRO to organize your bookmarks.`;
      }
      if (limits.maxCollections === null) {
        return `You have unlimited collections with ${tierName} tier`;
      }
      return `You've reached your collection limit (${limits.maxCollections} for ${tierName} tier)`;

    case 'favorite':
      if (limits.maxFavorites === null) {
        return `You have unlimited favorites with ${tierName} tier`;
      }
      return `You've reached your favorites limit (${limits.maxFavorites} for ${tierName} tier)`;

    default:
      return `Limit reached for ${tierName} tier`;
  }
}

/**
 * Check if user can add/edit notes
 */
export function canUseNotes(tier?: string | null): boolean {
  const limits = getTierLimits(tier);
  return limits.hasNotes;
}

/**
 * Check if note length is within tier limit
 */
export function isNoteWithinLimit(
  noteLength: number,
  tier?: string | null
): boolean {
  const limits = getTierLimits(tier);
  if (!limits.hasNotes) return false;
  if (limits.maxNoteLength === null) return true; // Unlimited
  return noteLength <= limits.maxNoteLength;
}

/**
 * Get remaining note characters
 */
export function getRemainingNoteChars(
  noteLength: number,
  tier?: string | null
): number | null {
  const limits = getTierLimits(tier);
  if (!limits.hasNotes) return 0;
  if (limits.maxNoteLength === null) return null; // Unlimited
  return Math.max(0, limits.maxNoteLength - noteLength);
}

/**
 * Get note character limit message
 */
export function getNoteLimitMessage(
  noteLength: number,
  tier?: string | null
): string {
  const limits = getTierLimits(tier);

  if (!limits.hasNotes) {
    return 'Notes are not available on FREE tier. Upgrade to BASIC or PRO.';
  }

  if (limits.maxNoteLength === null) {
    return `${noteLength.toLocaleString()} characters (unlimited)`;
  }

  const remaining = limits.maxNoteLength - noteLength;
  if (remaining < 0) {
    return `Over limit by ${Math.abs(remaining).toLocaleString()} characters`;
  }

  return `${noteLength.toLocaleString()} / ${limits.maxNoteLength.toLocaleString()} characters`;
}

/**
 * Get upgrade message for a specific feature
 */
export function getUpgradeMessage(
  feature: 'bookmark' | 'collection' | 'ai' | 'sidebar' | 'export' | 'bulk' | 'sharing' | 'notes' | 'ai-prompts' | 'voice-notes' | 'note-history' | 'workspaces',
  currentTier?: string | null
): { message: string; targetTier: SubscriptionTier } {
  const tier = (currentTier?.toUpperCase() || 'FREE') as SubscriptionTier;

  switch (feature) {
    case 'bookmark':
      if (tier === 'FREE') {
        return {
          message: 'Upgrade to BASIC for 100 bookmarks or PRO for unlimited',
          targetTier: 'BASIC',
        };
      }
      return {
        message: 'Upgrade to PRO for unlimited bookmarks',
        targetTier: 'PRO',
      };

    case 'collection':
      if (tier === 'FREE') {
        return {
          message: 'Upgrade to BASIC or PRO to create collections',
          targetTier: 'BASIC',
        };
      }
      return {
        message: 'Upgrade to PRO for unlimited collections',
        targetTier: 'PRO',
      };

    case 'ai':
      return {
        message: 'Upgrade to PRO for AI-powered insights, connections, and smart alerts',
        targetTier: 'PRO',
      };

    case 'sidebar':
      return {
        message: 'Upgrade to PRO for the always-accessible bookmark sidebar',
        targetTier: 'PRO',
      };

    case 'export':
      if (tier === 'FREE') {
        return {
          message: 'Upgrade to BASIC or PRO to export your bookmarks',
          targetTier: 'BASIC',
        };
      }
      return {
        message: 'Export is included in your plan',
        targetTier: tier,
      };

    case 'bulk':
      return {
        message: 'Upgrade to PRO for bulk operations',
        targetTier: 'PRO',
      };

    case 'sharing':
      return {
        message: 'Upgrade to PRO to share collections publicly',
        targetTier: 'PRO',
      };

    case 'notes':
      if (tier === 'FREE') {
        return {
          message: 'Upgrade to BASIC for note-taking or PRO for unlimited notes + AI features',
          targetTier: 'BASIC',
        };
      }
      return {
        message: 'Upgrade to PRO for unlimited note length and AI-powered features',
        targetTier: 'PRO',
      };

    case 'ai-prompts':
      return {
        message: 'Upgrade to PRO to add AI context prompts to your notes',
        targetTier: 'PRO',
      };

    case 'voice-notes':
      return {
        message: 'Upgrade to PRO to record voice notes',
        targetTier: 'PRO',
      };

    case 'note-history':
      return {
        message: 'Upgrade to PRO to access note version history',
        targetTier: 'PRO',
      };

    case 'workspaces':
      return {
        message: 'Upgrade to PRO to create workspaces for organizing your research',
        targetTier: 'PRO',
      };

    default:
      return {
        message: 'Upgrade to unlock this feature',
        targetTier: 'PRO',
      };
  }
}

/**
 * Calculate bookmark usage stats
 */
export interface BookmarkUsageStats {
  total: number;
  limit: number | null;
  percentage: number;
  isNearLimit: boolean; // >= 80%
  isAtLimit: boolean;
  canCreate: boolean;
}

export function getBookmarkUsageStats(
  currentCount: number,
  tier?: string | null
): BookmarkUsageStats {
  const limits = getTierLimits(tier);
  const { maxBookmarks } = limits;

  if (maxBookmarks === null) {
    // Unlimited
    return {
      total: currentCount,
      limit: null,
      percentage: 0,
      isNearLimit: false,
      isAtLimit: false,
      canCreate: true,
    };
  }

  const percentage = (currentCount / maxBookmarks) * 100;

  return {
    total: currentCount,
    limit: maxBookmarks,
    percentage,
    isNearLimit: percentage >= 80,
    isAtLimit: currentCount >= maxBookmarks,
    canCreate: currentCount < maxBookmarks,
  };
}
