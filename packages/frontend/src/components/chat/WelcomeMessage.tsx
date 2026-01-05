/**
 * WelcomeMessage Component
 *
 * Displays different welcome messages based on authentication status:
 * - Anonymous users: Signup CTA with feature overview
 * - Authenticated users: Gordie introduction message
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { MapleLeafIcon } from '@canadagpt/design-system';
import type { UserProfile } from '@/contexts/AuthContext';

interface WelcomeMessageProps {
  user: UserProfile | null;
}

export function WelcomeMessage({ user }: WelcomeMessageProps) {
  if (!user) {
    // Anonymous user - show signup CTA
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 space-y-6 text-center">
        {/* Logo */}
        <div className="w-16 h-16 bg-accent-red rounded-full flex items-center justify-center">
          <MapleLeafIcon className="w-12 h-12 text-white" size={48} />
        </div>

        {/* Heading */}
        <div className="space-y-3 max-w-md">
          <h2 className="text-2xl font-bold text-white">Welcome to CanadaGPT</h2>
          <p className="text-gray-300 text-base leading-relaxed">
            I can help you understand the Canadian Federal Government and hold it accountable.
          </p>
        </div>

        {/* Feature description */}
        <div className="space-y-2 max-w-md">
          <p className="text-sm text-gray-400">
            Browsing parliamentary information is always free.
          </p>
          <p className="text-sm text-gray-300 font-medium">
            Sign up to chat with Gordie and get personalized insights.
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="space-y-3 w-full max-w-xs">
          <Link
            href="/auth/signup"
            className="block w-full px-6 py-3 bg-accent-red text-white text-center rounded-lg font-medium hover:bg-red-700 transition-colors"
          >
            Create Free Account
          </Link>

          <p className="text-sm text-gray-400">
            Already have an account?{' '}
            <Link href="/auth/login" className="text-accent-red hover:text-red-400 font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    );
  }

  // Authenticated user - show Gordie intro
  return (
    <div className="flex flex-col items-center justify-center h-full p-6 space-y-6 text-center">
      {/* Logo */}
      <div className="w-16 h-16 bg-accent-red rounded-full flex items-center justify-center">
        <MapleLeafIcon className="w-12 h-12 text-white" size={48} />
      </div>

      {/* Gordie intro */}
      <div className="space-y-4 max-w-md">
        <h2 className="text-xl font-semibold text-white">
          Hey there. I'm Gordie, your guide to Canadian Parliament.
        </h2>
        <p className="text-gray-300 text-base leading-relaxed">
          Ask me about MPs, bills, committees, lobbying, or anything related to federal politics.
          I'll give you context and connections from parliamentary records, lobbying data, and The Canadian Encyclopedia.
        </p>
        <p className="text-gray-400 text-sm font-medium">
          What would you like to know?
        </p>
      </div>
    </div>
  );
}
