/**
 * API Route: /api/users/search
 *
 * GET: Search users by username, display_name, or bio
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const query = searchParams.get('q');
    const limit = parseInt(searchParams.get('limit') || '10');

    if (!query || query.trim().length === 0) {
      return NextResponse.json(
        { error: 'Query parameter required' },
        { status: 400 }
      );
    }

    if (limit < 1 || limit > 50) {
      return NextResponse.json(
        { error: 'Limit must be between 1 and 50' },
        { status: 400 }
      );
    }

    // Search users by username, display_name, or bio
    // Case-insensitive search using ILIKE
    const searchTerm = `%${query.trim()}%`;

    const { data: users, error } = await supabase
      .from('user_profiles')
      .select(`
        id,
        username,
        display_name,
        avatar_url,
        bio,
        followers_count,
        following_count,
        posts_count,
        reputation_score,
        profile_visibility
      `)
      .or(`username.ilike.${searchTerm},display_name.ilike.${searchTerm},bio.ilike.${searchTerm}`)
      .not('username', 'is', null) // Only include users with usernames
      .order('followers_count', { ascending: false })
      .limit(limit);

    if (error) {
      console.error('Error searching users:', error);
      return NextResponse.json(
        { error: 'Failed to search users' },
        { status: 500 }
      );
    }

    // Filter out private profiles (unless it's the user themselves searching)
    const filteredUsers = users?.filter(user => user.profile_visibility !== 'private') || [];

    return NextResponse.json({
      users: filteredUsers,
      count: filteredUsers.length,
      query: query.trim(),
    });
  } catch (error) {
    console.error('Error in GET /api/users/search:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
