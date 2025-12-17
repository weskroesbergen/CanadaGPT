/**
 * API Route: /api/messages/conversations/[conversationId]
 *
 * GET: Fetch messages in a conversation
 * POST: Send a new message
 */

import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function GET(
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
    const searchParams = request.nextUrl.searchParams;
    const limit = parseInt(searchParams.get('limit') || '50');
    const before = searchParams.get('before'); // For pagination

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

    // Build query
    let query = supabase
      .from('direct_messages')
      .select(`
        id,
        sender_id,
        recipient_id,
        content,
        attachments,
        is_read,
        read_at,
        created_at,
        sender:sender_id (
          id,
          username,
          display_name,
          avatar_url
        )
      `)
      .eq('conversation_id', conversationId)
      .order('created_at', { ascending: false })
      .limit(limit);

    // Pagination: fetch messages before a certain timestamp
    if (before) {
      query = query.lt('created_at', before);
    }

    const { data: messages, error: messagesError } = await query;

    if (messagesError) {
      console.error('Error fetching messages:', messagesError);
      return NextResponse.json(
        { error: 'Failed to fetch messages' },
        { status: 500 }
      );
    }

    // Reverse to show oldest first
    const orderedMessages = (messages || []).reverse();

    return NextResponse.json({
      messages: orderedMessages,
      count: orderedMessages.length,
      hasMore: (messages || []).length === limit,
    });
  } catch (error) {
    console.error('Error in GET /api/messages/conversations/[conversationId]:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

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
    const body = await request.json();
    const { content, attachments = [] } = body;

    // Validate content
    if (!content || content.trim().length === 0) {
      return NextResponse.json(
        { error: 'Message content is required' },
        { status: 400 }
      );
    }

    if (content.length > 5000) {
      return NextResponse.json(
        { error: 'Message too long (max 5000 characters)' },
        { status: 400 }
      );
    }

    // Verify user is participant and get other participant
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

    // Determine sender and recipient
    let recipientId: string;
    if (conversation.participant1_id === session.user.id) {
      recipientId = conversation.participant2_id;
    } else if (conversation.participant2_id === session.user.id) {
      recipientId = conversation.participant1_id;
    } else {
      return NextResponse.json(
        { error: 'Access denied' },
        { status: 403 }
      );
    }

    // Create message
    const { data: message, error: messageError } = await supabase
      .from('direct_messages')
      .insert({
        conversation_id: conversationId,
        sender_id: session.user.id,
        recipient_id: recipientId,
        content: content.trim(),
        attachments,
      })
      .select(`
        id,
        sender_id,
        recipient_id,
        content,
        attachments,
        is_read,
        read_at,
        created_at,
        sender:sender_id (
          id,
          username,
          display_name,
          avatar_url
        )
      `)
      .single();

    if (messageError) {
      console.error('Error creating message:', messageError);
      return NextResponse.json(
        { error: 'Failed to send message' },
        { status: 500 }
      );
    }

    // Note: Conversation metadata (last_message_at, unread_count) is updated by database trigger

    return NextResponse.json({ message });
  } catch (error) {
    console.error('Error in POST /api/messages/conversations/[conversationId]:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
