/**
 * Individual Bookmark API Route
 *
 * PATCH /api/bookmarks/[id] - Update bookmark metadata
 * DELETE /api/bookmarks/[id] - Delete bookmark
 */

import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { createAdminClient } from '@/lib/supabase-server';
import { getTierLimits } from '@/lib/bookmarks/tierLimits';

export const dynamic = 'force-dynamic';

type RouteContext = {
  params: Promise<{ id: string }>;
};

/**
 * PATCH /api/bookmarks/[id]
 * Update bookmark metadata (notes, tags, collection, favorite status)
 */
export async function PATCH(request: NextRequest, context: RouteContext) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await context.params;
    const supabase = createAdminClient();
    const body = await request.json();

    const {
      collectionId,
      tags,
      notes,
      aiPrompt,
      isFavorite,
      favoriteOrder,
      notificationsEnabled,
    } = body;

    // Verify bookmark exists and belongs to user
    const { data: existing, error: fetchError } = await supabase
      .from('bookmarks')
      .select('*')
      .eq('id', id)
      .eq('user_id', session.user.id)
      .single();

    if (fetchError || !existing) {
      return NextResponse.json({ error: 'Bookmark not found' }, { status: 404 });
    }

    // Check tier permissions for collections
    if (collectionId !== undefined && collectionId !== null) {
      const { data: profile } = await supabase
        .from('user_profiles')
        .select('subscription_tier')
        .eq('id', session.user.id)
        .single();

      const tier = profile?.subscription_tier || 'FREE';
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

    // Check favorites limit if changing to favorite
    if (isFavorite === true && !existing.is_favorite) {
      const { data: profile } = await supabase
        .from('user_profiles')
        .select('subscription_tier')
        .eq('id', session.user.id)
        .single();

      const tier = profile?.subscription_tier || 'FREE';
      const tierLimits = getTierLimits(tier);

      const { count: favoritesCount } = await supabase
        .from('bookmarks')
        .select('*', { count: 'exact', head: true })
        .eq('user_id', session.user.id)
        .eq('is_favorite', true);

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

    // Check notes tier permissions and limits
    if (notes !== undefined && notes !== null && notes.trim() !== '') {
      const { data: profile } = await supabase
        .from('user_profiles')
        .select('subscription_tier')
        .eq('id', session.user.id)
        .single();

      const tier = profile?.subscription_tier || 'FREE';
      const tierLimits = getTierLimits(tier);

      if (!tierLimits.hasNotes) {
        return NextResponse.json(
          {
            error: 'Notes are not available on your tier. Upgrade to BASIC or PRO.',
            tier,
            upgradeRequired: true,
          },
          { status: 403 }
        );
      }

      // Check note length limit
      if (tierLimits.maxNoteLength !== null && notes.length > tierLimits.maxNoteLength) {
        return NextResponse.json(
          {
            error: `Note exceeds character limit of ${tierLimits.maxNoteLength} for ${tier} tier`,
            tier,
            currentLength: notes.length,
            limit: tierLimits.maxNoteLength,
          },
          { status: 403 }
        );
      }
    }

    // Check AI prompt permissions (PRO tier only)
    if (aiPrompt !== undefined && aiPrompt !== null && aiPrompt.trim() !== '') {
      const { data: profile } = await supabase
        .from('user_profiles')
        .select('subscription_tier')
        .eq('id', session.user.id)
        .single();

      const tier = profile?.subscription_tier || 'FREE';
      const tierLimits = getTierLimits(tier);

      if (!tierLimits.hasAIPrompts) {
        return NextResponse.json(
          {
            error: 'AI context prompts are only available on PRO tier',
            tier,
            upgradeRequired: true,
          },
          { status: 403 }
        );
      }
    }

    // Build update object
    const updates: any = {};

    if (collectionId !== undefined) {
      updates.collection_id = collectionId;
    }
    if (tags !== undefined) {
      updates.tags = tags;
    }
    if (notes !== undefined) {
      updates.notes = notes;
    }
    if (aiPrompt !== undefined) {
      updates.ai_prompt = aiPrompt;
    }
    if (isFavorite !== undefined) {
      updates.is_favorite = isFavorite;
      if (!isFavorite) {
        updates.favorite_order = null; // Clear order when unfavoriting
      }
    }
    if (favoriteOrder !== undefined && isFavorite !== false) {
      updates.favorite_order = favoriteOrder;
    }
    if (notificationsEnabled !== undefined) {
      updates.notifications_enabled = notificationsEnabled;
    }

    // Update bookmark
    const { data: bookmark, error: updateError } = await supabase
      .from('bookmarks')
      .update(updates)
      .eq('id', id)
      .eq('user_id', session.user.id)
      .select()
      .single();

    if (updateError) {
      console.error('Error updating bookmark:', updateError);
      return NextResponse.json({ error: 'Failed to update bookmark' }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      bookmark,
    });
  } catch (error) {
    console.error('Bookmark PATCH error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

/**
 * DELETE /api/bookmarks/[id]
 * Delete bookmark
 */
export async function DELETE(request: NextRequest, context: RouteContext) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await context.params;
    const supabase = createAdminClient();

    // Delete bookmark (RLS ensures user can only delete their own)
    const { error: deleteError } = await supabase
      .from('bookmarks')
      .delete()
      .eq('id', id)
      .eq('user_id', session.user.id);

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
      success: true,
      count: count || 0,
    });
  } catch (error) {
    console.error('Bookmark DELETE error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
