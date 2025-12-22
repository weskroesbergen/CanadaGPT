/**
 * MentionAutocomplete Component
 *
 * Dropdown showing user suggestions for @mentions
 */

'use client';

import Image from 'next/image';
import { cn } from '@/lib/utils';

interface User {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

interface MentionAutocompleteProps {
  suggestions: User[];
  selectedIndex: number;
  onSelect: (user: User) => void;
  onHover: (index: number) => void;
}

export function MentionAutocomplete({
  suggestions,
  selectedIndex,
  onSelect,
  onHover,
}: MentionAutocompleteProps) {
  if (suggestions.length === 0) return null;

  return (
    <div className="absolute bottom-full left-0 mb-2 w-full max-w-xs rounded-lg border bg-background shadow-lg">
      <div className="max-h-60 overflow-y-auto">
        {suggestions.map((user, index) => (
          <button
            key={user.id}
            type="button"
            onClick={() => onSelect(user)}
            onMouseEnter={() => onHover(index)}
            className={cn(
              'flex w-full items-center gap-3 px-4 py-2 text-left transition-colors',
              'hover:bg-muted',
              index === selectedIndex && 'bg-muted'
            )}
          >
            {/* Avatar */}
            <div className="relative h-8 w-8 flex-shrink-0 rounded-full bg-muted">
              {user.avatar_url ? (
                <Image
                  src={user.avatar_url}
                  alt={user.display_name}
                  fill
                  className="rounded-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-xs font-bold text-white">
                  {user.display_name?.[0]?.toUpperCase() || '?'}
                </div>
              )}
            </div>

            {/* User info */}
            <div className="flex-1 overflow-hidden">
              <p className="truncate font-medium">{user.display_name}</p>
              <p className="truncate text-sm text-muted-foreground">
                @{user.username}
              </p>
            </div>
          </button>
        ))}
      </div>

      <div className="border-t bg-muted/50 px-4 py-2 text-xs text-muted-foreground">
        <kbd className="rounded bg-background px-1">↑</kbd>
        <kbd className="ml-1 rounded bg-background px-1">↓</kbd> to navigate,{' '}
        <kbd className="rounded bg-background px-1">Enter</kbd> to select
      </div>
    </div>
  );
}
