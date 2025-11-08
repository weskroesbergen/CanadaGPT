'use client';

import { useEffect, useState } from 'react';
import { createBrowserClient } from '@supabase/ssr';

/**
 * Real-time hook for vote updates
 * Subscribes to changes in the forum_votes table and updates vote counts
 */

interface VoteUpdate {
  postId: string;
  upvotes: number;
  downvotes: number;
}

export function useRealtimeVotes(
  postId: string,
  initialUpvotes: number,
  initialDownvotes: number,
  enabled: boolean = true
) {
  const [upvotes, setUpvotes] = useState(initialUpvotes);
  const [downvotes, setDownvotes] = useState(initialDownvotes);

  useEffect(() => {
    if (!enabled) return;

    // Create Supabase client for browser
    const supabase = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );

    // Subscribe to vote changes for this specific post
    const channel = supabase
      .channel(`votes-${postId}`)
      .on(
        'postgres_changes',
        {
          event: '*', // Listen to INSERT, UPDATE, DELETE
          schema: 'public',
          table: 'forum_votes',
          filter: `post_id=eq.${postId}`,
        },
        async () => {
          // When any vote changes, re-fetch the current counts from the post
          const { data } = await supabase
            .from('forum_posts')
            .select('upvotes_count, downvotes_count')
            .eq('id', postId)
            .single();

          if (data) {
            setUpvotes(data.upvotes_count);
            setDownvotes(data.downvotes_count);
          }
        }
      )
      .subscribe();

    // Cleanup subscription on unmount
    return () => {
      supabase.removeChannel(channel);
    };
  }, [postId, enabled]);

  // Reset counts when initial values change
  useEffect(() => {
    setUpvotes(initialUpvotes);
    setDownvotes(initialDownvotes);
  }, [initialUpvotes, initialDownvotes]);

  return { upvotes, downvotes };
}
