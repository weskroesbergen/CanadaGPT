/**
 * VotersModal Component
 *
 * Modal to display who voted on an entity (Bill, MP, or Statement)
 * Features:
 * - Tabs for All/Yeas/Nays
 * - Paginated voter list with avatars
 * - Real-time relative timestamps
 * - Portal rendering for proper z-index
 */

'use client';

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { EntityType, VoteType } from './EntityVoteButtons';
import { formatDistanceToNow } from 'date-fns';

interface Voter {
  user_id: string;
  vote_type: VoteType;
  voted_at: string;
  display_name: string;
  avatar_url: string | null;
  username: string;
}

interface VotersModalProps {
  entityType: EntityType;
  entityId: string;
  onClose: () => void;
}

type VoteFilter = 'all' | 'upvote' | 'downvote';

export function VotersModal({
  entityType,
  entityId,
  onClose,
}: VotersModalProps) {
  const t = useTranslations('votes');

  const [activeTab, setActiveTab] = useState<VoteFilter>('all');
  const [voters, setVoters] = useState<Voter[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [mounted, setMounted] = useState(false);

  const LIMIT = 50;

  // Ensure component is mounted before rendering portal
  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  // Fetch voters
  useEffect(() => {
    fetchVoters(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const fetchVoters = async (reset = false) => {
    if (reset) {
      setLoading(true);
      setOffset(0);
    } else {
      setLoadingMore(true);
    }

    try {
      const currentOffset = reset ? 0 : offset;
      const voteTypeParam =
        activeTab === 'all' ? '' : `&vote_type=${activeTab}`;
      const response = await fetch(
        `/api/votes/voters?entity_type=${entityType}&entity_id=${encodeURIComponent(
          entityId
        )}${voteTypeParam}&limit=${LIMIT}&offset=${currentOffset}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch voters');
      }

      const data = await response.json();

      setVoters((prev) => (reset ? data.voters : [...prev, ...data.voters]));
      setHasMore(data.has_more);
      setOffset(currentOffset + LIMIT);
    } catch (error) {
      console.error('Error fetching voters:', error);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const loadMore = () => {
    if (!loadingMore && hasMore) {
      fetchVoters(false);
    }
  };

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-bg-primary border border-border-subtle rounded-lg shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border-subtle">
          <h2 className="text-lg font-semibold text-text-primary">
            {t('whoVoted')}
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border-subtle">
          <button
            onClick={() => setActiveTab('all')}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              activeTab === 'all'
                ? 'text-accent-red border-b-2 border-accent-red'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {t('allVotes')}
          </button>
          <button
            onClick={() => setActiveTab('upvote')}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              activeTab === 'upvote'
                ? 'text-green-500 border-b-2 border-green-500'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {t('yeas')}
          </button>
          <button
            onClick={() => setActiveTab('downvote')}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              activeTab === 'downvote'
                ? 'text-red-500 border-b-2 border-red-500'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {t('nays')}
          </button>
        </div>

        {/* Voters List */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-text-tertiary" />
            </div>
          ) : voters.length === 0 ? (
            <div className="text-center py-8 text-text-secondary">
              {activeTab === 'all'
                ? 'No votes yet'
                : activeTab === 'upvote'
                ? 'No yeas yet'
                : 'No nays yet'}
            </div>
          ) : (
            <div className="space-y-3">
              {voters.map((voter) => (
                <div
                  key={`${voter.user_id}-${voter.voted_at}`}
                  className="flex items-center gap-3 p-3 rounded-lg bg-bg-elevated hover:bg-bg-secondary transition-colors"
                >
                  {/* Avatar */}
                  <div className="flex-shrink-0">
                    {voter.avatar_url ? (
                      <img
                        src={voter.avatar_url}
                        alt={voter.display_name || 'User'}
                        className="w-10 h-10 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-accent-red/10 flex items-center justify-center text-accent-red font-semibold">
                        {(voter.display_name || voter.username || '?').charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>

                  {/* User Info */}
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-text-primary truncate">
                      {voter.display_name || voter.username || 'Anonymous'}
                    </div>
                    <div className="text-xs text-text-tertiary">
                      {formatDistanceToNow(new Date(voter.voted_at), {
                        addSuffix: true,
                      })}
                    </div>
                  </div>

                  {/* Vote Badge */}
                  {activeTab === 'all' && (
                    <div
                      className={`flex-shrink-0 px-2 py-1 rounded-full text-xs font-medium ${
                        voter.vote_type === 'upvote'
                          ? 'bg-green-500/10 text-green-500'
                          : 'bg-red-500/10 text-red-500'
                      }`}
                    >
                      {voter.vote_type === 'upvote' ? (
                        <CheckCircle size={14} className="inline" />
                      ) : (
                        <XCircle size={14} className="inline" />
                      )}
                    </div>
                  )}
                </div>
              ))}

              {/* Load More Button */}
              {hasMore && (
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="w-full py-3 px-4 mt-4 rounded-lg border border-border text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loadingMore ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading...
                    </span>
                  ) : (
                    'Load More'
                  )}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // Use portal to render at document.body for proper z-index
  if (!mounted) return null;
  return createPortal(modalContent, document.body);
}
