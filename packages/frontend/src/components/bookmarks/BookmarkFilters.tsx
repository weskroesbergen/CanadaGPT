/**
 * BookmarkFilters Component
 *
 * Filter controls for bookmarks drawer
 */

'use client';

import { Search, Filter, Star, X } from 'lucide-react';

export interface BookmarkFilterOptions {
  search: string;
  type: string | null;
  favorites: boolean;
  collectionId: string | null;
}

interface BookmarkFiltersProps {
  filters: BookmarkFilterOptions;
  onFiltersChange: (filters: BookmarkFilterOptions) => void;
  totalBookmarks: number;
  filteredCount: number;
}

const BOOKMARK_TYPES = [
  { value: 'mp', label: 'MPs' },
  { value: 'bill', label: 'Bills' },
  { value: 'statement', label: 'Statements' },
  { value: 'debate', label: 'Debates' },
  { value: 'committee', label: 'Committees' },
  { value: 'post', label: 'Posts' },
];

export function BookmarkFilters({
  filters,
  onFiltersChange,
  totalBookmarks,
  filteredCount,
}: BookmarkFiltersProps) {
  const updateFilter = (key: keyof BookmarkFilterOptions, value: any) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const hasActiveFilters = filters.search || filters.type || filters.favorites || filters.collectionId;

  const clearFilters = () => {
    onFiltersChange({
      search: '',
      type: null,
      favorites: false,
      collectionId: null,
    });
  };

  return (
    <div className="space-y-3 pb-3 border-b border-border-subtle">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary" />
        <input
          type="text"
          value={filters.search}
          onChange={(e) => updateFilter('search', e.target.value)}
          placeholder="Search bookmarks..."
          className="w-full pl-10 pr-4 py-2 rounded-lg bg-bg-elevated border border-border-subtle text-sm text-text-primary placeholder-text-tertiary focus:border-accent-red focus:outline-none focus:ring-1 focus:ring-accent-red"
        />
      </div>

      {/* Quick Filters */}
      <div className="flex flex-wrap gap-2">
        {/* Favorites Toggle */}
        <button
          onClick={() => updateFilter('favorites', !filters.favorites)}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
            filters.favorites
              ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300'
              : 'bg-bg-elevated border-border text-text-secondary hover:border-accent-red'
          }`}
        >
          <Star
            size={12}
            className={filters.favorites ? 'fill-current' : ''}
          />
          Favorites
        </button>

        {/* Type Filters */}
        {BOOKMARK_TYPES.map((type) => (
          <button
            key={type.value}
            onClick={() => updateFilter('type', filters.type === type.value ? null : type.value)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
              filters.type === type.value
                ? 'bg-accent-red border-accent-red text-white'
                : 'bg-bg-elevated border-border text-text-secondary hover:border-accent-red'
            }`}
          >
            {type.label}
          </button>
        ))}

        {/* Clear Filters */}
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-border text-text-secondary hover:border-red-500 hover:text-red-600 transition-colors"
          >
            <X size={12} />
            Clear
          </button>
        )}
      </div>

      {/* Results Count */}
      {hasActiveFilters && (
        <div className="text-xs text-text-tertiary">
          Showing {filteredCount} of {totalBookmarks} bookmarks
        </div>
      )}
    </div>
  );
}
