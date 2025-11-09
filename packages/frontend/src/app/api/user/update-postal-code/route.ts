/**
 * Update User Postal Code API Route
 *
 * Updates the authenticated user's postal code in their profile
 */

import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { getAdminClient } from '@/lib/supabase';
import { validateCanadianPostalCode, formatPostalCode } from '@/lib/postalCodeUtils';

export async function POST(request: NextRequest) {
  try {
    // Check authentication
    const session = await auth();

    if (!session || !session.user?.email) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { postal_code, preferred_mp_id } = body;

    // Validate postal code if provided
    if (postal_code && !validateCanadianPostalCode(postal_code)) {
      return NextResponse.json(
        { error: 'Invalid Canadian postal code format' },
        { status: 400 }
      );
    }

    // Format the postal code
    const formattedPostalCode = postal_code ? formatPostalCode(postal_code) : null;

    // Prepare update data
    const updateData: {
      postal_code?: string | null;
      preferred_mp_id?: string | null;
      updated_at: string;
    } = {
      updated_at: new Date().toISOString()
    };

    // Only include fields that were provided
    if (postal_code !== undefined) {
      updateData.postal_code = formattedPostalCode;
    }

    if (preferred_mp_id !== undefined) {
      updateData.preferred_mp_id = preferred_mp_id;
    }

    // Update user profile
    const admin = getAdminClient();

    const { error } = await admin
      .from('user_profiles')
      .update(updateData)
      .eq('email', session.user.email);

    if (error) {
      console.error('Error updating postal code:', error);
      return NextResponse.json(
        { error: 'Failed to update postal code' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      postal_code: formattedPostalCode,
      preferred_mp_id: preferred_mp_id || null
    });
  } catch (error) {
    console.error('Update postal code error:', error);

    return NextResponse.json(
      {
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
