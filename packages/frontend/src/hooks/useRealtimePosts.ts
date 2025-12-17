'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import type { ForumPost } from '@/types/forum';

/**
 * Real-time hook for forum posts
 * Subscribes to Supabase Realtime channels for live updates
 *
 * Features:
 * - New posts appear automatically
 * - Vote counts update in real-time
 * - Deleted posts are removed from the list
 * - Reply counts update when new replies are added
 */

interface UseRealtimePostsOptions {
  categoryId?: string;
  billNumber?: string;
  billSession?: string;
  postType?: 'discussion' | 'bill_comment';
  threadRootId?: string;
  enabled?: boolean;
}

interface RealtimePostUpdate {
  new: ForumPost;
  old: ForumPost;
  eventType: 'INSERT' | 'UPDATE' | 'DELETE';
}

export function useRealtimePosts(
  initialPosts: ForumPost[],
  options: UseRealtimePostsOptions = {}
) {
  const {
    categoryId,
    billNumber,
    billSession,
    postType,
    threadRootId,
    enabled = true,
  } = options;

  const [posts, setPosts] = useState<ForumPost[]>(initialPosts);

  useEffect(() => {
    if (!enabled) return;

    // Build filter conditions
    let filter = 'is_deleted=eq.false';

    if (categoryId) {
      filter += `,category_id=eq.${categoryId}`;
    }

    if (billNumber) {
      filter += `,bill_number=eq.${billNumber}`;
    }

    if (billSession) {
      filter += `,bill_session=eq.${billSession}`;
    }

    if (postType) {
      filter += `,post_type=eq.${postType}`;
    }

    if (threadRootId) {
      filter += `,thread_root_id=eq.${threadRootId}`;
    }

    // Subscribe to real-time changes
    const channel = supabase
      .channel(`posts-${categoryId || billNumber || threadRootId || 'all'}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'forum_posts',
          filter,
        },
        (payload) => {
          const newPost = payload.new as ForumPost;

          // Only add if parent_post_id is null (top-level posts)
          // Nested replies are handled by their parent thread
          if (!newPost.parent_post_id) {
            setPosts((current) => [newPost, ...current]);
          }
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'forum_posts',
          filter,
        },
        (payload) => {
          const updatedPost = payload.new as ForumPost;

          setPosts((current) =>
            current.map((post) =>
              post.id === updatedPost.id ? { ...post, ...updatedPost } : post
            )
          );
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'DELETE',
          schema: 'public',
          table: 'forum_posts',
        },
        (payload) => {
          const deletedPost = payload.old as ForumPost;

          setPosts((current) =>
            current.filter((post) => post.id !== deletedPost.id)
          );
        }
      )
      .subscribe();

    // Cleanup subscription on unmount
    return () => {
      supabase.removeChannel(channel);
    };
  }, [categoryId, billNumber, billSession, postType, threadRootId, enabled]);

  // Reset posts when initialPosts change (e.g., when sorting or filtering)
  useEffect(() => {
    setPosts(initialPosts);
  }, [initialPosts]);

  return posts;
}
