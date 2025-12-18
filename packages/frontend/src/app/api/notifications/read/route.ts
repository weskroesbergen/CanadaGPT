/**
 * API Route: /api/notifications/read
 *
 * POST: Mark notification(s) as read
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
    const { notificationIds } = body; // Optional: array of notification IDs to mark as read

    // Use the helper function from the database
    const { data: markedCount, error } = await supabase.rpc(
      'mark_notifications_read',
      {
        p_user_id: session.user.id,
        p_notification_ids: notificationIds || null,
      }
    );

    if (error) {
      console.error('Error marking notifications as read:', error);
      return NextResponse.json(
        { error: 'Failed to mark notifications as read' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      marked_count: markedCount || 0,
    });
  } catch (error) {
    console.error('Error in POST /api/notifications/read:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
