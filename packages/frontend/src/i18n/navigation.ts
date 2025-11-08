import { createNavigation } from 'next-intl/navigation';
import { defineRouting } from 'next-intl/routing';
import { locales, defaultLocale, localePrefix, pathnames } from './config';

export const routing = defineRouting({
  locales,
  defaultLocale,
  localePrefix,
  pathnames,
});

// Create type-safe navigation functions
export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
