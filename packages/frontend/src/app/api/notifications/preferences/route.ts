/**
 * API Route: /api/notifications/preferences
 *
 * GET: Fetch user's notification preferences
 * PATCH: Update notification preferences
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

    // Get or create preferences
    let { data: preferences, error } = await supabase
      .from('notification_preferences')
      .select('*')
      .eq('user_id', session.user.id)
      .maybeSingle();

    // If no preferences exist, create defaults
    if (!preferences) {
      const { data: newPreferences, error: createError } = await supabase
        .from('notification_preferences')
        .insert({ user_id: session.user.id })
        .select()
        .single();

      if (createError) {
        console.error('Error creating preferences:', createError);
        return NextResponse.json(
          { error: 'Failed to create preferences' },
          { status: 500 }
        );
      }

      preferences = newPreferences;
    }

    if (error) {
      console.error('Error fetching preferences:', error);
      return NextResponse.json(
        { error: 'Failed to fetch preferences' },
        { status: 500 }
      );
    }

    return NextResponse.json({ preferences });
  } catch (error) {
    console.error('Error in GET /api/notifications/preferences:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const {
      email_enabled,
      push_enabled,
      in_app_enabled,
      notify_new_messages,
      notify_new_followers,
      notify_mentions,
      notify_replies,
      notify_likes,
      notify_comments,
      email_digest_frequency,
    } = body;

    // Build update object with only provided fields
    const updates: Record<string, any> = {};
    if (email_enabled !== undefined) updates.email_enabled = email_enabled;
    if (push_enabled !== undefined) updates.push_enabled = push_enabled;
    if (in_app_enabled !== undefined) updates.in_app_enabled = in_app_enabled;
    if (notify_new_messages !== undefined) updates.notify_new_messages = notify_new_messages;
    if (notify_new_followers !== undefined) updates.notify_new_followers = notify_new_followers;
    if (notify_mentions !== undefined) updates.notify_mentions = notify_mentions;
    if (notify_replies !== undefined) updates.notify_replies = notify_replies;
    if (notify_likes !== undefined) updates.notify_likes = notify_likes;
    if (notify_comments !== undefined) updates.notify_comments = notify_comments;
    if (email_digest_frequency !== undefined) updates.email_digest_frequency = email_digest_frequency;

    // Upsert preferences
    const { data: preferences, error } = await supabase
      .from('notification_preferences')
      .upsert({
        user_id: session.user.id,
        ...updates,
      })
      .select()
      .single();

    if (error) {
      console.error('Error updating preferences:', error);
      return NextResponse.json(
        { error: 'Failed to update preferences' },
        { status: 500 }
      );
    }

    return NextResponse.json({ preferences });
  } catch (error) {
    console.error('Error in PATCH /api/notifications/preferences:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
