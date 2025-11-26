/**
 * MobileStatementCard - Twitter/Instagram-Style Speech Card
 * Optimized for vertical scrolling with swipe gestures
 */

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Calendar, Hash, Heart, MessageCircle, Share2, Bookmark } from 'lucide-react';
import { useSimpleSwipe } from '@/hooks/useSwipeGesture';
import { getMPPhotoUrl } from '@/lib/utils/mpPhotoUrl';
import { PartyLogo } from '@/components/PartyLogo';

interface MobileStatementCardProps {
  statement: {
    id: string;
    content_en: string;
    time: string;
    wordcount?: number;
    h1_en?: string;
    h2_en?: string;
    madeBy?: {
      id: string;
      name: string;
      party?: string;
    };
    partOf?: {
      id: string;
      date?: string;
      document_type?: string;
    };
  };
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  showFullContent?: boolean;
  locale?: string;
}

export function MobileStatementCard({
  statement,
  onSwipeLeft,
  onSwipeRight,
  showFullContent = false,
  locale = 'en',
}: MobileStatementCardProps) {
  const router = useRouter();
  const [isExpanded, setIsExpanded] = useState(showFullContent);
  const [isLiked, setIsLiked] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);

  // Swipe gesture handlers
  const swipeHandlers = useSimpleSwipe({
    onSwipeLeft,
    onSwipeRight,
    threshold: 75,
  });

  // Truncate content for preview
  const content = statement.content_en || '';
  const preview = content.length > 300 ? content.substring(0, 300) + '...' : content;
  const shouldShowReadMore = content.length > 300;

  // Get MP photo
  const mpPhotoUrl = statement.madeBy ? getMPPhotoUrl(statement.madeBy) : null;

  // Party color for accent
  const getPartyColor = (party?: string) => {
    const colors: Record<string, string> = {
      Liberal: '#DC2626', // Red
      Conservative: '#2563EB', // Blue
      NDP: '#F59E0B', // Orange
      'Bloc Québécois': '#3B82F6', // Light blue
      Green: '#10B981', // Green
    };
    return colors[party || ''] || '#666';
  };

  const handleMPClick = () => {
    if (statement.madeBy) {
      router.push(`/${locale}/mps/${statement.madeBy.id}`);
    }
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `${statement.madeBy?.name} - CanadaGPT`,
          text: preview,
          url: `${window.location.origin}/${locale}/debates/${statement.partOf?.id}#${statement.id}`,
        });
      } catch (err) {
        console.error('Share failed:', err);
      }
    }
  };

  return (
    <div
      className="mobile-statement-card"
      {...swipeHandlers}
      style={{
        borderLeft: `4px solid ${getPartyColor(statement.madeBy?.party)}`,
      }}
    >
      {/* Header */}
      <div className="mobile-statement-header" onClick={handleMPClick}>
        {mpPhotoUrl && (
          <img
            src={mpPhotoUrl}
            alt={statement.madeBy?.name}
            className="mobile-statement-avatar"
          />
        )}
        <div className="mobile-statement-meta">
          <div className="mobile-statement-name">
            {statement.madeBy?.name || 'Unknown Speaker'}
            {statement.madeBy?.party && (
              <PartyLogo party={statement.madeBy.party} size="sm" />
            )}
          </div>
          {statement.partOf?.date && (
            <div className="mobile-statement-date">
              <Calendar className="h-3 w-3" />
              {new Date(statement.partOf.date).toLocaleDateString()}
            </div>
          )}
        </div>
      </div>

      {/* Topic Tags */}
      {(statement.h1_en || statement.h2_en) && (
        <div className="mobile-statement-topics">
          {statement.h1_en && (
            <span className="mobile-statement-topic primary">{statement.h1_en}</span>
          )}
          {statement.h2_en && (
            <span className="mobile-statement-topic secondary">{statement.h2_en}</span>
          )}
        </div>
      )}

      {/* Content */}
      <div className="mobile-statement-content">
        <p className="mobile-statement-text">
          {isExpanded ? content : preview}
        </p>
        {shouldShowReadMore && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="mobile-statement-read-more"
          >
            {isExpanded ? 'Show less' : 'Read more'}
          </button>
        )}
      </div>

      {/* Footer Actions */}
      <div className="mobile-statement-actions">
        <div className="mobile-statement-stats">
          {statement.wordcount && (
            <span className="mobile-statement-stat">
              <Hash className="h-4 w-4" />
              {statement.wordcount}
            </span>
          )}
          {statement.partOf?.document_type && (
            <span className="mobile-statement-badge">
              {statement.partOf.document_type === 'D' ? 'Debate' : 'Committee'}
            </span>
          )}
        </div>

        <div className="mobile-statement-buttons">
          <button
            onClick={() => setIsLiked(!isLiked)}
            className={`mobile-statement-action ${isLiked ? 'active' : ''}`}
            aria-label="Like"
          >
            <Heart className={`h-5 w-5 ${isLiked ? 'fill-current' : ''}`} />
          </button>

          <button
            className="mobile-statement-action"
            aria-label="Comment"
          >
            <MessageCircle className="h-5 w-5" />
          </button>

          <button
            onClick={handleShare}
            className="mobile-statement-action"
            aria-label="Share"
          >
            <Share2 className="h-5 w-5" />
          </button>

          <button
            onClick={() => setIsBookmarked(!isBookmarked)}
            className={`mobile-statement-action ${isBookmarked ? 'active' : ''}`}
            aria-label="Bookmark"
          >
            <Bookmark className={`h-5 w-5 ${isBookmarked ? 'fill-current' : ''}`} />
          </button>
        </div>
      </div>
    </div>
  );
}
