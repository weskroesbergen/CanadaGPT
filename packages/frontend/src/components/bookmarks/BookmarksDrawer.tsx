/**
 * BookmarksDrawer Component
 *
 * Slide-out drawer for viewing and managing bookmarks
 * Features:
 * - Filter by type, collection, favorites
 * - Search within bookmarks
 * - Tier-aware collections
 * - Usage stats and upgrade prompts
 * - Keyboard shortcut (Cmd/Ctrl + B)
 */

'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Bookmark, TrendingUp, FileText, Layers } from 'lucide-react';
import { useBookmarksContext } from '@/contexts/BookmarksContext';
import { useAuth } from '@/contexts/AuthContext';
import { BookmarkCard } from './BookmarkCard';
import { BookmarkFilters, BookmarkFilterOptions } from './BookmarkFilters';
import { CollectionManager } from './CollectionManager';
import { NoteEditModal } from './NoteEditModal';
import { Bookmark as BookmarkType } from '@/hooks/useBookmarks';

interface BookmarksDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function BookmarksDrawer({ isOpen, onClose }: BookmarksDrawerProps) {
  const { user, profile } = useAuth();
  const { bookmarks, favorites, loading, usage, toggleBookmark, deleteBookmark, refetch } = useBookmarksContext();
  const [filters, setFilters] = useState<BookmarkFilterOptions>({
    search: '',
    type: null,
    favorites: false,
    collectionId: null,
  });
  const [collections, setCollections] = useState<any[]>([]);
  const [loadingCollections, setLoadingCollections] = useState(false);

  // Note editing modal state
  const [editingBookmark, setEditingBookmark] = useState<BookmarkType | null>(null);
  const [isNoteModalOpen, setIsNoteModalOpen] = useState(false);

  // Tab navigation state
  const [activeTab, setActiveTab] = useState<'all' | 'bookmarks' | 'notes'>('all');

  // Fetch collections
  const fetchCollections = async () => {
    if (!user) return;
    setLoadingCollections(true);
    try {
      const response = await fetch('/api/bookmarks/collections');
      if (response.ok) {
        const data = await response.json();
        setCollections(data.collections || []);
      }
    } catch (error) {
      console.error('Failed to fetch collections:', error);
    } finally {
      setLoadingCollections(false);
    }
  };

  useEffect(() => {
    if (isOpen && user) {
      fetchCollections();
    }
  }, [isOpen, user]);

  // Handle create collection
  const handleCreateCollection = async (name: string, description?: string) => {
    const response = await fetch('/api/bookmarks/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to create collection');
    }

    await fetchCollections();
  };

  // Handle delete collection
  const handleDeleteCollection = async (collectionId: string) => {
    const response = await fetch(`/api/bookmarks/collections/${collectionId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('Failed to delete collection');
    }

    await fetchCollections();
    if (filters.collectionId === collectionId) {
      setFilters({ ...filters, collectionId: null });
    }
  };

  // Handle toggle favorite
  const handleToggleFavorite = async (bookmarkId: string) => {
    const bookmark = bookmarks.find((b) => b.id === bookmarkId);
    if (!bookmark) return;

    try {
      const response = await fetch(`/api/bookmarks/${bookmarkId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isFavorite: !bookmark.is_favorite }),
      });

      if (response.ok) {
        await refetch();
      } else {
        const error = await response.json();
        console.error('Failed to toggle favorite:', error);
      }
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    }
  };

  // Handle delete bookmark
  const handleDeleteBookmark = async (bookmarkId: string) => {
    await deleteBookmark(bookmarkId);
  };

  // Handle edit note
  const handleEditNote = (bookmarkId: string) => {
    const bookmark = bookmarks.find((b) => b.id === bookmarkId);
    if (bookmark) {
      setEditingBookmark(bookmark);
      setIsNoteModalOpen(true);
    }
  };

  // Handle save note
  const handleSaveNote = async (bookmarkId: string, notes: string, aiPrompt?: string) => {
    try {
      const response = await fetch(`/api/bookmarks/${bookmarkId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          notes,
          aiPrompt,
        }),
      });

      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.error || 'Failed to save note');
      }

      // Refresh bookmarks to show updated note
      await refetch();
    } catch (error) {
      console.error('Failed to save note:', error);
      throw error;
    }
  };

  // Filter bookmarks
  const filteredBookmarks = useMemo(() => {
    let result = bookmarks;

    // Filter by tab
    if (activeTab === 'bookmarks') {
      // Show only bookmarks without notes
      result = result.filter((b) => !b.notes || b.notes.trim() === '');
    } else if (activeTab === 'notes') {
      // Show only bookmarks with notes
      result = result.filter((b) => b.notes && b.notes.trim() !== '');
    }
    // activeTab === 'all' shows everything, no filtering needed

    // Filter by search
    if (filters.search) {
      const search = filters.search.toLowerCase();
      result = result.filter(
        (b) =>
          b.title.toLowerCase().includes(search) ||
          b.subtitle?.toLowerCase().includes(search) ||
          b.notes?.toLowerCase().includes(search) ||
          b.tags.some((tag) => tag.toLowerCase().includes(search))
      );
    }

    // Filter by type
    if (filters.type) {
      result = result.filter((b) => b.item_type === filters.type);
    }

    // Filter by favorites
    if (filters.favorites) {
      result = result.filter((b) => b.is_favorite);
    }

    // Filter by collection
    if (filters.collectionId) {
      result = result.filter((b) => b.collection_id === filters.collectionId);
    }

    return result;
  }, [bookmarks, filters, activeTab]);

  // Don't render if not authenticated
  if (!user) {
    return null;
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 h-full w-full sm:w-[400px] md:w-[450px] bg-bg-primary border-l border-border-subtle shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border-subtle bg-bg-elevated">
              <div className="flex items-center gap-3">
                <Bookmark className="h-5 w-5 text-accent-red" />
                <h2 className="text-lg font-bold text-text-primary">Bookmarks</h2>
                {usage && (
                  <span className="text-sm text-text-tertiary">
                    ({usage.total}{usage.limit ? `/${usage.limit}` : ''})
                  </span>
                )}
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-bg-overlay text-text-tertiary hover:text-text-primary transition-colors"
                aria-label="Close bookmarks"
              >
                <X size={20} />
              </button>
            </div>

            {/* Usage Meter */}
            {usage && usage.limit && (
              <div className="px-4 pt-3 pb-2">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-text-tertiary">
                    {usage.total} / {usage.limit} bookmarks used
                  </span>
                  {usage.isNearLimit && !usage.isAtLimit && (
                    <span className="text-amber-600 dark:text-amber-400 font-medium">
                      {usage.limit - usage.total} left
                    </span>
                  )}
                  {usage.isAtLimit && (
                    <span className="text-red-600 dark:text-red-400 font-medium">
                      Limit reached
                    </span>
                  )}
                </div>
                <div className="w-full bg-bg-elevated rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      usage.isAtLimit
                        ? 'bg-red-500'
                        : usage.isNearLimit
                        ? 'bg-amber-500'
                        : 'bg-accent-red'
                    }`}
                    style={{ width: `${Math.min(usage.percentage, 100)}%` }}
                  />
                </div>
                {usage.isAtLimit && (
                  <a
                    href="/pricing"
                    className="block mt-2 text-xs text-accent-red hover:text-accent-red-hover font-medium"
                  >
                    Upgrade for more bookmarks →
                  </a>
                )}
              </div>
            )}

            {/* Tab Navigation */}
            <div className="px-4 pt-3">
              <div className="flex gap-2 bg-bg-overlay rounded-lg p-1">
                <button
                  onClick={() => setActiveTab('all')}
                  className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all ${
                    activeTab === 'all'
                      ? 'bg-bg-elevated text-text-primary shadow-sm'
                      : 'text-text-tertiary hover:text-text-secondary'
                  }`}
                >
                  <Layers size={16} />
                  Show All
                </button>
                <button
                  onClick={() => setActiveTab('bookmarks')}
                  className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all ${
                    activeTab === 'bookmarks'
                      ? 'bg-bg-elevated text-text-primary shadow-sm'
                      : 'text-text-tertiary hover:text-text-secondary'
                  }`}
                >
                  <Bookmark size={16} />
                  Bookmarks
                </button>
                <button
                  onClick={() => setActiveTab('notes')}
                  className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all ${
                    activeTab === 'notes'
                      ? 'bg-bg-elevated text-text-primary shadow-sm'
                      : 'text-text-tertiary hover:text-text-secondary'
                  }`}
                >
                  <FileText size={16} />
                  Notes
                </button>
              </div>
            </div>

            {/* Filters */}
            <div className="px-4 pt-3">
              <BookmarkFilters
                filters={filters}
                onFiltersChange={setFilters}
                totalBookmarks={bookmarks.length}
                filteredCount={filteredBookmarks.length}
              />
            </div>

            {/* Collections */}
            <div className="px-4 pt-3 border-b border-border-subtle pb-3">
              <CollectionManager
                collections={collections}
                selectedCollectionId={filters.collectionId}
                onSelectCollection={(id) => setFilters({ ...filters, collectionId: id })}
                onCreateCollection={handleCreateCollection}
                onDeleteCollection={handleDeleteCollection}
              />
            </div>

            {/* Bookmarks List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {loading ? (
                <div className="text-center py-8 text-text-tertiary">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-red mx-auto mb-2" />
                  Loading bookmarks...
                </div>
              ) : filteredBookmarks.length > 0 ? (
                filteredBookmarks.map((bookmark) => (
                  <BookmarkCard
                    key={bookmark.id}
                    bookmark={bookmark}
                    onToggleFavorite={handleToggleFavorite}
                    onDelete={handleDeleteBookmark}
                    onEditNote={handleEditNote}
                    tier={profile?.subscription_tier}
                  />
                ))
              ) : bookmarks.length === 0 ? (
                <div className="text-center py-8">
                  <Bookmark className="h-12 w-12 text-text-tertiary mx-auto mb-3" />
                  <h3 className="text-lg font-semibold text-text-primary mb-2">
                    No Bookmarks Yet
                  </h3>
                  <p className="text-sm text-text-secondary mb-4">
                    Start bookmarking MPs, bills, debates, and more to access them quickly!
                  </p>
                  <p className="text-xs text-text-tertiary">
                    Look for the <Bookmark size={14} className="inline" /> icon throughout the site
                  </p>
                </div>
              ) : (
                <div className="text-center py-8 text-text-tertiary">
                  No bookmarks match your filters
                </div>
              )}
            </div>

            {/* Footer - Keyboard Hint */}
            <div className="px-4 py-3 border-t border-border-subtle bg-bg-elevated">
              <p className="text-xs text-text-tertiary text-center">
                Press <kbd className="px-1.5 py-0.5 bg-bg-overlay rounded text-[10px] font-mono">Cmd+B</kbd> or{' '}
                <kbd className="px-1.5 py-0.5 bg-bg-overlay rounded text-[10px] font-mono">Ctrl+B</kbd> to toggle
              </p>
            </div>
          </motion.div>

          {/* Note Edit Modal */}
          <NoteEditModal
            bookmark={editingBookmark}
            isOpen={isNoteModalOpen}
            onClose={() => {
              setIsNoteModalOpen(false);
              setEditingBookmark(null);
            }}
            onSave={handleSaveNote}
            tier={profile?.subscription_tier}
          />
        </>
      )}
    </AnimatePresence>
  );
}
