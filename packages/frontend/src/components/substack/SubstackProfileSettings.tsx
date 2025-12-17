/**
 * Substack Profile Settings Component
 *
 * Allows users to manage their Substack integration settings
 */

'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, ExternalLink, RefreshCw, Star, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { SubstackArticle } from './SubstackArticleCard';

interface SubstackProfile {
  user_id: string;
  substack_url: string;
  rss_feed_url: string;
  author_name: string | null;
  auto_import_enabled: boolean;
  last_imported_at: string | null;
  import_frequency_hours: number;
  subscribe_button_enabled: boolean;
  subscribe_button_text: string;
  show_on_profile: boolean;
  articles_per_page: number;
}

export function SubstackProfileSettings() {
  const [profile, setProfile] = useState<SubstackProfile | null>(null);
  const [articles, setArticles] = useState<SubstackArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Form state
  const [substackUrl, setSubstackUrl] = useState('');
  const [autoImportEnabled, setAutoImportEnabled] = useState(true);
  const [importFrequencyHours, setImportFrequencyHours] = useState(24);
  const [subscribeButtonEnabled, setSubscribeButtonEnabled] = useState(true);
  const [subscribeButtonText, setSubscribeButtonText] = useState('Subscribe');
  const [showOnProfile, setShowOnProfile] = useState(true);
  const [articlesPerPage, setArticlesPerPage] = useState(10);

  useEffect(() => {
    fetchProfile();
  }, []);

  async function fetchProfile() {
    try {
      const response = await fetch('/api/substack/profile');
      if (!response.ok) {
        throw new Error('Failed to fetch profile');
      }

      const data = await response.json();
      if (data.profile) {
        setProfile(data.profile);
        setSubstackUrl(data.profile.substack_url);
        setAutoImportEnabled(data.profile.auto_import_enabled);
        setImportFrequencyHours(data.profile.import_frequency_hours);
        setSubscribeButtonEnabled(data.profile.subscribe_button_enabled);
        setSubscribeButtonText(data.profile.subscribe_button_text);
        setShowOnProfile(data.profile.show_on_profile);
        setArticlesPerPage(data.profile.articles_per_page);

        // Fetch articles for featured selection
        await fetchArticles();
      }
    } catch (err) {
      console.error('Error fetching profile:', err);
      toast.error('Failed to load Substack settings');
    } finally {
      setLoading(false);
    }
  }

  async function fetchArticles() {
    try {
      const response = await fetch('/api/substack/articles?limit=50&offset=0');
      if (response.ok) {
        const data = await response.json();
        setArticles(data.articles || []);
      }
    } catch (err) {
      console.error('Error fetching articles:', err);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      const response = await fetch('/api/substack/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          substack_url: substackUrl,
          auto_import_enabled: autoImportEnabled,
          import_frequency_hours: importFrequencyHours,
          subscribe_button_enabled: subscribeButtonEnabled,
          subscribe_button_text: subscribeButtonText,
          show_on_profile: showOnProfile,
          articles_per_page: articlesPerPage,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to save settings');
      }

      const data = await response.json();
      setProfile(data.profile);
      toast.success('Substack settings saved!');
    } catch (err) {
      console.error('Error saving settings:', err);
      toast.error(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  }

  async function handleImport() {
    setImporting(true);
    try {
      const response = await fetch('/api/substack/import', {
        method: 'POST',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Import failed');
      }

      const data = await response.json();
      toast.success(
        `Import complete! ${data.imported_count} new, ${data.updated_count} updated, ${data.skipped_count} skipped`
      );

      // Refresh articles list
      await fetchArticles();
      await fetchProfile();
    } catch (err) {
      console.error('Error importing articles:', err);
      toast.error(err instanceof Error ? err.message : 'Failed to import articles');
    } finally {
      setImporting(false);
    }
  }

  async function handleDelete() {
    if (
      !confirm(
        'Are you sure you want to disconnect your Substack? All imported articles will be deleted.'
      )
    ) {
      return;
    }

    setDeleting(true);
    try {
      const response = await fetch('/api/substack/profile', {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete profile');
      }

      setProfile(null);
      setArticles([]);
      toast.success('Substack profile disconnected');
    } catch (err) {
      console.error('Error deleting profile:', err);
      toast.error('Failed to disconnect Substack');
    } finally {
      setDeleting(false);
    }
  }

  async function handleToggleFeatured(articleId: string, isFeatured: boolean) {
    try {
      if (isFeatured) {
        // Unfeature
        const response = await fetch(
          `/api/substack/featured?article_id=${articleId}`,
          { method: 'DELETE' }
        );

        if (!response.ok) {
          throw new Error('Failed to unfeature article');
        }

        toast.success('Article removed from featured');
      } else {
        // Feature
        const response = await fetch('/api/substack/featured', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ article_id: articleId }),
        });

        if (!response.ok) {
          throw new Error('Failed to feature article');
        }

        toast.success('Article featured!');
      }

      // Refresh articles
      await fetchArticles();
    } catch (err) {
      console.error('Error toggling featured:', err);
      toast.error(err instanceof Error ? err.message : 'Failed to update featured status');
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
        Substack Integration
      </h1>

      {/* Profile Form */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Substack Settings
        </h2>

        <div className="space-y-4">
          {/* Substack URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Substack URL
            </label>
            <input
              type="url"
              value={substackUrl}
              onChange={(e) => setSubstackUrl(e.target.value)}
              placeholder="https://username.substack.com"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Your Substack publication URL
            </p>
          </div>

          {/* Auto Import */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="auto-import"
              checked={autoImportEnabled}
              onChange={(e) => setAutoImportEnabled(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <label htmlFor="auto-import" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Enable automatic article import
            </label>
          </div>

          {/* Import Frequency */}
          {autoImportEnabled && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Import Frequency (hours)
              </label>
              <input
                type="number"
                value={importFrequencyHours}
                onChange={(e) => setImportFrequencyHours(parseInt(e.target.value))}
                min="1"
                max="168"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          )}

          {/* Subscribe Button */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="subscribe-button"
              checked={subscribeButtonEnabled}
              onChange={(e) => setSubscribeButtonEnabled(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <label htmlFor="subscribe-button" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Show subscribe button on profile
            </label>
          </div>

          {/* Subscribe Button Text */}
          {subscribeButtonEnabled && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Subscribe Button Text
              </label>
              <input
                type="text"
                value={subscribeButtonText}
                onChange={(e) => setSubscribeButtonText(e.target.value)}
                placeholder="Subscribe"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          )}

          {/* Show on Profile */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="show-on-profile"
              checked={showOnProfile}
              onChange={(e) => setShowOnProfile(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <label htmlFor="show-on-profile" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Display articles on profile
            </label>
          </div>

          {/* Articles Per Page */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Articles Per Page
            </label>
            <input
              type="number"
              value={articlesPerPage}
              onChange={(e) => setArticlesPerPage(parseInt(e.target.value))}
              min="5"
              max="50"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 mt-6">
          <Button onClick={handleSave} disabled={saving || !substackUrl}>
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Settings'
            )}
          </Button>

          {profile && (
            <>
              <Button variant="outline" onClick={handleImport} disabled={importing}>
                {importing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Importing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Import Now
                  </>
                )}
              </Button>

              <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
                {deleting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4 mr-2" />
                    Disconnect
                  </>
                )}
              </Button>
            </>
          )}
        </div>

        {profile?.last_imported_at && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-4">
            Last imported:{' '}
            {new Date(profile.last_imported_at).toLocaleString()}
          </p>
        )}
      </div>

      {/* Featured Articles Management */}
      {profile && articles.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Featured Articles
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Select up to 3 articles to feature prominently on your profile. Click the star to
            toggle featured status.
          </p>

          <div className="space-y-2">
            {articles.map((article) => (
              <div
                key={article.id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-md"
              >
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900 dark:text-white text-sm">
                    {article.title}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {new Date(article.published_at).toLocaleDateString()}
                  </p>
                </div>

                <button
                  onClick={() => handleToggleFeatured(article.id, article.is_featured)}
                  className={`p-2 rounded-md transition-colors ${
                    article.is_featured
                      ? 'bg-yellow-500 text-white hover:bg-yellow-600'
                      : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-500'
                  }`}
                  title={article.is_featured ? 'Remove from featured' : 'Add to featured'}
                >
                  <Star className="w-4 h-4" fill={article.is_featured ? 'currentColor' : 'none'} />
                </button>

                <a
                  href={article.article_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-2 p-2 text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
                  title="View article"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
