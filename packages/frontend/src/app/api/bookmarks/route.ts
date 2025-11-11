/**
 * Bookmarks API Route
 *
 * GET /api/bookmarks - List user's bookmarks with filters
 * POST /api/bookmarks - Create or toggle bookmark
 */

import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { createAdminClient } from '@/lib/supabase-server';
import { canCreateBookmark, getBookmarkUsageStats, getTierLimits } from '@/lib/bookmarks/tierLimits';

export const dynamic = 'force-dynamic';

/**
 * GET /api/bookmarks
 * List user's bookmarks with optional filters
 */
export async function GET(request: NextRequest) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const supabase = createAdminClient();
    const { searchParams } = new URL(request.url);

    // Parse query parameters
    const itemType = searchParams.get('type'); // Filter by item type
    const collectionId = searchParams.get('collectionId'); // Filter by collection
    const search = searchParams.get('search'); // Search in title/notes/tags
    const favoritesOnly = searchParams.get('favorites') === 'true';
    const limit = parseInt(searchParams.get('limit') || '50', 10);
    const offset = parseInt(searchParams.get('offset') || '0', 10);

    // Build query
    let query = supabase
      .from('bookmarks')
      .select('*', { count: 'exact' })
      .eq('user_id', session.user.id)
      .order('created_at', { ascending: false });

    // Apply filters
    if (itemType) {
      query = query.eq('item_type', itemType);
    }

    if (collectionId) {
      query = query.eq('collection_id', collectionId);
    }

    if (favoritesOnly) {
      query = query.eq('is_favorite', true).order('favorite_order', { ascending: true });
    }

    if (search) {
      // Search in title, notes, and tags
      query = query.or(`title.ilike.%${search}%,notes.ilike.%${search}%,tags.cs.{${search}}`);
    }

    // Pagination
    query = query.range(offset, offset + limit - 1);

    const { data: bookmarks, error, count } = await query;

    if (error) {
      console.error('Error fetching bookmarks:', error);
      return NextResponse.json({ error: 'Failed to fetch bookmarks' }, { status: 500 });
    }

    // Get user's subscription tier and usage stats
    const { data: profile } = await supabase
      .from('user_profiles')
      .select('subscription_tier')
      .eq('id', session.user.id)
      .single();

    const tier = profile?.subscription_tier || 'FREE';
    const usageStats = getBookmarkUsageStats(count || 0, tier);
    const tierLimits = getTierLimits(tier);

    return NextResponse.json({
      bookmarks: bookmarks || [],
      pagination: {
        total: count || 0,
        limit,
        offset,
        hasMore: (count || 0) > offset + limit,
      },
      tier: {
        current: tier,
        limits: tierLimits,
        usage: usageStats,
      },
    });
  } catch (error) {
    console.error('Bookmarks API error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

/**
 * POST /api/bookmarks
 * Create or toggle bookmark
 */
export async function POST(request: NextRequest) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const supabase = createAdminClient();
    const body = await request.json();

    const {
      itemType,
      itemId,
      title,
      subtitle,
      imageUrl,
      url,
      metadata = {},
      collectionId = null,
      tags = [],
      notes = '',
      isFavorite = false,
    } = body;

    // Validate required fields
    if (!itemType || !itemId || !title || !url) {
      return NextResponse.json(
        { error: 'Missing required fields: itemType, itemId, title, url' },
        { status: 400 }
      );
    }

    // Check if bookmark already exists (toggle behavior)
    const { data: existing } = await supabase
      .from('bookmarks')
      .select('id')
      .eq('user_id', session.user.id)
      .eq('item_type', itemType)
      .eq('item_id', itemId)
      .single();

    if (existing) {
      // Bookmark exists - delete it (toggle off)
      const { error: deleteError } = await supabase
        .from('bookmarks')
        .delete()
        .eq('id', existing.id);

      if (deleteError) {
        console.error('Error deleting bookmark:', deleteError);
        return NextResponse.json({ error: 'Failed to delete bookmark' }, { status: 500 });
      }

      // Get updated count
      const { count } = await supabase
        .from('bookmarks')
        .select('*', { count: 'exact', head: true })
        .eq('user_id', session.user.id);

      return NextResponse.json({
        action: 'removed',
        bookmarkId: existing.id,
        count: count || 0,
      });
    }

    // Bookmark doesn't exist - create it
    // First, check tier limits
    const { count: currentCount } = await supabase
      .from('bookmarks')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', session.user.id);

    const { data: profile } = await supabase
      .from('user_profiles')
      .select('subscription_tier')
      .eq('id', session.user.id)
      .single();

    const tier = profile?.subscription_tier || 'FREE';

    if (!canCreateBookmark(currentCount || 0, tier)) {
      const tierLimits = getTierLimits(tier);
      return NextResponse.json(
        {
          error: 'Bookmark limit reached',
          tier,
          currentCount,
          limit: tierLimits.maxBookmarks,
          upgradeRequired: true,
        },
        { status: 403 }
      );
    }

    // Check favorites limit if isFavorite
    if (isFavorite) {
      const { count: favoritesCount } = await supabase
        .from('bookmarks')
        .select('*', { count: 'exact', head: true })
        .eq('user_id', session.user.id)
        .eq('is_favorite', true);

      const tierLimits = getTierLimits(tier);
      if (
        tierLimits.maxFavorites !== null &&
        (favoritesCount || 0) >= tierLimits.maxFavorites
      ) {
        return NextResponse.json(
          {
            error: 'Favorites limit reached',
            tier,
            currentCount: favoritesCount,
            limit: tierLimits.maxFavorites,
          },
          { status: 403 }
        );
      }
    }

    // Check collection permission
    if (collectionId) {
      const tierLimits = getTierLimits(tier);
      if (tierLimits.maxCollections === 0) {
        return NextResponse.json(
          {
            error: 'Collections not available on your tier',
            tier,
            upgradeRequired: true,
          },
          { status: 403 }
        );
      }
    }

    // Calculate favorite_order if isFavorite
    let favoriteOrder = null;
    if (isFavorite) {
      const { data: maxOrderBookmark } = await supabase
        .from('bookmarks')
        .select('favorite_order')
        .eq('user_id', session.user.id)
        .eq('is_favorite', true)
        .order('favorite_order', { ascending: false })
        .limit(1)
        .single();

      favoriteOrder = (maxOrderBookmark?.favorite_order || 0) + 1;
    }

    // Create bookmark
    const { data: bookmark, error: createError } = await supabase
      .from('bookmarks')
      .insert({
        user_id: session.user.id,
        item_type: itemType,
        item_id: itemId,
        title,
        subtitle: subtitle || null,
        image_url: imageUrl || null,
        url,
        metadata,
        collection_id: collectionId,
        tags,
        notes,
        is_favorite: isFavorite,
        favorite_order: favoriteOrder,
        notifications_enabled: false, // Default to off
      })
      .select()
      .single();

    if (createError) {
      console.error('Error creating bookmark:', createError);
      return NextResponse.json({ error: 'Failed to create bookmark' }, { status: 500 });
    }

    // Get updated usage stats
    const usageStats = getBookmarkUsageStats((currentCount || 0) + 1, tier);

    return NextResponse.json({
      action: 'created',
      bookmark,
      tier: {
        current: tier,
        limits: getTierLimits(tier),
        usage: usageStats,
      },
    });
  } catch (error) {
    console.error('Bookmarks API error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
