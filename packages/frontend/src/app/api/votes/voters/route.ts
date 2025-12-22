/**
 * Entity Voters API Route
 *
 * GET /api/votes/voters - Get list of users who voted on an entity
 * Query params:
 *   - entity_type: 'bill' | 'mp' | 'statement'
 *   - entity_id: string
 *   - vote_type: 'upvote' | 'downvote' | undefined (all votes)
 *   - limit: number (default 50, max 100)
 *   - offset: number (default 0)
 */

import { createAdminClient } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

interface VoteRecord {
  id: string;
  user_id: string;
  vote_type: string;
  created_at: string;
}

interface UserProfile {
  id: string;
  username: string | null;
  display_name: string | null;
  full_name: string | null;
  avatar_url: string | null;
}

export async function GET(request: NextRequest) {
  try {
    const supabase = createAdminClient();

    // Parse query params
    const { searchParams } = new URL(request.url);
    const entity_type = searchParams.get('entity_type');
    const entity_id = searchParams.get('entity_id');
    const vote_type = searchParams.get('vote_type'); // Optional: 'upvote', 'downvote', or null for all
    const limit = Math.min(
      parseInt(searchParams.get('limit') || '50', 10),
      100
    );
    const offset = parseInt(searchParams.get('offset') || '0', 10);

    // Validate required params
    if (!entity_type || !entity_id) {
      return NextResponse.json(
        { error: 'Missing required params: entity_type, entity_id' },
        { status: 400 }
      );
    }

    if (!['bill', 'mp', 'statement'].includes(entity_type)) {
      return NextResponse.json(
        { error: 'Invalid entity_type. Must be: bill, mp, or statement' },
        { status: 400 }
      );
    }

    if (vote_type && !['upvote', 'downvote'].includes(vote_type)) {
      return NextResponse.json(
        { error: 'Invalid vote_type. Must be: upvote or downvote' },
        { status: 400 }
      );
    }

    // Query 1: Get votes from entity_votes (with count for pagination)
    let votesQuery = supabase
      .from('entity_votes')
      .select('id, user_id, vote_type, created_at', { count: 'exact' })
      .eq('entity_type', entity_type)
      .eq('entity_id', entity_id)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    // Filter by vote type if specified
    if (vote_type) {
      votesQuery = votesQuery.eq('vote_type', vote_type);
    }

    const { data: votesData, error: votesError, count } = await votesQuery;

    if (votesError) {
      console.error('Error fetching votes:', votesError);
      return NextResponse.json(
        { error: 'Failed to fetch votes' },
        { status: 500 }
      );
    }

    if (!votesData || votesData.length === 0) {
      return NextResponse.json({
        voters: [],
        total_count: 0,
        has_more: false,
        pagination: {
          limit,
          offset,
          next_offset: null,
        },
      });
    }

    // Query 2: Get user profiles for all user_ids
    const userIds = [...new Set((votesData as VoteRecord[]).map((vote: VoteRecord) => vote.user_id))];

    const { data: profiles, error: profilesError } = await supabase
      .from('user_profiles')
      .select('id, username, display_name, full_name, avatar_url')
      .in('id', userIds);

    if (profilesError) {
      console.error('Error fetching user profiles:', profilesError);
      return NextResponse.json(
        { error: 'Failed to fetch user profiles' },
        { status: 500 }
      );
    }

    // Create a map of user profiles for quick lookup
    const profileMap = new Map<string, UserProfile>(
      ((profiles || []) as UserProfile[]).map((profile: UserProfile) => [profile.id, profile])
    );

    // Join votes with user profiles in application code
    const voters = (votesData as VoteRecord[]).map((vote: VoteRecord) => {
      const profile = profileMap.get(vote.user_id);
      return {
        user_id: vote.user_id,
        username: profile?.username || null,
        display_name: profile?.display_name || null,
        full_name: profile?.full_name || null,
        avatar_url: profile?.avatar_url || null,
        vote_type: vote.vote_type,
        voted_at: vote.created_at,
      };
    });

    const total = count || 0;
    const has_more = offset + limit < total;

    return NextResponse.json({
      voters: voters || [],
      total_count: total,
      has_more,
      pagination: {
        limit,
        offset,
        next_offset: has_more ? offset + limit : null,
      },
    });
  } catch (error) {
    console.error('Error in GET /api/votes/voters:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
