'use client';

import React, { useState, useEffect } from 'react';
import { X, Save, Loader2 } from 'lucide-react';
import { Bookmark } from '@/hooks/useBookmarks';
import { NoteEditor } from './NoteEditor';
import { getTierLimits } from '@/lib/bookmarks/tierLimits';

interface NoteEditModalProps {
  bookmark: Bookmark | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (bookmarkId: string, notes: string, aiPrompt?: string) => Promise<void>;
  tier?: string | null;
}

/**
 * Modal for editing bookmark notes with markdown support and AI prompts (PRO).
 *
 * Features:
 * - Full NoteEditor with markdown preview
 * - AI context prompt editor (PRO tier only)
 * - Auto-save on Cmd+S
 * - Escape to close
 * - Loading states
 *
 * @example
 * ```tsx
 * <NoteEditModal
 *   bookmark={selectedBookmark}
 *   isOpen={isModalOpen}
 *   onClose={() => setIsModalOpen(false)}
 *   onSave={handleSaveNote}
 *   tier={user?.subscription_tier}
 * />
 * ```
 */
export function NoteEditModal({
  bookmark,
  isOpen,
  onClose,
  onSave,
  tier,
}: NoteEditModalProps) {
  const [notes, setNotes] = useState('');
  const [aiPrompt, setAIPrompt] = useState('');
  const [saving, setSaving] = useState(false);
  const [showAIPrompt, setShowAIPrompt] = useState(false);

  const tierLimits = getTierLimits(tier);

  // Initialize form when bookmark changes
  useEffect(() => {
    if (bookmark) {
      setNotes(bookmark.notes || '');
      setAIPrompt(bookmark.ai_prompt || '');
      setShowAIPrompt(!!(bookmark.ai_prompt && bookmark.ai_prompt.trim() !== ''));
    }
  }, [bookmark]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const handleSave = async () => {
    if (!bookmark) return;

    setSaving(true);
    try {
      await onSave(bookmark.id, notes, aiPrompt);
      onClose();
    } catch (error) {
      console.error('Failed to save note:', error);
      alert('Failed to save note. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveShortcut = () => {
    handleSave();
  };

  if (!isOpen || !bookmark) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div
          className="bg-white dark:bg-gray-900 rounded-lg shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col pointer-events-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
                {bookmark.notes ? 'Edit Note' : 'Add Note'}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 truncate mt-0.5">
                {bookmark.title}
              </p>
            </div>
            <button
              onClick={onClose}
              className="ml-4 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors"
              disabled={saving}
            >
              <X size={20} />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Notes Editor */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Your Notes (Markdown supported)
              </label>
              <NoteEditor
                value={notes}
                onChange={setNotes}
                tier={tier}
                placeholder="# My Analysis

Write your notes in **Markdown**...

- Point 1
- Point 2"
                autoFocus
                onSave={handleSaveShortcut}
                showCharCounter
              />
            </div>

            {/* AI Prompt Section (PRO only) */}
            {tierLimits.hasAIPrompts && (
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-purple-700 dark:text-purple-300">
                    🤖 AI Context Prompt (PRO)
                  </label>
                  {!showAIPrompt && (
                    <button
                      onClick={() => setShowAIPrompt(true)}
                      className="text-xs text-purple-600 dark:text-purple-400 hover:underline"
                    >
                      + Add AI instructions
                    </button>
                  )}
                </div>

                {showAIPrompt && (
                  <div className="space-y-2">
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Give the AI instructions for how to use this bookmark when answering questions.
                    </p>
                    <textarea
                      value={aiPrompt}
                      onChange={(e) => setAIPrompt(e.target.value)}
                      placeholder="When analyzing this, focus on...&#10;&#10;Example: 'Always fact-check claims in this speech' or 'Compare voting record to statements'"
                      className="w-full px-3 py-2 border border-purple-200 dark:border-purple-800 rounded-lg bg-purple-50/50 dark:bg-purple-900/20 focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm resize-y min-h-[100px]"
                    />
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500 dark:text-gray-400">
                        {aiPrompt.length} characters
                      </span>
                      <button
                        onClick={() => {
                          setAIPrompt('');
                          setShowAIPrompt(false);
                        }}
                        className="text-gray-500 hover:text-red-600 dark:hover:text-red-400"
                      >
                        Remove AI prompt
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Upgrade prompt for non-PRO users */}
            {!tierLimits.hasAIPrompts && tier !== 'PRO' && (
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                  <div className="flex items-start gap-2">
                    <span className="text-xl">🤖</span>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-purple-900 dark:text-purple-100">
                        Upgrade to PRO for AI Context Prompts
                      </p>
                      <p className="text-xs text-purple-700 dark:text-purple-300 mt-1">
                        Add instructions for how AI should analyze this bookmark when answering your questions.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            <div className="text-xs text-gray-500 dark:text-gray-400">
              <kbd className="px-2 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded">
                Esc
              </kbd>{' '}
              to close •{' '}
              <kbd className="px-2 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded">
                ⌘S
              </kbd>{' '}
              to save
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:bg-gray-400 rounded-lg transition-colors flex items-center gap-2"
              >
                {saving ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save size={16} />
                    Save Note
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
