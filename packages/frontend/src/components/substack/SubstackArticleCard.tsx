/**
 * Substack Article Card Component
 *
 * Displays individual Substack article in tile format
 */

import { formatDistanceToNow } from 'date-fns';
import Image from 'next/image';
import Link from 'next/link';
import { ExternalLink, Clock, Star } from 'lucide-react';

export interface SubstackArticle {
  id: string;
  title: string;
  author: string;
  article_url: string;
  published_at: string;
  excerpt: string;
  content_html: string;
  cover_image_url: string | null;
  word_count: number;
  read_time_minutes: number;
  is_featured: boolean;
  featured_order: number | null;
}

interface SubstackArticleCardProps {
  article: SubstackArticle;
  showFeaturedBadge?: boolean;
  compact?: boolean;
}

export function SubstackArticleCard({
  article,
  showFeaturedBadge = false,
  compact = false,
}: SubstackArticleCardProps) {
  const publishedDate = formatDistanceToNow(new Date(article.published_at), {
    addSuffix: true,
  });

  return (
    <Link
      href={article.article_url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block h-full"
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md hover:shadow-xl transition-shadow duration-200 overflow-hidden h-full flex flex-col">
        {/* Cover Image */}
        {article.cover_image_url && (
          <div className={`relative w-full ${compact ? 'h-40' : 'h-48'} bg-gray-200 dark:bg-gray-700`}>
            <Image
              src={article.cover_image_url}
              alt={article.title}
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-200"
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            />
            {showFeaturedBadge && article.is_featured && (
              <div className="absolute top-2 right-2 bg-yellow-500 text-white px-2 py-1 rounded-md text-xs font-semibold flex items-center gap-1">
                <Star className="w-3 h-3" />
                Featured
              </div>
            )}
          </div>
        )}

        {/* Content */}
        <div className="p-4 flex-1 flex flex-col">
          {/* Title */}
          <h3 className={`font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2 ${
            compact ? 'text-base' : 'text-lg'
          }`}>
            {article.title}
            <ExternalLink className="inline-block w-3 h-3 ml-1 opacity-0 group-hover:opacity-100 transition-opacity" />
          </h3>

          {/* Excerpt */}
          {!compact && (
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 line-clamp-3 flex-1">
              {article.excerpt}
            </p>
          )}

          {/* Metadata */}
          <div className="mt-3 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {article.read_time_minutes} min read
              </span>
              <span>{publishedDate}</span>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
