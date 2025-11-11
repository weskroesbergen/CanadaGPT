/**
 * ThreadedSpeechCard Component
 * Displays a conversation thread with connected cards design
 */

'use client';

import React, { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { ChevronDown, ChevronUp, MessageSquare, User, Calendar, Hash, CheckCircle } from 'lucide-react';
import { format } from 'date-fns';
import { fr, enUS } from 'date-fns/locale';
import { getBilingualContent } from '@/hooks/useBilingual';
import { ShareButton } from '../ShareButton';
import { PrintableCard } from '../PrintableCard';
import { getMPPhotoUrl } from '@/lib/utils/mpPhotoUrl';
import { useChatStore } from '@/lib/stores/chatStore';
import { BookmarkButton } from '../bookmarks/BookmarkButton';

interface Statement {
  id: string;
  time?: string;
  who_en?: string;
  who_fr?: string;
  content_en?: string;
  content_fr?: string;
  h2_en?: string;
  h2_fr?: string;
  h3_en?: string;
  h3_fr?: string;
  statement_type?: string;
  wordcount?: number;
  madeBy?: {
    id: string;
    name: string;
    party: string;
    photo_url?: string;
  };
  replyTo?: Statement;
  replies?: Statement[];
}

interface ThreadedSpeechCardProps {
  rootStatement: Statement;
  replies?: Statement[];
  defaultExpanded?: boolean;
  showContext?: boolean;
  onStatementClick?: (statement: Statement) => void;
  className?: string;
}

// Party color mapping
const getPartyColors = (party: string) => {
  const partyLower = party?.toLowerCase() || '';

  if (partyLower.includes('liberal')) {
    return {
      bg: 'bg-red-50/80 dark:bg-red-950/30',
      border: 'border-red-400 dark:border-red-700',
      line: 'stroke-red-500',
      badge: 'bg-red-100 text-red-800 dark:bg-red-900/60 dark:text-red-200',
    };
  }
  if (partyLower.includes('conservative')) {
    return {
      bg: 'bg-blue-50/80 dark:bg-blue-950/30',
      border: 'border-blue-400 dark:border-blue-700',
      line: 'stroke-blue-500',
      badge: 'bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200',
    };
  }
  if (partyLower.includes('ndp') || partyLower.includes('new democratic')) {
    return {
      bg: 'bg-orange-50/80 dark:bg-orange-950/30',
      border: 'border-orange-400 dark:border-orange-700',
      line: 'stroke-orange-500',
      badge: 'bg-orange-100 text-orange-800 dark:bg-orange-900/60 dark:text-orange-200',
    };
  }
  if (partyLower.includes('bloc')) {
    return {
      bg: 'bg-cyan-50/80 dark:bg-cyan-950/30',
      border: 'border-cyan-400 dark:border-cyan-700',
      line: 'stroke-cyan-500',
      badge: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/60 dark:text-cyan-200',
    };
  }
  if (partyLower.includes('green')) {
    return {
      bg: 'bg-green-50/80 dark:bg-green-950/30',
      border: 'border-green-400 dark:border-green-700',
      line: 'stroke-green-500',
      badge: 'bg-green-100 text-green-800 dark:bg-green-900/60 dark:text-green-200',
    };
  }

  // Default/Independent
  return {
    bg: 'bg-gray-50/80 dark:bg-gray-950/30',
    border: 'border-gray-400 dark:border-gray-600',
    line: 'stroke-gray-500',
    badge: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  };
};

// Statement type badge
const getStatementTypeBadge = (type?: string) => {
  switch (type?.toLowerCase()) {
    case 'question':
      return { label: 'Question', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300' };
    case 'answer':
      return { label: 'Answer', color: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' };
    case 'interjection':
      return { label: 'Interjection', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' };
    case 'debate':
      return { label: 'Debate', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' };
    default:
      return { label: 'Statement', color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' };
  }
};

/**
 * Individual statement card
 */
const StatementCard = React.memo(function StatementCard({
  statement,
  isReply = false,
  onClick,
}: {
  statement: Statement;
  isReply?: boolean;
  onClick?: () => void;
}) {
  const locale = useLocale();
  const dateLocale = locale === 'fr' ? fr : enUS;
  const bilingualStatement = getBilingualContent(statement, locale);

  const [isFactChecking, setIsFactChecking] = useState(false);
  const { sendMessage, toggleOpen, setContext, isOpen } = useChatStore();

  const party = statement.madeBy?.party || '';
  const colors = getPartyColors(party);
  const typeBadge = getStatementTypeBadge(statement.statement_type);

  // Get photo URL from GCS or fallback to ID-based construction
  const photoUrl = statement.madeBy ? getMPPhotoUrl(statement.madeBy) : null;
  const [imageError, setImageError] = React.useState(false);

  // Share data - use dedicated share route for rich social media previews
  const shareUrl = `/${locale}/share/speech/${statement.id}`;
  const shareTitle = `${statement.madeBy?.name || bilingualStatement.who} - ${typeBadge.label}`;
  const shareDescription = bilingualStatement.content
    ? bilingualStatement.content.substring(0, 150) + (bilingualStatement.content.length > 150 ? '...' : '')
    : '';

  // Fact-check handler
  const handleFactCheck = async () => {
    setIsFactChecking(true);

    try {
      // Get localized content
      const content = locale === 'fr' ? statement.content_fr : statement.content_en;
      const speaker = statement.madeBy?.name ||
                     (locale === 'fr' ? statement.who_fr : statement.who_en);
      const date = statement.time ?
                  new Date(statement.time).toLocaleDateString() :
                  'Unknown date';

      // Build parent context if exists
      let parentContext = '';
      if (statement.replyTo) {
        const parentContent = locale === 'fr' ?
                            statement.replyTo.content_fr :
                            statement.replyTo.content_en;
        const parentSpeaker = statement.replyTo.madeBy?.name ||
                            (locale === 'fr' ? statement.replyTo.who_fr : statement.replyTo.who_en);

        parentContext = `\n\nContext - Previous statement this is responding to:
Speaker: ${parentSpeaker} (${statement.replyTo.madeBy?.party || 'Unknown'})
Statement: "${parentContent}"
`;
      }

      // Build fact-check prompt
      const prompt = `Please act as a professional fact-checker and verify this parliamentary statement:

Speaker: ${speaker} (${statement.madeBy?.party || 'Unknown'})
Date: ${date}
Type: ${statement.statement_type || 'Unknown'}
${parentContext}

Statement to fact-check:
"${content}"

Please verify:
1. Any factual claims made
2. Statistics or numbers cited
3. References to legislation, bills, or votes
4. Claims about other MPs' positions or actions
5. Historical or contextual accuracy

Use Hansard records, bills, votes, and other parliamentary data to support your analysis. Provide sources for your verification.`;

      // Set context for AI
      setContext('general', statement.id, {
        statement_id: statement.id,
        speaker: speaker,
        party: statement.madeBy?.party,
        statement_type: statement.statement_type,
        action: 'fact_check'
      });

      // Open chat if closed
      if (!isOpen) {
        toggleOpen();
      }

      // Send message
      await sendMessage(prompt);
    } finally {
      setIsFactChecking(false);
    }
  };

  return (
    <PrintableCard>
      <article
      className={`
        relative
        ${isReply ? 'ml-8 mt-3' : ''}
        ${colors.bg} ${colors.border} border-l-4 border
        rounded-lg p-4 shadow-sm
        transition-all hover:shadow-md cursor-pointer
        focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2
      `}
      onClick={onClick}
      onKeyDown={(e: React.KeyboardEvent) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? 'button' : undefined}
      aria-label={`${isReply ? 'Reply from' : 'Statement by'} ${bilingualStatement.who}, ${statement.wordcount} words`}
    >
      {/* Action Buttons - Top Right */}
      <div className="absolute top-3 right-3 z-20 flex gap-2" onClick={(e) => e.stopPropagation()}>
        {/* Fact-Check Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleFactCheck();
          }}
          disabled={isFactChecking}
          className={`rounded-lg border-2 p-2 shadow-md transition-colors
                      bg-white dark:bg-gray-900
                      ${isFactChecking
                        ? 'border-accent-blue text-accent-blue animate-pulse cursor-wait shadow-lg'
                        : 'border-border text-text-secondary hover:text-accent-blue hover:border-accent-blue hover:shadow-lg'
                      }`}
          title="Fact-check this statement"
          aria-label="Fact-check this statement"
        >
          <CheckCircle size={18} />
        </button>

        {/* Bookmark Button */}
        <BookmarkButton
          bookmarkData={{
            itemType: 'statement',
            itemId: statement.id,
            title: shareTitle,
            subtitle: `${bilingualStatement.content?.substring(0, 100)}...`,
            imageUrl: photoUrl || undefined,
            url: shareUrl,
            metadata: {
              speaker: statement.madeBy?.name || bilingualStatement.who,
              party: statement.madeBy?.party,
              statement_type: statement.statement_type,
              wordcount: statement.wordcount,
              time: statement.time,
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

      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3 pr-40">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Avatar */}
          {photoUrl && !imageError ? (
            <img
              src={photoUrl}
              alt={statement.madeBy?.name || 'MP'}
              className="w-10 h-10 rounded-lg object-cover flex-shrink-0"
              style={{ objectPosition: 'center -3px' }}
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-10 h-10 rounded-lg bg-bg-tertiary flex items-center justify-center flex-shrink-0">
              <User className="h-5 w-5 text-text-tertiary" />
            </div>
          )}

          {/* Speaker info */}
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-gray-900 dark:text-gray-100 truncate">
              {statement.madeBy?.name || bilingualStatement.who || 'Unknown Speaker'}
            </div>
            <div className="flex items-center gap-2 flex-wrap text-xs text-gray-700 dark:text-gray-300">
              {party && (
                <span className={`px-2 py-0.5 rounded-full ${colors.badge} font-medium`}>
                  {party}
                </span>
              )}
              {statement.statement_type && (
                <span className={`px-2 py-0.5 rounded-full ${typeBadge.color} font-medium`}>
                  {typeBadge.label}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Metadata */}
        <div className="flex flex-col items-end gap-1 text-xs text-gray-600 dark:text-gray-400 flex-shrink-0">
          {statement.time && (
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <time dateTime={statement.time}>
                {format(new Date(statement.time), 'PPp', { locale: dateLocale })}
              </time>
            </div>
          )}
          {statement.wordcount && (
            <div className="flex items-center gap-1">
              <Hash className="h-3 w-3" />
              <span>{statement.wordcount} words</span>
            </div>
          )}
        </div>
      </div>

      {/* Context headers (h2/h3) */}
      {(bilingualStatement.h2 || bilingualStatement.h3) && (
        <div className="mb-2 text-sm text-gray-700 dark:text-gray-300">
          {bilingualStatement.h2 && <div className="font-medium">{bilingualStatement.h2}</div>}
          {bilingualStatement.h3 && <div className="text-xs italic">{bilingualStatement.h3}</div>}
        </div>
      )}

      {/* Content */}
      <div className="text-gray-900 dark:text-gray-100 leading-relaxed">
        {bilingualStatement.content ? (
          <p className="whitespace-pre-wrap">{bilingualStatement.content}</p>
        ) : (
          <p className="text-gray-500 dark:text-gray-400 italic">No content available</p>
        )}
      </div>
      </article>
    </PrintableCard>
  );
});

/**
 * Main threaded conversation component
 */
export const ThreadedSpeechCard = React.memo(function ThreadedSpeechCard({
  rootStatement,
  replies = [],
  defaultExpanded = false,
  showContext = true,
  onStatementClick,
  className = '',
}: ThreadedSpeechCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const locale = useLocale();
  const bilingualRoot = getBilingualContent(rootStatement, locale);

  const hasReplies = replies.length > 0;
  const rootColors = getPartyColors(rootStatement.madeBy?.party || '');

  return (
    <div className={`relative ${className}`}>
      {/* Root statement */}
      <StatementCard
        statement={rootStatement}
        onClick={() => onStatementClick?.(rootStatement)}
      />

      {/* Replies toggle button */}
      {hasReplies && (
        <button
          onClick={() => setExpanded(!expanded)}
          className={`
            mt-2 ml-8 flex items-center gap-2 px-3 py-1.5 rounded-lg
            bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700
            text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-gray-100
            text-sm font-medium transition-all
            focus:outline-none focus:ring-2 focus:ring-accent-red focus:ring-offset-2
          `}
          aria-expanded={expanded}
          aria-label={`${expanded ? 'Hide' : 'Show'} ${replies.length} ${replies.length === 1 ? 'reply' : 'replies'} to this statement`}
          aria-controls={`replies-${rootStatement.id}`}
        >
          <MessageSquare className="h-4 w-4" aria-hidden="true" />
          <span>
            {expanded ? 'Hide' : 'Show'} {replies.length} {replies.length === 1 ? 'reply' : 'replies'}
          </span>
          {expanded ? <ChevronUp className="h-4 w-4" aria-hidden="true" /> : <ChevronDown className="h-4 w-4" aria-hidden="true" />}
        </button>
      )}

      {/* Replies with connection lines */}
      {hasReplies && expanded && (
        <div
          className="relative"
          id={`replies-${rootStatement.id}`}
          role="region"
          aria-label={`${replies.length} ${replies.length === 1 ? 'reply' : 'replies'} to this statement`}
        >
          {/* SVG connection lines */}
          <svg
            className="absolute left-4 top-0 h-full pointer-events-none"
            width="40"
            style={{ zIndex: 0 }}
          >
            {replies.map((reply, idx) => {
              const replyColors = getPartyColors(reply.madeBy?.party || '');
              const yStart = idx === 0 ? 20 : idx * 140 + 20; // Approximate card height
              const yEnd = yStart + 60;

              return (
                <g key={reply.id || idx}>
                  {/* Vertical line */}
                  <line
                    x1="20"
                    y1={yStart}
                    x2="20"
                    y2={yEnd}
                    className={rootColors.line}
                    strokeWidth="2"
                    strokeDasharray={reply.statement_type === 'interjection' ? '4 2' : undefined}
                  />
                  {/* Horizontal line to card */}
                  <line
                    x1="20"
                    y1={yEnd}
                    x2="40"
                    y2={yEnd}
                    className={replyColors.line}
                    strokeWidth="2"
                  />
                  {/* Connection dot */}
                  <circle
                    cx="20"
                    cy={yEnd}
                    r="4"
                    className={replyColors.line}
                    fill="currentColor"
                  />
                </g>
              );
            })}
          </svg>

          {/* Reply cards */}
          <div className="space-y-3" style={{ position: 'relative', zIndex: 1 }}>
            {replies.map((reply) => (
              <StatementCard
                key={reply.id}
                statement={reply}
                isReply
                onClick={() => onStatementClick?.(reply)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
});

/**
 * Compact version for mobile or tight spaces
 */
export function ThreadedSpeechCardCompact(props: ThreadedSpeechCardProps) {
  return <ThreadedSpeechCard {...props} showContext={false} />;
}
