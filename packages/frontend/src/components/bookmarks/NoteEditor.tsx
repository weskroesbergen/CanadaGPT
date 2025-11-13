'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';
import {
  getTierLimits,
  isNoteWithinLimit,
  getNoteLimitMessage,
  getUpgradeMessage,
} from '@/lib/bookmarks/tierLimits';

interface NoteEditorProps {
  value: string;
  onChange: (value: string) => void;
  tier?: string | null;
  placeholder?: string;
  autoFocus?: boolean;
  minHeight?: string;
  showPreview?: boolean;
  className?: string;
  /**
   * Called when save is triggered (Cmd/Ctrl + S)
   */
  onSave?: () => void;
  /**
   * Show character counter
   */
  showCharCounter?: boolean;
}

/**
 * Markdown note editor with live preview and tier-aware character limits.
 *
 * Features:
 * - Split view: Edit | Preview
 * - Tier-aware character limits
 * - Keyboard shortcuts (Cmd+S to save, Cmd+B for bold, etc.)
 * - Auto-growing textarea
 * - Character counter with warnings
 *
 * @example
 * ```tsx
 * <NoteEditor
 *   value={note}
 *   onChange={setNote}
 *   tier="BASIC"
 *   onSave={handleSave}
 * />
 * ```
 */
export function NoteEditor({
  value,
  onChange,
  tier,
  placeholder = 'Write your note in Markdown...',
  autoFocus = false,
  minHeight = '120px',
  showPreview: initialShowPreview = false,
  className = '',
  onSave,
  showCharCounter = true,
}: NoteEditorProps) {
  const [showPreview, setShowPreview] = useState(initialShowPreview);
  const limits = getTierLimits(tier);

  // Check if notes are allowed for this tier
  if (!limits.hasNotes) {
    const upgradeMsg = getUpgradeMessage('notes', tier);
    return (
      <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600">
        <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
            />
          </svg>
          <span className="font-medium">{upgradeMsg.message}</span>
        </div>
      </div>
    );
  }

  const charCount = value.length;
  const isOverLimit = !isNoteWithinLimit(charCount, tier);
  const limitMessage = getNoteLimitMessage(charCount, tier);

  // Calculate warning level for character counter
  const maxLength = limits.maxNoteLength;
  let warningLevel: 'normal' | 'warning' | 'danger' = 'normal';
  if (maxLength !== null) {
    const percentage = (charCount / maxLength) * 100;
    if (percentage >= 100) warningLevel = 'danger';
    else if (percentage >= 80) warningLevel = 'warning';
  }

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Cmd/Ctrl + S to save
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        onSave?.();
        return;
      }

      // Cmd/Ctrl + B for bold
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault();
        insertMarkdown('**', '**', 'bold text');
        return;
      }

      // Cmd/Ctrl + I for italic
      if ((e.metaKey || e.ctrlKey) && e.key === 'i') {
        e.preventDefault();
        insertMarkdown('*', '*', 'italic text');
        return;
      }

      // Cmd/Ctrl + K for link
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        insertMarkdown('[', '](url)', 'link text');
        return;
      }
    },
    [onSave]
  );

  // Insert markdown formatting at cursor position
  const insertMarkdown = (before: string, after: string, placeholder: string) => {
    const textarea = document.querySelector('textarea') as HTMLTextAreaElement;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = value.substring(start, end);
    const textToInsert = selectedText || placeholder;

    const newValue =
      value.substring(0, start) + before + textToInsert + after + value.substring(end);

    onChange(newValue);

    // Set cursor position after inserted text
    setTimeout(() => {
      textarea.focus();
      const newCursorPos = start + before.length + textToInsert.length;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  return (
    <div className={`note-editor ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-gray-200 dark:border-gray-700">
        {/* Formatting buttons */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => insertMarkdown('**', '**', 'bold')}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-sm font-bold"
            title="Bold (Cmd+B)"
          >
            B
          </button>
          <button
            type="button"
            onClick={() => insertMarkdown('*', '*', 'italic')}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-sm italic"
            title="Italic (Cmd+I)"
          >
            I
          </button>
          <button
            type="button"
            onClick={() => insertMarkdown('[', '](url)', 'link')}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-sm"
            title="Link (Cmd+K)"
          >
            🔗
          </button>
          <button
            type="button"
            onClick={() => insertMarkdown('`', '`', 'code')}
            className="px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-xs font-mono"
            title="Inline code"
          >
            {'</>'}
          </button>
          <button
            type="button"
            onClick={() => {
              const textarea = document.querySelector('textarea') as HTMLTextAreaElement;
              const start = textarea.selectionStart;
              const lineStart = value.lastIndexOf('\n', start - 1) + 1;
              onChange(value.substring(0, lineStart) + '- ' + value.substring(lineStart));
            }}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-sm"
            title="Bullet list"
          >
            •
          </button>
        </div>

        {/* Preview toggle */}
        <button
          type="button"
          onClick={() => setShowPreview(!showPreview)}
          className={`px-3 py-1 text-sm rounded transition-colors ${
            showPreview
              ? 'bg-red-600 text-white'
              : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          {showPreview ? 'Edit' : 'Preview'}
        </button>
      </div>

      {/* Editor / Preview */}
      {showPreview ? (
        <div
          className="prose prose-sm max-w-none p-3 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900"
          style={{ minHeight }}
        >
          {value ? (
            <MarkdownRenderer content={value} />
          ) : (
            <p className="text-gray-400 italic">Nothing to preview</p>
          )}
        </div>
      ) : (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className={`w-full p-3 border rounded-lg font-mono text-sm resize-y focus:outline-none focus:ring-2 transition-colors ${
            isOverLimit
              ? 'border-red-500 focus:ring-red-500 bg-red-50 dark:bg-red-900/10'
              : 'border-gray-200 dark:border-gray-700 focus:ring-red-600 bg-white dark:bg-gray-900'
          }`}
          style={{ minHeight }}
        />
      )}

      {/* Character counter */}
      {showCharCounter && (
        <div className="flex items-center justify-between mt-2 text-xs">
          <div
            className={`font-medium ${
              warningLevel === 'danger'
                ? 'text-red-600 dark:text-red-400'
                : warningLevel === 'warning'
                ? 'text-amber-600 dark:text-amber-400'
                : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            {limitMessage}
          </div>

          {/* Keyboard shortcuts hint */}
          <div className="text-gray-400 dark:text-gray-500">
            <span className="hidden sm:inline">
              Shortcuts: <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">⌘S</kbd> save,{' '}
              <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">⌘B</kbd> bold
            </span>
          </div>
        </div>
      )}

      {/* Over limit warning */}
      {isOverLimit && (
        <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-600 dark:text-red-400">
          Your note exceeds the {maxLength?.toLocaleString()} character limit for {tier} tier.{' '}
          {tier === 'BASIC' && (
            <button
              type="button"
              className="underline font-medium hover:text-red-700 dark:hover:text-red-300"
              onClick={() => {
                // TODO: Integrate with upgrade flow
                console.log('Upgrade to PRO');
              }}
            >
              Upgrade to PRO for unlimited notes
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Compact note editor for inline use (e.g., in modals)
 */
export function CompactNoteEditor(props: Omit<NoteEditorProps, 'showPreview'>) {
  return (
    <NoteEditor
      {...props}
      minHeight="80px"
      showPreview={false}
      className="compact"
    />
  );
}
