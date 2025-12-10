'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { MessageSquare, Plus, Clock, TrendingUp, ArrowLeft, FileText, Users } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { PostCard, CreatePostForm, ReportModal } from '@/components/forum';
import { getPosts, deletePost } from '@/actions/forum';
import { useRealtimePosts } from '@/hooks/useRealtimePosts';
import type { ForumPost } from '@/types/forum';

/**
 * Discussion scope for section-level discussions
 */
export interface DiscussionScope {
  /** Full anchor ID (e.g., "bill:45-1:c-234:s2.1.a") */
  anchorId: string;
  /** Section reference extracted from anchor (e.g., "s2.1.a") */
  sectionRef: string;
  /** Human-readable label for the section */
  label?: string;
}

interface BillDiscussionPanelProps {
  /** Bill number (e.g., "C-234") */
  billNumber: string;
  /** Parliamentary session (e.g., "45-1") */
  session: string;
  /** Bill title for display */
  billTitle?: string;
  /** Current locale */
  locale: string;
  /** Currently selected section scope (null = whole bill) */
  selectedSection?: DiscussionScope | null;
  /** Callback to clear section selection */
  onClearSection?: () => void;
  /** Callback when a section is mentioned in a comment (for navigation) */
  onSectionMention?: (sectionRef: string) => void;
  /** Whether to show compact header */
  compactHeader?: boolean;
}

type SortOption = 'recent' | 'top';
type ViewMode = 'all' | 'section';

/**
 * Extract section reference from full anchor ID
 */
function extractSectionRef(anchorId: string): string {
  const parts = anchorId.split(':');
  return parts[parts.length - 1];
}

/**
 * Generate human-readable label for a section
 */
function getSectionLabel(sectionRef: string, locale: string): string {
  // Parse section reference like "s2.1.a" or "part-1"
  if (sectionRef.startsWith('part-')) {
    const partNum = sectionRef.replace('part-', '');
    return locale === 'fr' ? `Partie ${partNum}` : `Part ${partNum}`;
  }

  if (sectionRef.startsWith('s')) {
    const ref = sectionRef.slice(1); // Remove 's' prefix
    return locale === 'fr' ? `Section ${ref}` : `Section ${ref}`;
  }

  return sectionRef;
}

/**
 * Discussion count badge
 */
const DiscussionCount: React.FC<{ count: number; loading?: boolean }> = ({ count, loading }) => {
  if (loading) {
    return (
      <span className="text-xs text-gray-400 dark:text-gray-500 animate-pulse">
        ...
      </span>
    );
  }

  if (count === 0) return null;

  return (
    <span className="
      inline-flex items-center justify-center
      min-w-[1.25rem] h-5 px-1.5
      text-xs font-medium
      bg-blue-100 text-blue-700
      dark:bg-blue-900/50 dark:text-blue-300
      rounded-full
    ">
      {count > 99 ? '99+' : count}
    </span>
  );
};

/**
 * Section scope indicator
 */
const SectionScopeIndicator: React.FC<{
  scope: DiscussionScope;
  locale: string;
  onClear: () => void;
}> = ({ scope, locale, onClear }) => {
  const label = scope.label || getSectionLabel(scope.sectionRef, locale);

  return (
    <div className="
      flex items-center gap-2 px-3 py-2
      bg-blue-50 dark:bg-blue-900/30
      border border-blue-200 dark:border-blue-800
      rounded-lg mb-4
    ">
      <FileText className="h-4 w-4 text-blue-600 dark:text-blue-400" />
      <span className="text-sm text-blue-700 dark:text-blue-300 flex-1">
        {locale === 'fr'
          ? `Discussion pour ${label}`
          : `Discussion for ${label}`}
      </span>
      <button
        onClick={onClear}
        className="
          text-xs text-blue-600 dark:text-blue-400
          hover:text-blue-800 dark:hover:text-blue-200
          underline
        "
      >
        {locale === 'fr' ? 'Voir tout' : 'View all'}
      </button>
    </div>
  );
};

/**
 * Empty state for discussions
 */
const EmptyState: React.FC<{
  locale: string;
  sectionScope?: DiscussionScope | null;
  onCreateClick?: () => void;
  canCreate: boolean;
}> = ({ locale, sectionScope, onCreateClick, canCreate }) => {
  const sectionLabel = sectionScope
    ? getSectionLabel(sectionScope.sectionRef, locale)
    : null;

  return (
    <div className="text-center py-8">
      <MessageSquare className="h-12 w-12 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
      <h4 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
        {sectionScope
          ? (locale === 'fr'
              ? `Aucune discussion pour ${sectionLabel}`
              : `No discussions for ${sectionLabel}`)
          : (locale === 'fr'
              ? 'Aucune discussion'
              : 'No discussions yet')}
      </h4>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 max-w-xs mx-auto">
        {locale === 'fr'
          ? 'Soyez le premier a partager votre opinion sur cette section.'
          : 'Be the first to share your thoughts on this section.'}
      </p>
      {canCreate ? (
        <button
          onClick={onCreateClick}
          className="
            inline-flex items-center gap-2
            px-4 py-2
            bg-blue-600 hover:bg-blue-700
            text-white text-sm font-medium
            rounded-lg
            transition-colors
          "
        >
          <Plus className="h-4 w-4" />
          {locale === 'fr' ? 'Commencer la discussion' : 'Start discussion'}
        </button>
      ) : (
        <p className="text-xs text-gray-400 dark:text-gray-500">
          {locale === 'fr'
            ? 'Connectez-vous pour participer'
            : 'Sign in to participate'}
        </p>
      )}
    </div>
  );
};

/**
 * BillDiscussionPanel - Section-level discussions for bills
 *
 * Features:
 * - Section-scoped discussions (linked to specific bill sections)
 * - Fall back to whole-bill discussions when no section selected
 * - Real-time updates via Supabase subscription
 * - Sort by recent or top-voted
 * - Create new comments with section context
 */
export const BillDiscussionPanel: React.FC<BillDiscussionPanelProps> = ({
  billNumber,
  session,
  billTitle,
  locale,
  selectedSection,
  onClearSection,
  onSectionMention,
  compactHeader = false,
}) => {
  const { user } = useAuth();
  const [initialPosts, setInitialPosts] = useState<ForumPost[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sortBy, setSortBy] = useState<SortOption>('recent');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportTarget, setReportTarget] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const limit = 10;

  // Determine the current discussion scope
  const sectionRef = selectedSection?.sectionRef || null;

  // Fetch posts based on current scope
  useEffect(() => {
    const fetchPosts = async () => {
      setIsLoading(true);

      // For section discussions, we pass the section_ref
      // For whole-bill discussions, we don't
      const params: Parameters<typeof getPosts>[0] = {
        post_type: 'bill_comment',
        bill_number: billNumber,
        bill_session: session,
        sort_by: sortBy,
        limit,
        offset,
      };

      // If a section is selected, add section filtering
      // Note: This requires the forum API to support section_ref filtering
      // We'll add the section_ref to entity_metadata
      if (sectionRef) {
        // For now, we'll filter client-side until the API supports it
        // TODO: Add section_ref support to getPosts
      }

      const result = await getPosts(params);

      if (result.success && result.data) {
        let postsData = result.data.data;

        // Client-side filtering by section (temporary until API supports it)
        if (sectionRef) {
          postsData = postsData.filter(
            (post) => post.entity_metadata?.section_ref === sectionRef
          );
        }

        setInitialPosts(
          offset === 0 ? postsData : [...initialPosts, ...postsData]
        );
        setHasMore(result.data.has_more);
      }
      setIsLoading(false);
    };

    fetchPosts();
  }, [billNumber, session, sectionRef, sortBy, offset]);

  // Reset pagination when scope changes
  useEffect(() => {
    setOffset(0);
  }, [selectedSection]);

  // Real-time updates
  const posts = useRealtimePosts(initialPosts, {
    billNumber,
    billSession: session,
    postType: 'bill_comment',
    enabled: true,
  });

  // Filter posts by section if needed
  const filteredPosts = sectionRef
    ? posts.filter((post) => post.entity_metadata?.section_ref === sectionRef)
    : posts;

  const handleSortChange = useCallback((newSort: SortOption) => {
    setSortBy(newSort);
    setOffset(0);
  }, []);

  const handleLoadMore = useCallback(() => {
    setOffset((prev) => prev + limit);
  }, []);

  const handlePostCreated = useCallback(() => {
    setOffset(0);
    setSortBy('recent');
    setIsCreateModalOpen(false);
  }, []);

  const handleDelete = useCallback(async (postId: string) => {
    const result = await deletePost(postId);
    if (!result.success) {
      alert(result.error || 'Failed to delete post');
    }
  }, []);

  const handleReport = useCallback((postId: string) => {
    if (!user) {
      alert(locale === 'fr'
        ? 'Connectez-vous pour signaler'
        : 'Please sign in to report posts');
      return;
    }
    setReportTarget(postId);
    setIsReportModalOpen(true);
  }, [user, locale]);

  const handleReportSuccess = useCallback(() => {
    alert(locale === 'fr'
      ? 'Merci pour votre signalement.'
      : 'Thank you for your report.');
  }, [locale]);

  const handleClearSection = useCallback(() => {
    onClearSection?.();
  }, [onClearSection]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className={`
        flex-shrink-0 px-4 py-3
        border-b border-gray-200 dark:border-gray-700
        ${compactHeader ? '' : 'bg-white dark:bg-gray-800'}
      `}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <h3 className={`font-semibold text-gray-900 dark:text-gray-100 ${compactHeader ? 'text-sm' : ''}`}>
              {locale === 'fr' ? 'Discussion' : 'Discussion'}
            </h3>
            <DiscussionCount count={filteredPosts.length} loading={isLoading} />
          </div>

          {user && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="
                flex items-center gap-1.5
                px-3 py-1.5
                text-sm font-medium
                bg-blue-600 hover:bg-blue-700
                text-white
                rounded-lg
                transition-colors
              "
            >
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">
                {locale === 'fr' ? 'Commenter' : 'Comment'}
              </span>
            </button>
          )}
        </div>
      </div>

      {/* Section scope indicator */}
      {selectedSection && (
        <div className="flex-shrink-0 px-4 pt-4">
          <SectionScopeIndicator
            scope={selectedSection}
            locale={locale}
            onClear={handleClearSection}
          />
        </div>
      )}

      {/* Sort controls */}
      {filteredPosts.length > 0 && (
        <div className="flex-shrink-0 px-4 py-2 flex items-center gap-2">
          <button
            onClick={() => handleSortChange('recent')}
            className={`
              flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium
              transition-colors
              ${sortBy === 'recent'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
              }
            `}
          >
            <Clock className="h-3.5 w-3.5" />
            {locale === 'fr' ? 'Récent' : 'Recent'}
          </button>
          <button
            onClick={() => handleSortChange('top')}
            className={`
              flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium
              transition-colors
              ${sortBy === 'top'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
              }
            `}
          >
            <TrendingUp className="h-3.5 w-3.5" />
            {locale === 'fr' ? 'Populaire' : 'Top'}
          </button>
        </div>
      )}

      {/* Posts list */}
      <div className="flex-1 overflow-y-auto px-4 py-2">
        {isLoading && offset === 0 ? (
          // Loading skeleton
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 animate-pulse"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700" />
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24" />
                </div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2" />
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
              </div>
            ))}
          </div>
        ) : filteredPosts.length === 0 ? (
          <EmptyState
            locale={locale}
            sectionScope={selectedSection}
            onCreateClick={() => setIsCreateModalOpen(true)}
            canCreate={!!user}
          />
        ) : (
          <>
            <div className="space-y-3">
              {filteredPosts.map((post) => (
                <PostCard
                  key={post.id}
                  post={post}
                  showReplyButton={false}
                  onDelete={handleDelete}
                  onReport={handleReport}
                  variant="compact"
                />
              ))}
            </div>

            {/* Load more */}
            {hasMore && (
              <div className="mt-4 text-center">
                <button
                  onClick={handleLoadMore}
                  disabled={isLoading}
                  className="
                    px-4 py-2
                    text-sm font-medium
                    text-gray-600 dark:text-gray-400
                    hover:text-gray-900 dark:hover:text-gray-200
                    disabled:opacity-50
                  "
                >
                  {isLoading
                    ? (locale === 'fr' ? 'Chargement...' : 'Loading...')
                    : (locale === 'fr' ? 'Voir plus' : 'Load more')}
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Create comment modal */}
      <CreatePostForm
        postType="bill_comment"
        billNumber={billNumber}
        billSession={session}
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handlePostCreated}
        placeholder={
          selectedSection
            ? (locale === 'fr'
                ? `Commentez ${getSectionLabel(selectedSection.sectionRef, locale)}...`
                : `Comment on ${getSectionLabel(selectedSection.sectionRef, locale)}...`)
            : (locale === 'fr'
                ? `Partagez votre avis sur ${billTitle || `le projet de loi ${billNumber}`}...`
                : `Share your thoughts on ${billTitle || `Bill ${billNumber}`}...`)
        }
        submitButtonText={locale === 'fr' ? 'Publier' : 'Post'}
        entityMetadata={
          selectedSection
            ? { section_ref: selectedSection.sectionRef }
            : undefined
        }
      />

      {/* Report modal */}
      {reportTarget && (
        <ReportModal
          postId={reportTarget}
          isOpen={isReportModalOpen}
          onClose={() => {
            setIsReportModalOpen(false);
            setReportTarget(null);
          }}
          onSuccess={handleReportSuccess}
        />
      )}
    </div>
  );
};

export default BillDiscussionPanel;
