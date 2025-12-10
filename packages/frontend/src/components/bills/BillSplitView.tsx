'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { BillTextViewer } from './BillTextViewer';

/**
 * View modes for the split view layout
 */
export type SplitViewMode = 'read' | 'discuss-50' | 'discuss-33';

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
          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
          : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
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
  <div className="flex flex-col items-center justify-center h-full text-center p-6 text-gray-500 dark:text-gray-400">
    <svg
      className="w-16 h-16 mb-4 text-gray-300 dark:text-gray-600"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
    <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
      {locale === 'fr' ? 'Aucune section sélectionnée' : 'No Section Selected'}
    </h3>
    <p className="text-sm max-w-xs">
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
        w-1 bg-gray-200 dark:bg-gray-700
        hover:bg-blue-400 dark:hover:bg-blue-600
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
        bg-gray-400 dark:bg-gray-500
        group-hover:bg-blue-500 dark:group-hover:bg-blue-400
        rounded-full
        opacity-50 group-hover:opacity-100
        transition-all duration-150
      " />
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
  initialMode = 'read',
  initialSection,
  onSectionSelect,
  onModeChange,
  discussionPanel,
  discussionsEnabled = true,
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
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="
        flex items-center justify-between
        px-4 py-2
        border-b border-gray-200 dark:border-gray-700
        bg-white dark:bg-gray-800
        flex-shrink-0
      ">
        {/* Bill info */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {locale === 'fr' ? 'Projet de loi' : 'Bill'} {billNumber}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            ({session})
          </span>
        </div>

        {/* Mode toggles */}
        {discussionsEnabled && (
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
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
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {locale === 'fr' ? 'Section:' : 'Section:'}
            </span>
            <code className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
              {selectedSection.split(':').pop()}
            </code>
            <button
              onClick={() => setSelectedSection(undefined)}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              title={locale === 'fr' ? 'Effacer la sélection' : 'Clear selection'}
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Main content area */}
      <div
        ref={containerRef}
        className={`
          flex flex-1 overflow-hidden
          ${isDragging ? 'select-none cursor-col-resize' : ''}
        `}
      >
        {/* Bill text panel */}
        <div
          className="overflow-auto transition-all duration-300 ease-in-out"
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
            className="overflow-auto bg-gray-50 dark:bg-gray-900 transition-all duration-300 ease-in-out"
            style={{ width: discussionWidth }}
          >
            {discussionPanel ?? (
              selectedSection ? (
                <div className="p-4">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    {locale === 'fr'
                      ? `Discussion pour la section ${selectedSection.split(':').pop()}`
                      : `Discussion for section ${selectedSection.split(':').pop()}`}
                  </div>
                  {/* Placeholder - will be replaced by BillDiscussionPanel */}
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
                    <p className="text-gray-400 dark:text-gray-500 text-sm italic">
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
