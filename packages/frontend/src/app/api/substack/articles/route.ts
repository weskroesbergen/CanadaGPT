/**
 * API Route: /api/substack/articles
 *
 * GET: Fetch Substack articles for a user
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
    const searchParams = request.nextUrl.searchParams;
    const username = searchParams.get('username');
    const limit = parseInt(searchParams.get('limit') || '10');
    const offset = parseInt(searchParams.get('offset') || '0');
    const featured_only = searchParams.get('featured_only') === 'true';

    if (!username) {
      return NextResponse.json(
        { error: 'Username is required' },
        { status: 400 }
      );
    }

    // Get user ID from username
    const { data: userProfile, error: userError } = await supabase
      .from('user_profiles')
      .select('id')
      .eq('username', username)
      .single();

    if (userError || !userProfile) {
      return NextResponse.json(
        { error: 'User not found' },
        { status: 404 }
      );
    }

    // Check if user has Substack profile
    const { data: substackProfile, error: profileError } = await supabase
      .from('user_substack_profiles')
      .select('*')
      .eq('user_id', userProfile.id)
      .maybeSingle();

    if (profileError) {
      console.error('Error fetching Substack profile:', profileError);
      return NextResponse.json(
        { error: 'Failed to fetch profile' },
        { status: 500 }
      );
    }

    if (!substackProfile) {
      return NextResponse.json({
        profile: null,
        articles: [],
        count: 0,
        hasMore: false,
      });
    }

    // Build articles query
    let query = supabase
      .from('substack_articles')
      .select('*', { count: 'exact' })
      .eq('user_id', userProfile.id)
      .order('published_at', { ascending: false })
      .range(offset, offset + limit - 1);

    // Filter by featured if requested
    if (featured_only) {
      query = query.eq('is_featured', true).order('featured_order', { ascending: true });
    }

    const { data: articles, error, count } = await query;

    if (error) {
      console.error('Error fetching articles:', error);
      return NextResponse.json(
        { error: 'Failed to fetch articles' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      profile: substackProfile,
      articles: articles || [],
      count: count || 0,
      hasMore: (count || 0) > offset + limit,
    });
  } catch (error) {
    console.error('Error in GET /api/substack/articles:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
