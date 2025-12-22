/**
 * useEntityVotes Hook
 *
 * Batch load vote data for multiple entities efficiently
 * Prevents N+1 query problem when displaying lists of bills/MPs/statements
 *
 * Usage:
 * ```tsx
 * const billIds = bills.map(b => `${b.session}-${b.number}`);
 * const { getVoteData, isLoading, error, refetch } = useEntityVotes('bill', billIds);
 *
 * // In render:
 * <EntityVoteButtons
 *   entityType="bill"
 *   entityId={billId}
 *   {...getVoteData(billId)}
 * />
 * ```
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import type { VoteType, EntityType } from '@/components/votes/EntityVoteButtons';

interface VoteData {
  entity_id: string;
  upvotes: number;
  downvotes: number;
  net_score: number;
  user_vote: VoteType | null;
}

interface UseEntityVotesReturn {
  /** Get vote data for a specific entity */
  getVoteData: (
    entityId: string
  ) => {
    initialUpvotes: number;
    initialDownvotes: number;
    initialUserVote: VoteType | null;
  };
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: Error | null;
  /** Refetch vote data */
  refetch: () => void;
  /** Raw vote data map */
  voteDataMap: Map<string, VoteData>;
}

/**
 * Batch load vote data for multiple entities
 */
export function useEntityVotes(
  entityType: EntityType,
  entityIds: string[]
): UseEntityVotesReturn {
  const [voteDataMap, setVoteDataMap] = useState<Map<string, VoteData>>(
    new Map()
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Create a stable key from entityIds to prevent infinite loops
  // Arrays are compared by reference, so we need a stable primitive value
  const entityIdsKey = entityIds.join(',');

  const fetchVotes = useCallback(async () => {
    // Skip if no entity IDs
    if (entityIds.length === 0) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Build query params for batch request
      const entityIdsParam = entityIds.join(',');
      const response = await fetch(
        `/api/votes?entity_type=${entityType}&entity_ids=${encodeURIComponent(
          entityIdsParam
        )}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch votes: ${response.statusText}`);
      }

      const data = await response.json();

      // Create a map for O(1) lookup
      const newMap = new Map<string, VoteData>();
      data.votes.forEach((vote: VoteData) => {
        newMap.set(vote.entity_id, vote);
      });

      setVoteDataMap(newMap);
    } catch (err) {
      console.error('Error fetching entity votes:', err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [entityType, entityIdsKey]); // Use stable string key instead of array

  // Fetch votes on mount and when entityIds change
  useEffect(() => {
    fetchVotes();
  }, [fetchVotes]);

  /**
   * Get vote data for a specific entity ID
   * Returns default values if data not yet loaded
   */
  const getVoteData = useCallback(
    (entityId: string) => {
      const data = voteDataMap.get(entityId);
      return {
        initialUpvotes: data?.upvotes || 0,
        initialDownvotes: data?.downvotes || 0,
        initialUserVote: data?.user_vote || null,
      };
    },
    [voteDataMap]
  );

  return {
    getVoteData,
    isLoading,
    error,
    refetch: fetchVotes,
    voteDataMap,
  };
}
