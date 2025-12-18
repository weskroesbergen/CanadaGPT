/**
 * useBillChatSummary Hook
 *
 * Automatically loads or generates AI bill summary when chatbot is open on a bill page.
 * Runs as a system action (doesn't count against user quota).
 */

import { useEffect, useRef } from 'react';
import { useChatStore } from '@/lib/stores/chatStore';
import { useAuth } from '@/contexts/AuthContext';

interface BillChatSummaryProps {
  billNumber: string;
  session: string;
  billTitle: string;
  billType?: string;
  sponsor?: {
    name: string;
    party?: string;
  };
  votes?: any[];
  debates?: any[];
  lobbying?: {
    organizations_lobbying: number;
  };
}

export function useBillChatSummary({
  billNumber,
  session,
  billTitle,
  billType,
  sponsor,
  votes,
  debates,
  lobbying,
}: BillChatSummaryProps) {
  const { user } = useAuth();
  const isOpen = useChatStore((state) => state.isOpen);
  const messages = useChatStore((state) => state.messages);
  const addMessage = useChatStore((state) => state.addMessage);
  const conversation = useChatStore((state) => state.conversation);
  const createConversation = useChatStore((state) => state.createConversation);

  // Track if we've already loaded the summary for this bill
  const hasLoadedSummary = useRef(false);
  const currentBillKey = `${session}/${billNumber}`;
  const billKeyRef = useRef(currentBillKey);

  useEffect(() => {
    // Reset if we navigated to a different bill
    if (billKeyRef.current !== currentBillKey) {
      hasLoadedSummary.current = false;
      billKeyRef.current = currentBillKey;
    }

    // Only run if:
    // 1. User is authenticated
    // 2. Chat is open
    // 3. We haven't already loaded summary for this bill
    // 4. We have valid bill data
    if (!user || !isOpen || hasLoadedSummary.current || !billNumber || !session || !billTitle) {
      return;
    }

    const loadOrGenerateSummary = async () => {
      try {
        // Mark as loaded immediately to prevent duplicate requests
        hasLoadedSummary.current = true;

        // Ensure we have a conversation
        if (!conversation) {
          await createConversation({
            type: 'bill',
            id: `${session}/${billNumber}`,
            data: {
              name: billTitle,
              session,
              number: billNumber,
            },
          });
        }

        // Validate we have required data
        if (!session || !billNumber || !billTitle) {
          // Don't log error - this is expected during initial render
          hasLoadedSummary.current = false;
          return;
        }

        // Check if summary already exists
        const getSummaryResponse = await fetch(`/api/bills/${encodeURIComponent(session)}/${encodeURIComponent(billNumber)}/summary`, {
          method: 'GET',
        });

        let summary: string;

        if (getSummaryResponse.ok) {
          // Summary exists, use it
          const data = await getSummaryResponse.json();
          summary = data.summary;
        } else {
          // Summary doesn't exist, generate it (as system action)
          const generateResponse = await fetch(`/api/bills/${encodeURIComponent(session)}/${encodeURIComponent(billNumber)}/summary`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              billTitle,
              billType,
              sponsor,
              votes,
              debates,
              lobbying,
              is_system_action: true, // Flag to indicate this doesn't count against quota
            }),
          });

          if (!generateResponse.ok) {
            console.error('Failed to generate summary for chat:', await generateResponse.text());
            hasLoadedSummary.current = false; // Allow retry
            return;
          }

          const data = await generateResponse.json();
          summary = data.summary;
        }

        // Add summary as assistant message to chat
        // Wait a moment to ensure conversation is created
        setTimeout(() => {
          const currentConversation = useChatStore.getState().conversation;
          if (currentConversation) {
            addMessage({
              id: crypto.randomUUID(),
              conversation_id: currentConversation.id,
              role: 'assistant',
              content: `**Bill ${billNumber} Summary**\n\n${summary}\n\n---\n\nI can help you understand this bill better. Feel free to ask me questions about its purpose, impact, or current status.`,
              used_byo_key: false,
              created_at: new Date().toISOString(),
            });
          }
        }, 500);

      } catch (error) {
        console.error('Error loading/generating bill summary for chat:', error);
        hasLoadedSummary.current = false; // Allow retry
      }
    };

    loadOrGenerateSummary();
  }, [
    user,
    isOpen,
    billNumber,
    session,
    billTitle,
    billType,
    sponsor,
    votes,
    debates,
    lobbying,
    conversation,
    createConversation,
    addMessage,
    currentBillKey,
  ]);

  // Reset when chat closes
  useEffect(() => {
    if (!isOpen) {
      hasLoadedSummary.current = false;
    }
  }, [isOpen]);
}
