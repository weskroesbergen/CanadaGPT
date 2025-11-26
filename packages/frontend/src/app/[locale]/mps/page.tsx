/**
 * MPs list page - Server Component with SSR
 *
 * Performance optimizations:
 * - Server-side data fetching (no loading spinner)
 * - Initial 24 MPs pre-rendered
 * - Client-side infinite scroll for more
 * - Lazy image loading
 */

import { Suspense } from 'react';
import { getTranslations } from 'next-intl/server';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Loading } from '@/components/Loading';
import { MPsGrid } from '@/components/mps/MPsGrid';
import { print } from 'graphql';
import { PAGINATED_MPS, COUNT_MPS } from '@/lib/queries';

const GRAPHQL_URL = process.env.NEXT_PUBLIC_GRAPHQL_URL || 'http://localhost:4000/graphql';
const API_KEY = process.env.NEXT_PUBLIC_GRAPHQL_API_KEY;

interface MPData {
  id: string;
  name: string;
  party?: string | null;
  riding?: string | null;
  current: boolean;
  cabinet_position?: string | null;
  photo_url?: string | null;
  photo_url_source?: string | null;
}

async function fetchInitialMPs(): Promise<{ mps: MPData[]; count: number }> {
  try {
    // Fetch MPs and count in parallel
    const [mpsResponse, countResponse] = await Promise.all([
      fetch(GRAPHQL_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
        },
        body: JSON.stringify({
          query: print(PAGINATED_MPS),
          variables: {
            current: true,
            limit: 24,
            offset: 0,
          },
        }),
        next: { revalidate: 3600 }, // Cache for 1 hour (ISR)
      }),
      fetch(GRAPHQL_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
        },
        body: JSON.stringify({
          query: print(COUNT_MPS),
          variables: {
            current: true,
          },
        }),
        next: { revalidate: 3600 },
      }),
    ]);

    const [mpsResult, countResult] = await Promise.all([
      mpsResponse.json(),
      countResponse.json(),
    ]);

    if (mpsResult.errors) {
      console.error('GraphQL errors (MPs):', mpsResult.errors);
      throw new Error(mpsResult.errors[0]?.message || 'GraphQL error');
    }

    const mps = mpsResult.data?.paginatedMPs || [];
    const count = countResult.data?.countMPs?.count || mps.length;

    return { mps, count };
  } catch (error) {
    console.error('Error fetching initial MPs:', error);
    return { mps: [], count: 0 };
  }
}

export default async function MPsPage() {
  // Fetch initial data server-side
  const { mps, count } = await fetchInitialMPs();

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 page-container">
        <Suspense fallback={<Loading />}>
          <MPsGrid initialMPs={mps} initialCount={count} />
        </Suspense>
      </main>

      <Footer />
    </div>
  );
}

// Generate static params for locales
export function generateStaticParams() {
  return [{ locale: 'en' }, { locale: 'fr' }];
}

// Metadata
export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'mps' });

  return {
    title: t('title'),
    description: t('subtitle', { count: 343 }),
  };
}
