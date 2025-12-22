/**
 * API Route: /api/messages/conversations/[conversationId]/read
 *
 * POST: Mark messages as read
 */

import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ conversationId: string }> }
) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { conversationId } = await params;

    // Verify user is participant in conversation
    const { data: conversation, error: convError } = await supabase
      .from('conversations')
      .select('participant1_id, participant2_id')
      .eq('id', conversationId)
      .single();

    if (convError || !conversation) {
      return NextResponse.json(
        { error: 'Conversation not found' },
        { status: 404 }
      );
    }

    if (
      conversation.participant1_id !== session.user.id &&
      conversation.participant2_id !== session.user.id
    ) {
      return NextResponse.json(
        { error: 'Access denied' },
        { status: 403 }
      );
    }

    // Use helper function to mark messages as read
    const { data: markedCount, error: markError } = await supabase.rpc(
      'mark_messages_read',
      {
        conv_id: conversationId,
        reader_id: session.user.id,
      }
    );

    if (markError) {
      console.error('Error marking messages as read:', markError);
      return NextResponse.json(
        { error: 'Failed to mark messages as read' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      marked_count: markedCount || 0,
    });
  } catch (error) {
    console.error('Error in POST /api/messages/conversations/[conversationId]/read:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
