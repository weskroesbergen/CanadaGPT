/**
 * useFollow Hook
 *
 * Client-side state management for user follows with optimistic updates
 * Follows the same pattern as useBookmarks.ts
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';

export interface UserProfile {
  id: string;
  username: string | null;
  display_name: string | null;
  avatar_url: string | null;
  bio: string | null;
  followers_count: number;
  following_count: number;
  posts_count: number;
  replies_count: number;
  reputation_score: number;
}

export interface Follow {
  id: string;
  follower_id: string;
  following_id: string;
  created_at: string;
}

export function useFollow() {
  const { user } = useAuth();
  const [following, setFollowing] = useState<Set<string>>(new Set());
  const [followers, setFollowers] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Check if current user follows a specific user
   */
  const isFollowing = useCallback(
    (userId: string): boolean => {
      return following.has(userId);
    },
    [following]
  );

  /**
   * Check if a specific user follows current user
   */
  const isFollower = useCallback(
    (userId: string): boolean => {
      return followers.has(userId);
    },
    [followers]
  );

  /**
   * Fetch user's following and followers
   */
  const fetchFollows = useCallback(async () => {
    if (!user?.id) return;

    setLoading(true);
    setError(null);

    try {
      // Fetch both following and followers in parallel
      const [followingRes, followersRes] = await Promise.all([
        fetch(`/api/users/${user.id}/following`),
        fetch(`/api/users/${user.id}/followers`),
      ]);

      if (!followingRes.ok || !followersRes.ok) {
        throw new Error('Failed to fetch follows');
      }

      const [followingData, followersData] = await Promise.all([
        followingRes.json(),
        followersRes.json(),
      ]);

      // Convert to Sets for O(1) lookup
      setFollowing(new Set(followingData.following.map((f: Follow) => f.following_id)));
      setFollowers(new Set(followersData.followers.map((f: Follow) => f.follower_id)));
    } catch (err) {
      console.error('Error fetching follows:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  /**
   * Follow or unfollow a user
   */
  const toggleFollow = useCallback(
    async (
      targetUserId: string
    ): Promise<{ success: boolean; action: 'followed' | 'unfollowed'; error?: string }> => {
      if (!user) {
        return { success: false, action: 'unfollowed', error: 'Not authenticated' };
      }

      if (targetUserId === user.id) {
        return { success: false, action: 'unfollowed', error: 'Cannot follow yourself' };
      }

      // Optimistic update
      const wasFollowing = isFollowing(targetUserId);
      const previousFollowing = new Set(following);

      if (wasFollowing) {
        // Optimistically remove
        setFollowing(prev => {
          const next = new Set(prev);
          next.delete(targetUserId);
          return next;
        });
      } else {
        // Optimistically add
        setFollowing(prev => {
          const next = new Set(prev);
          next.add(targetUserId);
          return next;
        });
      }

      try {
        const response = await fetch(`/api/users/${targetUserId}/follow`, {
          method: wasFollowing ? 'DELETE' : 'POST',
        });

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.error || 'Failed to toggle follow');
        }

        return {
          success: true,
          action: wasFollowing ? 'unfollowed' : 'followed',
        };
      } catch (err) {
        console.error('Error toggling follow:', err);

        // Revert optimistic update on error
        setFollowing(previousFollowing);

        return {
          success: false,
          action: 'unfollowed',
          error: err instanceof Error ? err.message : 'Unknown error',
        };
      }
    },
    [user, following, isFollowing]
  );

  /**
   * Get followers for a specific user
   */
  const getFollowers = useCallback(
    async (userId: string): Promise<UserProfile[]> => {
      try {
        const response = await fetch(`/api/users/${userId}/followers`);
        if (!response.ok) {
          throw new Error('Failed to fetch followers');
        }
        const data = await response.json();
        return data.followers || [];
      } catch (err) {
        console.error('Error fetching followers:', err);
        throw err;
      }
    },
    []
  );

  /**
   * Get users that a specific user is following
   */
  const getFollowing = useCallback(
    async (userId: string): Promise<UserProfile[]> => {
      try {
        const response = await fetch(`/api/users/${userId}/following`);
        if (!response.ok) {
          throw new Error('Failed to fetch following');
        }
        const data = await response.json();
        return data.following || [];
      } catch (err) {
        console.error('Error fetching following:', err);
        throw err;
      }
    },
    []
  );

  /**
   * Get suggested users to follow
   */
  const getSuggested = useCallback(
    async (limit: number = 5): Promise<UserProfile[]> => {
      try {
        const response = await fetch(`/api/users/suggested?limit=${limit}`);
        if (!response.ok) {
          throw new Error('Failed to fetch suggested users');
        }
        const data = await response.json();
        return data.users || [];
      } catch (err) {
        console.error('Error fetching suggested users:', err);
        throw err;
      }
    },
    []
  );

  // Fetch follows on mount and when user changes
  useEffect(() => {
    if (user?.id) {
      fetchFollows();
    } else {
      setFollowing(new Set());
      setFollowers(new Set());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]); // Only re-fetch when user ID changes

  return {
    following: Array.from(following),
    followers: Array.from(followers),
    loading,
    error,
    isFollowing,
    isFollower,
    toggleFollow,
    getFollowers,
    getFollowing,
    getSuggested,
    refetch: fetchFollows,
  };
}
