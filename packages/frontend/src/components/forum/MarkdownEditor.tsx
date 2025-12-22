'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Eye, Edit3 } from 'lucide-react';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minLength?: number;
  maxLength?: number;
  rows?: number;
  label?: string;
  error?: string;
}

export function MarkdownEditor({
  value,
  onChange,
  placeholder = 'Write your post... (Markdown supported)',
  minLength,
  maxLength = 10000,
  rows = 6,
  label,
  error,
}: MarkdownEditorProps) {
  const [activeTab, setActiveTab] = useState<'write' | 'preview'>('write');
  const characterCount = value.length;
  const isOverLimit = maxLength && characterCount > maxLength;
  const isUnderLimit = minLength && characterCount < minLength;

  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-text-primary mb-2">
          {label}
        </label>
      )}

      {/* Tab buttons */}
      <div className="flex border-b border-border-primary mb-2">
        <button
          type="button"
          onClick={() => setActiveTab('write')}
          className={`
            px-4 py-2 text-sm font-medium transition-colors flex items-center gap-2
            ${
              activeTab === 'write'
                ? 'text-accent-red border-b-2 border-accent-red'
                : 'text-text-secondary hover:text-text-primary'
            }
          `}
        >
          <Edit3 size={14} />
          Write
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('preview')}
          className={`
            px-4 py-2 text-sm font-medium transition-colors flex items-center gap-2
            ${
              activeTab === 'preview'
                ? 'text-accent-red border-b-2 border-accent-red'
                : 'text-text-secondary hover:text-text-primary'
            }
          `}
        >
          <Eye size={14} />
          Preview
        </button>
      </div>

      {/* Editor/Preview area */}
      {activeTab === 'write' ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={rows}
          maxLength={maxLength}
          className={`
            w-full px-4 py-3 rounded-lg
            bg-background-primary border-2
            ${error || isOverLimit ? 'border-red-500' : 'border-border-primary'}
            text-gray-900 dark:text-gray-100 placeholder-text-tertiary
            focus:outline-none focus:border-accent-red
            resize-y font-mono text-sm
            transition-colors
          `}
        />
      ) : (
        <div
          className="
            w-full min-h-[150px] px-4 py-3 rounded-lg
            bg-background-secondary border-2 border-border-primary
          "
        >
          {value.trim() ? (
            <div className="prose prose-invert max-w-none prose-sm text-text-primary">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {value}
              </ReactMarkdown>
            </div>
          ) : (
            <p className="text-text-tertiary text-sm italic">
              Nothing to preview. Start writing in the Write tab.
            </p>
          )}
        </div>
      )}

      {/* Footer info */}
      <div className="flex justify-between items-center mt-2 text-xs">
        <div className="text-text-tertiary">
          Markdown supported: **bold**, *italic*, [links](url), # headings, - lists
        </div>
        <div
          className={`
            font-medium
            ${isOverLimit ? 'text-red-500' : isUnderLimit ? 'text-yellow-500' : 'text-text-tertiary'}
          `}
        >
          {characterCount}
          {maxLength && ` / ${maxLength}`}
        </div>
      </div>

      {error && <p className="text-red-400 font-medium text-sm mt-2">{error}</p>}
    </div>
  );
}
