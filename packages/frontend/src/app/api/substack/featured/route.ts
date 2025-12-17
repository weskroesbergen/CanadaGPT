/**
 * API Route: /api/substack/featured
 *
 * POST: Set article as featured
 * DELETE: Unset article from featured
 */

import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

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
    const { article_id } = body;

    if (!article_id) {
      return NextResponse.json(
        { error: 'Article ID is required' },
        { status: 400 }
      );
    }

    // Use database function to set featured
    const { data, error } = await supabase.rpc('set_article_featured', {
      p_article_id: article_id,
      p_user_id: session.user.id,
    });

    if (error) {
      console.error('Error setting featured article:', error);
      return NextResponse.json(
        { error: 'Failed to set featured article' },
        { status: 500 }
      );
    }

    if (!data) {
      return NextResponse.json(
        { error: 'Article not found or not owned by user' },
        { status: 404 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error in POST /api/substack/featured:', error);
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

    const searchParams = request.nextUrl.searchParams;
    const article_id = searchParams.get('article_id');

    if (!article_id) {
      return NextResponse.json(
        { error: 'Article ID is required' },
        { status: 400 }
      );
    }

    // Use database function to unset featured
    const { data, error } = await supabase.rpc('unset_article_featured', {
      p_article_id: article_id,
      p_user_id: session.user.id,
    });

    if (error) {
      console.error('Error unsetting featured article:', error);
      return NextResponse.json(
        { error: 'Failed to unset featured article' },
        { status: 500 }
      );
    }

    if (!data) {
      return NextResponse.json(
        { error: 'Article not found or not owned by user' },
        { status: 404 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error in DELETE /api/substack/featured:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
