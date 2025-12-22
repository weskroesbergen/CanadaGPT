/**
 * API Route: /api/substack/profile
 *
 * GET: Fetch user's Substack profile
 * POST: Create/update Substack profile
 * DELETE: Remove Substack profile
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

    const { data: profile, error } = await supabase
      .from('user_substack_profiles')
      .select('*')
      .eq('user_id', session.user.id)
      .maybeSingle();

    if (error) {
      console.error('Error fetching Substack profile:', error);
      return NextResponse.json(
        { error: 'Failed to fetch profile' },
        { status: 500 }
      );
    }

    return NextResponse.json({ profile });
  } catch (error) {
    console.error('Error in GET /api/substack/profile:', error);
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
    const {
      substack_url,
      auto_import_enabled,
      import_frequency_hours,
      subscribe_button_enabled,
      subscribe_button_text,
      show_on_profile,
      articles_per_page,
    } = body;

    // Validate Substack URL format
    if (!substack_url) {
      return NextResponse.json(
        { error: 'Substack URL is required' },
        { status: 400 }
      );
    }

    const substackUrlPattern = /^https?:\/\/[a-zA-Z0-9-]+\.substack\.com\/?$/;
    if (!substackUrlPattern.test(substack_url)) {
      return NextResponse.json(
        { error: 'Invalid Substack URL format. Must be like: https://username.substack.com' },
        { status: 400 }
      );
    }

    // Upsert profile
    const { data: profile, error } = await supabase
      .from('user_substack_profiles')
      .upsert({
        user_id: session.user.id,
        substack_url: substack_url.replace(/\/$/, ''), // Remove trailing slash
        auto_import_enabled: auto_import_enabled ?? true,
        import_frequency_hours: import_frequency_hours ?? 24,
        subscribe_button_enabled: subscribe_button_enabled ?? true,
        subscribe_button_text: subscribe_button_text || 'Subscribe',
        show_on_profile: show_on_profile ?? true,
        articles_per_page: articles_per_page ?? 10,
      })
      .select()
      .single();

    if (error) {
      console.error('Error saving Substack profile:', error);
      return NextResponse.json(
        { error: 'Failed to save profile' },
        { status: 500 }
      );
    }

    return NextResponse.json({ profile });
  } catch (error) {
    console.error('Error in POST /api/substack/profile:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { error } = await supabase
      .from('user_substack_profiles')
      .delete()
      .eq('user_id', session.user.id);

    if (error) {
      console.error('Error deleting Substack profile:', error);
      return NextResponse.json(
        { error: 'Failed to delete profile' },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error in DELETE /api/substack/profile:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
