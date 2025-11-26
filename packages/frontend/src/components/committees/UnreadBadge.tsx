/**
 * UnreadBadge Component
 *
 * Displays a count badge for new/unread committee meetings
 */

import React from 'react';
import { cn } from '@canadagpt/design-system';

export interface UnreadBadgeProps {
  count: number;
  className?: string;
  variant?: 'default' | 'subtle';
}

export function UnreadBadge({ count, className, variant = 'default' }: UnreadBadgeProps) {
  // Don't render if count is 0 or negative
  if (count <= 0) return null;

  const variantStyles = {
    default: 'bg-accent text-accent-foreground',
    subtle: 'bg-muted text-muted-foreground',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded-full px-2 py-0.5 text-xs font-medium',
        variantStyles[variant],
        className
      )}
      aria-label={`${count} new meeting${count !== 1 ? 's' : ''}`}
    >
      {count} new
    </span>
  );
}
