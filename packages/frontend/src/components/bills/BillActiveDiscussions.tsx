'use client';

import { useEffect, useState } from 'react';
import { Card } from '@canadagpt/design-system';
import { MessageSquare, ThumbsUp, ArrowRight } from 'lucide-react';
import { getPosts } from '@/actions/forum';
import { formatDistanceToNow } from 'date-fns';
import { fr, enUS } from 'date-fns/locale';
import type { ForumPost } from '@/types/forum';

interface BillActiveDiscussionsProps {
  billNumber: string;
  session: string;
  locale: string;
  onViewAll?: () => void;
}

export function BillActiveDiscussions({
  billNumber,
  session,
  locale,
  onViewAll,
}: BillActiveDiscussionsProps) {
  const [threads, setThreads] = useState<ForumPost[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const dateLocale = locale === 'fr' ? fr : enUS;

  useEffect(() => {
    const fetchActiveThreads = async () => {
      setLoading(true);

      const result = await getPosts({
        post_type: 'bill_comment',
        bill_number: billNumber,
        bill_session: session,
        sort_by: 'top',
        limit: 5,
        offset: 0,
      });

      if (result.success && result.data) {
        setThreads(result.data.data || []);
        setTotalCount(result.data.total || 0);
      }

      setLoading(false);
    };

    fetchActiveThreads();
  }, [billNumber, session]);

  if (loading) {
    return (
      <Card className="mb-6">
        <div className="flex items-center mb-4">
          <MessageSquare className="h-5 w-5 mr-2 text-accent-red" />
          <h3 className="text-xl font-bold text-text-primary">
            {locale === 'fr' ? 'Discussions actives' : 'Active Discussions'}
          </h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-4 rounded-lg bg-bg-elevated border border-border-subtle animate-pulse"
            >
              <div className="h-4 bg-border-subtle rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-border-subtle rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  if (threads.length === 0) {
    return null; // Don't show if no discussions
  }

  return (
    <Card className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <MessageSquare className="h-5 w-5 mr-2 text-accent-red" />
          <h3 className="text-xl font-bold text-text-primary">
            {locale === 'fr' ? 'Discussions actives' : 'Active Discussions'}
          </h3>
        </div>
        {totalCount > 5 && (
          <button
            onClick={onViewAll}
            className="text-sm text-accent-red hover:underline flex items-center gap-1"
          >
            {locale === 'fr' ? 'Voir tout' : 'View all'} ({totalCount})
            <ArrowRight className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="space-y-3">
        {threads.map((thread) => {
          const preview =
            thread.content.length > 120
              ? thread.content.slice(0, 120) + '...'
              : thread.content;

          const timeAgo = formatDistanceToNow(new Date(thread.created_at), {
            addSuffix: true,
            locale: dateLocale,
          });

          return (
            <div
              key={thread.id}
              className="p-4 rounded-lg bg-bg-elevated border border-border-subtle hover:border-accent-red/30 transition-all cursor-pointer group"
            >
              {/* Author and time */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-full bg-accent-red/20 flex items-center justify-center text-accent-red text-sm font-medium">
                    {thread.author?.display_name?.[0]?.toUpperCase() || '?'}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-text-primary">
                      {thread.author?.display_name || 'Anonymous'}
                    </div>
                    <div className="text-xs text-text-tertiary">{timeAgo}</div>
                  </div>
                </div>

                {/* Engagement metrics */}
                <div className="flex items-center gap-3">
                  {thread.reply_count > 0 && (
                    <div className="flex items-center gap-1 text-text-secondary">
                      <MessageSquare className="h-4 w-4" />
                      <span className="text-sm">{thread.reply_count}</span>
                    </div>
                  )}
                  {thread.upvotes_count > 0 && (
                    <div className="flex items-center gap-1 text-green-400">
                      <ThumbsUp className="h-4 w-4" />
                      <span className="text-sm">{thread.upvotes_count}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Thread preview */}
              <p className="text-sm text-text-secondary group-hover:text-text-primary transition-colors">
                {preview}
              </p>
            </div>
          );
        })}
      </div>

      {totalCount > 5 && (
        <div className="mt-4 flex justify-center">
          <button
            onClick={onViewAll}
            className="px-6 py-2 rounded-lg bg-accent-red/10 text-accent-red hover:bg-accent-red/20 transition-colors flex items-center gap-2"
          >
            {locale === 'fr'
              ? 'Voir toutes les discussions'
              : 'View All Discussions'}
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </Card>
  );
}
