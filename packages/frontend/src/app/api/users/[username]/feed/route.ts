/**
 * API Route: /api/users/[username]/feed
 *
 * GET: Fetch user's activity feed
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
  { params }: { params: Promise<{ username: string }> }
) {
  try {
    const { username } = await params;
    const searchParams = request.nextUrl.searchParams;
    const limit = parseInt(searchParams.get('limit') || '20');
    const offset = parseInt(searchParams.get('offset') || '0');

    // Get target user by username
    const { data: targetUser, error: userError } = await supabase
      .from('user_profiles')
      .select('id, username, activity_feed_visibility')
      .eq('username', username)
      .single();

    if (userError || !targetUser) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }

    // Check permissions
    const session = await auth();
    const currentUserId = session?.user?.id;

    // If feed is private, only owner can view
    if (targetUser.activity_feed_visibility === 'private' && currentUserId !== targetUser.id) {
      return NextResponse.json(
        { error: 'Activity feed is private' },
        { status: 403 }
      );
    }

    // If feed is followers-only, check if current user follows
    if (targetUser.activity_feed_visibility === 'followers' && currentUserId !== targetUser.id) {
      if (!currentUserId) {
        return NextResponse.json(
          { error: 'Must be logged in to view this feed' },
          { status: 401 }
        );
      }

      const { data: follows } = await supabase
        .from('user_follows')
        .select('id')
        .eq('follower_id', currentUserId)
        .eq('following_id', targetUser.id)
        .single();

      if (!follows) {
        return NextResponse.json(
          { error: 'You must follow this user to view their activity' },
          { status: 403 }
        );
      }
    }

    // Fetch activity feed events
    const { data: events, error: eventsError, count } = await supabase
      .from('activity_feed_events')
      .select('*', { count: 'exact' })
      .eq('user_id', targetUser.id)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (eventsError) {
      console.error('Error fetching activity feed:', eventsError);
      return NextResponse.json(
        { error: 'Failed to fetch activity feed' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      events: events || [],
      count: count || 0,
      hasMore: (count || 0) > offset + limit,
      user: {
        id: targetUser.id,
        username: targetUser.username,
      },
    });
  } catch (error) {
    console.error('Error in GET /api/users/[username]/feed:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
