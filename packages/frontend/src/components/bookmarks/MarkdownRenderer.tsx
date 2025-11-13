'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  /**
   * Maximum lines to show before truncation. Null = show all.
   */
  maxLines?: number | null;
}

/**
 * Renders Markdown content safely with GitHub Flavored Markdown support.
 *
 * Features:
 * - GFM support (tables, strikethrough, task lists)
 * - XSS protection via sanitization
 * - Automatic link targets (open in new tab)
 * - Optional line truncation for previews
 *
 * @example
 * ```tsx
 * <MarkdownRenderer content="**Bold text**" />
 * <MarkdownRenderer content={note} maxLines={3} />
 * ```
 */
export function MarkdownRenderer({
  content,
  className = '',
  maxLines = null,
}: MarkdownRendererProps) {
  if (!content || content.trim() === '') {
    return null;
  }

  // Truncate content if maxLines is specified
  const displayContent =
    maxLines !== null
      ? content.split('\n').slice(0, maxLines).join('\n')
      : content;

  const isTruncated = maxLines !== null && content.split('\n').length > maxLines;

  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          // Open links in new tab
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" />
          ),
          // Style code blocks
          code: ({ node, inline, ...props }) =>
            inline ? (
              <code
                className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-sm font-mono"
                {...props}
              />
            ) : (
              <code
                className="block p-3 bg-gray-100 dark:bg-gray-800 rounded-md text-sm font-mono overflow-x-auto"
                {...props}
              />
            ),
          // Style blockquotes
          blockquote: ({ node, ...props }) => (
            <blockquote
              className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic my-2"
              {...props}
            />
          ),
          // Style lists
          ul: ({ node, ...props }) => (
            <ul className="list-disc list-inside my-2 space-y-1" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal list-inside my-2 space-y-1" {...props} />
          ),
          // Style headings
          h1: ({ node, ...props }) => (
            <h1 className="text-2xl font-bold my-3" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-xl font-bold my-2.5" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-lg font-semibold my-2" {...props} />
          ),
          h4: ({ node, ...props }) => (
            <h4 className="text-base font-semibold my-1.5" {...props} />
          ),
          // Style paragraphs
          p: ({ node, ...props }) => <p className="my-2" {...props} />,
          // Style tables (GFM)
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-3">
              <table
                className="min-w-full border-collapse border border-gray-300 dark:border-gray-600"
                {...props}
              />
            </div>
          ),
          th: ({ node, ...props }) => (
            <th
              className="border border-gray-300 dark:border-gray-600 px-3 py-2 bg-gray-50 dark:bg-gray-700 font-semibold text-left"
              {...props}
            />
          ),
          td: ({ node, ...props }) => (
            <td
              className="border border-gray-300 dark:border-gray-600 px-3 py-2"
              {...props}
            />
          ),
        }}
      >
        {displayContent}
      </ReactMarkdown>

      {isTruncated && (
        <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          ...
        </div>
      )}

      <style jsx global>{`
        .markdown-content {
          font-size: 0.9375rem;
          line-height: 1.6;
          color: inherit;
        }

        .markdown-content > *:first-child {
          margin-top: 0;
        }

        .markdown-content > *:last-child {
          margin-bottom: 0;
        }

        .markdown-content a {
          color: #dc143c;
          text-decoration: underline;
          text-underline-offset: 2px;
        }

        .markdown-content a:hover {
          color: #a00f2e;
        }

        .markdown-content strong {
          font-weight: 600;
        }

        .markdown-content em {
          font-style: italic;
        }

        .markdown-content hr {
          border: none;
          border-top: 1px solid #e5e7eb;
          margin: 1.5rem 0;
        }

        .dark .markdown-content hr {
          border-top-color: #374151;
        }

        /* Task lists (GFM) */
        .markdown-content input[type='checkbox'] {
          margin-right: 0.5rem;
        }

        /* Strikethrough (GFM) */
        .markdown-content del {
          text-decoration: line-through;
          opacity: 0.7;
        }
      `}</style>
    </div>
  );
}

/**
 * Get a plain text preview from markdown content
 * Strips all markdown formatting
 */
export function getMarkdownPreview(content: string, maxLength: number = 100): string {
  if (!content) return '';

  // Remove markdown formatting
  const stripped = content
    .replace(/#{1,6}\s/g, '') // Remove headings
    .replace(/\*\*(.+?)\*\*/g, '$1') // Remove bold
    .replace(/\*(.+?)\*/g, '$1') // Remove italic
    .replace(/__(.+?)__/g, '$1') // Remove bold alt
    .replace(/_(.+?)_/g, '$1') // Remove italic alt
    .replace(/~~(.+?)~~/g, '$1') // Remove strikethrough
    .replace(/`(.+?)`/g, '$1') // Remove inline code
    .replace(/\[(.+?)\]\(.+?\)/g, '$1') // Remove links
    .replace(/!\[(.+?)\]\(.+?\)/g, '$1') // Remove images
    .replace(/>\s/g, '') // Remove blockquotes
    .replace(/[-*+]\s/g, '') // Remove list bullets
    .replace(/\d+\.\s/g, '') // Remove ordered list numbers
    .trim();

  // Truncate to max length
  if (stripped.length > maxLength) {
    return stripped.slice(0, maxLength) + '...';
  }

  return stripped;
}

/**
 * Count characters in markdown content (excluding formatting)
 */
export function getMarkdownCharCount(content: string): number {
  return content.length; // For tier limits, we count all characters including formatting
}
