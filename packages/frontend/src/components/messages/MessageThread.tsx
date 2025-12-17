/**
 * MessageThread Component
 *
 * Displays messages in a conversation with real-time updates
 */

'use client';

import { useEffect, useRef } from 'react';
import Image from 'next/image';
import { formatDistanceToNow, format } from 'date-fns';
import { Loader2, FileText, ExternalLink } from 'lucide-react';
import { useRealtimeMessages, Message } from '@/hooks/useRealtimeMessages';
import { useTypingIndicator } from '@/hooks/useTypingIndicator';
import { MessageInput } from './MessageInput';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';

interface MessageThreadProps {
  conversationId: string;
  otherParticipant: {
    id: string;
    username: string;
    display_name: string;
    avatar_url: string | null;
  };
}

export function MessageThread({ conversationId, otherParticipant }: MessageThreadProps) {
  const { user } = useAuth();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, loading, sendMessage } = useRealtimeMessages({
    conversationId,
    autoMarkAsRead: true,
  });
  const { isOtherUserTyping, setTyping } = useTypingIndicator({
    conversationId,
    otherUserId: otherParticipant.id,
  });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOtherUserTyping]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 border-b p-4">
        <div className="relative h-10 w-10 rounded-full bg-muted">
          {otherParticipant.avatar_url ? (
            <Image
              src={otherParticipant.avatar_url}
              alt={otherParticipant.display_name}
              fill
              className="rounded-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-sm font-bold text-white">
              {otherParticipant.display_name?.[0]?.toUpperCase() || '?'}
            </div>
          )}
        </div>
        <div>
          <h3 className="font-semibold">{otherParticipant.display_name}</h3>
          <p className="text-sm text-muted-foreground">
            @{otherParticipant.username}
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-center text-muted-foreground">
            <p>No messages yet. Start the conversation!</p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                isOwn={message.sender_id === user?.id}
              />
            ))}

            {/* Typing Indicator */}
            {isOtherUserTyping && (
              <div className="flex items-start gap-2">
                <div className="relative h-8 w-8 rounded-full bg-muted flex-shrink-0">
                  {otherParticipant.avatar_url ? (
                    <Image
                      src={otherParticipant.avatar_url}
                      alt={otherParticipant.display_name}
                      fill
                      className="rounded-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-xs font-bold text-white">
                      {otherParticipant.display_name?.[0]?.toUpperCase() || '?'}
                    </div>
                  )}
                </div>
                <div className="rounded-2xl bg-muted px-4 py-2">
                  <div className="flex gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]"></span>
                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]"></span>
                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground"></span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <MessageInput
        onSend={sendMessage}
        onTyping={setTyping}
      />
    </div>
  );
}

function MessageBubble({ message, isOwn }: { message: Message; isOwn: boolean }) {
  const timeAgo = formatDistanceToNow(new Date(message.created_at), { addSuffix: true });
  const fullTime = format(new Date(message.created_at), 'PPp');

  return (
    <div className={cn('flex items-start gap-2', isOwn && 'flex-row-reverse')}>
      {/* Avatar */}
      {!isOwn && (
        <div className="relative h-8 w-8 rounded-full bg-muted flex-shrink-0">
          {message.sender.avatar_url ? (
            <Image
              src={message.sender.avatar_url}
              alt={message.sender.display_name}
              fill
              className="rounded-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-xs font-bold text-white">
              {message.sender.display_name?.[0]?.toUpperCase() || '?'}
            </div>
          )}
        </div>
      )}

      {/* Message Content */}
      <div className={cn('flex flex-col gap-1', isOwn && 'items-end')}>
        <div
          className={cn(
            'max-w-[70%] rounded-2xl px-4 py-2',
            isOwn
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-foreground'
          )}
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>

          {/* Attachments */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="mt-2 space-y-2">
              {message.attachments.map((attachment, index) => (
                <AttachmentPreview key={index} attachment={attachment} />
              ))}
            </div>
          )}
        </div>

        <span className="px-2 text-xs text-muted-foreground" title={fullTime}>
          {timeAgo}
        </span>
      </div>
    </div>
  );
}

function AttachmentPreview({ attachment }: { attachment: any }) {
  const isImage = attachment.type.startsWith('image/');

  if (isImage) {
    return (
      <a
        href={attachment.url}
        target="_blank"
        rel="noopener noreferrer"
        className="block"
      >
        <img
          src={attachment.url}
          alt={attachment.filename}
          className="max-w-full rounded-lg border"
        />
      </a>
    );
  }

  return (
    <a
      href={attachment.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2 rounded-lg border bg-background/50 p-2 text-sm hover:bg-background"
    >
      <FileText className="h-4 w-4" />
      <span className="flex-1 truncate">{attachment.filename}</span>
      <ExternalLink className="h-4 w-4" />
    </a>
  );
}
