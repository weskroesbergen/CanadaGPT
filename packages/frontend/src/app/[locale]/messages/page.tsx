/**
 * Messages Page
 *
 * Direct messaging interface
 * Route: /messages
 */

'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { ConversationsList, type Conversation } from '@/components/messages/ConversationsList';
import { MessageThread } from '@/components/messages/MessageThread';
import { useAuth } from '@/contexts/AuthContext';
import { MessageSquare } from 'lucide-react';

export default function MessagesPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [isCreatingConversation, setIsCreatingConversation] = useState(false);

  // Handle ?user=username query param (start conversation with user)
  useEffect(() => {
    const targetUsername = searchParams.get('user');
    if (targetUsername && user) {
      createOrGetConversation(targetUsername);
    }
  }, [searchParams, user]);

  const createOrGetConversation = async (username: string) => {
    setIsCreatingConversation(true);

    try {
      // First, get user ID from username
      const userResponse = await fetch(`/api/users/${username}`);
      if (!userResponse.ok) {
        throw new Error('User not found');
      }

      const userData = await userResponse.json();
      const targetUserId = userData.profile.id;

      // Create or get conversation
      const response = await fetch('/api/messages/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ targetUserId }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to create conversation');
      }

      const data = await response.json();
      setSelectedConversation(data.conversation);
    } catch (error) {
      console.error('Error creating conversation:', error);
    } finally {
      setIsCreatingConversation(false);
    }
  };

  if (!user) {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
        <div className="text-center">
          <MessageSquare className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
          <h2 className="mb-2 text-xl font-semibold">Sign in to view messages</h2>
          <p className="text-muted-foreground">
            You need to be signed in to access your messages
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)]">
      {/* Mobile: Show either list or thread */}
      <div className="md:hidden h-full">
        {selectedConversation ? (
          <div className="h-full">
            <button
              onClick={() => setSelectedConversation(null)}
              className="w-full border-b p-4 text-left text-sm text-muted-foreground hover:bg-muted"
            >
              ← Back to conversations
            </button>
            <div className="h-[calc(100%-57px)]">
              <MessageThread
                conversationId={selectedConversation.id}
                otherParticipant={selectedConversation.other_participant}
              />
            </div>
          </div>
        ) : (
          <ConversationsList
            selectedConversationId={undefined}
            onSelectConversation={setSelectedConversation}
          />
        )}
      </div>

      {/* Desktop: Two-column layout */}
      <div className="hidden md:grid md:grid-cols-[350px_1fr] h-full border-t">
        {/* Conversations List */}
        <div className="border-r">
          <ConversationsList
            selectedConversationId={selectedConversation?.id}
            onSelectConversation={setSelectedConversation}
          />
        </div>

        {/* Message Thread */}
        <div className="h-full">
          {selectedConversation ? (
            <MessageThread
              conversationId={selectedConversation.id}
              otherParticipant={selectedConversation.other_participant}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-center text-muted-foreground">
              <div>
                <MessageSquare className="mx-auto mb-4 h-12 w-12" />
                <p>Select a conversation to start messaging</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
