/**
 * MobileDebateViewer - Twitter/Instagram-Style Debate Reader
 * Vertical infinite scroll with swipe gestures and party filtering
 */

'use client';

import React, { useState, useRef } from 'react';
import { Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import { MobileStatementCard } from './MobileStatementCard';
import { SwipeableDrawer } from './SwipeableDrawer';
import { useMobileDetect } from '@/hooks/useMobileDetect';

interface MobileDebateViewerProps {
  statements: any[];
  locale?: string;
}

export function MobileDebateViewer({ statements, locale = 'en' }: MobileDebateViewerProps) {
  const { screenHeight } = useMobileDetect();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [partyFilter, setPartyFilter] = useState<string | null>(null);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'scroll' | 'focus'>('scroll');
  // Filter statements by party
  const filteredStatements = partyFilter
    ? statements.filter((s) => s.madeBy?.party === partyFilter)
    : statements;

  // Get unique parties
  const parties = Array.from(
    new Set(statements.map((s) => s.madeBy?.party).filter(Boolean))
  ) as string[];

  // Scroll to specific statement
  const scrollToIndex = (index: number) => {
    setCurrentIndex(index);
  };

  // Handle swipe navigation in focus mode
  const handleSwipeLeft = () => {
    if (viewMode === 'focus' && currentIndex < filteredStatements.length - 1) {
      scrollToIndex(currentIndex + 1);
    }
  };

  const handleSwipeRight = () => {
    if (viewMode === 'focus' && currentIndex > 0) {
      scrollToIndex(currentIndex - 1);
    }
  };

  // Party filter toggle
  const togglePartyFilter = (party: string) => {
    setPartyFilter(partyFilter === party ? null : party);
    setIsFilterOpen(false);
    setCurrentIndex(0);
  };

  // Timeline scrubber dots
  const getPartyColor = (party: string) => {
    const colors: Record<string, string> = {
      Liberal: '#DC2626',
      Conservative: '#2563EB',
      NDP: '#F59E0B',
      'Bloc Québécois': '#3B82F6',
      Green: '#10B981',
    };
    return colors[party] || '#666';
  };

  return (
    <div className="mobile-debate-viewer">
      {/* Top Controls */}
      <div className="mobile-debate-controls">
        <button
          onClick={() => setViewMode(viewMode === 'scroll' ? 'focus' : 'scroll')}
          className="mobile-debate-mode-toggle"
        >
          {viewMode === 'scroll' ? 'Focus Mode' : 'Scroll Mode'}
        </button>

        <button
          onClick={() => setIsFilterOpen(true)}
          className="mobile-debate-filter-button"
        >
          <Filter className="h-5 w-5" />
          {partyFilter && <span className="mobile-debate-filter-badge">{partyFilter}</span>}
        </button>
      </div>

      {/* Timeline Scrubber */}
      <div className="mobile-debate-timeline">
        {filteredStatements.slice(0, 50).map((statement, index) => (
          <button
            key={statement.id}
            onClick={() => scrollToIndex(index)}
            className="mobile-debate-timeline-dot"
            style={{
              background: statement.madeBy?.party
                ? getPartyColor(statement.madeBy.party)
                : '#666',
              opacity: index === currentIndex ? 1 : 0.4,
            }}
            aria-label={`Jump to statement ${index + 1}`}
          />
        ))}
      </div>

      {/* Statements List */}
      {viewMode === 'scroll' ? (
        <div className="mobile-debate-scroll-container">
          {filteredStatements.map((statement, index) => (
            <MobileStatementCard
              key={statement.id}
              statement={statement}
              locale={locale}
              showFullContent={false}
            />
          ))}
        </div>
      ) : (
        /* Focus Mode - One at a Time */
        <div className="mobile-debate-focus-container">
          {currentIndex > 0 && (
            <button
              onClick={() => scrollToIndex(currentIndex - 1)}
              className="mobile-debate-nav-button left"
              aria-label="Previous statement"
            >
              <ChevronLeft className="h-8 w-8" />
            </button>
          )}

          <div className="mobile-debate-focus-content">
            <MobileStatementCard
              statement={filteredStatements[currentIndex]}
              onSwipeLeft={handleSwipeLeft}
              onSwipeRight={handleSwipeRight}
              locale={locale}
              showFullContent={true}
            />

            <div className="mobile-debate-focus-counter">
              {currentIndex + 1} / {filteredStatements.length}
            </div>
          </div>

          {currentIndex < filteredStatements.length - 1 && (
            <button
              onClick={() => scrollToIndex(currentIndex + 1)}
              className="mobile-debate-nav-button right"
              aria-label="Next statement"
            >
              <ChevronRight className="h-8 w-8" />
            </button>
          )}
        </div>
      )}

      {/* Filter Drawer */}
      <SwipeableDrawer
        isOpen={isFilterOpen}
        onClose={() => setIsFilterOpen(false)}
        title="Filter by Party"
        height="auto"
      >
        <div className="mobile-debate-filter-options">
          <button
            onClick={() => togglePartyFilter('')}
            className={`mobile-debate-filter-option ${!partyFilter ? 'active' : ''}`}
          >
            All Parties
          </button>
          {parties.map((party) => (
            <button
              key={party}
              onClick={() => togglePartyFilter(party)}
              className={`mobile-debate-filter-option ${partyFilter === party ? 'active' : ''}`}
              style={{
                borderLeft: `4px solid ${getPartyColor(party)}`,
              }}
            >
              {party}
            </button>
          ))}
        </div>
      </SwipeableDrawer>
    </div>
  );
}
