/**
 * Substack Articles List Component
 *
 * Displays full list of articles with pagination
 */

'use client';

import { useEffect, useState } from 'react';
import { SubstackArticle, SubstackArticleCard } from './SubstackArticleCard';
import { Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SubstackArticlesListProps {
  username: string;
  articlesPerPage?: number;
}

interface SubstackProfile {
  substack_url: string;
  author_name: string | null;
  articles_per_page: number;
}

export function SubstackArticlesList({
  username,
  articlesPerPage = 10,
}: SubstackArticlesListProps) {
  const [articles, setArticles] = useState<SubstackArticle[]>([]);
  const [profile, setProfile] = useState<SubstackProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);

  const limit = profile?.articles_per_page || articlesPerPage;
  const offset = page * limit;

  useEffect(() => {
    async function fetchArticles() {
      setLoading(true);
      try {
        const response = await fetch(
          `/api/substack/articles?username=${username}&limit=${limit}&offset=${offset}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch articles');
        }

        const data = await response.json();
        setArticles(data.articles || []);
        setProfile(data.profile);
        setHasMore(data.hasMore || false);
        setTotalCount(data.count || 0);
      } catch (err) {
        console.error('Error fetching articles:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    fetchArticles();
  }, [username, limit, offset, page]);

  if (loading && page === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  if (!profile) {
    return null; // No Substack profile
  }

  if (articles.length === 0 && page === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 dark:text-gray-400">
          No articles published yet.
        </p>
        <a
          href={profile.substack_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-orange-600 dark:text-orange-400 hover:underline mt-2 inline-block"
        >
          Visit their Substack →
        </a>
      </div>
    );
  }

  const totalPages = Math.ceil(totalCount / limit);
  const currentPage = page + 1;

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          All Articles
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {totalCount} {totalCount === 1 ? 'article' : 'articles'} published
        </p>
      </div>

      {/* Articles Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
        {articles.map((article) => (
          <SubstackArticleCard
            key={article.id}
            article={article}
            showFeaturedBadge={true}
            compact={false}
          />
        ))}
      </div>

      {/* Loading indicator for pagination */}
      {loading && page > 0 && (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-8">
          <Button
            variant="outline"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || loading}
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Previous
          </Button>

          <span className="text-sm text-gray-600 dark:text-gray-400">
            Page {currentPage} of {totalPages}
          </span>

          <Button
            variant="outline"
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasMore || loading}
          >
            Next
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  );
}
