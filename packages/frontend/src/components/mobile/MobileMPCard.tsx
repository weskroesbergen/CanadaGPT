/**
 * MobileMPCard - Compact MP Profile Card for Lists
 */

'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { PartyLogo } from '@/components/PartyLogo';
import { getMPPhotoUrl } from '@/lib/utils/mpPhotoUrl';

interface MobileMPCardProps {
  mp: {
    id: string;
    name: string;
    party?: string;
    riding?: string;
    province?: string;
    current?: boolean;
  };
  stats?: {
    bills?: number;
    votes?: number;
    speeches?: number;
  };
  locale?: string;
}

export function MobileMPCard({ mp, stats, locale = 'en' }: MobileMPCardProps) {
  const router = useRouter();
  const mpPhotoUrl = getMPPhotoUrl(mp);

  const handleClick = () => {
    router.push(`/${locale}/mps/${mp.id}`);
  };

  return (
    <div className="mobile-mp-card" onClick={handleClick}>
      {mpPhotoUrl && (
        <img
          src={mpPhotoUrl}
          alt={mp.name}
          className="mobile-mp-avatar"
        />
      )}
      <div className="mobile-mp-info">
        <div className="mobile-mp-name">
          {mp.name}
          {mp.party && <PartyLogo party={mp.party} size="sm" />}
        </div>
        <div className="mobile-mp-details">
          {mp.riding && `${mp.riding}`}
          {mp.province && `, ${mp.province}`}
        </div>
        {stats && (
          <div className="mobile-mp-stats">
            {stats.bills !== undefined && (
              <div className="mobile-mp-stat">
                <div className="mobile-mp-stat-value">{stats.bills}</div>
                <div className="mobile-mp-stat-label">Bills</div>
              </div>
            )}
            {stats.votes !== undefined && (
              <div className="mobile-mp-stat">
                <div className="mobile-mp-stat-value">{stats.votes}</div>
                <div className="mobile-mp-stat-label">Votes</div>
              </div>
            )}
            {stats.speeches !== undefined && (
              <div className="mobile-mp-stat">
                <div className="mobile-mp-stat-value">{stats.speeches}</div>
                <div className="mobile-mp-stat-label">Speeches</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
