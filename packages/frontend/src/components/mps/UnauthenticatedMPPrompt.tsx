/**
 * UnauthenticatedMPPrompt Component
 *
 * Call-to-action shown to unauthenticated users
 * encouraging them to sign up to find their MP
 */

'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { MapPin, UserPlus } from 'lucide-react';

export function UnauthenticatedMPPrompt() {
  const t = useTranslations('mps.myMP');

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 border-2 border-blue-200 dark:border-blue-800 rounded-lg p-8">
      <div className="flex flex-col items-center text-center space-y-4">
        {/* Icon */}
        <div className="relative">
          <div className="absolute inset-0 bg-blue-500/20 dark:bg-blue-400/20 rounded-full blur-xl" />
          <div className="relative bg-blue-500 dark:bg-blue-600 rounded-full p-4">
            <MapPin className="w-8 h-8 text-white" />
          </div>
        </div>

        {/* Heading */}
        <div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            {t('findYourMP')}
          </h3>
          <p className="text-gray-600 dark:text-gray-300 max-w-md">
            {t('signUpPrompt')}
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto mt-4">
          <Link
            href={"/auth/signup" as any}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-md transition-colors shadow-md hover:shadow-lg"
          >
            <UserPlus className="w-5 h-5" />
            {t('signUpFree')}
          </Link>

          <Link
            href={"/auth/login" as any}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-semibold rounded-md border border-gray-300 dark:border-gray-600 transition-colors"
          >
            {t('alreadyHaveAccount')} {t('logIn')}
          </Link>
        </div>

        {/* Features list */}
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm text-gray-600 dark:text-gray-400">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span>Find your local MP</span>
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span>Track accountability</span>
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span>100% Free</span>
          </div>
        </div>
      </div>
    </div>
  );
}
