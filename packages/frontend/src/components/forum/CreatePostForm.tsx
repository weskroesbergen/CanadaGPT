'use client';

import { useState } from 'react';
import { X, FileText } from 'lucide-react';
import { MarkdownEditor } from './MarkdownEditor';
import { createPost } from '@/actions/forum';
import { useAuth } from '@/contexts/AuthContext';
import type { PostType } from '@/types/forum';

// Helper function to auto-generate titles for bill comments
function generateBillCommentTitle(
  postType: PostType,
  billNumber?: string,
  billSession?: string,
  entityMetadata?: Record<string, unknown>
): string {
  if (postType === 'bill_comment') {
    const sectionRef = entityMetadata?.section_ref as string | undefined;
    if (sectionRef && billNumber) {
      // Extract readable section label (e.g., "s2.1.a" → "Section 2.1.a")
      const label = sectionRef.startsWith('s')
        ? `Section ${sectionRef.slice(1)}`
        : sectionRef;
      return `Comment on Bill ${billSession}/${billNumber} - ${label}`;
    }
    return `Comment on Bill ${billSession}/${billNumber}`;
  }
  return 'Untitled Post';
}

// Helper function to get readable section label from section_ref
function getSectionLabel(sectionRef: string): string {
  if (sectionRef.startsWith('s')) {
    return `Section ${sectionRef.slice(1)}`;
  }
  if (sectionRef.startsWith('part-')) {
    return `Part ${sectionRef.replace('part-', '')}`;
  }
  return sectionRef;
}

interface CreatePostFormProps {
  postType: PostType;
  categoryId?: string;
  billNumber?: string;
  billSession?: string;
  parentPostId?: string;
  threadRootId?: string;
  depth?: number;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  placeholder?: string;
  submitButtonText?: string;
  /** Additional entity metadata (e.g., section_ref for bill section discussions) */
  entityMetadata?: Record<string, unknown>;
}

export function CreatePostForm({
  postType,
  categoryId,
  billNumber,
  billSession,
  parentPostId,
  threadRootId,
  depth = 0,
  isOpen,
  onClose,
  onSuccess,
  placeholder = 'Write your post...',
  submitButtonText = 'Post',
  entityMetadata,
}: CreatePostFormProps) {
  const { user } = useAuth();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isReply = !!parentPostId;
  const requiresTitle = depth === 0; // All top-level posts need title

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user) {
      setError('You must be logged in to post');
      return;
    }

    // Validation - title required only for discussion posts (bill_comment titles are auto-generated)
    if (requiresTitle && postType === 'discussion' && !title.trim()) {
      setError('Title is required');
      return;
    }

    if (!content.trim()) {
      setError('Content is required');
      return;
    }

    if (content.length > 10000) {
      setError('Post must be less than 10,000 characters');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const result = await createPost({
        post_type: postType,
        category_id: categoryId,
        bill_number: billNumber,
        bill_session: billSession,
        parent_post_id: parentPostId,
        thread_root_id: threadRootId,
        depth,
        title: requiresTitle
          ? (title.trim() || generateBillCommentTitle(postType, billNumber, billSession, entityMetadata))
          : undefined,
        content: content.trim(),
        entity_metadata: entityMetadata,
      });

      if (result.success) {
        // Reset form
        setTitle('');
        setContent('');
        setError(null);
        onSuccess?.();
        onClose();
      } else {
        setError(result.error || 'Failed to create post');
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
      console.error('Post creation error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setTitle('');
      setContent('');
      setError(null);
      onClose();
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="
            bg-background-secondary border-2 border-border-primary rounded-lg
            max-w-3xl w-full max-h-[90vh] overflow-y-auto
            shadow-2xl
          "
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border-primary">
            <h2 className="text-xl font-bold text-text-primary">
              {isReply ? 'Reply to Post' : 'Create New Post'}
            </h2>
            <button
              onClick={handleClose}
              disabled={isSubmitting}
              className="text-text-tertiary hover:text-text-primary transition-colors disabled:opacity-50"
              aria-label="Close"
            >
              <X size={24} />
            </button>
          </div>

          {/* Section context banner */}
          {typeof entityMetadata?.section_ref === 'string' && entityMetadata.section_ref && (
            <div className="px-6 py-3 bg-blue-500/10 border-b border-blue-500/20">
              <div className="flex items-center gap-2 text-sm">
                <FileText className="h-4 w-4 text-blue-400" />
                <span className="text-blue-300">
                  Commenting on: <strong>{getSectionLabel(entityMetadata.section_ref)}</strong>
                </span>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6">
            {/* Title field - only show for discussion posts (bill_comment titles are auto-generated) */}
            {requiresTitle && postType === 'discussion' && (
              <div className="mb-4">
                <label
                  htmlFor="post-title"
                  className="block text-sm font-medium text-text-primary mb-2"
                >
                  Title *
                </label>
                <input
                  id="post-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="What's your post about?"
                  maxLength={255}
                  disabled={isSubmitting}
                  className={`
                    w-full px-4 py-3 rounded-lg
                    bg-background-primary border-2
                    ${error && !title.trim() ? 'border-red-500' : 'border-border-primary'}
                    text-text-primary placeholder-text-tertiary
                    focus:outline-none focus:border-accent-red
                    transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                  `}
                />
                <div className="flex justify-between items-center mt-1 text-xs">
                  <span className="text-text-tertiary">
                    Choose a clear, descriptive title
                  </span>
                  <span
                    className={
                      title.length > 200
                        ? 'text-yellow-500'
                        : 'text-text-tertiary'
                    }
                  >
                    {title.length} / 255
                  </span>
                </div>
              </div>
            )}

            {/* Content editor */}
            <MarkdownEditor
              value={content}
              onChange={setContent}
              placeholder={placeholder}
              maxLength={10000}
              rows={isReply ? 6 : 12}
              label={`Content *`}
              error={error && !content.trim() ? 'Content is required' : undefined}
            />

            {/* Error message */}
            {error && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500 rounded-lg">
                <p className="text-red-400 font-medium text-sm">{error}</p>
              </div>
            )}

            {/* Guidelines */}
            <div className="mt-4 p-4 bg-background-primary rounded-lg border border-border-primary">
              <p className="text-sm text-text-secondary mb-2 font-medium">
                Community Guidelines:
              </p>
              <ul className="text-xs text-text-tertiary space-y-1 list-disc list-inside">
                <li>Be respectful and constructive</li>
                <li>Stay on topic and provide evidence for claims</li>
                <li>No spam, harassment, or misinformation</li>
                <li>Follow Canadian parliamentary decorum standards</li>
              </ul>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-6">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSubmitting}
                className="
                  flex-1 px-4 py-2 rounded-lg
                  bg-background-primary border-2 border-border-primary
                  text-text-primary font-medium
                  hover:border-border-hover
                  transition-all
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || (requiresTitle && postType === 'discussion' && !title.trim()) || !content.trim()}
                className="
                  flex-1 px-4 py-2 rounded-lg
                  bg-accent-red text-white font-medium
                  hover:bg-red-700
                  transition-all
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              >
                {isSubmitting ? 'Posting...' : submitButtonText}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
