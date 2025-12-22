/**
 * Entity Voting API Routes
 *
 * POST /api/votes - Create, toggle, or switch vote
 * GET /api/votes - Batch query for vote counts and user votes
 */

import { createServerClient, createAdminClient } from '@/lib/supabase-server';
import { auth } from '@/auth';
import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

// Vote types
type VoteType = 'upvote' | 'downvote';
type EntityType = 'bill' | 'mp' | 'statement';

interface VoteRequest {
  entity_type: EntityType;
  entity_id: string;
  vote_type: VoteType;
}

interface VoteData {
  entity_id: string;
  upvotes: number;
  downvotes: number;
  net_score: number;
  user_vote: VoteType | null;
}

/**
 * POST /api/votes
 * Create, toggle, or switch a vote
 */
export async function POST(request: NextRequest) {
  try {
    // Check authentication using NextAuth
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = session.user.id;
    const supabase = createAdminClient();

    // Parse request body
    const body = (await request.json()) as VoteRequest;
    const { entity_type, entity_id, vote_type } = body;

    // Validate input
    if (!entity_type || !entity_id || !vote_type) {
      return NextResponse.json(
        { error: 'Missing required fields: entity_type, entity_id, vote_type' },
        { status: 400 }
      );
    }

    if (!['bill', 'mp', 'statement'].includes(entity_type)) {
      return NextResponse.json(
        { error: 'Invalid entity_type. Must be: bill, mp, or statement' },
        { status: 400 }
      );
    }

    if (!['upvote', 'downvote'].includes(vote_type)) {
      return NextResponse.json(
        { error: 'Invalid vote_type. Must be: upvote or downvote' },
        { status: 400 }
      );
    }

    // Check for existing vote
    const { data: existingVote, error: fetchError } = await supabase
      .from('entity_votes')
      .select('id, vote_type')
      .eq('user_id', userId)
      .eq('entity_type', entity_type)
      .eq('entity_id', entity_id)
      .maybeSingle();

    if (fetchError) {
      console.error('Error fetching existing vote:', fetchError);
      return NextResponse.json(
        { error: 'Failed to check existing vote' },
        { status: 500 }
      );
    }

    let action: 'created' | 'deleted' | 'updated';

    if (existingVote) {
      if (existingVote.vote_type === vote_type) {
        // Same vote type → Toggle off (DELETE)
        const { error: deleteError } = await supabase
          .from('entity_votes')
          .delete()
          .eq('id', existingVote.id);

        if (deleteError) {
          console.error('Error deleting vote:', deleteError);
          return NextResponse.json(
            { error: 'Failed to remove vote' },
            { status: 500 }
          );
        }

        action = 'deleted';
      } else {
        // Different vote type → Switch (UPDATE)
        const { error: updateError } = await supabase
          .from('entity_votes')
          .update({
            vote_type,
            updated_at: new Date().toISOString(),
          })
          .eq('id', existingVote.id);

        if (updateError) {
          console.error('Error updating vote:', updateError);
          return NextResponse.json(
            { error: 'Failed to update vote' },
            { status: 500 }
          );
        }

        action = 'updated';
      }
    } else {
      // No existing vote → Create new (INSERT)
      const { error: insertError } = await supabase.from('entity_votes').insert({
        user_id: userId,
        entity_type,
        entity_id,
        vote_type,
      });

      if (insertError) {
        console.error('Error creating vote:', insertError);
        return NextResponse.json(
          { error: 'Failed to create vote' },
          { status: 500 }
        );
      }

      action = 'created';
    }

    // Fetch updated vote counts
    const { data: counts, error: countsError } = await supabase
      .from('entity_vote_counts')
      .select('upvotes_count, downvotes_count, net_score')
      .eq('entity_type', entity_type)
      .eq('entity_id', entity_id)
      .maybeSingle();

    if (countsError) {
      console.error('Error fetching vote counts:', countsError);
    }

    // Fetch user's current vote status
    const { data: currentVote } = await supabase
      .from('entity_votes')
      .select('vote_type')
      .eq('user_id', userId)
      .eq('entity_type', entity_type)
      .eq('entity_id', entity_id)
      .maybeSingle();

    return NextResponse.json({
      success: true,
      action,
      upvotes: counts?.upvotes_count || 0,
      downvotes: counts?.downvotes_count || 0,
      net_score: counts?.net_score || 0,
      user_vote: currentVote?.vote_type || null,
    });
  } catch (error) {
    console.error('Error in POST /api/votes:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * GET /api/votes
 * Batch query for vote counts and user's votes
 * Query params: ?entity_type=bill&entity_ids=45-1-C-2,45-1-C-3
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = createAdminClient();

    // Parse query params
    const { searchParams } = new URL(request.url);
    const entity_type = searchParams.get('entity_type');
    const entity_ids_param = searchParams.get('entity_ids');

    // Validate input
    if (!entity_type || !entity_ids_param) {
      return NextResponse.json(
        { error: 'Missing required params: entity_type, entity_ids' },
        { status: 400 }
      );
    }

    if (!['bill', 'mp', 'statement'].includes(entity_type)) {
      return NextResponse.json(
        { error: 'Invalid entity_type. Must be: bill, mp, or statement' },
        { status: 400 }
      );
    }

    // Parse entity IDs
    const entity_ids = entity_ids_param.split(',').filter(Boolean);

    if (entity_ids.length === 0) {
      return NextResponse.json(
        { error: 'No entity_ids provided' },
        { status: 400 }
      );
    }

    // Batch query for vote counts using helper function
    const { data: counts, error: countsError } = await supabase.rpc(
      'get_entity_vote_counts',
      {
        p_entity_type: entity_type,
        p_entity_ids: entity_ids,
      }
    );

    if (countsError) {
      console.error('Error fetching vote counts:', countsError);
      return NextResponse.json(
        { error: 'Failed to fetch vote counts' },
        { status: 500 }
      );
    }

    // Check if user is authenticated using NextAuth
    const session = await auth();

    // If authenticated, batch query for user's votes
    let userVotes: { entity_id: string; vote_type: VoteType }[] = [];
    if (session?.user?.id) {
      const { data: votes, error: votesError } = await supabase.rpc(
        'get_user_entity_votes',
        {
          p_user_id: session.user.id,
          p_entity_type: entity_type,
          p_entity_ids: entity_ids,
        }
      );

      if (votesError) {
        console.error('Error fetching user votes:', votesError);
        // Don't fail the request, just continue without user votes
      } else {
        userVotes = votes || [];
      }
    }

    // Create a map of user votes for quick lookup
    const userVoteMap = new Map(
      userVotes.map((v) => [v.entity_id, v.vote_type])
    );

    // Combine counts and user votes
    const votes: VoteData[] = entity_ids.map((entity_id) => {
      const count = counts?.find((c: any) => c.entity_id === entity_id);
      return {
        entity_id,
        upvotes: count?.upvotes_count || 0,
        downvotes: count?.downvotes_count || 0,
        net_score: count?.net_score || 0,
        user_vote: userVoteMap.get(entity_id) || null,
      };
    });

    return NextResponse.json({ votes });
  } catch (error) {
    console.error('Error in GET /api/votes:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
