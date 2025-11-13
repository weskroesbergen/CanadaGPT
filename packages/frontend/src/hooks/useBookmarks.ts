/**
 * useBookmarks Hook
 *
 * Client-side state management for bookmarks with optimistic updates
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';

export interface Bookmark {
  id: string;
  user_id: string;
  item_type: 'mp' | 'statement' | 'bill' | 'post' | 'committee' | 'debate';
  item_id: string;
  title: string;
  subtitle?: string;
  image_url?: string;
  url: string;
  metadata: Record<string, any>;
  collection_id?: string | null;
  tags: string[];
  notes?: string;
  ai_prompt?: string; // PRO tier: AI context instructions
  is_favorite: boolean;
  favorite_order?: number | null;
  notifications_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateBookmarkData {
  itemType: string;
  itemId: string;
  title: string;
  subtitle?: string;
  imageUrl?: string;
  url: string;
  metadata?: Record<string, any>;
  collectionId?: string | null;
  tags?: string[];
  notes?: string;
  isFavorite?: boolean;
}

export interface BookmarkUsage {
  total: number;
  limit: number | null;
  percentage: number;
  isNearLimit: boolean;
  isAtLimit: boolean;
  canCreate: boolean;
}

export function useBookmarks() {
  const { user, profile } = useAuth();
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [favorites, setFavorites] = useState<Bookmark[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<BookmarkUsage | null>(null);

  /**
   * Check if an item is bookmarked
   */
  const isBookmarked = useCallback(
    (itemType: string, itemId: string): boolean => {
      return bookmarks.some(
        (b) => b.item_type === itemType && b.item_id === itemId
      );
    },
    [bookmarks]
  );

  /**
   * Get bookmark for an item
   */
  const getBookmark = useCallback(
    (itemType: string, itemId: string): Bookmark | undefined => {
      return bookmarks.find(
        (b) => b.item_type === itemType && b.item_id === itemId
      );
    },
    [bookmarks]
  );

  /**
   * Fetch all bookmarks
   */
  const fetchBookmarks = useCallback(async () => {
    if (!user?.id) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/bookmarks');

      if (!response.ok) {
        throw new Error('Failed to fetch bookmarks');
      }

      const data = await response.json();
      setBookmarks(data.bookmarks || []);
      setUsage(data.tier?.usage || null);

      // Extract favorites
      const favs = (data.bookmarks || [])
        .filter((b: Bookmark) => b.is_favorite)
        .sort((a: Bookmark, b: Bookmark) => {
          const orderA = a.favorite_order || 0;
          const orderB = b.favorite_order || 0;
          return orderA - orderB;
        });
      setFavorites(favs);
    } catch (err) {
      console.error('Error fetching bookmarks:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  /**
   * Create or toggle bookmark
   */
  const toggleBookmark = useCallback(
    async (data: CreateBookmarkData): Promise<{ success: boolean; action: 'created' | 'removed'; error?: string }> => {
      if (!user) {
        return { success: false, action: 'removed', error: 'Not authenticated' };
      }

      // Optimistic update
      const existingBookmark = getBookmark(data.itemType, data.itemId);
      const isRemoving = !!existingBookmark;

      if (isRemoving) {
        // Optimistically remove
        setBookmarks((prev) =>
          prev.filter((b) => !(b.item_type === data.itemType && b.item_id === data.itemId))
        );
        setFavorites((prev) =>
          prev.filter((b) => !(b.item_type === data.itemType && b.item_id === data.itemId))
        );
      }

      try {
        const response = await fetch('/api/bookmarks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.error || 'Failed to toggle bookmark');
        }

        if (result.action === 'created') {
          // Add new bookmark
          setBookmarks((prev) => [result.bookmark, ...prev]);
          if (result.bookmark.is_favorite) {
            setFavorites((prev) => [...prev, result.bookmark].sort((a, b) => {
              const orderA = a.favorite_order || 0;
              const orderB = b.favorite_order || 0;
              return orderA - orderB;
            }));
          }
          setUsage(result.tier?.usage || null);
        } else {
          // Already removed optimistically
          setUsage((prev) => prev ? { ...prev, total: prev.total - 1 } : null);
        }

        return { success: true, action: result.action };
      } catch (err) {
        console.error('Error toggling bookmark:', err);

        // Revert optimistic update on error
        if (isRemoving && existingBookmark) {
          setBookmarks((prev) => [existingBookmark, ...prev]);
          if (existingBookmark.is_favorite) {
            setFavorites((prev) => [existingBookmark, ...prev]);
          }
        }

        return {
          success: false,
          action: 'removed',
          error: err instanceof Error ? err.message : 'Unknown error',
        };
      }
    },
    [user, getBookmark]
  );

  /**
   * Update bookmark
   */
  const updateBookmark = useCallback(
    async (
      bookmarkId: string,
      updates: Partial<{
        collectionId: string | null;
        tags: string[];
        notes: string;
        aiPrompt: string; // PRO tier only
        isFavorite: boolean;
        notificationsEnabled: boolean;
      }>
    ): Promise<{ success: boolean; error?: string }> => {
      if (!user) {
        return { success: false, error: 'Not authenticated' };
      }

      try {
        const response = await fetch(`/api/bookmarks/${bookmarkId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates),
        });

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.error || 'Failed to update bookmark');
        }

        // Update local state
        setBookmarks((prev) =>
          prev.map((b) => (b.id === bookmarkId ? result.bookmark : b))
        );

        // Update favorites if necessary
        if (updates.isFavorite !== undefined) {
          if (updates.isFavorite) {
            setFavorites((prev) => [...prev, result.bookmark].sort((a, b) => {
              const orderA = a.favorite_order || 0;
              const orderB = b.favorite_order || 0;
              return orderA - orderB;
            }));
          } else {
            setFavorites((prev) => prev.filter((b) => b.id !== bookmarkId));
          }
        }

        return { success: true };
      } catch (err) {
        console.error('Error updating bookmark:', err);
        return {
          success: false,
          error: err instanceof Error ? err.message : 'Unknown error',
        };
      }
    },
    [user]
  );

  /**
   * Delete bookmark
   */
  const deleteBookmark = useCallback(
    async (bookmarkId: string): Promise<{ success: boolean; error?: string }> => {
      if (!user) {
        return { success: false, error: 'Not authenticated' };
      }

      // Optimistic update
      const bookmark = bookmarks.find((b) => b.id === bookmarkId);
      setBookmarks((prev) => prev.filter((b) => b.id !== bookmarkId));
      setFavorites((prev) => prev.filter((b) => b.id !== bookmarkId));

      try {
        const response = await fetch(`/api/bookmarks/${bookmarkId}`, {
          method: 'DELETE',
        });

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.error || 'Failed to delete bookmark');
        }

        setUsage((prev) => prev ? { ...prev, total: result.count } : null);

        return { success: true };
      } catch (err) {
        console.error('Error deleting bookmark:', err);

        // Revert optimistic update
        if (bookmark) {
          setBookmarks((prev) => [bookmark, ...prev]);
          if (bookmark.is_favorite) {
            setFavorites((prev) => [bookmark, ...prev]);
          }
        }

        return {
          success: false,
          error: err instanceof Error ? err.message : 'Unknown error',
        };
      }
    },
    [user, bookmarks]
  );

  // Fetch bookmarks on mount and when user changes
  useEffect(() => {
    if (user?.id) {
      fetchBookmarks();
    } else {
      setBookmarks([]);
      setFavorites([]);
      setUsage(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]); // Only re-fetch when user ID changes, not on fetchBookmarks updates

  return {
    bookmarks,
    favorites,
    loading,
    error,
    usage,
    isBookmarked,
    getBookmark,
    toggleBookmark,
    updateBookmark,
    deleteBookmark,
    refetch: fetchBookmarks,
  };
}
