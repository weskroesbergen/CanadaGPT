/**
 * useTypingIndicator Hook
 *
 * Detects and broadcasts typing status in a conversation
 * Uses debouncing to avoid excessive updates
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

const TYPING_TIMEOUT = 3000; // Stop showing typing after 3 seconds of inactivity

interface UseTypingIndicatorOptions {
  conversationId: string;
  otherUserId: string;
}

export function useTypingIndicator({
  conversationId,
  otherUserId,
}: UseTypingIndicatorOptions) {
  const { user } = useAuth();
  const [isOtherUserTyping, setIsOtherUserTyping] = useState(false);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const updateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Subscribe to other user's typing status
  useEffect(() => {
    if (!conversationId || !user) return;

    const channel = supabase
      .channel(`typing:${conversationId}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'typing_indicators',
          filter: `conversation_id=eq.${conversationId}`,
        },
        (payload) => {
          if (payload.eventType === 'INSERT' || payload.eventType === 'UPDATE') {
            const indicator = payload.new as any;

            // Only show typing for other user
            if (indicator.user_id === otherUserId) {
              setIsOtherUserTyping(true);

              // Clear existing timeout
              if (typingTimeoutRef.current) {
                clearTimeout(typingTimeoutRef.current);
              }

              // Hide typing after timeout
              typingTimeoutRef.current = setTimeout(() => {
                setIsOtherUserTyping(false);
              }, TYPING_TIMEOUT);
            }
          } else if (payload.eventType === 'DELETE') {
            const indicator = payload.old as any;
            if (indicator.user_id === otherUserId) {
              setIsOtherUserTyping(false);
            }
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, [conversationId, otherUserId, user]);

  // Broadcast typing status (debounced)
  const setTyping = useCallback(
    async (isTyping: boolean) => {
      if (!conversationId || !user) return;

      // Clear existing update timeout
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }

      if (isTyping) {
        // Update typing indicator
        updateTimeoutRef.current = setTimeout(async () => {
          try {
            await supabase.from('typing_indicators').upsert({
              conversation_id: conversationId,
              user_id: user.id,
              expires_at: new Date(Date.now() + 5000).toISOString(),
            });
          } catch (error) {
            console.error('Error setting typing indicator:', error);
          }
        }, 300); // Debounce: only update after 300ms of typing
      } else {
        // Remove typing indicator immediately when stopped
        try {
          await supabase
            .from('typing_indicators')
            .delete()
            .eq('conversation_id', conversationId)
            .eq('user_id', user.id);
        } catch (error) {
          console.error('Error removing typing indicator:', error);
        }
      }
    },
    [conversationId, user]
  );

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }
      // Remove typing indicator when component unmounts
      if (conversationId && user) {
        supabase
          .from('typing_indicators')
          .delete()
          .eq('conversation_id', conversationId)
          .eq('user_id', user.id)
          .then(({ error }) => {
            if (error) console.error('Error cleaning up typing indicator:', error);
          });
      }
    };
  }, [conversationId, user]);

  return {
    isOtherUserTyping,
    setTyping,
  };
}
