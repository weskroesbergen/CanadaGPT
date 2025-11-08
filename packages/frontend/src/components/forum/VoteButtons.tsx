'use client';

import { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { votePost } from '@/actions/forum';
import type { VoteType } from '@/types/forum';
import { useAuth } from '@/contexts/AuthContext';

interface VoteButtonsProps {
  postId: string;
  upvotes: number;
  downvotes: number;
  userVote?: VoteType | null;
  size?: 'sm' | 'md' | 'lg';
  onVoteChange?: (upvotes: number, downvotes: number) => void;
}

export function VoteButtons({
  postId,
  upvotes: initialUpvotes,
  downvotes: initialDownvotes,
  userVote: initialUserVote,
  size = 'md',
  onVoteChange,
}: VoteButtonsProps) {
  const { user } = useAuth();
  const [upvotes, setUpvotes] = useState(initialUpvotes);
  const [downvotes, setDownvotes] = useState(initialDownvotes);
  const [userVote, setUserVote] = useState<VoteType | null>(initialUserVote || null);
  const [isVoting, setIsVoting] = useState(false);

  const handleVote = async (voteType: VoteType) => {
    if (!user) {
      alert('Please sign in to vote');
      return;
    }

    if (isVoting) return;

    setIsVoting(true);

    try {
      const result = await votePost(postId, voteType);

      if (result.success && result.data) {
        // Update local state
        setUpvotes(result.data.upvotes);
        setDownvotes(result.data.downvotes);

        // Toggle vote (if same vote, remove it)
        if (userVote === voteType) {
          setUserVote(null);
        } else {
          setUserVote(voteType);
        }

        // Notify parent component
        onVoteChange?.(result.data.upvotes, result.data.downvotes);
      } else {
        alert(result.error || 'Failed to vote');
      }
    } catch (error) {
      console.error('Error voting:', error);
      alert('Failed to vote. Please try again.');
    } finally {
      setIsVoting(false);
    }
  };

  const score = upvotes - downvotes;

  const sizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
  };

  const iconSizes = {
    sm: 14,
    md: 18,
    lg: 22,
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <button
        onClick={() => handleVote('upvote')}
        disabled={isVoting}
        className={`
          p-2 rounded-lg transition-all
          ${
            userVote === 'upvote'
              ? 'text-accent-red bg-accent-red/10'
              : 'text-text-secondary hover:text-accent-red hover:bg-accent-red/5'
          }
          ${isVoting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          disabled:cursor-not-allowed
        `}
        aria-label="Upvote"
      >
        <ThumbsUp size={iconSizes[size]} />
      </button>

      <span
        className={`
          font-semibold ${sizeClasses[size]}
          ${score > 0 ? 'text-green-500' : score < 0 ? 'text-red-500' : 'text-text-tertiary'}
        `}
      >
        {score > 0 ? '+' : ''}
        {score}
      </span>

      <button
        onClick={() => handleVote('downvote')}
        disabled={isVoting}
        className={`
          p-2 rounded-lg transition-all
          ${
            userVote === 'downvote'
              ? 'text-blue-500 bg-blue-500/10'
              : 'text-text-secondary hover:text-blue-500 hover:bg-blue-500/5'
          }
          ${isVoting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          disabled:cursor-not-allowed
        `}
        aria-label="Downvote"
      >
        <ThumbsDown size={iconSizes[size]} />
      </button>
    </div>
  );
}
