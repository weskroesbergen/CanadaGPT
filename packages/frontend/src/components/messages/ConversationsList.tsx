/**
 * ConversationsList Component
 *
 * List of user's conversations with preview and unread counts
 */

'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { formatDistanceToNow } from 'date-fns';
import { MessageSquare, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface Conversation {
  id: string;
  other_participant: {
    id: string;
    username: string;
    display_name: string;
    avatar_url: string | null;
  };
  last_message_at: string;
  last_message_preview: string | null;
  unread_count: number;
  is_archived: boolean;
}

interface ConversationsListProps {
  selectedConversationId?: string;
  onSelectConversation: (conversation: Conversation) => void;
}

export function ConversationsList({
  selectedConversationId,
  onSelectConversation,
}: ConversationsListProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/messages/conversations');
      if (!response.ok) throw new Error('Failed to fetch conversations');

      const data = await response.json();
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Error fetching conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <MessageSquare className="mb-4 h-12 w-12 text-muted-foreground" />
        <h3 className="mb-2 text-lg font-semibold">No messages yet</h3>
        <p className="text-sm text-muted-foreground">
          Start a conversation by visiting a user's profile
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-4">
        <h2 className="text-xl font-semibold">Messages</h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {conversations.map((conversation) => (
          <ConversationItem
            key={conversation.id}
            conversation={conversation}
            isSelected={conversation.id === selectedConversationId}
            onClick={() => onSelectConversation(conversation)}
          />
        ))}
      </div>
    </div>
  );
}

function ConversationItem({
  conversation,
  isSelected,
  onClick,
}: {
  conversation: Conversation;
  isSelected: boolean;
  onClick: () => void;
}) {
  const { other_participant, last_message_at, last_message_preview, unread_count } = conversation;
  const timeAgo = formatDistanceToNow(new Date(last_message_at), { addSuffix: true });

  return (
    <button
      onClick={onClick}
      className={cn(
        'flex w-full items-start gap-3 border-b p-4 text-left transition-colors hover:bg-muted/50',
        isSelected && 'bg-muted'
      )}
    >
      {/* Avatar */}
      <div className="relative h-12 w-12 flex-shrink-0 rounded-full bg-muted">
        {other_participant.avatar_url ? (
          <Image
            src={other_participant.avatar_url}
            alt={other_participant.display_name}
            fill
            className="rounded-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-lg font-bold text-white">
            {other_participant.display_name?.[0]?.toUpperCase() || '?'}
          </div>
        )}
        {unread_count > 0 && (
          <div className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
            {unread_count > 9 ? '9+' : unread_count}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <div className="mb-1 flex items-baseline justify-between gap-2">
          <span className={cn('font-semibold', unread_count > 0 && 'text-primary')}>
            {other_participant.display_name}
          </span>
          <span className="text-xs text-muted-foreground">{timeAgo}</span>
        </div>

        {last_message_preview && (
          <p className={cn(
            'truncate text-sm',
            unread_count > 0 ? 'font-medium text-foreground' : 'text-muted-foreground'
          )}>
            {last_message_preview}
          </p>
        )}
      </div>
    </button>
  );
}
