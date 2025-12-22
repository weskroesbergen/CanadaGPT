/**
 * useRealtimeMessages Hook
 *
 * Subscribe to real-time message updates in a conversation
 * Auto-marks messages as read when viewing
 */

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export interface Message {
  id: string;
  sender_id: string;
  recipient_id: string;
  content: string;
  attachments: Array<{
    url: string;
    filename: string;
    type: string;
    size: number;
  }>;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  sender: {
    id: string;
    username: string;
    display_name: string;
    avatar_url: string;
  };
}

interface UseRealtimeMessagesOptions {
  conversationId: string;
  autoMarkAsRead?: boolean;
}

export function useRealtimeMessages({
  conversationId,
  autoMarkAsRead = true,
}: UseRealtimeMessagesOptions) {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch initial messages
  const fetchMessages = useCallback(async () => {
    if (!conversationId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/messages/conversations/${conversationId}?limit=50`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch messages');
      }

      const data = await response.json();
      setMessages(data.messages || []);
    } catch (err) {
      console.error('Error fetching messages:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  // Mark messages as read
  const markAsRead = useCallback(async () => {
    if (!conversationId || !user) return;

    try {
      await fetch(`/api/messages/conversations/${conversationId}/read`, {
        method: 'POST',
      });
    } catch (err) {
      console.error('Error marking messages as read:', err);
    }
  }, [conversationId, user]);

  // Subscribe to new messages
  useEffect(() => {
    if (!conversationId || !user) return;

    // Fetch initial messages
    fetchMessages();

    // Subscribe to new messages via Supabase Realtime
    const channel = supabase
      .channel(`messages:${conversationId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'direct_messages',
          filter: `conversation_id=eq.${conversationId}`,
        },
        async (payload) => {
          const newMessage = payload.new as any;

          // Fetch sender info
          const { data: sender } = await supabase
            .from('user_profiles')
            .select('id, username, display_name, avatar_url')
            .eq('id', newMessage.sender_id)
            .single();

          const formattedMessage: Message = {
            ...newMessage,
            sender: sender || {
              id: newMessage.sender_id,
              username: '',
              display_name: 'Unknown',
              avatar_url: null,
            },
          };

          setMessages((prev) => [...prev, formattedMessage]);

          // Auto-mark as read if recipient is viewing
          if (autoMarkAsRead && newMessage.recipient_id === user.id) {
            markAsRead();
          }
        }
      )
      .subscribe();

    // Auto-mark as read when viewing
    if (autoMarkAsRead) {
      markAsRead();
    }

    return () => {
      supabase.removeChannel(channel);
    };
  }, [conversationId, user, autoMarkAsRead, fetchMessages, markAsRead]);

  // Send message
  const sendMessage = useCallback(
    async (content: string, attachments: any[] = []) => {
      if (!conversationId) {
        throw new Error('No conversation ID');
      }

      const response = await fetch(
        `/api/messages/conversations/${conversationId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, attachments }),
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to send message');
      }

      const data = await response.json();
      return data.message;
    },
    [conversationId]
  );

  return {
    messages,
    loading,
    error,
    sendMessage,
    markAsRead,
    refetch: fetchMessages,
  };
}
