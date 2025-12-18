'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Real-time notifications hook
 * Notifies users when:
 * - Someone replies to their post
 * - Their post receives votes
 * - Their post is mentioned (future feature)
 */

export interface Notification {
  id: string;
  type: 'reply' | 'vote' | 'mention';
  message: string;
  postId: string;
  createdAt: Date;
  read: boolean;
}

export function useRealtimeNotifications() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user) return;

    // Subscribe to new replies on user's posts
    const replyChannel = supabase
      .channel(`user-notifications-${user.id}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'forum_posts',
        },
        async (payload) => {
          const newPost = payload.new as any;

          // Check if this is a reply to one of the user's posts
          if (newPost.parent_post_id) {
            const { data: parentPost } = await supabase
              .from('forum_posts')
              .select('author_id, title, content')
              .eq('id', newPost.parent_post_id)
              .single();

            // If the parent post belongs to the current user
            if (parentPost && parentPost.author_id === user.id) {
              // Fetch the reply author's name
              const { data: replyAuthor } = await supabase
                .from('user_profiles')
                .select('display_name')
                .eq('id', newPost.author_id)
                .single();

              const notification: Notification = {
                id: `reply-${newPost.id}`,
                type: 'reply',
                message: `${replyAuthor?.display_name || 'Someone'} replied to your post`,
                postId: newPost.parent_post_id,
                createdAt: new Date(newPost.created_at),
                read: false,
              };

              setNotifications((current) => [notification, ...current]);
              setUnreadCount((count) => count + 1);

              // Show browser notification if permitted
              if ('Notification' in window && Notification.permission === 'granted') {
                new Notification('New Reply', {
                  body: notification.message,
                  icon: '/favicon.ico',
                  tag: notification.id,
                });
              }
            }
          }
        }
      )
      .subscribe();

    // Request browser notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    // Cleanup subscription on unmount
    return () => {
      supabase.removeChannel(replyChannel);
    };
  }, [user]);

  const markAsRead = (notificationId: string) => {
    setNotifications((current) =>
      current.map((n) =>
        n.id === notificationId ? { ...n, read: true } : n
      )
    );
    setUnreadCount((count) => Math.max(0, count - 1));
  };

  const markAllAsRead = () => {
    setNotifications((current) =>
      current.map((n) => ({ ...n, read: true }))
    );
    setUnreadCount(0);
  };

  const clearNotifications = () => {
    setNotifications([]);
    setUnreadCount(0);
  };

  return {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearNotifications,
  };
}
