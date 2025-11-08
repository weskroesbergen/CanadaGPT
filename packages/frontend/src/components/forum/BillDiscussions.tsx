'use client';

import { useState, useEffect } from 'react';
import { MessageSquare, Plus, TrendingUp, Clock } from 'lucide-react';
import { PostCard, CreatePostForm, ReportModal } from '@/components/forum';
import { getPosts, deletePost } from '@/actions/forum';
import type { ForumPost } from '@/types/forum';
import { useAuth } from '@/contexts/AuthContext';
import { useRealtimePosts } from '@/hooks/useRealtimePosts';

interface BillDiscussionsProps {
  billNumber: string;
  billSession: string;
  billTitle?: string;
}

type SortOption = 'recent' | 'top';

export function BillDiscussions({
  billNumber,
  billSession,
  billTitle,
}: BillDiscussionsProps) {
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

  // Fetch posts
  useEffect(() => {
    const fetchPosts = async () => {
      setIsLoading(true);

      const result = await getPosts({
        post_type: 'bill_comment',
        bill_number: billNumber,
        bill_session: billSession,
        sort_by: sortBy,
        limit,
        offset,
      });

      if (result.success && result.data) {
        setInitialPosts(offset === 0 ? result.data.data : [...initialPosts, ...result.data.data]);
        setHasMore(result.data.has_more);
      }
      setIsLoading(false);
    };

    fetchPosts();
  }, [billNumber, billSession, sortBy, offset]);

  // Real-time posts (automatically updates when new posts are created)
  const posts = useRealtimePosts(initialPosts, {
    billNumber,
    billSession,
    postType: 'bill_comment',
    enabled: true,
  });

  const handleSortChange = (newSort: SortOption) => {
    setSortBy(newSort);
    setOffset(0);
  };

  const handleLoadMore = () => {
    setOffset(offset + limit);
  };

  const handlePostCreated = () => {
    // Refresh posts
    setOffset(0);
    setSortBy('recent');
  };

  const handleDelete = async (postId: string) => {
    const result = await deletePost(postId);
    if (result.success) {
      // Real-time hook will automatically update when database changes
      // No need to manually update state
    } else {
      alert(result.error || 'Failed to delete post');
    }
  };

  const handleReport = (postId: string) => {
    if (!user) {
      alert('Please sign in to report posts');
      return;
    }
    setReportTarget(postId);
    setIsReportModalOpen(true);
  };

  const handleReportSuccess = () => {
    alert('Thank you for your report. Our moderation team will review it.');
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-2xl font-bold text-text-primary flex items-center gap-2 mb-1">
            <MessageSquare className="text-accent-red" size={24} />
            Community Discussion
          </h3>
          <p className="text-text-secondary text-sm">
            Share your thoughts and engage with others about this bill
          </p>
        </div>

        {user && (
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="
              flex items-center gap-2 px-4 py-2 rounded-lg
              bg-accent-red text-white font-medium
              hover:bg-red-700 transition-all
              whitespace-nowrap
            "
          >
            <Plus size={18} />
            Add Comment
          </button>
        )}
      </div>

      {/* Sort controls */}
      {posts.length > 0 && (
        <div className="flex items-center gap-2 mb-4">
          <button
            onClick={() => handleSortChange('recent')}
            className={`
              flex items-center gap-2 px-3 py-1.5 rounded-lg font-medium text-sm transition-all
              ${
                sortBy === 'recent'
                  ? 'bg-accent-red text-white'
                  : 'bg-background-secondary text-text-secondary hover:bg-background-primary'
              }
            `}
          >
            <Clock size={14} />
            Recent
          </button>
          <button
            onClick={() => handleSortChange('top')}
            className={`
              flex items-center gap-2 px-3 py-1.5 rounded-lg font-medium text-sm transition-all
              ${
                sortBy === 'top'
                  ? 'bg-accent-red text-white'
                  : 'bg-background-secondary text-text-secondary hover:bg-background-primary'
              }
            `}
          >
            <TrendingUp size={14} />
            Top
          </button>
        </div>
      )}

      {/* Posts list */}
      {isLoading && offset === 0 ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="bg-background-secondary border-2 border-border-primary rounded-lg p-6 animate-pulse"
            >
              <div className="h-4 bg-background-primary rounded mb-2 w-full" />
              <div className="h-4 bg-background-primary rounded mb-2 w-full" />
              <div className="h-4 bg-background-primary rounded w-5/6" />
            </div>
          ))}
        </div>
      ) : posts.length === 0 ? (
        <div className="text-center py-12 bg-background-secondary border-2 border-border-primary rounded-lg">
          <MessageSquare size={48} className="mx-auto text-text-tertiary mb-4" />
          <p className="text-text-secondary mb-4">No comments yet on this bill</p>
          {user ? (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="px-4 py-2 bg-accent-red text-white rounded-lg hover:bg-red-700 transition-all"
            >
              Start the discussion
            </button>
          ) : (
            <p className="text-text-tertiary text-sm">Sign in to join the discussion</p>
          )}
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {posts.map((post) => (
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

          {/* Load more button */}
          {hasMore && (
            <div className="mt-6 text-center">
              <button
                onClick={handleLoadMore}
                disabled={isLoading}
                className="
                  px-6 py-3 bg-background-secondary border-2 border-border-primary
                  text-text-primary font-medium rounded-lg
                  hover:border-accent-red transition-all
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              >
                {isLoading ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </>
      )}

      {/* Create comment modal */}
      <CreatePostForm
        postType="bill_comment"
        billNumber={billNumber}
        billSession={billSession}
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handlePostCreated}
        placeholder={`Share your thoughts about ${billTitle || `Bill ${billNumber}`}...`}
        submitButtonText="Post Comment"
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
}
