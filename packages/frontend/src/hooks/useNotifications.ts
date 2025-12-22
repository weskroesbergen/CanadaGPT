/**
 * useNotifications Hook
 *
 * Manages notification state and real-time updates
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/lib/supabase';

export interface Notification {
  id: string;
  type: 'new_message' | 'new_follower' | 'mention' | 'reply' | 'like' | 'comment' | 'system';
  title: string;
  message: string;
  related_entity_type: 'message' | 'user' | 'post' | 'comment' | 'bill' | 'debate' | null;
  related_entity_id: string | null;
  read_at: string | null;
  created_at: string;
  actor: {
    id: string;
    username: string;
    display_name: string;
    avatar_url: string | null;
  } | null;
}

export function useNotifications() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);

  // Fetch notifications
  const fetchNotifications = useCallback(async (limit = 20, offset = 0) => {
    if (!user) return;

    setLoading(true);
    try {
      const response = await fetch(
        `/api/notifications?limit=${limit}&offset=${offset}`
      );

      if (!response.ok) throw new Error('Failed to fetch notifications');

      const data = await response.json();
      setNotifications(data.notifications);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setLoading(false);
    }
  }, [user]);

  // Fetch unread count
  const fetchUnreadCount = useCallback(async () => {
    if (!user) return;

    try {
      const response = await fetch('/api/notifications/count');

      if (!response.ok) throw new Error('Failed to fetch unread count');

      const data = await response.json();
      setUnreadCount(data.count);
    } catch (error) {
      console.error('Error fetching unread count:', error);
    }
  }, [user]);

  // Mark as read
  const markAsRead = useCallback(async (notificationIds?: string[]) => {
    if (!user) return;

    try {
      const response = await fetch('/api/notifications/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notificationIds }),
      });

      if (!response.ok) throw new Error('Failed to mark as read');

      // Update local state
      if (notificationIds) {
        setNotifications((prev) =>
          prev.map((n) =>
            notificationIds.includes(n.id) ? { ...n, read_at: new Date().toISOString() } : n
          )
        );
        setUnreadCount((prev) => Math.max(0, prev - notificationIds.length));
      } else {
        // Mark all as read
        setNotifications((prev) =>
          prev.map((n) => ({ ...n, read_at: new Date().toISOString() }))
        );
        setUnreadCount(0);
      }
    } catch (error) {
      console.error('Error marking notifications as read:', error);
    }
  }, [user]);

  // Mark single notification as read
  const markOneAsRead = useCallback(
    (notificationId: string) => {
      markAsRead([notificationId]);
    },
    [markAsRead]
  );

  // Subscribe to real-time notifications
  useEffect(() => {
    if (!user) return;

    // Initial fetch
    fetchNotifications();
    fetchUnreadCount();

    // Subscribe to new notifications
    const channel = supabase
      .channel(`notifications:${user.id}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'notifications',
          filter: `user_id=eq.${user.id}`,
        },
        async (payload: any) => {
          const newNotification = payload.new as Notification;

          // Fetch full notification data (with actor)
          const response = await fetch(
            `/api/notifications?limit=1&offset=0`
          );

          if (response.ok) {
            const data = await response.json();
            if (data.notifications.length > 0) {
              setNotifications((prev) => [data.notifications[0], ...prev]);
              setUnreadCount((prev) => prev + 1);
            }
          }
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'notifications',
          filter: `user_id=eq.${user.id}`,
        },
        (payload: any) => {
          const updatedNotification = payload.new as Notification;

          // Update local state
          setNotifications((prev) =>
            prev.map((n) =>
              n.id === updatedNotification.id ? { ...n, ...updatedNotification } : n
            )
          );

          // Update unread count if status changed
          if (updatedNotification.read_at) {
            setUnreadCount((prev) => Math.max(0, prev - 1));
          }
        }
      )
      .subscribe();

    return () => {
      channel.unsubscribe();
    };
  }, [user, fetchNotifications, fetchUnreadCount]);

  return {
    notifications,
    unreadCount,
    loading,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markOneAsRead,
  };
}
