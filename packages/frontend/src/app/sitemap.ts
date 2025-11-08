/**
 * Sitemap generation for CanadaGPT
 * Includes bilingual routes for SEO
 */

import { MetadataRoute } from 'next';
import { locales } from '@/i18n/config';

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://canadagpt.ca';

// Main routes that should appear in sitemap
const routes = [
  '',
  '/dashboard',
  '/mps',
  '/bills',
  '/chamber',
  '/hansard',
  '/committees',
  '/lobbying',
  '/spending',
  '/about',
  '/contact',
  '/privacy',
];

export default function sitemap(): MetadataRoute.Sitemap {
  const sitemap: MetadataRoute.Sitemap = [];

  // Add each route for each locale
  locales.forEach((locale) => {
    routes.forEach((route) => {
      sitemap.push({
        url: `${baseUrl}/${locale}${route}`,
        lastModified: new Date(),
        changeFrequency: route === '' ? 'daily' : 'weekly',
        priority: route === '' ? 1.0 : 0.8,
        alternates: {
          languages: {
            en: `${baseUrl}/en${route}`,
            fr: `${baseUrl}/fr${route}`,
          },
        },
      });
    });
  });

  return sitemap;
}
