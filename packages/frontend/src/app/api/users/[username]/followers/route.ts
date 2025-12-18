/**
 * API Route: /api/users/[username]/followers
 *
 * GET: Fetch list of users who follow this user
 */

import { NextRequest, NextResponse } from 'next/server';
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
    const limit = parseInt(searchParams.get('limit') || '50');

    // Get user ID from username
    const { data: user, error: userError } = await supabase
      .from('user_profiles')
      .select('id')
      .eq('username', username)
      .single();

    if (userError || !user) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }

    // Fetch followers
    const { data: follows, error: followsError } = await supabase
      .from('user_follows')
      .select(`
        id,
        follower_id,
        created_at,
        follower:follower_id (
          id,
          username,
          display_name,
          avatar_url,
          bio,
          followers_count,
          following_count,
          posts_count,
          reputation_score
        )
      `)
      .eq('following_id', user.id)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (followsError) {
      console.error('Error fetching followers:', followsError);
      return NextResponse.json(
        { error: 'Failed to fetch followers' },
        { status: 500 }
      );
    }

    // Extract follower profiles
    const followers = follows?.map((f: any) => ({
      ...f.follower,
      followed_at: f.created_at,
    })) || [];

    return NextResponse.json({
      followers,
      count: followers.length,
    });
  } catch (error) {
    console.error('Error in GET /api/users/[username]/followers:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
