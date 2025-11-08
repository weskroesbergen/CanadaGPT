/**
 * ThreadToggle Component
 * Toggle button to switch between threaded and linear views
 */

'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { MessageSquare, List } from 'lucide-react';

interface ThreadToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  showLabels?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const ThreadToggle = React.memo(function ThreadToggle({
  enabled,
  onChange,
  showLabels = true,
  size = 'md',
  className = '',
}: ThreadToggleProps) {
  const t = useTranslations('hansard');

  const sizes = {
    sm: {
      button: 'px-3 py-1.5 text-sm',
      icon: 'h-3.5 w-3.5',
    },
    md: {
      button: 'px-4 py-2 text-base',
      icon: 'h-4 w-4',
    },
    lg: {
      button: 'px-5 py-2.5 text-lg',
      icon: 'h-5 w-5',
    },
  };

  const sizeClasses = sizes[size];

  const handleKeyDown = (e: React.KeyboardEvent, value: boolean) => {
    // Arrow key navigation
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      onChange(!value);
    }
  };

  return (
    <div
      className={`inline-flex rounded-lg bg-bg-secondary p-1 ${className}`}
      role="group"
      aria-label="View mode toggle"
    >
      {/* Threaded View Button */}
      <button
        onClick={() => onChange(true)}
        onKeyDown={(e) => handleKeyDown(e, enabled)}
        className={`
          ${sizeClasses.button}
          flex items-center gap-2 rounded-md font-medium transition-all
          focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2 focus:ring-offset-bg-base
          ${enabled
            ? 'bg-accent-red text-white shadow-sm'
            : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
          }
        `}
        aria-label="Switch to threaded view - groups related speeches into conversations"
        aria-pressed={enabled}
        title="Threaded view groups related speeches into conversations"
      >
        <MessageSquare className={sizeClasses.icon} aria-hidden="true" />
        {showLabels && <span>Threaded</span>}
      </button>

      {/* Linear View Button */}
      <button
        onClick={() => onChange(false)}
        onKeyDown={(e) => handleKeyDown(e, !enabled)}
        className={`
          ${sizeClasses.button}
          flex items-center gap-2 rounded-md font-medium transition-all
          focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2 focus:ring-offset-bg-base
          ${!enabled
            ? 'bg-accent-red text-white shadow-sm'
            : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
          }
        `}
        aria-label="Switch to linear view - shows all speeches in chronological order"
        aria-pressed={!enabled}
        title="Linear view shows all speeches in chronological order"
      >
        <List className={sizeClasses.icon} aria-hidden="true" />
        {showLabels && <span>Linear</span>}
      </button>
    </div>
  );
});

/**
 * Compact version for mobile or tight spaces
 */
export function ThreadToggleCompact(props: Omit<ThreadToggleProps, 'showLabels' | 'size'>) {
  return <ThreadToggle {...props} showLabels={false} size="sm" />;
}
