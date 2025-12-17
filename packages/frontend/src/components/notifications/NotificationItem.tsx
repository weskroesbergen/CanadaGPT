/**
 * NotificationItem Component
 *
 * Individual notification row with icon, message, and action
 */

'use client';

import { formatDistanceToNow } from 'date-fns';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { MessageSquare, UserPlus, AtSign, MessageCircle, Heart, FileText } from 'lucide-react';
import { useNotifications, type Notification } from '@/hooks/useNotifications';
import { cn } from '@/lib/utils';

interface NotificationItemProps {
  notification: Notification;
  onClose: () => void;
}

const notificationIcons = {
  new_message: MessageSquare,
  new_follower: UserPlus,
  mention: AtSign,
  reply: MessageCircle,
  like: Heart,
  comment: MessageCircle,
  system: FileText,
};

const notificationColors = {
  new_message: 'text-blue-500',
  new_follower: 'text-green-500',
  mention: 'text-purple-500',
  reply: 'text-orange-500',
  like: 'text-red-500',
  comment: 'text-yellow-500',
  system: 'text-gray-500',
};

export function NotificationItem({ notification, onClose }: NotificationItemProps) {
  const router = useRouter();
  const { markOneAsRead } = useNotifications();

  const Icon = notificationIcons[notification.type];
  const iconColor = notificationColors[notification.type];
  const timeAgo = formatDistanceToNow(new Date(notification.created_at), { addSuffix: true });
  const isUnread = !notification.read_at;

  const handleClick = () => {
    // Mark as read
    if (isUnread) {
      markOneAsRead(notification.id);
    }

    // Navigate to related entity
    if (notification.related_entity_type && notification.related_entity_id) {
      switch (notification.related_entity_type) {
        case 'message':
          router.push('/messages');
          break;
        case 'user':
          // Extract username from actor
          if (notification.actor) {
            router.push(`/users/${notification.actor.username}`);
          }
          break;
        case 'post':
          // TODO: Navigate to post
          break;
        case 'comment':
          // TODO: Navigate to comment
          break;
        case 'bill':
          router.push(`/bills/${notification.related_entity_id}`);
          break;
        case 'debate':
          router.push(`/debates/${notification.related_entity_id}`);
          break;
      }
    }

    onClose();
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        'flex w-full items-start gap-3 p-4 text-left transition-colors hover:bg-muted',
        isUnread && 'bg-blue-50 dark:bg-blue-950/20'
      )}
    >
      {/* Icon or Avatar */}
      <div className="flex-shrink-0">
        {notification.actor?.avatar_url ? (
          <div className="relative h-10 w-10 rounded-full">
            <Image
              src={notification.actor.avatar_url}
              alt={notification.actor.display_name}
              fill
              className="rounded-full object-cover"
            />
            <div className={cn('absolute -bottom-1 -right-1 rounded-full bg-background p-1', iconColor)}>
              <Icon className="h-3 w-3" />
            </div>
          </div>
        ) : (
          <div className={cn('rounded-full bg-muted p-2', iconColor)}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <p className={cn('text-sm', isUnread && 'font-semibold')}>
          {notification.message}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">{timeAgo}</p>
      </div>

      {/* Unread indicator */}
      {isUnread && (
        <div className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-blue-500" />
      )}
    </button>
  );
}
