/**
 * useMentionAutocomplete Hook
 *
 * Detects @mentions in text and provides autocomplete suggestions
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

interface User {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

export function useMentionAutocomplete(
  textareaRef: React.RefObject<HTMLTextAreaElement>
) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [suggestions, setSuggestions] = useState<User[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [cursorPosition, setCursorPosition] = useState(0);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Detect @ symbol and extract search term
  const detectMention = useCallback((text: string, cursorPos: number) => {
    // Look backward from cursor to find @ symbol
    let atIndex = -1;
    for (let i = cursorPos - 1; i >= 0; i--) {
      if (text[i] === '@') {
        atIndex = i;
        break;
      }
      // Stop if we hit a space or newline
      if (text[i] === ' ' || text[i] === '\n') {
        break;
      }
    }

    if (atIndex >= 0) {
      const searchTerm = text.substring(atIndex + 1, cursorPos);
      // Only show autocomplete if search term is reasonable
      if (searchTerm.length <= 30 && !/\s/.test(searchTerm)) {
        return { found: true, searchTerm, atIndex };
      }
    }

    return { found: false, searchTerm: '', atIndex: -1 };
  }, []);

  // Fetch user suggestions
  const fetchSuggestions = useCallback(async (searchTerm: string) => {
    if (!searchTerm) {
      setSuggestions([]);
      return;
    }

    try {
      const response = await fetch(
        `/api/users/search?q=${encodeURIComponent(searchTerm)}&limit=5`
      );

      if (!response.ok) return;

      const data = await response.json();
      setSuggestions(data.users || []);
    } catch (error) {
      console.error('Error fetching user suggestions:', error);
    }
  }, []);

  // Handle text change
  const handleTextChange = useCallback(
    (text: string) => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const cursorPos = textarea.selectionStart;
      setCursorPosition(cursorPos);

      const { found, searchTerm, atIndex } = detectMention(text, cursorPos);

      if (found) {
        setSearch(searchTerm);
        setIsOpen(true);
        setSelectedIndex(0);

        // Debounce search
        if (searchTimeoutRef.current) {
          clearTimeout(searchTimeoutRef.current);
        }
        searchTimeoutRef.current = setTimeout(() => {
          fetchSuggestions(searchTerm);
        }, 150);
      } else {
        setIsOpen(false);
        setSuggestions([]);
      }
    },
    [textareaRef, detectMention, fetchSuggestions]
  );

  // Insert mention into text
  const insertMention = useCallback(
    (user: User, currentText: string) => {
      const textarea = textareaRef.current;
      if (!textarea) return currentText;

      const cursorPos = textarea.selectionStart;
      const { atIndex } = detectMention(currentText, cursorPos);

      if (atIndex >= 0) {
        // Replace from @ to cursor with @username
        const before = currentText.substring(0, atIndex);
        const after = currentText.substring(cursorPos);
        const newText = `${before}@${user.username} ${after}`;

        // Update cursor position
        setTimeout(() => {
          const newCursorPos = atIndex + user.username.length + 2; // @ + username + space
          textarea.setSelectionRange(newCursorPos, newCursorPos);
          textarea.focus();
        }, 0);

        setIsOpen(false);
        setSuggestions([]);

        return newText;
      }

      return currentText;
    },
    [textareaRef, detectMention]
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (!isOpen || suggestions.length === 0) return false;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
          return true;

        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          return true;

        case 'Enter':
        case 'Tab':
          if (suggestions[selectedIndex]) {
            e.preventDefault();
            const currentText = textareaRef.current?.value || '';
            const newText = insertMention(suggestions[selectedIndex], currentText);
            // Return the new text so the parent can update
            if (textareaRef.current) {
              textareaRef.current.value = newText;
            }
            return true;
          }
          break;

        case 'Escape':
          e.preventDefault();
          setIsOpen(false);
          return true;
      }

      return false;
    },
    [isOpen, suggestions, selectedIndex, insertMention, textareaRef]
  );

  // Cleanup
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  return {
    isOpen,
    suggestions,
    selectedIndex,
    handleTextChange,
    handleKeyDown,
    insertMention,
    setIsOpen,
    setSelectedIndex,
  };
}
