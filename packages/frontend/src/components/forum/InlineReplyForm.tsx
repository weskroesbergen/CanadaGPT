'use client';

import { useState } from 'react';
import { MarkdownEditor } from './MarkdownEditor';
import { createPost } from '@/actions/forum';
import { useAuth } from '@/contexts/AuthContext';
import type { ForumPost } from '@/types/forum';

interface InlineReplyFormProps {
  parentPost: ForumPost;
  onSuccess?: () => void;
  onCancel?: () => void;
  placeholder?: string;
}

export function InlineReplyForm({
  parentPost,
  onSuccess,
  onCancel,
  placeholder = 'Write a reply...',
}: InlineReplyFormProps) {
  const { user } = useAuth();
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user) {
      setError('You must be logged in to reply');
      return;
    }

    if (!content.trim()) {
      setError('Reply cannot be empty');
      return;
    }

    if (content.length < 10) {
      setError('Reply must be at least 10 characters');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const result = await createPost({
        post_type: parentPost.post_type,
        category_id: parentPost.category_id ?? undefined,
        bill_number: parentPost.bill_number ?? undefined,
        bill_session: parentPost.bill_session ?? undefined,
        parent_post_id: parentPost.id,
        thread_root_id: parentPost.thread_root_id || parentPost.id,
        depth: parentPost.depth + 1,
        content: content.trim(),
        entity_metadata: parentPost.entity_metadata ?? undefined,
      });

      if (result.success) {
        setContent('');
        setError(null);
        onSuccess?.();
      } else {
        setError(result.error || 'Failed to post reply');
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
      console.error('Reply error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-background-primary border-2 border-border-primary rounded-lg p-4">
      {/* Markdown editor */}
      <MarkdownEditor
        value={content}
        onChange={setContent}
        placeholder={placeholder}
        rows={3}
        minLength={10}
        maxLength={10000}
        error={error || undefined}
      />

      {/* Error message */}
      {error && (
        <p className="text-red-500 text-sm mt-2">{error}</p>
      )}

      {/* Action buttons */}
      <div className="flex justify-end gap-2 mt-3">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={isSubmitting || !content.trim() || content.length < 10}
          className="
            px-4 py-2 rounded-lg text-sm font-medium
            bg-accent-red text-white
            hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors
          "
        >
          {isSubmitting ? 'Posting...' : 'Reply'}
        </button>
      </div>
    </form>
  );
}
