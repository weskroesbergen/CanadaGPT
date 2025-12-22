/**
 * EntityVoteButtons Component
 *
 * Universal Yea/Nay voting component for Bills, MPs, and Statements
 * Features:
 * - Toggle voting (click same button to remove vote)
 * - Switch votes (Yea → Nay or vice versa)
 * - Net score display with color coding
 * - Optimistic UI updates with rollback on error
 * - Size variants (sm, md, lg)
 * - Layout variants (horizontal, vertical)
 * - Optional "Who voted" button
 * - Parliamentary terminology (Yea/Nay instead of Upvote/Downvote)
 */

'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Users } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@canadagpt/design-system';
import { toast } from 'sonner';
import { useTranslations } from 'next-intl';
import { VotersModal } from './VotersModal';

export type VoteType = 'upvote' | 'downvote';
export type EntityType = 'bill' | 'mp' | 'statement';

export interface EntityVoteButtonsProps {
  /** Type of entity being voted on */
  entityType: EntityType;
  /** Unique identifier for the entity */
  entityId: string;
  /** Initial upvote count (for hydration) */
  initialUpvotes?: number;
  /** Initial downvote count (for hydration) */
  initialDownvotes?: number;
  /** User's current vote on this entity */
  initialUserVote?: VoteType | null;
  /** Button size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Layout direction */
  layout?: 'horizontal' | 'vertical';
  /** Show "Who voted" button */
  showVotersList?: boolean;
  /** Callback when vote counts change */
  onVoteChange?: (upvotes: number, downvotes: number, netScore: number) => void;
  /** Additional CSS classes */
  className?: string;
}

export function EntityVoteButtons({
  entityType,
  entityId,
  initialUpvotes = 0,
  initialDownvotes = 0,
  initialUserVote = null,
  size = 'sm',
  layout = 'horizontal',
  showVotersList = false,
  onVoteChange,
  className,
}: EntityVoteButtonsProps) {
  const { user } = useAuth();
  const t = useTranslations('votes');

  // State for vote counts and user vote
  const [upvotes, setUpvotes] = useState(initialUpvotes);
  const [downvotes, setDownvotes] = useState(initialDownvotes);
  const [userVote, setUserVote] = useState<VoteType | null>(initialUserVote);
  const [isVoting, setIsVoting] = useState(false);
  const [showVotersModal, setShowVotersModal] = useState(false);

  // Sync state when props change (e.g., after batch vote data loads)
  useEffect(() => {
    setUpvotes(initialUpvotes ?? 0);
    setDownvotes(initialDownvotes ?? 0);
    setUserVote(initialUserVote ?? null);
  }, [initialUpvotes, initialDownvotes, initialUserVote]);

  // Calculate net score
  const netScore = upvotes - downvotes;

  // Size mappings (from BookmarkButton pattern)
  const iconSizes = {
    sm: 16,
    md: 18,
    lg: 20,
  };

  const paddingSizes = {
    sm: 'p-1.5',
    md: 'p-2',
    lg: 'p-2.5',
  };

  const textSizes = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  /**
   * Handle vote button click
   */
  const handleVote = async (voteType: VoteType) => {
    // Require authentication
    if (!user) {
      toast.error(t('signInToVote'));
      window.location.href = '/api/auth/signin';
      return;
    }

    // Prevent double-clicking
    if (isVoting) return;

    setIsVoting(true);

    // Store previous state for rollback
    const prevUpvotes = upvotes;
    const prevDownvotes = downvotes;
    const prevUserVote = userVote;

    // Optimistic update
    let newUpvotes = upvotes;
    let newDownvotes = downvotes;
    let newUserVote: VoteType | null = null;

    if (userVote === voteType) {
      // Toggle off (same vote type clicked)
      newUserVote = null;
      if (voteType === 'upvote') {
        newUpvotes = Math.max(0, upvotes - 1);
      } else {
        newDownvotes = Math.max(0, downvotes - 1);
      }
    } else if (userVote && userVote !== voteType) {
      // Switch vote (different vote type clicked)
      newUserVote = voteType;
      if (voteType === 'upvote') {
        newUpvotes = upvotes + 1;
        newDownvotes = Math.max(0, downvotes - 1);
      } else {
        newUpvotes = Math.max(0, upvotes - 1);
        newDownvotes = downvotes + 1;
      }
    } else {
      // New vote
      newUserVote = voteType;
      if (voteType === 'upvote') {
        newUpvotes = upvotes + 1;
      } else {
        newDownvotes = downvotes + 1;
      }
    }

    // Update UI immediately (optimistic)
    setUpvotes(newUpvotes);
    setDownvotes(newDownvotes);
    setUserVote(newUserVote);

    try {
      // Call API
      const response = await fetch('/api/votes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_type: entityType,
          entity_id: entityId,
          vote_type: voteType,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to vote');
      }

      const data = await response.json();

      // Update with server response (in case of race conditions)
      setUpvotes(data.upvotes);
      setDownvotes(data.downvotes);
      setUserVote(data.user_vote);

      // Notify parent component
      onVoteChange?.(data.upvotes, data.downvotes, data.net_score);
    } catch (error) {
      console.error('Error voting:', error);

      // Rollback optimistic update
      setUpvotes(prevUpvotes);
      setDownvotes(prevDownvotes);
      setUserVote(prevUserVote);

      toast.error(t('voteError') || 'Failed to submit vote. Please try again.');
    } finally {
      setIsVoting(false);
    }
  };

  /**
   * Get net score color
   */
  const getScoreColor = () => {
    if (netScore > 0) return 'text-green-500';
    if (netScore < 0) return 'text-red-500';
    return 'text-text-tertiary';
  };

  /**
   * Format large numbers (e.g., 10200 → 10.2k)
   */
  const formatCount = (count: number) => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}k`;
    }
    return count.toString();
  };

  /**
   * Get tooltip text for vote button
   */
  const getTooltip = (voteType: VoteType) => {
    if (!user) return t('signInToVote');
    if (userVote === voteType) {
      return voteType === 'upvote' ? t('removeYea') : t('removeNay');
    }
    return voteType === 'upvote' ? t('yea') : t('nay');
  };

  const containerClass = cn(
    'flex items-center gap-2',
    layout === 'vertical' && 'flex-col',
    className
  );

  const buttonBaseClass = cn(
    'rounded-lg border-2 transition-all',
    'bg-bg-secondary/80 backdrop-blur-sm',
    'hover:shadow-lg',
    'disabled:opacity-50 disabled:cursor-not-allowed',
    paddingSizes[size]
  );

  const upvoteActive = userVote === 'upvote';
  const downvoteActive = userVote === 'downvote';

  return (
    <>
      <div className={containerClass}>
        {/* Yea Button */}
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            handleVote('upvote');
          }}
          disabled={isVoting}
          className={cn(
            buttonBaseClass,
            upvoteActive
              ? 'border-green-500 text-green-500 shadow-md'
              : 'border-border text-text-secondary hover:border-green-500 hover:text-green-500'
          )}
          title={getTooltip('upvote')}
          aria-label={getTooltip('upvote')}
          aria-pressed={upvoteActive}
        >
          <CheckCircle
            size={iconSizes[size]}
            className={cn(
              'transition-all',
              upvoteActive && 'fill-current'
            )}
          />
        </button>

        {/* Net Score Display */}
        <div
          className={cn(
            'font-semibold tabular-nums',
            textSizes[size],
            getScoreColor()
          )}
          title={`${upvotes} ${t('yeas')}, ${downvotes} ${t('nays')}`}
        >
          {netScore > 0 && '+'}
          {formatCount(netScore)}
        </div>

        {/* Nay Button */}
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            handleVote('downvote');
          }}
          disabled={isVoting}
          className={cn(
            buttonBaseClass,
            downvoteActive
              ? 'border-red-500 text-red-500 shadow-md'
              : 'border-border text-text-secondary hover:border-red-500 hover:text-red-500'
          )}
          title={getTooltip('downvote')}
          aria-label={getTooltip('downvote')}
          aria-pressed={downvoteActive}
        >
          <XCircle
            size={iconSizes[size]}
            className={cn(
              'transition-all',
              downvoteActive && 'fill-current'
            )}
          />
        </button>

        {/* Optional "Who voted" button */}
        {showVotersList && (upvotes > 0 || downvotes > 0) && (
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setShowVotersModal(true);
            }}
            className={cn(
              buttonBaseClass,
              'border-border text-text-secondary hover:border-accent-red hover:text-accent-red'
            )}
            title={t('whoVoted')}
            aria-label={t('whoVoted')}
          >
            <Users size={iconSizes[size]} />
          </button>
        )}
      </div>

      {/* Voters Modal */}
      {showVotersModal && (
        <VotersModal
          entityType={entityType}
          entityId={entityId}
          onClose={() => setShowVotersModal(false)}
        />
      )}
    </>
  );
}
