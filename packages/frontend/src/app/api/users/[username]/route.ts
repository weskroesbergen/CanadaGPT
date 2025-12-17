/**
 * API Route: /api/users/[username]
 *
 * GET: Fetch user profile by username
 * PATCH: Update own profile
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

    // Fetch user profile by username
    const { data: profile, error } = await supabase
      .from('user_profiles')
      .select(`
        id,
        username,
        display_name,
        avatar_url,
        bio,
        location,
        website_url,
        cover_image_url,
        followers_count,
        following_count,
        posts_count,
        replies_count,
        reputation_score,
        profile_visibility,
        activity_feed_visibility,
        party_affiliation,
        party_affiliation_visibility,
        created_at
      `)
      .eq('username', username)
      .single();

    if (error || !profile) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }

    // Check if current user can view this profile
    const session = await auth();
    const currentUserId = session?.user?.id;

    // If profile is private, only owner can view
    if (profile.profile_visibility === 'private' && currentUserId !== profile.id) {
      return NextResponse.json(
        { error: 'Profile is private' },
        { status: 403 }
      );
    }

    // If profile is followers-only, check if current user follows
    if (profile.profile_visibility === 'followers' && currentUserId !== profile.id) {
      const { data: follows } = await supabase
        .from('user_follows')
        .select('id')
        .eq('follower_id', currentUserId)
        .eq('following_id', profile.id)
        .single();

      if (!follows) {
        return NextResponse.json(
          { error: 'You must follow this user to view their profile' },
          { status: 403 }
        );
      }
    }

    // Check if current user follows this user
    let isFollowing = false;
    if (currentUserId && currentUserId !== profile.id) {
      const { data: follow } = await supabase
        .from('user_follows')
        .select('id')
        .eq('follower_id', currentUserId)
        .eq('following_id', profile.id)
        .single();
      isFollowing = !!follow;
    }

    // Get mutual followers count if logged in
    let mutualFollowers = 0;
    if (currentUserId && currentUserId !== profile.id) {
      // First get the profile's followers
      const { data: profileFollowers } = await supabase
        .from('user_follows')
        .select('follower_id')
        .eq('following_id', profile.id);

      if (profileFollowers && profileFollowers.length > 0) {
        const followerIds = profileFollowers.map((f) => f.follower_id);

        // Then count how many of those the current user also follows
        const { count } = await supabase
          .from('user_follows')
          .select('*', { count: 'exact', head: true })
          .eq('follower_id', currentUserId)
          .in('following_id', followerIds);
        mutualFollowers = count || 0;
      }
    }

    // Determine if current user can view party affiliation
    let canViewPartyAffiliation = false;
    const isOwnProfile = currentUserId === profile.id;

    if (isOwnProfile) {
      // Profile owner can always see their own party affiliation
      canViewPartyAffiliation = true;
    } else if (profile.party_affiliation_visibility === 'public') {
      // Public: everyone can see
      canViewPartyAffiliation = true;
    } else if (profile.party_affiliation_visibility === 'followers' && isFollowing) {
      // Followers only: visible if current user follows
      canViewPartyAffiliation = true;
    }
    // Private: only owner can see (already handled by isOwnProfile check)

    return NextResponse.json({
      profile,
      isFollowing,
      mutualFollowers,
      isOwnProfile,
      canViewPartyAffiliation,
    });
  } catch (error) {
    console.error('Error fetching user profile:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function PATCH(
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

    // Verify user is updating their own profile
    const { data: existingProfile } = await supabase
      .from('user_profiles')
      .select('id, username')
      .eq('username', username)
      .single();

    if (!existingProfile || existingProfile.id !== session.user.id) {
      return NextResponse.json(
        { error: 'Forbidden: Can only update own profile' },
        { status: 403 }
      );
    }

    const body = await request.json();

    // Allowed fields to update
    const allowedFields = [
      'display_name',
      'bio',
      'location',
      'website_url',
      'avatar_url',
      'cover_image_url',
      'profile_visibility',
      'activity_feed_visibility',
      'allow_messages_from',
      'party_affiliation',
      'party_affiliation_visibility',
    ];

    // Filter to only allowed fields
    const updates: Record<string, any> = {};
    for (const field of allowedFields) {
      if (field in body) {
        updates[field] = body[field];
      }
    }

    // Validate fields
    if (updates.display_name && updates.display_name.length > 100) {
      return NextResponse.json(
        { error: 'Display name must be 100 characters or less' },
        { status: 400 }
      );
    }

    if (updates.bio && updates.bio.length > 500) {
      return NextResponse.json(
        { error: 'Bio must be 500 characters or less' },
        { status: 400 }
      );
    }

    if (updates.website_url && !isValidUrl(updates.website_url)) {
      return NextResponse.json(
        { error: 'Invalid website URL' },
        { status: 400 }
      );
    }

    // Update profile
    const { data: profile, error } = await supabase
      .from('user_profiles')
      .update(updates)
      .eq('id', session.user.id)
      .select()
      .single();

    if (error) {
      console.error('Error updating profile:', error);
      return NextResponse.json(
        { error: 'Failed to update profile' },
        { status: 500 }
      );
    }

    return NextResponse.json({ profile });
  } catch (error) {
    console.error('Error in PATCH /api/users/[username]:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// Helper function to validate URLs
function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}
