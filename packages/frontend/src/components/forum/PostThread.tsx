'use client';

import { useState } from 'react';
import { PostCard } from './PostCard';
import type { ForumPost } from '@/types/forum';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface PostThreadProps {
  post: ForumPost;
  onReply?: (post: ForumPost) => void;
  onEdit?: (post: ForumPost) => void;
  onDelete?: (postId: string) => void;
  onReport?: (postId: string) => void;
  maxDepth?: number;
  showCollapseButton?: boolean;
}

export function PostThread({
  post,
  onReply,
  onEdit,
  onDelete,
  onReport,
  maxDepth = 10,
  showCollapseButton = true,
}: PostThreadProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const hasReplies = post.replies && post.replies.length > 0;
  const canShowReplies = hasReplies && post.depth < maxDepth;

  // Calculate indent level based on depth
  const getIndentStyle = (depth: number) => {
    if (depth === 0) return {};
    // Each level adds 24px of left margin, with a subtle border
    return {
      marginLeft: `${Math.min(depth, 5) * 24}px`,
      borderLeft: depth > 0 ? '2px solid rgba(239, 68, 68, 0.2)' : undefined,
      paddingLeft: depth > 0 ? '16px' : undefined,
    };
  };

  return (
    <div className="relative">
      {/* Main post */}
      <div style={getIndentStyle(post.depth)}>
        <div className="flex items-start gap-2">
          {/* Collapse button for posts with replies */}
          {showCollapseButton && hasReplies && (
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="flex-shrink-0 mt-4 p-1 rounded hover:bg-background-primary transition-colors text-text-tertiary"
              aria-label={isCollapsed ? 'Expand replies' : 'Collapse replies'}
            >
              {isCollapsed ? (
                <ChevronRight size={18} />
              ) : (
                <ChevronDown size={18} />
              )}
            </button>
          )}

          {/* Post card */}
          <div className="flex-1 min-w-0">
            <PostCard
              post={post}
              showReplyButton={post.depth < maxDepth}
              onReply={onReply}
              onEdit={onEdit}
              onDelete={onDelete}
              onReport={onReport}
              variant={post.depth > 0 ? 'compact' : 'full'}
            />

            {/* Collapsed reply count indicator */}
            {isCollapsed && hasReplies && (
              <button
                onClick={() => setIsCollapsed(false)}
                className="ml-4 mt-2 text-sm text-accent-red hover:underline"
              >
                {post.reply_count} {post.reply_count === 1 ? 'reply' : 'replies'} hidden
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Nested replies */}
      {!isCollapsed && canShowReplies && (
        <div className="mt-3 space-y-3">
          {post.replies!.map((reply) => (
            <PostThread
              key={reply.id}
              post={reply}
              onReply={onReply}
              onEdit={onEdit}
              onDelete={onDelete}
              onReport={onReport}
              maxDepth={maxDepth}
              showCollapseButton={showCollapseButton}
            />
          ))}
        </div>
      )}

      {/* Max depth indicator */}
      {post.depth >= maxDepth && hasReplies && (
        <div
          style={getIndentStyle(post.depth + 1)}
          className="mt-3 p-3 bg-background-primary rounded border border-border-primary"
        >
          <p className="text-sm text-text-tertiary">
            Thread continues...{' '}
            <a
              href={`/forum/posts/${post.replies![0].id}`}
              className="text-accent-red hover:underline"
            >
              View {post.reply_count} more {post.reply_count === 1 ? 'reply' : 'replies'}
            </a>
          </p>
        </div>
      )}
    </div>
  );
}
