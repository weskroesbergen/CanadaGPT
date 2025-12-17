/**
 * NotificationsPanel Component
 *
 * Dropdown panel showing list of notifications
 */

'use client';

import { useNotifications } from '@/hooks/useNotifications';
import { NotificationItem } from './NotificationItem';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCheck, Bell } from 'lucide-react';

interface NotificationsPanelProps {
  onClose: () => void;
}

export function NotificationsPanel({ onClose }: NotificationsPanelProps) {
  const { notifications, loading, unreadCount, markAsRead } = useNotifications();

  const handleMarkAllRead = async () => {
    await markAsRead();
  };

  return (
    <div className="absolute right-0 top-12 z-50 w-[400px] max-h-[600px] overflow-hidden rounded-lg border bg-background shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4">
        <h3 className="text-lg font-semibold">Notifications</h3>
        {unreadCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleMarkAllRead}
            className="text-xs"
          >
            <CheckCheck className="mr-1 h-4 w-4" />
            Mark all read
          </Button>
        )}
      </div>

      {/* Notifications List */}
      <div className="max-h-[500px] overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <div className="mb-2 rounded-full bg-muted p-3">
              <Bell className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">No notifications yet</p>
          </div>
        ) : (
          <div className="divide-y">
            {notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onClose={onClose}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      {notifications.length > 0 && (
        <div className="border-t p-2 text-center">
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="w-full text-sm"
          >
            View all notifications
          </Button>
        </div>
      )}
    </div>
  );
}
