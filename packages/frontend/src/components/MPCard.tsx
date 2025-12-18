/**
 * MPCard Component
 *
 * Reusable card component for displaying MP information
 * Features:
 * - MP photo, name, party, riding
 * - Cabinet position badge
 * - Party logo in top-right corner
 * - Share button for social sharing
 * - Clickable to MP profile
 * - Fully bilingual with party name translation
 */

'use client';

import React from 'react';
import Image from 'next/image';
import { Link } from '@/i18n/navigation';
import { useTranslations, useLocale } from 'next-intl';
import { Card } from '@canadagpt/design-system';
import { Crown } from 'lucide-react';
import { PartyLogo } from './PartyLogo';
import { usePartyName } from '@/hooks/useBilingual';
import { ShareButton } from './ShareButton';
import { PrintableCard } from './PrintableCard';
import { getMPPhotoUrl } from '@/lib/utils/mpPhotoUrl';
import { BookmarkButton } from './bookmarks/BookmarkButton';
import { EntityVoteButtons } from './votes/EntityVoteButtons';

export interface MPCardData {
  id: string;
  name: string;
  party?: string | null;
  riding?: string | null;
  cabinet_position?: string | null;
}

export interface MPCardProps {
  mp: MPCardData;
  linkToParty?: boolean;
  className?: string;
  // Optional vote data for batch loading optimization
  initialUpvotes?: number;
  initialDownvotes?: number;
  initialUserVote?: 'upvote' | 'downvote' | null;
}

export function MPCard({
  mp,
  linkToParty = true,
  className = '',
  initialUpvotes,
  initialDownvotes,
  initialUserVote,
}: MPCardProps) {
  const t = useTranslations('mps.card');
  const locale = useLocale();
  const partyName = usePartyName(mp.party);
  const [imageError, setImageError] = React.useState(false);

  // Get photo URL from GCS or fallback to ID-based construction
  const photoUrl = getMPPhotoUrl(mp);

  // Share data
  const shareUrl = `/${locale}/mps/${mp.id}`;
  const shareTitle = mp.name;
  const shareDescription = `${partyName || t('independent')} - ${mp.riding || t('ridingTBD')}`;

  return (
    <Link href={`/mps/${mp.id}` as any}>
      <PrintableCard>
        <Card className={`hover:border-accent-red transition-colors cursor-pointer h-full relative ${className}`}>
          {/* Top Right Corner: Vote, Bookmark + Share Button */}
          <div className="absolute top-3 right-3 z-20 flex items-center gap-2">
            {/* Vote Buttons */}
            <EntityVoteButtons
              entityType="mp"
              entityId={mp.id}
              size="sm"
              initialUpvotes={initialUpvotes}
              initialDownvotes={initialDownvotes}
              initialUserVote={initialUserVote}
            />
            {/* Bookmark Button */}
            <BookmarkButton
              bookmarkData={{
                itemType: 'mp',
                itemId: mp.id,
                title: mp.name,
                subtitle: shareDescription,
                imageUrl: photoUrl || undefined,
                url: shareUrl,
                metadata: {
                  party: mp.party,
                  riding: mp.riding,
                  cabinet_position: mp.cabinet_position,
                },
              }}
              size="sm"
            />
            {/* Share Button */}
            <ShareButton
              url={shareUrl}
              title={shareTitle}
              description={shareDescription}
              size="sm"
            />
          </div>

          {/* Bottom Right Corner: Party Logo Badge */}
          <div className="absolute bottom-3 right-3 z-10">
            <PartyLogo
              party={mp.party}
              size="md"
              linkTo={undefined}
            />
          </div>

        <div className="flex items-start space-x-4">
          {/* MP Photo */}
          {photoUrl && !imageError && (
            <Image
              src={photoUrl}
              alt={mp.name}
              width={60}
              height={96}
              className="w-[60px] h-24 rounded-lg object-contain flex-shrink-0 bg-bg-elevated"
              loading="lazy"
              onError={() => setImageError(true)}
            />
          )}

          {/* MP Info */}
          <div className="flex-1 min-w-0 pr-28">
            {/* Name */}
            <h3 className="font-semibold text-text-primary truncate">{mp.name}</h3>

            {/* Party */}
            <p className="text-sm text-text-secondary">{partyName || t('independent')}</p>

            {/* Riding */}
            <p className="text-sm text-text-tertiary truncate">{mp.riding || t('ridingTBD')}</p>

            {/* Cabinet Position Badge */}
            {mp.cabinet_position && (
              <div className="mt-2 flex items-center gap-1">
                <div className="inline-flex items-center gap-1 px-2 py-1 bg-accent-red text-white rounded-md text-xs font-medium">
                  <Crown className="h-3 w-3" />
                  <span className="line-clamp-1">{mp.cabinet_position}</span>
                </div>
              </div>
            )}
          </div>
        </div>
        </Card>
      </PrintableCard>
    </Link>
  );
}

/**
 * CompactMPCard Component
 *
 * Smaller variant for chamber view and lists
 */
export interface CompactMPCardProps {
  mp: MPCardData;
  linkToParty?: boolean;
  className?: string;
}

export function CompactMPCard({ mp, linkToParty = true, className = '' }: CompactMPCardProps) {
  const t = useTranslations('mps.card');
  const [imageError, setImageError] = React.useState(false);

  // Get photo URL from GCS or fallback to ID-based construction
  const photoUrl = getMPPhotoUrl(mp);

  return (
    <Link href={`/mps/${mp.id}` as any}>
      <Card className={`hover:border-accent-red transition-colors cursor-pointer p-2 relative ${className}`}>
        {/* Party Logo Badge - Top Corner */}
        <div className="absolute top-2 right-2 z-10">
          <PartyLogo
            party={mp.party}
            size="sm"
            linkTo={undefined}
          />
        </div>

        {/* MP Photo */}
        {photoUrl && !imageError && (
          <Image
            src={photoUrl}
            alt={mp.name}
            width={300}
            height={384}
            className="w-full h-96 object-cover object-[50%_25%] rounded-md mb-2"
            onError={() => setImageError(true)}
          />
        )}

        {/* MP Info */}
        <div>
          <h4 className="text-xs font-semibold text-text-primary truncate pr-6">{mp.name}</h4>
          <p className="text-xs text-text-tertiary truncate mt-0.5">{mp.riding || t('ridingTBD')}</p>

          {/* Cabinet Badge */}
          {mp.cabinet_position && (
            <div className="mt-1">
              <div className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-accent-red text-white rounded text-xs">
                <Crown className="h-2.5 w-2.5" />
              </div>
            </div>
          )}
        </div>
      </Card>
    </Link>
  );
}
