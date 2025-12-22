'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { BillTextViewer } from './BillTextViewer';
import { getActivityLevel, type ActivityLevel } from './DiscussionActivityIndicator';

/**
 * View modes for the split view layout
 */
export type SplitViewMode = 'read' | 'discuss-50' | 'discuss-33';

/**
 * Section discussion count data
 */
export interface SectionDiscussionCount {
  /** Section anchor ID */
  sectionId: string;
  /** Number of comments/replies */
  count: number;
}

interface BillSplitViewProps {
  /** Bill number (e.g., "C-234") */
  billNumber: string;
  /** Parliamentary session (e.g., "45-1") */
  session: string;
  /** Current locale for i18n */
  locale: string;
  /** Initial view mode */
  initialMode?: SplitViewMode;
  /** Initial section to scroll to (anchor ID) */
  initialSection?: string;
  /** Callback when a section is selected for discussion */
  onSectionSelect?: (sectionAnchorId: string) => void;
  /** Callback when view mode changes */
  onModeChange?: (mode: SplitViewMode) => void;
  /** Children to render in the discussion panel */
  discussionPanel?: React.ReactNode;
  /** Whether discussions are enabled */
  discussionsEnabled?: boolean;
  /** Discussion counts per section for heatmap */
  sectionDiscussionCounts?: SectionDiscussionCount[];
  /** Whether to show the heatmap margin */
  showHeatmap?: boolean;
  /** Action button to render in Discussion header */
  discussionHeaderAction?: React.ReactNode;
}

/**
 * Mode configuration for split view layouts
 */
const MODE_CONFIG: Record<SplitViewMode, { billWidth: string; discussionWidth: string; label: string }> = {
  'read': {
    billWidth: '100%',
    discussionWidth: '0%',
    label: 'Read',
  },
  'discuss-50': {
    billWidth: '50%',
    discussionWidth: '50%',
    label: '50/50',
  },
  'discuss-33': {
    billWidth: '33.333%',
    discussionWidth: '66.666%',
    label: '1/3 - 2/3',
  },
};

/**
 * Icon components for the mode toggle buttons
 */
const ReadIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M4 6h16M4 12h16M4 18h16" />
  </svg>
);

const SplitIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="3" width="8" height="18" rx="1" />
    <rect x="13" y="3" width="8" height="18" rx="1" />
  </svg>
);

const DiscussIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="3" width="6" height="18" rx="1" />
    <rect x="11" y="3" width="10" height="18" rx="1" />
  </svg>
);

/**
 * Mode toggle button component
 */
interface ModeButtonProps {
  mode: SplitViewMode;
  currentMode: SplitViewMode;
  onClick: (mode: SplitViewMode) => void;
  disabled?: boolean;
}

const ModeButton: React.FC<ModeButtonProps> = ({ mode, currentMode, onClick, disabled }) => {
  const isActive = mode === currentMode;
  const config = MODE_CONFIG[mode];

  const Icon = mode === 'read' ? ReadIcon : mode === 'discuss-50' ? SplitIcon : DiscussIcon;

  return (
    <button
      onClick={() => onClick(mode)}
      disabled={disabled}
      className={`
        flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md
        transition-colors duration-200
        ${isActive
          ? 'bg-accent-red/20 text-accent-red'
          : 'text-text-secondary hover:bg-bg-secondary'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
      title={config.label}
      aria-pressed={isActive}
    >
      <Icon />
      <span className="hidden sm:inline">{config.label}</span>
    </button>
  );
};

/**
 * Empty state for discussion panel when no section is selected
 */
const EmptyDiscussionState: React.FC<{ locale: string }> = ({ locale }) => (
  <div className="flex flex-col items-center justify-center h-full text-center p-6 text-text-tertiary">
    <svg
      className="w-16 h-16 mb-4 text-text-tertiary"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
    <h3 className="text-lg font-medium text-text-primary mb-2">
      {locale === 'fr' ? 'Aucune section sélectionnée' : 'No Section Selected'}
    </h3>
    <p className="text-sm text-text-secondary max-w-xs">
      {locale === 'fr'
        ? 'Cliquez sur le bouton de discussion d\'une section pour voir ou démarrer une discussion.'
        : 'Click on a section\'s discussion button to view or start a discussion.'}
    </p>
  </div>
);

/**
 * Resizable divider between panels
 */
interface DividerProps {
  onDragStart: () => void;
  onDrag: (deltaX: number) => void;
  onDragEnd: () => void;
}

const ResizableDivider: React.FC<DividerProps> = ({ onDragStart, onDrag, onDragEnd }) => {
  const dividerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const startX = useRef(0);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    isDragging.current = true;
    startX.current = e.clientX;
    onDragStart();
    e.preventDefault();
  }, [onDragStart]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const deltaX = e.clientX - startX.current;
      startX.current = e.clientX;
      onDrag(deltaX);
    };

    const handleMouseUp = () => {
      if (isDragging.current) {
        isDragging.current = false;
        onDragEnd();
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [onDrag, onDragEnd]);

  return (
    <div
      ref={dividerRef}
      onMouseDown={handleMouseDown}
      className="
        w-1 bg-border-subtle
        hover:bg-accent-red
        cursor-col-resize
        transition-colors duration-150
        flex-shrink-0
        relative
        group
      "
      role="separator"
      aria-orientation="vertical"
      aria-valuenow={50}
      tabIndex={0}
    >
      {/* Visual grip indicator */}
      <div className="
        absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
        w-1 h-8
        bg-text-tertiary
        group-hover:bg-accent-red
        rounded-full
        opacity-50 group-hover:opacity-100
        transition-all duration-150
      " />
    </div>
  );
};

/**
 * Activity level color mapping
 */
const ACTIVITY_COLORS: Record<ActivityLevel, string> = {
  none: 'bg-transparent',
  low: 'bg-text-tertiary/30',
  medium: 'bg-blue-500',
  hot: 'bg-orange-500',
};

/**
 * Heatmap margin column showing discussion activity per section
 */
interface HeatmapMarginProps {
  /** Discussion counts per section */
  sectionCounts: SectionDiscussionCount[];
  /** Currently selected section */
  selectedSection?: string;
  /** Callback when a section heatbar is clicked */
  onSectionClick?: (sectionId: string) => void;
  /** Current locale for tooltips */
  locale: string;
}

const HeatmapMargin: React.FC<HeatmapMarginProps> = ({
  sectionCounts,
  selectedSection,
  onSectionClick,
  locale,
}) => {
  // Get tooltip text
  const getTooltip = (sectionId: string, count: number) => {
    const section = sectionId.split(':').pop() || sectionId;
    if (count === 0) {
      return locale === 'fr'
        ? `Section ${section}: Aucun commentaire`
        : `Section ${section}: No comments`;
    }
    return locale === 'fr'
      ? `Section ${section}: ${count} commentaire${count > 1 ? 's' : ''}`
      : `Section ${section}: ${count} comment${count > 1 ? 's' : ''}`;
  };

  return (
    <div
      className="
        w-3 flex-shrink-0
        bg-bg-secondary
        border-l border-r border-border-subtle
        overflow-y-auto
        scrollbar-hide
      "
      aria-label={locale === 'fr' ? 'Indicateur d\'activité des discussions' : 'Discussion activity indicator'}
    >
      <div className="flex flex-col py-2 gap-1 min-h-full">
        {sectionCounts.map(({ sectionId, count }) => {
          const level = getActivityLevel(count);
          const isSelected = sectionId === selectedSection;

          return (
            <button
              key={sectionId}
              onClick={() => onSectionClick?.(sectionId)}
              className={`
                w-2 h-6 mx-auto rounded-full
                ${ACTIVITY_COLORS[level]}
                ${isSelected ? 'ring-2 ring-accent-red ring-offset-1 ring-offset-bg-secondary' : ''}
                ${count > 0 ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}
                transition-all duration-200
              `}
              title={getTooltip(sectionId, count)}
              aria-label={getTooltip(sectionId, count)}
            />
          );
        })}
      </div>
    </div>
  );
};

/**
 * BillSplitView - Layout component for bill text with optional discussion panel
 *
 * Provides three view modes:
 * - Read (100% bill text)
 * - Discuss 50/50 (equal split)
 * - Discuss 1/3-2/3 (more space for discussion)
 *
 * Features:
 * - Resizable divider between panels
 * - Section selection for focused discussions
 * - Responsive layout with mobile fallback
 * - Keyboard navigation support
 */
export const BillSplitView: React.FC<BillSplitViewProps> = ({
  billNumber,
  session,
  locale,
  initialMode = 'discuss-50',
  initialSection,
  onSectionSelect,
  onModeChange,
  discussionPanel,
  discussionsEnabled = true,
  sectionDiscussionCounts = [],
  showHeatmap = true,
  discussionHeaderAction,
}) => {
  const [mode, setMode] = useState<SplitViewMode>(initialMode);
  const [selectedSection, setSelectedSection] = useState<string | undefined>(initialSection);
  const [customBillWidth, setCustomBillWidth] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle mode change
  const handleModeChange = useCallback((newMode: SplitViewMode) => {
    setMode(newMode);
    setCustomBillWidth(null); // Reset custom width when mode changes
    onModeChange?.(newMode);
  }, [onModeChange]);

  // Handle section selection from bill viewer
  const handleSectionClick = useCallback((sectionAnchorId: string) => {
    setSelectedSection(sectionAnchorId);
    onSectionSelect?.(sectionAnchorId);

    // Auto-switch to discussion mode if in read mode
    if (mode === 'read' && discussionsEnabled) {
      handleModeChange('discuss-50');
    }
  }, [mode, discussionsEnabled, handleModeChange, onSectionSelect]);

  // Handle divider drag
  const handleDragStart = useCallback(() => {
    setIsDragging(true);
  }, []);

  const handleDrag = useCallback((deltaX: number) => {
    if (!containerRef.current) return;

    const containerWidth = containerRef.current.offsetWidth;
    const currentWidth = customBillWidth ??
      (mode === 'discuss-50' ? 50 : mode === 'discuss-33' ? 33.333 : 100);

    const deltaPercent = (deltaX / containerWidth) * 100;
    const newWidth = Math.max(20, Math.min(80, currentWidth + deltaPercent));

    setCustomBillWidth(newWidth);
  }, [mode, customBillWidth]);

  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Calculate panel widths
  const billWidth = mode === 'read'
    ? '100%'
    : customBillWidth !== null
      ? `${customBillWidth}%`
      : MODE_CONFIG[mode].billWidth;

  const discussionWidth = mode === 'read'
    ? '0%'
    : customBillWidth !== null
      ? `${100 - customBillWidth}%`
      : MODE_CONFIG[mode].discussionWidth;

  const showDiscussion = mode !== 'read';

  return (
    <div className="flex flex-col">
      {/* Toolbar - sticky below main header */}
      <div className="
        sticky top-16
        flex items-center justify-between
        px-4 py-2
        border-b border-border-subtle
        bg-bg-secondary
        flex-shrink-0
        z-30
      ">
        {/* Bill info */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-primary">
            {locale === 'fr' ? 'Projet de loi' : 'Bill'} {billNumber}
          </span>
          <span className="text-xs text-text-tertiary">
            ({session})
          </span>
        </div>

        {/* Mode toggles */}
        {discussionsEnabled && (
          <div className="flex items-center gap-1 bg-bg-elevated rounded-lg p-1">
            <ModeButton
              mode="read"
              currentMode={mode}
              onClick={handleModeChange}
            />
            <ModeButton
              mode="discuss-50"
              currentMode={mode}
              onClick={handleModeChange}
            />
            <ModeButton
              mode="discuss-33"
              currentMode={mode}
              onClick={handleModeChange}
            />
          </div>
        )}

        {/* Selected section indicator */}
        {selectedSection && showDiscussion && (
          <div className="hidden md:flex items-center gap-2">
            <span className="text-xs text-text-tertiary">
              {locale === 'fr' ? 'Section:' : 'Section:'}
            </span>
            <code className="text-xs bg-bg-elevated px-2 py-0.5 rounded text-text-primary">
              {selectedSection.split(':').pop()}
            </code>
            <button
              onClick={() => setSelectedSection(undefined)}
              className="text-text-tertiary hover:text-text-primary"
              title={locale === 'fr' ? 'Effacer la sélection' : 'Clear selection'}
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Column Headers Row - sticky (below main header + toolbar) */}
      <div className="sticky top-[119px] z-40 flex border-b border-border-subtle bg-bg-primary">
        {/* Note: 119px = 64px (header) + 55px (toolbar with py-2 padding, text content, and borders) */}
        {/* Bill Text Header */}
        <div
          className="px-4 py-4 border-r border-border-subtle flex items-center gap-2"
          style={{ width: billWidth }}
        >
          <svg className="h-5 w-5 text-accent-red" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          <h3 className="text-xl font-bold text-text-primary">Bill Text</h3>
        </div>

        {/* Discussion Header */}
        {showDiscussion && (
          <div
            className="px-4 py-3 flex items-center justify-between bg-white dark:bg-gray-800"
            style={{ width: discussionWidth }}
          >
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                {locale === 'fr' ? 'Discussion' : 'Discussion'}
              </h3>
            </div>
            {discussionHeaderAction && (
              <div>{discussionHeaderAction}</div>
            )}
          </div>
        )}
      </div>

      {/* Main content area */}
      <div
        ref={containerRef}
        className={`
          flex min-h-screen
          ${isDragging ? 'select-none cursor-col-resize' : ''}
        `}
      >
        {/* Bill text panel */}
        <div
          className="transition-all duration-300 ease-in-out"
          style={{ width: billWidth }}
        >
          <BillTextViewer
            billNumber={billNumber}
            session={session}
            locale={locale}
            onSectionDiscuss={discussionsEnabled ? handleSectionClick : undefined}
            highlightedSection={selectedSection}
          />
        </div>

        {/* Heatmap margin - always visible when there are discussion counts */}
        {showHeatmap && sectionDiscussionCounts.length > 0 && (
          <HeatmapMargin
            sectionCounts={sectionDiscussionCounts}
            selectedSection={selectedSection}
            onSectionClick={handleSectionClick}
            locale={locale}
          />
        )}

        {/* Resizable divider */}
        {showDiscussion && (
          <ResizableDivider
            onDragStart={handleDragStart}
            onDrag={handleDrag}
            onDragEnd={handleDragEnd}
          />
        )}

        {/* Discussion panel */}
        {showDiscussion && (
          <div
            className="bg-bg-primary transition-all duration-300 ease-in-out"
            style={{ width: discussionWidth }}
          >
            {discussionPanel ?? (
              selectedSection ? (
                <div className="p-4">
                  <div className="text-sm text-text-secondary mb-4">
                    {locale === 'fr'
                      ? `Discussion pour la section ${selectedSection.split(':').pop()}`
                      : `Discussion for section ${selectedSection.split(':').pop()}`}
                  </div>
                  {/* Placeholder - will be replaced by BillDiscussionPanel */}
                  <div className="bg-bg-secondary rounded-lg p-4 shadow-sm">
                    <p className="text-text-tertiary text-sm italic">
                      {locale === 'fr'
                        ? 'Le panneau de discussion sera implémenté prochainement...'
                        : 'Discussion panel will be implemented soon...'}
                    </p>
                  </div>
                </div>
              ) : (
                <EmptyDiscussionState locale={locale} />
              )
            )}
          </div>
        )}
      </div>

      {/* Mobile bottom sheet trigger (for mobile views) */}
      {discussionsEnabled && (
        <div className="md:hidden fixed bottom-4 right-4 z-50">
          <button
            onClick={() => handleModeChange(mode === 'read' ? 'discuss-50' : 'read')}
            className="
              flex items-center justify-center
              w-14 h-14 rounded-full
              bg-blue-600 hover:bg-blue-700
              text-white shadow-lg
              transition-colors duration-200
            "
            aria-label={locale === 'fr' ? 'Basculer la discussion' : 'Toggle discussion'}
          >
            {mode === 'read' ? (
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            ) : (
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default BillSplitView;
