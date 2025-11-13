/**
 * BookmarksDrawerWrapper - Manages bookmarks drawer state and keyboard shortcuts
 *
 * Wraps the BookmarksDrawer and connects it to global state management
 */

'use client';

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bookmark } from 'lucide-react';
import { BookmarksDrawer } from './BookmarksDrawer';
import { useBookmarksDrawerOpen } from '@/lib/stores/bookmarksDrawerStore';
import { useBookmarksContext } from '@/contexts/BookmarksContext';
import { useAuth } from '@/contexts/AuthContext';
import { useChatOpen } from '@/lib/stores/chatStore';

export function BookmarksDrawerWrapper() {
  const { user } = useAuth();
  const { isOpen, toggleOpen, setOpen } = useBookmarksDrawerOpen();
  const { bookmarks } = useBookmarksContext();
  const [isChatOpen] = useChatOpen();

  // Global keyboard shortcut: Cmd/Ctrl + B
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault();
        if (user) {
          setOpen(!isOpen);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, setOpen, user]);

  // Don't render if not authenticated
  if (!user) {
    return null;
  }

  return (
    <>
      {/* Floating bookmark button (above chat button) */}
      {!isOpen && !isChatOpen && (
        <motion.button
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 260, damping: 20 }}
          onClick={toggleOpen}
          className="fixed bottom-[100px] right-7 z-50 w-12 h-12 bg-accent-red text-white rounded-full shadow-lg hover:bg-red-700 active:scale-95 transition-colors flex items-center justify-center group"
          title="Open bookmarks (⌘B)"
        >
          <Bookmark className="w-5 h-5" />

          {/* Badge for bookmark count */}
          {bookmarks.length > 0 && (
            <span className="absolute -top-1 -right-1 bg-white text-accent-red text-[10px] rounded-full h-5 w-5 flex items-center justify-center font-bold border-2 border-accent-red">
              {bookmarks.length > 99 ? '99+' : bookmarks.length}
            </span>
          )}

          {/* Keyboard hint tooltip */}
          <div className="absolute bottom-full right-0 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
            Press ⌘B to open
          </div>
        </motion.button>
      )}

      {/* Bookmarks drawer */}
      <BookmarksDrawer
        isOpen={isOpen}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
