/**
 * Auth Callback Route Handler
 *
 * This route handles OAuth callbacks from providers (Google, GitHub) and
 * email confirmation links. It exchanges the auth code for a session and
 * redirects the user to the appropriate page.
 *
 * Next.js 15 App Router API route - runs on the server
 */

import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ locale: string }> }
) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get('code');
  const next = requestUrl.searchParams.get('next');
  const { locale } = await params;
  const cookieStore = await cookies();

  // Default redirect includes locale
  const defaultRedirect = `/${locale}`;
  const loginUrl = `/${locale}/auth/login`;

  if (code) {
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll();
          },
          setAll(cookiesToSet) {
            try {
              cookiesToSet.forEach(({ name, value, options }) =>
                cookieStore.set(name, value, options)
              );
            } catch {
              // The `setAll` method was called from a Server Component.
              // This can be ignored if you have middleware refreshing
              // user sessions.
            }
          },
        },
      }
    );

    // Exchange code for session
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (error) {
      console.error('Auth callback error:', error);
      // Redirect to login with error
      return NextResponse.redirect(
        new URL(`${loginUrl}?error=${encodeURIComponent(error.message)}`, requestUrl.origin)
      );
    }

    // Successfully authenticated - redirect to intended destination
    const redirectPath = next || defaultRedirect;
    return NextResponse.redirect(new URL(redirectPath, requestUrl.origin));
  }

  // No code parameter - redirect to login
  return NextResponse.redirect(new URL(loginUrl, requestUrl.origin));
}
