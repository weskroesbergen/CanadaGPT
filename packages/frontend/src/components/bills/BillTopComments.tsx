'use client';

import { Card } from '@canadagpt/design-system';
import { TrendingUp, Flame, ThumbsUp, ThumbsDown, MessageSquare } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import { useEffect, useState } from 'react';
import { getPosts } from '@/actions/forum';
import type { ForumPost } from '@/types/forum';
import { formatDistanceToNow } from 'date-fns';
import { fr, enUS } from 'date-fns/locale';

interface BillTopCommentsProps {
  billNumber: string;
  session: string;
  locale: string;
}

export function BillTopComments({ billNumber, session, locale }: BillTopCommentsProps) {
  const [topComments, setTopComments] = useState<ForumPost[]>([]);
  const [controversialComments, setControversialComments] = useState<ForumPost[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchComments = async () => {
      setLoading(true);

      // Fetch top 3 most upvoted
      const topResult = await getPosts({
        bill_number: billNumber,
        bill_session: session,
        post_type: 'bill_comment',
        sort: 'top',
        limit: 3,
        offset: 0
      });

      // Fetch top 3 most controversial
      const controversialResult = await getPosts({
        bill_number: billNumber,
        bill_session: session,
        post_type: 'bill_comment',
        sort: 'controversial',
        limit: 3,
        offset: 0
      });

      if (topResult.success && topResult.data) {
        setTopComments(topResult.data.data);
      }

      if (controversialResult.success && controversialResult.data) {
        setControversialComments(controversialResult.data.data);
      }

      setLoading(false);
    };

    fetchComments();
  }, [billNumber, session]);

  const dateLocale = locale === 'fr' ? fr : enUS;

  // Don't show card if no comments
  if (!loading && topComments.length === 0 && controversialComments.length === 0) {
    return null;
  }

  return (
    <Card className="mb-6">
      <div className="flex items-center mb-4">
        <TrendingUp className="h-5 w-5 mr-2 text-accent-red" />
        <h3 className="text-xl font-bold text-text-primary">
          {locale === 'fr' ? 'Points forts de la communauté' : 'Community Highlights'}
        </h3>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Comments Section */}
        {topComments.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center">
              <ThumbsUp className="h-4 w-4 mr-2 text-green-400" />
              {locale === 'fr' ? 'Commentaires les plus populaires' : 'Top Comments'}
            </h4>
            <div className="space-y-3">
              {topComments.map((comment) => (
                <Link
                  key={comment.id}
                  href={`/bills/${session}/${billNumber}?tab=fulltext#comment-${comment.id}` as any}
                  className="block p-3 rounded-lg bg-bg-elevated border border-border-subtle hover:border-accent-red/30 transition-all"
                >
                  {/* Author & timestamp */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {comment.author_avatar_url && (
                        <img
                          src={comment.author_avatar_url}
                          alt={comment.author_name || 'User'}
                          className="w-6 h-6 rounded-full"
                        />
                      )}
                      <span className="text-sm font-medium text-text-primary">
                        {comment.author_name || 'Anonymous'}
                      </span>
                    </div>
                    <span className="text-xs text-text-tertiary">
                      {formatDistanceToNow(new Date(comment.created_at), {
                        addSuffix: true,
                        locale: dateLocale
                      })}
                    </span>
                  </div>

                  {/* Comment preview */}
                  <p className="text-sm text-text-secondary line-clamp-2 mb-2">
                    {comment.content}
                  </p>

                  {/* Engagement metrics */}
                  <div className="flex items-center gap-4 text-xs text-text-tertiary">
                    <span className="flex items-center gap-1 text-green-400">
                      <ThumbsUp className="h-3 w-3" />
                      {comment.upvotes_count}
                    </span>
                    <span className="flex items-center gap-1 text-red-400">
                      <ThumbsDown className="h-3 w-3" />
                      {comment.downvotes_count}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="h-3 w-3" />
                      {comment.reply_count}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Controversial Comments Section */}
        {controversialComments.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center">
              <Flame className="h-4 w-4 mr-2 text-orange-400" />
              {locale === 'fr' ? 'Commentaires controversés' : 'Most Controversial'}
            </h4>
            <div className="space-y-3">
              {controversialComments.map((comment) => (
                <Link
                  key={comment.id}
                  href={`/bills/${session}/${billNumber}?tab=fulltext#comment-${comment.id}` as any}
                  className="block p-3 rounded-lg bg-bg-elevated border border-border-subtle hover:border-accent-red/30 transition-all"
                >
                  {/* Author & timestamp */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {comment.author_avatar_url && (
                        <img
                          src={comment.author_avatar_url}
                          alt={comment.author_name || 'User'}
                          className="w-6 h-6 rounded-full"
                        />
                      )}
                      <span className="text-sm font-medium text-text-primary">
                        {comment.author_name || 'Anonymous'}
                      </span>
                    </div>
                    <span className="text-xs text-text-tertiary">
                      {formatDistanceToNow(new Date(comment.created_at), {
                        addSuffix: true,
                        locale: dateLocale
                      })}
                    </span>
                  </div>

                  {/* Comment preview */}
                  <p className="text-sm text-text-secondary line-clamp-2 mb-2">
                    {comment.content}
                  </p>

                  {/* Engagement metrics */}
                  <div className="flex items-center gap-4 text-xs text-text-tertiary">
                    <span className="flex items-center gap-1 text-green-400">
                      <ThumbsUp className="h-3 w-3" />
                      {comment.upvotes_count}
                    </span>
                    <span className="flex items-center gap-1 text-red-400">
                      <ThumbsDown className="h-3 w-3" />
                      {comment.downvotes_count}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="h-3 w-3" />
                      {comment.reply_count}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>

      {loading && (
        <div className="text-center py-8 text-text-tertiary">
          {locale === 'fr' ? 'Chargement...' : 'Loading...'}
        </div>
      )}
    </Card>
  );
}
