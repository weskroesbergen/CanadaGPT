/**
 * API Route: /api/users/[username]/follow
 *
 * POST: Follow a user
 * DELETE: Unfollow a user
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
  { params }: { params: Promise<{ username: string }> }
) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { username } = await params;

    // Get target user by username
    const { data: targetUser, error: userError } = await supabase
      .from('user_profiles')
      .select('id, username, display_name, avatar_url, allow_messages_from')
      .eq('username', username)
      .single();

    if (userError || !targetUser) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }

    // Prevent self-follow
    if (targetUser.id === session.user.id) {
      return NextResponse.json(
        { error: 'Cannot follow yourself' },
        { status: 400 }
      );
    }

    // Check if already following
    const { data: existing } = await supabase
      .from('user_follows')
      .select('id')
      .eq('follower_id', session.user.id)
      .eq('following_id', targetUser.id)
      .single();

    if (existing) {
      return NextResponse.json(
        { error: 'Already following this user' },
        { status: 400 }
      );
    }

    // Create follow relationship
    const { error: followError } = await supabase
      .from('user_follows')
      .insert({
        follower_id: session.user.id,
        following_id: targetUser.id,
      });

    if (followError) {
      console.error('Error creating follow:', followError);
      return NextResponse.json(
        { error: 'Failed to follow user' },
        { status: 500 }
      );
    }

    // Create notification for followed user
    const { data: followerProfile } = await supabase
      .from('user_profiles')
      .select('display_name, avatar_url, username')
      .eq('id', session.user.id)
      .single();

    // Note: We'll implement notifications table in Phase 3
    // For now, just return success

    return NextResponse.json({
      success: true,
      action: 'followed',
      targetUser: {
        id: targetUser.id,
        username: targetUser.username,
        display_name: targetUser.display_name,
      },
    });
  } catch (error) {
    console.error('Error in POST /api/users/[username]/follow:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ username: string }> }
) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { username } = await params;

    // Get target user by username
    const { data: targetUser, error: userError } = await supabase
      .from('user_profiles')
      .select('id')
      .eq('username', username)
      .single();

    if (userError || !targetUser) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }

    // Delete follow relationship
    const { error: unfollowError } = await supabase
      .from('user_follows')
      .delete()
      .eq('follower_id', session.user.id)
      .eq('following_id', targetUser.id);

    if (unfollowError) {
      console.error('Error deleting follow:', unfollowError);
      return NextResponse.json(
        { error: 'Failed to unfollow user' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      action: 'unfollowed',
      targetUser: {
        id: targetUser.id,
        username: username,
      },
    });
  } catch (error) {
    console.error('Error in DELETE /api/users/[username]/follow:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
