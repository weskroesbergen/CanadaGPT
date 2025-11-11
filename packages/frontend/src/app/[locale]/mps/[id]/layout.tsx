/**
 * MP Detail Page Layout
 *
 * Provides dynamic metadata generation for MP pages with rich social media previews
 */

import { Metadata } from 'next';
import { createApolloClient } from '@/lib/apollo-client';
import { GET_MP } from '@/lib/queries';
import { getMPPhotoUrl } from '@/lib/utils/mpPhotoUrl';

type Props = {
  params: Promise<{ locale: string; id: string }>;
  children: React.ReactNode;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, id } = await params;
  const client = createApolloClient();

  try {
    const { data } = await client.query({
      query: GET_MP,
      variables: { id },
    });

    const mp = data?.mps?.[0];

    if (!mp) {
      return {
        title: 'MP Not Found | CanadaGPT',
      };
    }

    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://canadagpt.ca';
    const partyName = mp.memberOf?.name || mp.party || 'Independent';
    const ridingName = mp.represents?.name || mp.riding || 'TBD';

    const title = `${mp.name} - ${partyName}`;
    const description = `${partyName} MP for ${ridingName}${mp.cabinet_position ? ` | ${mp.cabinet_position}` : ''}`;

    // Build OG image URL with MP photo
    const photoUrl = getMPPhotoUrl(mp);
    const ogImageParams = new URLSearchParams({
      title: mp.name,
      description: `${partyName} | ${ridingName}`,
      type: 'mp',
    });

    if (photoUrl) {
      ogImageParams.set('image', photoUrl);
    }

    const ogImageUrl = `${baseUrl}/api/og?${ogImageParams.toString()}`;

    return {
      title,
      description,
      keywords: `${mp.name}, MP, ${partyName}, ${ridingName}, Canadian Parliament, House of Commons`,
      openGraph: {
        title,
        description,
        url: `${baseUrl}/${locale}/mps/${id}`,
        siteName: 'CanadaGPT',
        locale: locale === 'fr' ? 'fr_CA' : 'en_CA',
        type: 'profile',
        images: [
          {
            url: ogImageUrl,
            width: 1200,
            height: 630,
            alt: `${mp.name} - ${partyName}`,
          },
        ],
      },
      twitter: {
        card: 'summary_large_image',
        title,
        description,
        images: [ogImageUrl],
        creator: '@CanadaGPT',
        site: '@CanadaGPT',
      },
    };
  } catch (error) {
    console.error('Failed to generate metadata for MP:', error);
    return {
      title: 'CanadaGPT',
    };
  }
}

export default function MPLayout({ children }: Props) {
  return <>{children}</>;
}
