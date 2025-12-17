/**
 * Substack Featured Articles Component
 *
 * Displays up to 3 featured articles prominently on profile
 */

'use client';

import { useEffect, useState } from 'react';
import { SubstackArticle, SubstackArticleCard } from './SubstackArticleCard';
import { Loader2 } from 'lucide-react';

interface SubstackFeaturedArticlesProps {
  username: string;
}

interface SubstackProfile {
  substack_url: string;
  author_name: string | null;
  subscribe_button_enabled: boolean;
  subscribe_button_text: string;
}

export function SubstackFeaturedArticles({ username }: SubstackFeaturedArticlesProps) {
  const [articles, setArticles] = useState<SubstackArticle[]>([]);
  const [profile, setProfile] = useState<SubstackProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchFeaturedArticles() {
      try {
        const response = await fetch(
          `/api/substack/articles?username=${username}&featured_only=true&limit=3`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch articles');
        }

        const data = await response.json();
        setArticles(data.articles || []);
        setProfile(data.profile);
      } catch (err) {
        console.error('Error fetching featured articles:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    fetchFeaturedArticles();
  }, [username]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error || !profile) {
    return null; // Don't show section if there's an error or no Substack profile
  }

  if (articles.length === 0) {
    return null; // Don't show section if no featured articles
  }

  return (
    <div className="bg-gradient-to-br from-orange-50 to-red-50 dark:from-gray-800 dark:to-gray-900 rounded-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Featured Articles
          </h2>
          {profile.author_name && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              by {profile.author_name}
            </p>
          )}
        </div>

        {/* Subscribe Button */}
        {profile.subscribe_button_enabled && (
          <a
            href={profile.substack_url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-lg transition-colors"
          >
            {profile.subscribe_button_text || 'Subscribe'}
          </a>
        )}
      </div>

      {/* Featured Articles Grid */}
      <div className={`grid gap-4 ${
        articles.length === 1
          ? 'grid-cols-1 md:grid-cols-1'
          : articles.length === 2
          ? 'grid-cols-1 md:grid-cols-2'
          : 'grid-cols-1 md:grid-cols-3'
      }`}>
        {articles.map((article) => (
          <SubstackArticleCard
            key={article.id}
            article={article}
            showFeaturedBadge={true}
          />
        ))}
      </div>

      {/* View All Link */}
      <div className="mt-4 text-center">
        <a
          href={profile.substack_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-orange-600 dark:text-orange-400 hover:underline font-medium"
        >
          View all articles on Substack →
        </a>
      </div>
    </div>
  );
}
