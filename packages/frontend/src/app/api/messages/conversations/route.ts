/**
 * API Route: /api/messages/conversations
 *
 * GET: List user's conversations
 * POST: Create or get existing conversation with a user
 */

import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function GET(request: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const userId = session.user.id;
    const searchParams = request.nextUrl.searchParams;
    const limit = parseInt(searchParams.get('limit') || '50');

    // Fetch conversations where user is a participant
    const { data: conversations, error } = await supabase
      .from('conversations')
      .select(`
        id,
        participant1_id,
        participant2_id,
        last_message_at,
        last_message_preview,
        participant1_archived,
        participant2_archived,
        participant1_unread_count,
        participant2_unread_count,
        created_at,
        participant1:participant1_id (
          id,
          username,
          display_name,
          avatar_url
        ),
        participant2:participant2_id (
          id,
          username,
          display_name,
          avatar_url
        )
      `)
      .or(`participant1_id.eq.${userId},participant2_id.eq.${userId}`)
      .order('last_message_at', { ascending: false })
      .limit(limit);

    if (error) {
      console.error('Error fetching conversations:', error);
      return NextResponse.json(
        { error: 'Failed to fetch conversations' },
        { status: 500 }
      );
    }

    // Format conversations with other participant info and unread count
    const formattedConversations = conversations?.map((conv: any) => {
      const isParticipant1 = conv.participant1_id === userId;
      const otherParticipant = isParticipant1 ? conv.participant2 : conv.participant1;
      const unreadCount = isParticipant1
        ? conv.participant1_unread_count
        : conv.participant2_unread_count;
      const isArchived = isParticipant1
        ? conv.participant1_archived
        : conv.participant2_archived;

      return {
        id: conv.id,
        other_participant: otherParticipant,
        last_message_at: conv.last_message_at,
        last_message_preview: conv.last_message_preview,
        unread_count: unreadCount,
        is_archived: isArchived,
        created_at: conv.created_at,
      };
    }) || [];

    return NextResponse.json({
      conversations: formattedConversations,
      count: formattedConversations.length,
    });
  } catch (error) {
    console.error('Error in GET /api/messages/conversations:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { targetUserId } = body;

    if (!targetUserId) {
      return NextResponse.json(
        { error: 'targetUserId is required' },
        { status: 400 }
      );
    }

    // Prevent messaging yourself
    if (targetUserId === session.user.id) {
      return NextResponse.json(
        { error: 'Cannot message yourself' },
        { status: 400 }
      );
    }

    // Check if target user exists
    const { data: targetUser, error: userError } = await supabase
      .from('user_profiles')
      .select('id, username, display_name, avatar_url, allow_messages_from')
      .eq('id', targetUserId)
      .single();

    if (userError || !targetUser) {
      return NextResponse.json(
        { error: 'Target user not found' },
        { status: 404 }
      );
    }

    // Check messaging permissions
    if (targetUser.allow_messages_from === 'nobody') {
      return NextResponse.json(
        { error: 'This user has disabled messages' },
        { status: 403 }
      );
    }

    if (targetUser.allow_messages_from === 'followers') {
      // Check if current user follows target
      const { data: follow } = await supabase
        .from('user_follows')
        .select('id')
        .eq('follower_id', session.user.id)
        .eq('following_id', targetUserId)
        .single();

      if (!follow) {
        return NextResponse.json(
          { error: 'You must follow this user to send them messages' },
          { status: 403 }
        );
      }
    }

    // Use helper function to get or create conversation
    const { data: convId, error: convError } = await supabase.rpc(
      'get_or_create_conversation',
      {
        user1_id: session.user.id,
        user2_id: targetUserId,
      }
    );

    if (convError) {
      console.error('Error creating conversation:', convError);
      return NextResponse.json(
        { error: 'Failed to create conversation' },
        { status: 500 }
      );
    }

    // Fetch the conversation with participant info
    const { data: conversation, error: fetchError } = await supabase
      .from('conversations')
      .select(`
        id,
        participant1_id,
        participant2_id,
        last_message_at,
        last_message_preview,
        participant1_unread_count,
        participant2_unread_count,
        created_at,
        participant1:participant1_id (
          id,
          username,
          display_name,
          avatar_url
        ),
        participant2:participant2_id (
          id,
          username,
          display_name,
          avatar_url
        )
      `)
      .eq('id', convId)
      .single();

    if (fetchError || !conversation) {
      console.error('Error fetching conversation:', fetchError);
      return NextResponse.json(
        { error: 'Failed to fetch conversation' },
        { status: 500 }
      );
    }

    // Format response
    const isParticipant1 = conversation.participant1_id === session.user.id;
    const otherParticipant = isParticipant1
      ? conversation.participant2
      : conversation.participant1;

    return NextResponse.json({
      conversation: {
        id: conversation.id,
        other_participant: otherParticipant,
        last_message_at: conversation.last_message_at,
        last_message_preview: conversation.last_message_preview,
        unread_count: isParticipant1
          ? conversation.participant1_unread_count
          : conversation.participant2_unread_count,
        created_at: conversation.created_at,
      },
    });
  } catch (error) {
    console.error('Error in POST /api/messages/conversations:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
