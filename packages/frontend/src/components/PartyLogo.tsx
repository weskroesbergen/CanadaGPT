/**
 * PartyLogo Component
 *
 * Displays official party logos where available, falls back to branded badges
 * Supports different sizes and optional linking
 */

'use client';

import Image from 'next/image';
import Link from 'next/link';
import { getPartyInfo, getPartySlug } from '@/lib/partyConstants';

export interface PartyLogoProps {
  party: string | null | undefined;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  linkTo?: 'party' | 'filter' | string;
  showLabel?: boolean;
  className?: string;
}

// Image sizes in pixels
const imageSizes = {
  sm: 28,
  md: 38,
  lg: 48,
  xl: 58,
};

const sizeClasses = {
  sm: 'h-[30px] w-[30px] text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-[50px] w-[50px] text-base',
  xl: 'h-15 w-15 text-lg',
};

const labelSizes = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-base',
  xl: 'text-lg',
};

/**
 * Get party logo URL from Google Cloud Storage
 * Returns null if no official logo exists (will fall back to initials badge)
 */
function getPartyLogoPath(partyName: string): string | null {
  const GCS_BASE = 'https://storage.googleapis.com/canada-gpt-ca-mp-photos/party-logos';

  const logos: Record<string, string> = {
    'Liberal': `${GCS_BASE}/liberal-logo.png`,
    'Conservative': `${GCS_BASE}/conservative-logo.png`,
    'NDP': `${GCS_BASE}/ndp-logo.png?v=2`,
    'Bloc Québécois': `${GCS_BASE}/bloc-quebecois-logo.png`,
    'Green': `${GCS_BASE}/green-logo.png`,
  };

  return logos[partyName] || null;
}

/**
 * Get party initials for badge display (fallback when no logo available)
 */
function getPartyInitials(partyName: string): string {
  const initials: Record<string, string> = {
    'Liberal': 'L',
    'Conservative': 'C',
    'NDP': 'NDP',
    'Bloc Québécois': 'BQ',
    'Green': 'G',
    'Independent': 'I',
  };

  return initials[partyName] || partyName.charAt(0).toUpperCase();
}

export function PartyLogo({
  party,
  size = 'md',
  linkTo,
  showLabel = false,
  className = '',
}: PartyLogoProps) {
  const partyInfo = getPartyInfo(party);

  if (!partyInfo) return null;

  const logoPath = getPartyLogoPath(partyInfo.name);
  const initials = getPartyInitials(partyInfo.name);

  // Build the link URL if linkTo is specified
  let href: string | undefined;
  if (linkTo === 'party') {
    href = `/parties/${partyInfo.slug}`;
  } else if (linkTo === 'filter') {
    href = `/mps?party=${encodeURIComponent(partyInfo.name)}`;
  } else if (linkTo && linkTo !== 'party' && linkTo !== 'filter') {
    href = linkTo;
  }

  // Render official logo if available with consistent badge styling
  let badge;
  if (logoPath) {
    badge = (
      <div
        className={`flex items-center justify-center rounded-md bg-white dark:bg-gray-900 shadow-md border border-border-subtle p-1 ${sizeClasses[size]} ${className} ${
          href ? 'cursor-pointer hover:opacity-90 hover:shadow-lg transition-all' : ''
        }`}
        title={partyInfo.fullName}
      >
        <Image
          src={logoPath}
          alt={`${partyInfo.fullName} logo`}
          width={imageSizes[size]}
          height={imageSizes[size]}
          className="object-contain"
        />
      </div>
    );
  } else {
    // Fall back to initials badge with same styling
    badge = (
      <div
        className={`flex items-center justify-center rounded-md font-bold shadow-md border border-border-subtle ${sizeClasses[size]} ${className} ${
          href ? 'cursor-pointer hover:opacity-90 hover:shadow-lg transition-all' : ''
        }`}
        style={{
          backgroundColor: partyInfo.color,
          color: partyInfo.textColor,
        }}
        title={partyInfo.fullName}
      >
        {initials}
      </div>
    );
  }

  const content = showLabel ? (
    <div className="flex items-center gap-2">
      {badge}
      <span className={`font-medium ${labelSizes[size]}`} style={{ color: partyInfo.color }}>
        {partyInfo.name}
      </span>
    </div>
  ) : (
    badge
  );

  if (href) {
    return (
      <Link href={href} className="inline-block">
        {content}
      </Link>
    );
  }

  return content;
}

/**
 * PartyBadge Component
 *
 * Alternative component for larger, pill-shaped party badges
 * Similar to cabinet position badges
 */
export interface PartyBadgeProps {
  party: string | null | undefined;
  linkTo?: 'party' | 'filter' | string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const badgeSizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
  lg: 'px-4 py-1.5 text-base',
};

export function PartyBadge({
  party,
  linkTo,
  size = 'sm',
  className = '',
}: PartyBadgeProps) {
  const partyInfo = getPartyInfo(party);

  if (!partyInfo) return null;

  // Build the link URL if linkTo is specified
  let href: string | undefined;
  if (linkTo === 'party') {
    href = `/parties/${partyInfo.slug}`;
  } else if (linkTo === 'filter') {
    href = `/mps?party=${encodeURIComponent(partyInfo.name)}`;
  } else if (linkTo && linkTo !== 'party' && linkTo !== 'filter') {
    href = linkTo;
  }

  const badge = (
    <span
      className={`inline-flex items-center rounded-full font-medium ${badgeSizeClasses[size]} ${className} ${
        href ? 'cursor-pointer hover:opacity-90 transition-opacity' : ''
      }`}
      style={{
        backgroundColor: partyInfo.color,
        color: partyInfo.textColor,
      }}
    >
      {partyInfo.name}
    </span>
  );

  if (href) {
    return (
      <Link href={href} className="inline-block">
        {badge}
      </Link>
    );
  }

  return badge;
}
