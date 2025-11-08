'use client';

import { useState, useRef, useEffect } from 'react';
import { Bell, Check, X } from 'lucide-react';
import { useRealtimeNotifications } from '@/hooks/useRealtimeNotifications';
import { useRouter } from 'next/navigation';

export function NotificationBell() {
  const router = useRouter();
  const { notifications, unreadCount, markAsRead, markAllAsRead, clearNotifications } =
    useRealtimeNotifications();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleNotificationClick = (postId: string, notificationId: string) => {
    markAsRead(notificationId);
    setIsOpen(false);
    router.push(`/forum/posts/${postId}`);
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-lg hover:bg-background-secondary transition-colors"
        aria-label="Notifications"
      >
        <Bell size={20} className="text-text-secondary" />
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 bg-accent-red text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          className="
            absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto
            bg-background-secondary border-2 border-border-primary rounded-lg
            shadow-2xl z-50
          "
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-border-primary sticky top-0 bg-background-secondary">
            <h3 className="font-bold text-text-primary">Notifications</h3>
            {notifications.length > 0 && (
              <div className="flex gap-2">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-xs text-accent-red hover:underline"
                  >
                    Mark all read
                  </button>
                )}
                <button
                  onClick={clearNotifications}
                  className="text-xs text-text-tertiary hover:text-text-primary"
                >
                  Clear all
                </button>
              </div>
            )}
          </div>

          {/* Notifications list */}
          {notifications.length === 0 ? (
            <div className="p-8 text-center">
              <Bell size={48} className="mx-auto text-text-tertiary mb-3 opacity-50" />
              <p className="text-text-secondary text-sm">No notifications yet</p>
              <p className="text-text-tertiary text-xs mt-1">
                We'll notify you when someone replies to your posts
              </p>
            </div>
          ) : (
            <div className="divide-y divide-border-primary">
              {notifications.map((notification) => (
                <button
                  key={notification.id}
                  onClick={() => handleNotificationClick(notification.postId, notification.id)}
                  className={`
                    w-full p-4 text-left hover:bg-background-primary transition-colors
                    ${!notification.read ? 'bg-accent-red/5' : ''}
                  `}
                >
                  <div className="flex items-start gap-3">
                    {/* Icon */}
                    <div
                      className={`
                        w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
                        ${notification.read ? 'bg-background-primary' : 'bg-accent-red/20'}
                      `}
                    >
                      {notification.type === 'reply' && (
                        <span className="text-lg">💬</span>
                      )}
                      {notification.type === 'vote' && (
                        <span className="text-lg">👍</span>
                      )}
                      {notification.type === 'mention' && (
                        <span className="text-lg">@</span>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-sm ${
                          notification.read ? 'text-text-secondary' : 'text-text-primary font-medium'
                        }`}
                      >
                        {notification.message}
                      </p>
                      <p className="text-xs text-text-tertiary mt-1">
                        {formatTime(notification.createdAt)}
                      </p>
                    </div>

                    {/* Unread indicator */}
                    {!notification.read && (
                      <div className="w-2 h-2 rounded-full bg-accent-red flex-shrink-0 mt-2" />
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
