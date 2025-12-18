/**
 * API Route: /api/user/update-profile
 *
 * PATCH: Update user profile fields
 */

import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { getAdminClient } from '@/lib/supabase';

export async function PATCH(request: NextRequest) {
  try {
    // Check authentication
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const body = await request.json();

    // Allowed fields to update
    const allowedFields = [
      'full_name',
      'postal_code',
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

    if (Object.keys(updates).length === 0) {
      return NextResponse.json(
        { error: 'No valid fields to update' },
        { status: 400 }
      );
    }

    // Use admin client to bypass RLS
    const admin = getAdminClient();

    const { data, error } = await admin
      .from('user_profiles')
      .update(updates)
      .eq('id', session.user.id)
      .select();

    if (error) {
      console.error('Error updating profile:', error);
      return NextResponse.json(
        { error: 'Failed to update profile' },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true, data });
  } catch (error) {
    console.error('Error in PATCH /api/user/update-profile:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
