'use client';

import React, {
  useState,
  useCallback,
  useRef,
  useEffect,
  useMemo,
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
} from 'lucide-react';

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

/**
 * Parse mention query to extract type prefix and search term
 * Examples:
 *   "@bill:c-234" -> { type: "bill", search: "c-234" }
 *   "@mp:poili" -> { type: "mp", search: "poili" }
 *   "@poili" -> { type: null, search: "poili" }
 */
function parseQuery(query: string): {
  type: MentionEntityType | null;
  search: string;
} {
  // Remove @ prefix if present
  const cleanQuery = query.startsWith('@') ? query.slice(1) : query;

  // Check for type prefix (e.g., "bill:", "mp:")
  const colonIndex = cleanQuery.indexOf(':');
  if (colonIndex > 0) {
    const potentialType = cleanQuery.slice(0, colonIndex).toLowerCase();
    const validTypes: MentionEntityType[] = [
      'bill',
      'mp',
      'committee',
      'vote',
      'debate',
      'petition',
    ];

    if (validTypes.includes(potentialType as MentionEntityType)) {
      return {
        type: potentialType as MentionEntityType,
        search: cleanQuery.slice(colonIndex + 1),
      };
    }
  }

  return { type: null, search: cleanQuery };
}

/**
 * Generate mock suggestions (to be replaced with real API calls)
 * In production, this would fetch from GraphQL or a search API
 */
function generateMockSuggestions(
  query: string,
  locale: string,
  allowedTypes?: MentionEntityType[]
): MentionSuggestion[] {
  const { type, search } = parseQuery(query);
  const suggestions: MentionSuggestion[] = [];

  const lowerSearch = search.toLowerCase();

  // Filter by allowed types if specified
  const typesToSearch =
    type !== null
      ? [type]
      : allowedTypes || ['bill', 'mp', 'committee', 'vote', 'debate', 'petition'];

  // Bill suggestions
  if (typesToSearch.includes('bill')) {
    const bills = [
      { id: 'c-234', title: 'Budget Implementation Act', session: '45-1' },
      { id: 'c-21', title: 'Online Harms Act', session: '45-1' },
      { id: 's-12', title: 'Strengthening Environmental Act', session: '45-1' },
      { id: 'c-3', title: 'Citizenship Act Amendments', session: '45-1' },
      { id: 'c-56', title: 'Affordable Housing Act', session: '45-1' },
    ];

    bills
      .filter(
        (b) =>
          b.id.toLowerCase().includes(lowerSearch) ||
          b.title.toLowerCase().includes(lowerSearch)
      )
      .forEach((bill) => {
        suggestions.push({
          type: 'bill',
          id: bill.id,
          label: `Bill ${bill.id.toUpperCase()}`,
          secondary: bill.title,
          mentionString: `@bill:${bill.id}`,
          url: `/bills/${bill.session}/${bill.id}`,
          metadata: { session: bill.session },
        });
      });
  }

  // MP suggestions
  if (typesToSearch.includes('mp')) {
    const mps = [
      {
        id: 'pierre-poilievre',
        name: 'Pierre Poilievre',
        riding: 'Carleton',
        party: 'Conservative',
      },
      {
        id: 'mark-carney',
        name: 'Mark Carney',
        riding: 'Toronto Centre',
        party: 'Liberal',
      },
      {
        id: 'jagmeet-singh',
        name: 'Jagmeet Singh',
        riding: 'Burnaby South',
        party: 'NDP',
      },
      {
        id: 'elizabeth-may',
        name: 'Elizabeth May',
        riding: 'Saanich-Gulf Islands',
        party: 'Green',
      },
      {
        id: 'yves-francois-blanchet',
        name: 'Yves-Francois Blanchet',
        riding: 'Beloeil-Chambly',
        party: 'Bloc',
      },
    ];

    mps
      .filter(
        (mp) =>
          mp.name.toLowerCase().includes(lowerSearch) ||
          mp.riding.toLowerCase().includes(lowerSearch) ||
          mp.id.toLowerCase().includes(lowerSearch)
      )
      .forEach((mp) => {
        suggestions.push({
          type: 'mp',
          id: mp.id,
          label: mp.name,
          secondary: `${mp.riding} - ${mp.party}`,
          mentionString: `@mp:${mp.id}`,
          url: `/mps/${mp.id}`,
          metadata: { party: mp.party },
        });
      });
  }

  // Committee suggestions
  if (typesToSearch.includes('committee')) {
    const committees = [
      { code: 'FINA', name: 'Finance' },
      { code: 'ETHI', name: 'Ethics and Privacy' },
      { code: 'ENVI', name: 'Environment and Sustainable Development' },
      { code: 'HESA', name: 'Health' },
      { code: 'JUST', name: 'Justice and Human Rights' },
    ];

    committees
      .filter(
        (c) =>
          c.code.toLowerCase().includes(lowerSearch) ||
          c.name.toLowerCase().includes(lowerSearch)
      )
      .forEach((committee) => {
        suggestions.push({
          type: 'committee',
          id: committee.code,
          label: committee.code,
          secondary: committee.name,
          mentionString: `@committee:${committee.code.toLowerCase()}`,
          url: `/committees/${committee.code.toLowerCase()}`,
        });
      });
  }

  // Vote suggestions
  if (typesToSearch.includes('vote')) {
    const votes = [
      { id: '45-1-234', subject: 'Bill C-234 Third Reading', result: 'Passed' },
      { id: '45-1-233', subject: 'Opposition Motion', result: 'Negatived' },
      { id: '45-1-232', subject: 'Budget Vote', result: 'Passed' },
    ];

    votes
      .filter(
        (v) =>
          v.id.includes(lowerSearch) ||
          v.subject.toLowerCase().includes(lowerSearch)
      )
      .forEach((vote) => {
        suggestions.push({
          type: 'vote',
          id: vote.id,
          label: `Vote #${vote.id.split('-')[2]}`,
          secondary: `${vote.subject} - ${vote.result}`,
          mentionString: `@vote:${vote.id}`,
          url: `/votes/${vote.id}`,
        });
      });
  }

  // Debate suggestions
  if (typesToSearch.includes('debate')) {
    const debates = [
      { date: '2025-12-09', subject: 'Question Period', time: '14:00' },
      { date: '2025-12-08', subject: 'Government Orders', time: '10:00' },
      { date: '2025-12-07', subject: 'Private Members Business', time: '11:00' },
    ];

    debates
      .filter(
        (d) =>
          d.date.includes(lowerSearch) ||
          d.subject.toLowerCase().includes(lowerSearch)
      )
      .forEach((debate) => {
        suggestions.push({
          type: 'debate',
          id: debate.date,
          label: debate.date,
          secondary: `${debate.subject} at ${debate.time}`,
          mentionString: `@debate:${debate.date}:${debate.time.replace(':', '-')}`,
          url: `/debates/${debate.date}`,
        });
      });
  }

  // Petition suggestions
  if (typesToSearch.includes('petition')) {
    const petitions = [
      { id: 'e-4823', title: 'Climate Action Now', signatures: 125000 },
      { id: 'e-4756', title: 'Healthcare Funding', signatures: 89000 },
      { id: 'e-4698', title: 'Housing Affordability', signatures: 156000 },
    ];

    petitions
      .filter(
        (p) =>
          p.id.includes(lowerSearch) ||
          p.title.toLowerCase().includes(lowerSearch)
      )
      .forEach((petition) => {
        suggestions.push({
          type: 'petition',
          id: petition.id,
          label: petition.id.toUpperCase(),
          secondary: `${petition.title} (${petition.signatures.toLocaleString()} signatures)`,
          mentionString: `@petition:${petition.id}`,
          url: `/petitions/${petition.id}`,
        });
      });
  }

  return suggestions;
}

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

  // Generate suggestions based on query
  const suggestions = useMemo(() => {
    if (!isVisible || query.length < 1) return [];

    const typesToSearch = activeTypeFilter
      ? [activeTypeFilter]
      : availableTypes;
    const results = generateMockSuggestions(query, locale, typesToSearch);

    return results.slice(0, maxSuggestions);
  }, [query, isVisible, activeTypeFilter, availableTypes, locale, maxSuggestions]);

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
        {suggestions.length === 0 ? (
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
