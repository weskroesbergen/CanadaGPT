/**
 * Bookmark Tier Limits and Enforcement
 *
 * FREE: 10 bookmarks
 * BASIC: 100 bookmarks + 10 collections
 * PRO: Unlimited bookmarks + unlimited collections + AI features
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
 * Get upgrade message for a specific feature
 */
export function getUpgradeMessage(
  feature: 'bookmark' | 'collection' | 'ai' | 'sidebar' | 'export' | 'bulk' | 'sharing',
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
