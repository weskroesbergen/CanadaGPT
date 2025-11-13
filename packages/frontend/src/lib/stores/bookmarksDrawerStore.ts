/**
 * Bookmarks Drawer Store - Zustand state management for bookmarks drawer
 */

import { create } from 'zustand';

interface BookmarksDrawerState {
  isOpen: boolean;
}

interface BookmarksDrawerActions {
  toggleOpen: () => void;
  setOpen: (open: boolean) => void;
}

interface BookmarksDrawerStore extends BookmarksDrawerState, BookmarksDrawerActions {}

export const useBookmarksDrawerStore = create<BookmarksDrawerStore>((set) => ({
  isOpen: false,

  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),
  setOpen: (open: boolean) => set({ isOpen: open }),
}));

// Hook for common operations
export const useBookmarksDrawerOpen = () => {
  const isOpen = useBookmarksDrawerStore((state) => state.isOpen);
  const toggleOpen = useBookmarksDrawerStore((state) => state.toggleOpen);
  const setOpen = useBookmarksDrawerStore((state) => state.setOpen);
  return { isOpen, toggleOpen, setOpen } as const;
};
