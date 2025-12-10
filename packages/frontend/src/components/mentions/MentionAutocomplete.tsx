'use client';

import React, {
  useState,
  useRef,
  useEffect,
} from 'react';
import {
  FileText,
  User,
  Vote,
  Users,
  MessageSquare,
  FileSignature,
  Search,
  ChevronRight,
  X,
  Loader2,
} from 'lucide-react';
import { useMentionSearch } from '@/hooks/useMentionSearch';

/**
 * Entity types that can be mentioned
 */
export type MentionEntityType =
  | 'bill'
  | 'mp'
  | 'committee'
  | 'vote'
  | 'debate'
  | 'petition';

/**
 * Mention suggestion item
 */
export interface MentionSuggestion {
  /** Entity type */
  type: MentionEntityType;
  /** Unique identifier */
  id: string;
  /** Display label */
  label: string;
  /** Secondary text (e.g., description, subtitle) */
  secondary?: string;
  /** Full mention string to insert (e.g., "@bill:c-234:s2.1") */
  mentionString: string;
  /** URL to navigate to when clicked */
  url?: string;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Props for MentionAutocomplete component
 */
interface MentionAutocompleteProps {
  /** Callback when a mention is selected */
  onSelect: (suggestion: MentionSuggestion) => void;
  /** Callback when autocomplete is cancelled */
  onCancel: () => void;
  /** Current search query (text after @) */
  query: string;
  /** Position for the autocomplete popup */
  position?: { top: number; left: number };
  /** Whether the autocomplete is visible */
  isVisible: boolean;
  /** Current locale */
  locale?: string;
  /** Optional filter to specific entity types */
  allowedTypes?: MentionEntityType[];
  /** Maximum suggestions to show */
  maxSuggestions?: number;
}

/**
 * Icon component for entity types
 */
const EntityIcon: React.FC<{ type: MentionEntityType; className?: string }> = ({
  type,
  className = 'h-4 w-4',
}) => {
  const icons: Record<MentionEntityType, React.ReactNode> = {
    bill: <FileText className={className} />,
    mp: <User className={className} />,
    committee: <Users className={className} />,
    vote: <Vote className={className} />,
    debate: <MessageSquare className={className} />,
    petition: <FileSignature className={className} />,
  };

  return <>{icons[type]}</>;
};

/**
 * Entity type labels
 */
const getEntityTypeLabel = (
  type: MentionEntityType,
  locale: string
): string => {
  const labels: Record<MentionEntityType, { en: string; fr: string }> = {
    bill: { en: 'Bill', fr: 'Projet de loi' },
    mp: { en: 'MP', fr: 'Depute' },
    committee: { en: 'Committee', fr: 'Comite' },
    vote: { en: 'Vote', fr: 'Vote' },
    debate: { en: 'Debate', fr: 'Debat' },
    petition: { en: 'Petition', fr: 'Petition' },
  };

  return locale === 'fr' ? labels[type].fr : labels[type].en;
};

/**
 * Entity type colors
 */
const getEntityTypeColor = (type: MentionEntityType): string => {
  const colors: Record<MentionEntityType, string> = {
    bill: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
    mp: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    committee:
      'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/30',
    vote: 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30',
    debate: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
    petition:
      'text-teal-600 bg-teal-100 dark:text-teal-400 dark:bg-teal-900/30',
  };

  return colors[type];
};

// Query parsing is now handled in useMentionSearch hook

/**
 * Suggestion item component
 */
const SuggestionItem: React.FC<{
  suggestion: MentionSuggestion;
  isSelected: boolean;
  onClick: () => void;
  locale: string;
}> = ({ suggestion, isSelected, onClick, locale }) => {
  const colorClass = getEntityTypeColor(suggestion.type);

  return (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center gap-3 px-3 py-2 text-left
        transition-colors duration-100
        ${
          isSelected
            ? 'bg-blue-50 dark:bg-blue-900/30'
            : 'hover:bg-gray-50 dark:hover:bg-gray-800'
        }
      `}
      role="option"
      aria-selected={isSelected}
    >
      {/* Entity type icon */}
      <span className={`p-1.5 rounded ${colorClass}`}>
        <EntityIcon type={suggestion.type} className="h-4 w-4" />
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-gray-100 truncate">
            {suggestion.label}
          </span>
          <span
            className={`text-xs px-1.5 py-0.5 rounded ${colorClass} opacity-75`}
          >
            {getEntityTypeLabel(suggestion.type, locale)}
          </span>
        </div>
        {suggestion.secondary && (
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
            {suggestion.secondary}
          </p>
        )}
      </div>

      {/* Arrow indicator */}
      <ChevronRight className="h-4 w-4 text-gray-400 dark:text-gray-500 flex-shrink-0" />
    </button>
  );
};

/**
 * Entity type filter buttons
 */
const TypeFilter: React.FC<{
  types: MentionEntityType[];
  activeType: MentionEntityType | null;
  onTypeSelect: (type: MentionEntityType | null) => void;
  locale: string;
}> = ({ types, activeType, onTypeSelect, locale }) => {
  return (
    <div className="flex items-center gap-1 px-2 py-1.5 border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
      <button
        onClick={() => onTypeSelect(null)}
        className={`
          px-2 py-1 text-xs font-medium rounded-md whitespace-nowrap
          transition-colors
          ${
            activeType === null
              ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
          }
        `}
      >
        {locale === 'fr' ? 'Tous' : 'All'}
      </button>

      {types.map((type) => (
        <button
          key={type}
          onClick={() => onTypeSelect(type)}
          className={`
            flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md whitespace-nowrap
            transition-colors
            ${
              activeType === type
                ? `${getEntityTypeColor(type)}`
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
            }
          `}
        >
          <EntityIcon type={type} className="h-3 w-3" />
          {getEntityTypeLabel(type, locale)}
        </button>
      ))}
    </div>
  );
};

/**
 * MentionAutocomplete - Universal autocomplete for @mentions
 *
 * Features:
 * - Multi-entity search (bills, MPs, committees, votes, debates, petitions)
 * - Type filtering with keyboard shortcuts
 * - Keyboard navigation (up/down, enter, escape)
 * - Debounced search
 * - Position-aware popup
 */
export const MentionAutocomplete: React.FC<MentionAutocompleteProps> = ({
  onSelect,
  onCancel,
  query,
  position,
  isVisible,
  locale = 'en',
  allowedTypes,
  maxSuggestions = 8,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [activeTypeFilter, setActiveTypeFilter] =
    useState<MentionEntityType | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Available entity types
  const availableTypes: MentionEntityType[] =
    allowedTypes || ['bill', 'mp', 'committee', 'vote', 'debate', 'petition'];

  // Determine types to search based on filter
  const typesToSearch = activeTypeFilter
    ? [activeTypeFilter]
    : availableTypes;

  // Use the real search hook
  const { suggestions, loading } = useMentionSearch({
    query: isVisible && query.length >= 1 ? query : '',
    types: typesToSearch,
    locale,
    maxResults: maxSuggestions,
  });

  // Reset selection when suggestions change
  useEffect(() => {
    setSelectedIndex(0);
  }, [suggestions]);

  // Keyboard navigation
  useEffect(() => {
    if (!isVisible) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev < suggestions.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev > 0 ? prev - 1 : suggestions.length - 1
          );
          break;
        case 'Enter':
          e.preventDefault();
          if (suggestions[selectedIndex]) {
            onSelect(suggestions[selectedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          onCancel();
          break;
        case 'Tab':
          // Allow tab to cycle through type filters
          if (e.shiftKey) {
            const currentIndex = activeTypeFilter
              ? availableTypes.indexOf(activeTypeFilter)
              : -1;
            const newIndex =
              currentIndex <= 0
                ? availableTypes.length - 1
                : currentIndex - 1;
            setActiveTypeFilter(availableTypes[newIndex]);
          } else {
            const currentIndex = activeTypeFilter
              ? availableTypes.indexOf(activeTypeFilter)
              : -1;
            if (currentIndex >= availableTypes.length - 1) {
              setActiveTypeFilter(null);
            } else {
              setActiveTypeFilter(availableTypes[currentIndex + 1]);
            }
          }
          e.preventDefault();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [
    isVisible,
    suggestions,
    selectedIndex,
    onSelect,
    onCancel,
    activeTypeFilter,
    availableTypes,
  ]);

  // Click outside to close
  useEffect(() => {
    if (!isVisible) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        onCancel();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isVisible, onCancel]);

  if (!isVisible) return null;

  const style: React.CSSProperties = position
    ? {
        position: 'absolute',
        top: position.top,
        left: position.left,
      }
    : {};

  return (
    <div
      ref={containerRef}
      style={style}
      className="
        z-50 w-80 max-h-96
        bg-white dark:bg-gray-900
        border border-gray-200 dark:border-gray-700
        rounded-lg shadow-lg
        overflow-hidden
      "
      role="listbox"
      aria-label={locale === 'fr' ? 'Suggestions de mention' : 'Mention suggestions'}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-gray-400" />
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {query || (locale === 'fr' ? 'Rechercher...' : 'Search...')}
          </span>
        </div>
        <button
          onClick={onCancel}
          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          aria-label={locale === 'fr' ? 'Fermer' : 'Close'}
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Type filters */}
      <TypeFilter
        types={availableTypes}
        activeType={activeTypeFilter}
        onTypeSelect={setActiveTypeFilter}
        locale={locale}
      />

      {/* Suggestions list */}
      <div className="max-h-64 overflow-y-auto">
        {loading ? (
          <div className="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
            <Loader2 className="h-8 w-8 mx-auto mb-2 animate-spin opacity-50" />
            <p className="text-sm">
              {locale === 'fr' ? 'Recherche...' : 'Searching...'}
            </p>
          </div>
        ) : suggestions.length === 0 ? (
          <div className="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
            <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">
              {locale === 'fr'
                ? 'Aucun resultat trouve'
                : 'No results found'}
            </p>
            <p className="text-xs mt-1 opacity-75">
              {locale === 'fr'
                ? 'Essayez un autre terme de recherche'
                : 'Try a different search term'}
            </p>
          </div>
        ) : (
          suggestions.map((suggestion, index) => (
            <SuggestionItem
              key={`${suggestion.type}-${suggestion.id}`}
              suggestion={suggestion}
              isSelected={index === selectedIndex}
              onClick={() => onSelect(suggestion)}
              locale={locale}
            />
          ))
        )}
      </div>

      {/* Footer hint */}
      <div className="px-3 py-1.5 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
          {locale === 'fr' ? (
            <>
              <kbd className="px-1 bg-gray-200 dark:bg-gray-700 rounded">
                Tab
              </kbd>{' '}
              filtrer{' '}
              <kbd className="px-1 bg-gray-200 dark:bg-gray-700 rounded">
                Entree
              </kbd>{' '}
              selectionner{' '}
              <kbd className="px-1 bg-gray-200 dark:bg-gray-700 rounded">
                Echap
              </kbd>{' '}
              fermer
            </>
          ) : (
            <>
              <kbd className="px-1 bg-gray-200 dark:bg-gray-700 rounded">
                Tab
              </kbd>{' '}
              filter{' '}
              <kbd className="px-1 bg-gray-200 dark:bg-gray-700 rounded">
                Enter
              </kbd>{' '}
              select{' '}
              <kbd className="px-1 bg-gray-200 dark:bg-gray-700 rounded">
                Esc
              </kbd>{' '}
              close
            </>
          )}
        </p>
      </div>
    </div>
  );
};

export default MentionAutocomplete;
