/**
 * BookmarksContext
 *
 * Provides shared bookmark state across the entire application
 * Prevents each BookmarkButton from creating its own useBookmarks instance
 * Reduces API calls from 343+ to just 1
 */

'use client';

import React, { createContext, useContext, ReactNode } from 'react';
import { useBookmarks, Bookmark, CreateBookmarkData, BookmarkUsage } from '@/hooks/useBookmarks';

interface BookmarksContextType {
  bookmarks: Bookmark[];
  favorites: Bookmark[];
  loading: boolean;
  error: string | null;
  usage: BookmarkUsage | null;
  isBookmarked: (itemType: string, itemId: string) => boolean;
  getBookmark: (itemType: string, itemId: string) => Bookmark | undefined;
  toggleBookmark: (data: CreateBookmarkData) => Promise<{ success: boolean; action: 'created' | 'removed'; error?: string }>;
  updateBookmark: (
    bookmarkId: string,
    updates: Partial<{
      collectionId: string | null;
      tags: string[];
      notes: string;
      isFavorite: boolean;
      notificationsEnabled: boolean;
    }>
  ) => Promise<{ success: boolean; error?: string }>;
  deleteBookmark: (bookmarkId: string) => Promise<{ success: boolean; error?: string }>;
  refetch: () => Promise<void>;
}

const BookmarksContext = createContext<BookmarksContextType | undefined>(undefined);

export function BookmarksProvider({ children }: { children: ReactNode }) {
  const bookmarksState = useBookmarks();

  return (
    <BookmarksContext.Provider value={bookmarksState}>
      {children}
    </BookmarksContext.Provider>
  );
}

export function useBookmarksContext() {
  const context = useContext(BookmarksContext);
  if (context === undefined) {
    throw new Error('useBookmarksContext must be used within a BookmarksProvider');
  }
  return context;
}
