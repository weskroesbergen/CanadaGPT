'use client';

import { User } from 'lucide-react';
import type { UserProfile } from '@/types/forum';

interface UserBadgeProps {
  user?: UserProfile | null;
  showAvatar?: boolean;
  showReputation?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function UserBadge({
  user,
  showAvatar = true,
  showReputation = false,
  size = 'md',
  className = '',
}: UserBadgeProps) {
  if (!user) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="w-6 h-6 rounded-full bg-background-primary flex items-center justify-center">
          <User size={14} className="text-text-tertiary" />
        </div>
        <span className="text-text-tertiary text-sm">Anonymous</span>
      </div>
    );
  }

  const sizeClasses = {
    sm: {
      avatar: 'w-6 h-6 text-xs',
      text: 'text-xs',
      reputation: 'text-xs',
    },
    md: {
      avatar: 'w-8 h-8 text-sm',
      text: 'text-sm',
      reputation: 'text-xs',
    },
    lg: {
      avatar: 'w-12 h-12 text-base',
      text: 'text-base',
      reputation: 'text-sm',
    },
  };

  const classes = sizeClasses[size];

  // Calculate reputation badge color
  const getReputationColor = (score: number) => {
    if (score >= 1000) return 'text-yellow-500';
    if (score >= 500) return 'text-purple-500';
    if (score >= 100) return 'text-blue-500';
    if (score >= 50) return 'text-green-500';
    return 'text-text-tertiary';
  };

  const getReputationTitle = (score: number) => {
    if (score >= 1000) return 'Expert Contributor';
    if (score >= 500) return 'Trusted Member';
    if (score >= 100) return 'Active Member';
    if (score >= 50) return 'Regular Contributor';
    return 'New Member';
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Avatar */}
      {showAvatar && (
        <div
          className={`
            ${classes.avatar} rounded-full overflow-hidden
            bg-background-primary flex items-center justify-center
            flex-shrink-0
          `}
        >
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.display_name || 'User avatar'}
              className="w-full h-full object-cover"
            />
          ) : (
            <div
              className={`
                w-full h-full flex items-center justify-center
                bg-gradient-to-br from-accent-red to-red-700
                text-white font-semibold
              `}
            >
              {(user.display_name || 'U').charAt(0).toUpperCase()}
            </div>
          )}
        </div>
      )}

      {/* User info */}
      <div className="flex flex-col min-w-0">
        <span className={`font-medium text-text-primary truncate ${classes.text}`}>
          {user.display_name || 'Anonymous User'}
        </span>

        {/* Reputation */}
        {showReputation && user.reputation_score !== undefined && (
          <div className="flex items-center gap-1">
            <span
              className={`
                font-semibold ${classes.reputation}
                ${getReputationColor(user.reputation_score)}
              `}
              title={getReputationTitle(user.reputation_score)}
            >
              {user.reputation_score.toLocaleString()} rep
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
