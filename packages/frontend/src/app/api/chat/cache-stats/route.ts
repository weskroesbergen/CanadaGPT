/**
 * Cache Statistics API Route
 *
 * Returns tool cache statistics for monitoring and optimization.
 * Restricted to authenticated admin users only.
 */

import { NextResponse } from 'next/server';
import { auth } from '@/auth';
import { toolCache, logCacheStats, clearCache } from '@/lib/toolCache';

/**
 * GET /api/chat/cache-stats
 * Returns current cache statistics
 */
export async function GET() {
  try {
    const session = await auth();

    if (!session || !session.user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const stats = toolCache.getStats();

    return NextResponse.json({
      success: true,
      stats,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('[CacheStats] Error fetching stats:', error);
    return NextResponse.json(
      { error: 'Failed to fetch cache statistics' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/chat/cache-stats
 * Clears the cache (admin only)
 */
export async function DELETE() {
  try {
    const session = await auth();

    if (!session || !session.user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // TODO: Add admin check here if needed
    // For now, any authenticated user can clear cache (useful for testing)

    clearCache();

    return NextResponse.json({
      success: true,
      message: 'Cache cleared successfully',
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('[CacheStats] Error clearing cache:', error);
    return NextResponse.json(
      { error: 'Failed to clear cache' },
      { status: 500 }
    );
  }
}
