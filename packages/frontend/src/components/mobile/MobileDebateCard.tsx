/**
 * MobileDebateCard - Compact Debate Card for Lists
 */

'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Calendar, MessageSquare, Users } from 'lucide-react';

interface MobileDebateCardProps {
  debate: {
    id: string;
    date: string;
    number?: string;
    statement_count?: number;
    speaker_count?: number;
  };
  preview?: string;
  title?: string;
  locale?: string;
}

export function MobileDebateCard({
  debate,
  preview,
  title,
  locale = 'en',
}: MobileDebateCardProps) {
  const router = useRouter();

  const handleClick = () => {
    router.push(`/${locale}/debates/${debate.id}`);
  };

  return (
    <div className="mobile-debate-card" onClick={handleClick}>
      <div className="mobile-debate-date">
        <Calendar className="h-4 w-4" />
        {new Date(debate.date).toLocaleDateString('en-CA', {
          weekday: 'long',
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        })}
      </div>

      {title && <h3 className="mobile-debate-title">{title}</h3>}

      {preview && <p className="mobile-debate-preview">{preview}</p>}

      <div className="mobile-debate-meta">
        {debate.statement_count !== undefined && (
          <div className="mobile-debate-meta-item">
            <MessageSquare className="h-4 w-4" />
            <span>{debate.statement_count} statements</span>
          </div>
        )}
        {debate.speaker_count !== undefined && (
          <div className="mobile-debate-meta-item">
            <Users className="h-4 w-4" />
            <span>{debate.speaker_count} speakers</span>
          </div>
        )}
      </div>
    </div>
  );
}
