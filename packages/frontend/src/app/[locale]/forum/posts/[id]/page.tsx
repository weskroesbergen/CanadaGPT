'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { PostThread, CreatePostForm, ReportModal } from '@/components/forum';
import { getPost, getPostThread, deletePost, updatePost } from '@/actions/forum';
import type { ForumPost } from '@/types/forum';
import { useAuth } from '@/contexts/AuthContext';

export default function PostPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const postId = params.id as string;

  const [post, setPost] = useState<ForumPost | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isReplyModalOpen, setIsReplyModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [replyTarget, setReplyTarget] = useState<ForumPost | null>(null);
  const [editTarget, setEditTarget] = useState<ForumPost | null>(null);
  const [reportTarget, setReportTarget] = useState<string | null>(null);

  // Fetch post and thread
  useEffect(() => {
    const fetchPost = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch the post details
        const postResult = await getPost(postId);
        if (!postResult.success || !postResult.data) {
          setError(postResult.error || 'Post not found');
          return;
        }

        // Fetch the full thread
        const threadResult = await getPostThread(postId);
        if (threadResult.success && threadResult.data) {
          // Build the thread tree
          const rootPost = threadResult.data[0];
          setPost(rootPost);
        } else {
          setPost(postResult.data);
        }
      } catch (err) {
        setError('Failed to load post');
        console.error('Error loading post:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPost();
  }, [postId]);

  const handleReply = (targetPost: ForumPost) => {
    if (!user) {
      alert('Please sign in to reply');
      return;
    }
    setReplyTarget(targetPost);
    setIsReplyModalOpen(true);
  };

  const handleEdit = (targetPost: ForumPost) => {
    setEditTarget(targetPost);
    setIsEditModalOpen(true);
  };

  const handleDelete = async (deletePostId: string) => {
    const result = await deletePost(deletePostId);
    if (result.success) {
      // Refresh the thread
      window.location.reload();
    } else {
      alert(result.error || 'Failed to delete post');
    }
  };

  const handleReport = (reportPostId: string) => {
    if (!user) {
      alert('Please sign in to report posts');
      return;
    }
    setReportTarget(reportPostId);
    setIsReportModalOpen(true);
  };

  const handleReplySuccess = () => {
    // Refresh the thread
    window.location.reload();
  };

  const handleEditSuccess = () => {
    // Refresh the thread
    window.location.reload();
  };

  const handleReportSuccess = () => {
    alert('Thank you for your report. Our moderation team will review it.');
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="space-y-4">
          <div className="bg-background-secondary border-2 border-border-primary rounded-lg p-6 animate-pulse">
            <div className="h-8 bg-background-primary rounded mb-4 w-3/4" />
            <div className="h-4 bg-background-primary rounded mb-2 w-full" />
            <div className="h-4 bg-background-primary rounded mb-2 w-full" />
            <div className="h-4 bg-background-primary rounded w-5/6" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="bg-background-secondary border-2 border-red-500 rounded-lg p-8 text-center">
          <p className="text-red-500 text-lg mb-4">{error || 'Post not found'}</p>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-accent-red text-white rounded-lg hover:bg-red-700 transition-all"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      {/* Back button */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-text-secondary hover:text-accent-red transition-colors mb-6"
      >
        <ArrowLeft size={20} />
        Back
      </button>

      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm text-text-tertiary mb-6">
        <a href="/forum" className="hover:text-accent-red transition-colors">
          Forum
        </a>
        {post.category && (
          <>
            <span>/</span>
            <a
              href={`/forum/${post.category.slug}`}
              className="hover:text-accent-red transition-colors"
            >
              {post.category.name}
            </a>
          </>
        )}
        <span>/</span>
        <span className="text-text-primary truncate">{post.title || 'Post'}</span>
      </div>

      {/* Thread */}
      <div className="space-y-4">
        <PostThread
          post={post}
          onReply={handleReply}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onReport={handleReport}
        />
      </div>

      {/* Reply modal */}
      {replyTarget && (
        <CreatePostForm
          postType={post.post_type}
          categoryId={replyTarget.category_id || undefined}
          billNumber={replyTarget.bill_number || undefined}
          billSession={replyTarget.bill_session || undefined}
          parentPostId={replyTarget.id}
          threadRootId={replyTarget.thread_root_id || replyTarget.id}
          depth={replyTarget.depth + 1}
          isOpen={isReplyModalOpen}
          onClose={() => {
            setIsReplyModalOpen(false);
            setReplyTarget(null);
          }}
          onSuccess={handleReplySuccess}
          placeholder="Write your reply..."
          submitButtonText="Reply"
        />
      )}

      {/* Edit modal */}
      {editTarget && (
        <div>
          {/* TODO: Create EditPostForm component or reuse CreatePostForm with edit mode */}
          <p className="text-text-secondary">Edit functionality coming soon</p>
        </div>
      )}

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
