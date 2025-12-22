'use client';

import React from 'react';
import { MessageSquare } from 'lucide-react';

/**
 * Discussion activity levels based on comment count
 */
export type ActivityLevel = 'none' | 'low' | 'medium' | 'hot';

/**
 * Get activity level based on comment count
 */
export function getActivityLevel(commentCount: number): ActivityLevel {
  if (commentCount === 0) return 'none';
  if (commentCount <= 5) return 'low';
  if (commentCount <= 20) return 'medium';
  return 'hot';
}

/**
 * Color mapping for activity levels
 */
const ACTIVITY_COLORS: Record<ActivityLevel, { bar: string; badge: string }> = {
  none: {
    bar: 'bg-transparent',
    badge: 'bg-bg-secondary text-text-tertiary',
  },
  low: {
    bar: 'bg-text-tertiary/50',
    badge: 'bg-bg-secondary text-text-secondary',
  },
  medium: {
    bar: 'bg-blue-500',
    badge: 'bg-blue-500/20 text-blue-400',
  },
  hot: {
    bar: 'bg-orange-500',
    badge: 'bg-orange-500/20 text-orange-400',
  },
};

interface DiscussionActivityIndicatorProps {
  /** Number of comments/replies on this section */
  commentCount: number;
  /** Whether to show the comment count badge */
  showBadge?: boolean;
  /** Whether to show the vertical bar */
  showBar?: boolean;
  /** Click handler for the badge */
  onClick?: () => void;
  /** Position for the bar (left or right) */
  barPosition?: 'left' | 'right';
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Locale for tooltips */
  locale?: string;
}

/**
 * DiscussionActivityIndicator - Shows visual indicator of discussion activity
 *
 * Features:
 * - Vertical colored bar in margin (heat indicator)
 * - Comment count badge with icon
 * - Color-coded by activity level:
 *   - Gray: Low (1-5 comments)
 *   - Blue: Medium (6-20 comments)
 *   - Orange: Hot (21+ comments)
 */
export const DiscussionActivityIndicator: React.FC<DiscussionActivityIndicatorProps> = ({
  commentCount,
  showBadge = true,
  showBar = true,
  onClick,
  barPosition = 'left',
  size = 'md',
  locale = 'en',
}) => {
  const level = getActivityLevel(commentCount);
  const colors = ACTIVITY_COLORS[level];

  // Size configurations
  const sizeConfig = {
    sm: { bar: 'w-1', badge: 'text-xs px-1.5 py-0.5', icon: 'h-3 w-3' },
    md: { bar: 'w-1.5', badge: 'text-xs px-2 py-1', icon: 'h-3.5 w-3.5' },
    lg: { bar: 'w-2', badge: 'text-sm px-2.5 py-1', icon: 'h-4 w-4' },
  };

  const config = sizeConfig[size];

  // Don't render anything if no activity and not forcing visibility
  if (level === 'none' && !showBar) {
    return null;
  }

  const tooltipText = commentCount === 0
    ? (locale === 'fr' ? 'Aucun commentaire' : 'No comments')
    : (locale === 'fr'
        ? `${commentCount} commentaire${commentCount > 1 ? 's' : ''}`
        : `${commentCount} comment${commentCount > 1 ? 's' : ''}`);

  return (
    <div
      className={`flex items-center gap-2 ${barPosition === 'right' ? 'flex-row-reverse' : ''}`}
    >
      {/* Vertical activity bar */}
      {showBar && level !== 'none' && (
        <div
          className={`
            ${config.bar} h-full min-h-[24px] rounded-full
            ${colors.bar}
            transition-colors duration-300
          `}
          title={tooltipText}
        />
      )}

      {/* Comment count badge */}
      {showBadge && commentCount > 0 && (
        <button
          onClick={onClick}
          className={`
            flex items-center gap-1 rounded-full font-medium
            ${config.badge}
            ${colors.badge}
            hover:opacity-80 transition-opacity
            ${onClick ? 'cursor-pointer' : 'cursor-default'}
          `}
          title={tooltipText}
        >
          <MessageSquare className={config.icon} />
          <span>{commentCount}</span>
        </button>
      )}
    </div>
  );
};

/**
 * DiscussionHeatBar - Just the vertical bar component for inline use
 */
export const DiscussionHeatBar: React.FC<{
  commentCount: number;
  className?: string;
}> = ({ commentCount, className = '' }) => {
  const level = getActivityLevel(commentCount);
  const colors = ACTIVITY_COLORS[level];

  if (level === 'none') {
    return <div className={`w-1 ${className}`} />;
  }

  return (
    <div
      className={`
        w-1 rounded-full
        ${colors.bar}
        transition-colors duration-300
        ${className}
      `}
    />
  );
};

export default DiscussionActivityIndicator;
