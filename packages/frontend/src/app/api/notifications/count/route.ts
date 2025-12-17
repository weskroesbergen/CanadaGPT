/**
 * API Route: /api/notifications/count
 *
 * GET: Get unread notification count
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

    // Use the helper function from the database
    const { data: count, error } = await supabase.rpc(
      'get_unread_notification_count',
      {
        p_user_id: session.user.id,
      }
    );

    if (error) {
      console.error('Error fetching unread count:', error);
      return NextResponse.json(
        { error: 'Failed to fetch unread count' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      count: count || 0,
    });
  } catch (error) {
    console.error('Error in GET /api/notifications/count:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
