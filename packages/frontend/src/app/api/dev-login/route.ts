import { NextResponse } from 'next/server';
import { encode } from 'next-auth/jwt';
import { cookies } from 'next/headers';

export async function GET() {
  // Only allow in development
  if (process.env.NODE_ENV !== 'development') {
    return NextResponse.json({ error: 'Not available in production' }, { status: 403 });
  }

  const token = {
    id: '3d231e06-9c0f-428d-bc85-e11ef856c31b',
    email: 'dev@test.com',
    name: 'Dev User',
    subscriptionTier: 'PRO',
    monthlyUsage: 0,
    isBetaTester: true,
    isAdmin: true,
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 30 * 24 * 60 * 60, // 30 days
  };

  const secret = process.env.NEXTAUTH_SECRET || process.env.AUTH_SECRET;
  if (!secret) {
    return NextResponse.json({ error: 'No auth secret configured' }, { status: 500 });
  }

  const encoded = await encode({
    token,
    secret,
    salt: 'authjs.session-token',
  });

  const cookieStore = await cookies();
  cookieStore.set('authjs.session-token', encoded, {
    httpOnly: true,
    secure: false,
    sameSite: 'lax',
    path: '/',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  });

  return NextResponse.json({ success: true, message: 'Logged in as Dev User' });
}
