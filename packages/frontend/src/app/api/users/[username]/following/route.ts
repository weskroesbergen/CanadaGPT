/**
 * API Route: /api/users/[username]/following
 *
 * GET: Fetch list of users that this user follows
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

    // Fetch following
    const { data: follows, error: followsError } = await supabase
      .from('user_follows')
      .select(`
        id,
        following_id,
        created_at,
        following:following_id (
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
      .eq('follower_id', user.id)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (followsError) {
      console.error('Error fetching following:', followsError);
      return NextResponse.json(
        { error: 'Failed to fetch following' },
        { status: 500 }
      );
    }

    // Extract following profiles
    const following = follows?.map((f: any) => ({
      ...f.following,
      followed_at: f.created_at,
    })) || [];

    return NextResponse.json({
      following,
      count: following.length,
    });
  } catch (error) {
    console.error('Error in GET /api/users/[username]/following:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
