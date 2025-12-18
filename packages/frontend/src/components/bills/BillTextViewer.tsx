/**
 * BillTextViewer - Displays structured bill text with navigation anchors
 *
 * Features:
 * - Hierarchical display of Parts, Sections, Subsections, Paragraphs
 * - Anchor IDs for deep linking (e.g., #s2.1.a)
 * - Collapsible sections
 * - Version selector for different readings
 * - Discussion button per section (Phase 1A)
 */

'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery } from '@apollo/client';
import { useLocale } from 'next-intl';
import { GET_BILL_STRUCTURE } from '@/lib/queries';
import { Loading } from '@/components/Loading';
import { TextHighlighter } from './TextHighlighter';
import { DiscussionHeatBar, DiscussionActivityIndicator } from './DiscussionActivityIndicator';
import {
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Link as LinkIcon,
  FileText,
  Download,
  History,
  GitBranch,
} from 'lucide-react';

// Type definitions for bill structure
interface BillSubparagraph {
  id: string;
  numeral: string;
  text_en: string;
  text_fr: string | null;
  anchor_id: string;
  sequence: number;
}

interface BillParagraph {
  id: string;
  letter: string;
  text_en: string;
  text_fr: string | null;
  anchor_id: string;
  sequence: number;
  subparagraphs: BillSubparagraph[];
}

interface BillSubsection {
  id: string;
  number: string;
  text_en: string;
  text_fr: string | null;
  anchor_id: string;
  sequence: number;
  paragraphs: BillParagraph[];
}

interface BillSection {
  id: string;
  number: string;
  marginal_note_en: string | null;
  marginal_note_fr: string | null;
  text_en: string;
  text_fr: string | null;
  anchor_id: string;
  sequence: number;
  subsections: BillSubsection[];
}

interface BillPart {
  id: string;
  number: number;
  title_en: string;
  title_fr: string | null;
  anchor_id: string;
  sequence: number;
  sections: BillSection[];
}

interface BillVersion {
  id: string;
  version_number: number;
  stage: string;
  publication_type_name: string | null;
  publication_date: string | null;
  has_amendments: boolean;
  xml_url: string | null;
  pdf_url: string | null;
}

interface BillAmendmentEvent {
  id: string;
  event_type: string;
  description_en: string;
  description_fr: string | null;
  event_date: string | null;
  chamber: string;
  stage: string;
  committee_code: string | null;
  committee_name: string | null;
  report_number: number | null;
  number_of_amendments: number | null;
}

interface BillStructure {
  number: string;
  session: string;
  title: string;
  versions: BillVersion[];
  amendmentEvents: BillAmendmentEvent[];
  parts: BillPart[];
  sections: BillSection[];
}

interface BillTextViewerProps {
  billNumber: string;
  session: string;
  locale?: string;
  /** Callback when section discuss button is clicked (alias for onSectionClick) */
  onSectionDiscuss?: (anchorId: string) => void;
  /** Deprecated: use onSectionDiscuss */
  onSectionClick?: (anchorId: string) => void;
  /** Currently highlighted section anchor (alias for highlightAnchor) */
  highlightedSection?: string;
  /** Deprecated: use highlightedSection */
  highlightAnchor?: string;
  showVersionSelector?: boolean;
  showAmendments?: boolean;
  /** Discussion counts per section anchor (from Supabase) */
  discussionCounts?: Record<string, number>;
  /** Whether to show the discussion heatmap on the left margin */
  showHeatmap?: boolean;
}

// Helper to convert anchor_id to URL hash
function anchorToHash(anchorId: string): string {
  // Convert "bill:45-1:c-234:s2.1.a" to "s2.1.a"
  const parts = anchorId.split(':');
  return parts[parts.length - 1];
}

// Section component with collapsible subsections
function SectionView({
  section,
  locale,
  onSectionClick,
  highlightAnchor,
  discussionCount = 0,
  showHeatmap = false,
  level = 0,
}: {
  section: BillSection;
  locale: string;
  onSectionClick?: (anchorId: string) => void;
  highlightAnchor?: string;
  discussionCount?: number;
  showHeatmap?: boolean;
  level?: number;
}) {
  const [expanded, setExpanded] = useState(true);
  const sectionRef = useRef<HTMLDivElement>(null);
  const hash = anchorToHash(section.anchor_id);
  const isHighlighted = highlightAnchor === hash;

  const text = locale === 'fr' && section.text_fr ? section.text_fr : section.text_en;
  const marginalNote = locale === 'fr' && section.marginal_note_fr
    ? section.marginal_note_fr
    : section.marginal_note_en;

  useEffect(() => {
    if (isHighlighted && sectionRef.current) {
      sectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [isHighlighted]);

  const handleCopyLink = useCallback(() => {
    const url = `${window.location.pathname}#${hash}`;
    navigator.clipboard.writeText(window.location.origin + url);
  }, [hash]);

  return (
    <div
      ref={sectionRef}
      id={hash}
      data-section-id={hash}
      className={`mb-4 rounded-lg transition-colors flex ${
        isHighlighted ? 'bg-accent-red/10 ring-2 ring-accent-red/30' : ''
      }`}
    >
      {/* Main section content */}
      <div className="flex-1">
        {/* Section header */}
        <div
          className="flex items-start gap-3 p-3 hover:bg-bg-elevated/50 rounded-lg cursor-pointer group"
          onClick={() => setExpanded(!expanded)}
        >
          <button className="mt-1 text-text-tertiary hover:text-accent-red">
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>

          <div className="flex-1">
            {marginalNote ? (
              // With title: show number and title on same line, text below
              <>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-accent-red">
                    {section.number}.
                  </span>
                  <span className="text-sm font-semibold text-text-primary">
                    {marginalNote}
                  </span>
                </div>
                {text && expanded && (
                  <>
                    <p className="mt-2 text-text-secondary leading-relaxed">
                      {text}
                    </p>
                    {/* Show note if section ends with ':' but has no subsections */}
                    {text.trim().endsWith(':') && section.subsections.length === 0 && (
                      <p className="mt-2 text-xs italic text-text-tertiary">
                        (Content not yet available - see full bill text)
                      </p>
                    )}
                  </>
                )}
              </>
            ) : text ? (
              // No title but has text: show number and text inline
              <div className="flex items-start gap-2">
                <span className="font-mono font-bold text-accent-red flex-shrink-0">
                  {section.number}.
                </span>
                {expanded && (
                  <div className="flex-1">
                    <p className="text-text-secondary leading-relaxed">
                      {text}
                    </p>
                    {/* Show note if section ends with ':' but has no subsections */}
                    {text.trim().endsWith(':') && section.subsections.length === 0 && (
                      <p className="mt-2 text-xs italic text-text-tertiary">
                        (Content not yet available - see full bill text)
                      </p>
                    )}
                  </div>
                )}
              </div>
            ) : (
              // No title and no text (only subsections): just show the number
              <span className="font-mono font-bold text-accent-red">
                {section.number}.
              </span>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCopyLink();
              }}
              className="p-1 text-text-tertiary hover:text-accent-red"
              title="Copy link"
            >
              <LinkIcon className="h-4 w-4" />
            </button>
            {onSectionClick && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSectionClick(section.anchor_id);
                }}
                className="p-1 text-text-tertiary hover:text-accent-red"
                title="Discuss section"
              >
                <MessageSquare className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {/* Subsections */}
        {expanded && section.subsections.length > 0 && (
          <div className="ml-8 border-l-2 border-border-subtle pl-4">
            {section.subsections.map((subsection) => (
              <SubsectionView
                key={subsection.id}
                subsection={subsection}
                locale={locale}
                onSectionClick={onSectionClick}
                highlightAnchor={highlightAnchor}
              />
            ))}
          </div>
        )}
      </div>

      {/* Right-side heatmap indicator */}
      {showHeatmap && (
        <div className="flex-shrink-0 w-6 flex justify-center py-3">
          <DiscussionActivityIndicator
            commentCount={discussionCount}
            showBadge={true}
            showBar={false}
            onClick={onSectionClick ? () => onSectionClick(section.anchor_id) : undefined}
            locale={locale}
            size="sm"
          />
        </div>
      )}
    </div>
  );
}

function SubsectionView({
  subsection,
  locale,
  onSectionClick,
  highlightAnchor,
}: {
  subsection: BillSubsection;
  locale: string;
  onSectionClick?: (anchorId: string) => void;
  highlightAnchor?: string;
}) {
  const hash = anchorToHash(subsection.anchor_id);
  const isHighlighted = highlightAnchor === hash;
  const text = locale === 'fr' && subsection.text_fr ? subsection.text_fr : subsection.text_en;

  const handleCopyLink = useCallback(() => {
    const url = `${window.location.pathname}#${hash}`;
    navigator.clipboard.writeText(window.location.origin + url);
  }, [hash]);

  return (
    <div
      id={hash}
      data-section-id={hash}
      className={`mb-3 p-2 rounded group hover:bg-bg-elevated/30 ${
        isHighlighted ? 'bg-accent-red/10 ring-1 ring-accent-red/30' : ''
      }`}
    >
      <div className="flex items-start gap-2">
        <span className="font-mono text-sm text-text-tertiary">
          ({subsection.number})
        </span>
        <div className="flex-1">
          {text && (
            <p className="text-sm text-text-secondary leading-relaxed">{text}</p>
          )}

          {/* Paragraphs */}
          {subsection.paragraphs.length > 0 && (
            <div className="mt-2 ml-4">
              {subsection.paragraphs.map((para) => (
                <ParagraphView
                  key={para.id}
                  paragraph={para}
                  locale={locale}
                  onSectionClick={onSectionClick}
                  highlightAnchor={highlightAnchor}
                />
              ))}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
          <button
            onClick={handleCopyLink}
            className="p-1 text-text-tertiary hover:text-accent-red"
            title="Copy link"
          >
            <LinkIcon className="h-3.5 w-3.5" />
          </button>
          {onSectionClick && (
            <button
              onClick={() => onSectionClick(subsection.anchor_id)}
              className="p-1 text-text-tertiary hover:text-accent-red"
              title="Discuss subsection"
            >
              <MessageSquare className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ParagraphView({
  paragraph,
  locale,
  onSectionClick,
  highlightAnchor,
}: {
  paragraph: BillParagraph;
  locale: string;
  onSectionClick?: (anchorId: string) => void;
  highlightAnchor?: string;
}) {
  const hash = anchorToHash(paragraph.anchor_id);
  const isHighlighted = highlightAnchor === hash;
  const text = locale === 'fr' && paragraph.text_fr ? paragraph.text_fr : paragraph.text_en;

  const handleCopyLink = useCallback(() => {
    const url = `${window.location.pathname}#${hash}`;
    navigator.clipboard.writeText(window.location.origin + url);
  }, [hash]);

  return (
    <div
      id={hash}
      data-section-id={hash}
      className={`mb-2 flex items-start gap-2 group hover:bg-bg-elevated/20 rounded px-1 py-0.5 ${
        isHighlighted ? 'bg-accent-red/10 px-2 py-1' : ''
      }`}
    >
      <span className="font-mono text-xs text-text-tertiary">
        ({paragraph.letter})
      </span>
      <div className="flex-1">
        {text && (
          <p className="text-sm text-text-secondary">{text}</p>
        )}

        {/* Subparagraphs */}
        {paragraph.subparagraphs.length > 0 && (
          <div className="mt-1 ml-4">
            {paragraph.subparagraphs.map((subpara) => (
              <SubparagraphView
                key={subpara.id}
                subparagraph={subpara}
                locale={locale}
                onSectionClick={onSectionClick}
                highlightAnchor={highlightAnchor}
              />
            ))}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
        <button
          onClick={handleCopyLink}
          className="p-0.5 text-text-tertiary hover:text-accent-red"
          title="Copy link"
        >
          <LinkIcon className="h-3 w-3" />
        </button>
        {onSectionClick && (
          <button
            onClick={() => onSectionClick(paragraph.anchor_id)}
            className="p-0.5 text-text-tertiary hover:text-accent-red"
            title="Discuss paragraph"
          >
            <MessageSquare className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}

function SubparagraphView({
  subparagraph,
  locale,
  onSectionClick,
  highlightAnchor,
}: {
  subparagraph: BillSubparagraph;
  locale: string;
  onSectionClick?: (anchorId: string) => void;
  highlightAnchor?: string;
}) {
  const hash = anchorToHash(subparagraph.anchor_id);
  const isHighlighted = highlightAnchor === hash;
  const text = locale === 'fr' && subparagraph.text_fr
    ? subparagraph.text_fr
    : subparagraph.text_en;

  const handleCopyLink = useCallback(() => {
    const url = `${window.location.pathname}#${hash}`;
    navigator.clipboard.writeText(window.location.origin + url);
  }, [hash]);

  return (
    <div
      id={hash}
      data-section-id={hash}
      className={`mb-1 flex items-start gap-2 group hover:bg-bg-elevated/20 rounded px-1 py-0.5 ${
        isHighlighted ? 'bg-accent-red/10 px-2 py-0.5' : ''
      }`}
    >
      <span className="font-mono text-xs text-text-tertiary">
        ({subparagraph.numeral})
      </span>
      <p className="text-sm text-text-secondary flex-1">{text}</p>

      {/* Action buttons */}
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
        <button
          onClick={handleCopyLink}
          className="p-0.5 text-text-tertiary hover:text-accent-red"
          title="Copy link"
        >
          <LinkIcon className="h-3 w-3" />
        </button>
        {onSectionClick && (
          <button
            onClick={() => onSectionClick(subparagraph.anchor_id)}
            className="p-0.5 text-text-tertiary hover:text-accent-red"
            title="Discuss subparagraph"
          >
            <MessageSquare className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}

// Part component with collapsible sections
function PartView({
  part,
  locale,
  onSectionClick,
  highlightAnchor,
}: {
  part: BillPart;
  locale: string;
  onSectionClick?: (anchorId: string) => void;
  highlightAnchor?: string;
}) {
  const [expanded, setExpanded] = useState(true);
  const hash = anchorToHash(part.anchor_id);
  const title = locale === 'fr' && part.title_fr ? part.title_fr : part.title_en;

  return (
    <div id={hash} className="mb-6">
      {/* Part header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 p-4 bg-bg-elevated hover:bg-bg-elevated/80 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-5 w-5 text-accent-red" />
        ) : (
          <ChevronRight className="h-5 w-5 text-accent-red" />
        )}
        <span className="font-bold text-lg text-text-primary">
          Part {part.number}
        </span>
        {title && (
          <span className="text-text-secondary">— {title}</span>
        )}
      </button>

      {/* Sections in this part */}
      {expanded && part.sections.length > 0 && (
        <div className="mt-4 ml-4">
          {part.sections.map((section) => (
            <SectionView
              key={section.id}
              section={section}
              locale={locale}
              onSectionClick={onSectionClick}
              highlightAnchor={highlightAnchor}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Version selector dropdown
function VersionSelector({
  versions,
  selectedVersion,
  onSelect,
}: {
  versions: BillVersion[];
  selectedVersion: number;
  onSelect: (version: number) => void;
}) {
  const [open, setOpen] = useState(false);

  const currentVersion = versions.find((v) => v.version_number === selectedVersion);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-2 bg-bg-elevated rounded-lg hover:bg-bg-elevated/80 transition-colors"
      >
        <History className="h-4 w-4 text-accent-red" />
        <span className="text-sm text-text-primary">
          {currentVersion?.publication_type_name || `Version ${selectedVersion}`}
        </span>
        <ChevronDown className={`h-4 w-4 text-text-tertiary transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-bg-elevated rounded-lg shadow-lg border border-border-subtle z-50">
          {versions.map((version) => (
            <button
              key={version.id}
              onClick={() => {
                onSelect(version.version_number);
                setOpen(false);
              }}
              className={`w-full flex items-start gap-3 px-4 py-3 hover:bg-bg-overlay transition-colors text-left ${
                version.version_number === selectedVersion ? 'bg-accent-red/10' : ''
              }`}
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-text-primary">
                    {version.publication_type_name || `Version ${version.version_number}`}
                  </span>
                  {version.has_amendments && (
                    <span title="Has amendments">
                      <GitBranch className="h-3 w-3 text-accent-red" />
                    </span>
                  )}
                </div>
                <div className="text-xs text-text-tertiary mt-0.5">
                  {version.stage && <span className="capitalize">{version.stage.replace('-', ' ')}</span>}
                  {version.publication_date && (
                    <span className="ml-2">
                      {new Date(version.publication_date).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              {version.pdf_url && (
                <a
                  href={version.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="p-1 text-text-tertiary hover:text-accent-red"
                  title="Download PDF"
                >
                  <Download className="h-4 w-4" />
                </a>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Amendment events timeline
function AmendmentTimeline({ events }: { events: BillAmendmentEvent[] }) {
  if (events.length === 0) return null;

  return (
    <div className="mb-6 p-4 bg-bg-elevated rounded-lg">
      <h4 className="flex items-center gap-2 font-semibold text-text-primary mb-3">
        <GitBranch className="h-4 w-4 text-accent-red" />
        Amendments
      </h4>
      <div className="space-y-2">
        {events.map((event) => (
          <div key={event.id} className="flex items-start gap-3 text-sm">
            <div className="w-24 flex-shrink-0 text-text-tertiary">
              {event.event_date
                ? new Date(event.event_date).toLocaleDateString()
                : event.stage}
            </div>
            <div className="flex-1">
              <div className="text-text-primary">{event.description_en}</div>
              {event.committee_name && (
                <div className="text-xs text-text-tertiary mt-0.5">
                  {event.committee_name}
                  {event.number_of_amendments && ` (${event.number_of_amendments} amendments)`}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Main BillTextViewer component
export function BillTextViewer({
  billNumber,
  session,
  locale: localeProp,
  onSectionDiscuss,
  onSectionClick,
  highlightedSection,
  highlightAnchor,
  showVersionSelector = true,
  showAmendments = true,
}: BillTextViewerProps) {
  const localeFromHook = useLocale();
  // Use prop locale if provided, otherwise use hook
  const locale = localeProp || localeFromHook;
  // Support both prop names (new ones take precedence)
  const sectionClickHandler = onSectionDiscuss || onSectionClick;
  const highlightValue = highlightedSection || highlightAnchor;
  const [selectedVersion, setSelectedVersion] = useState(1);

  // Container ref for text selection/highlighting
  const containerRef = useRef<HTMLDivElement>(null);

  const { data, loading, error } = useQuery(GET_BILL_STRUCTURE, {
    variables: { number: billNumber, session },
  });

  // Handle text selection for discuss action - must be before any early returns
  const handleTextDiscuss = useCallback((selection: { sectionAnchorId: string }) => {
    if (sectionClickHandler) {
      sectionClickHandler(selection.sectionAnchorId);
    }
  }, [sectionClickHandler]);

  // Handle URL hash for deep linking
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const hash = window.location.hash.slice(1);
      if (hash) {
        const element = document.getElementById(hash);
        if (element) {
          setTimeout(() => {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }, 100);
        }
      }
    }
  }, [data]);

  if (loading) {
    return <Loading />;
  }

  if (error) {
    return (
      <div className="p-4 text-accent-red">
        Error loading bill structure: {error.message}
      </div>
    );
  }

  const bill: BillStructure | null = data?.bills?.[0];

  if (!bill) {
    return (
      <div className="p-6 text-center text-text-secondary">
        <FileText className="h-12 w-12 mx-auto mb-4 text-text-tertiary" />
        <p className="text-lg font-semibold text-text-primary mb-2">
          Bill text not yet available
        </p>
        <p className="text-sm">
          The structured text for this bill has not been imported yet.
          Check back later or view the official PDF on Parliament.ca.
        </p>
      </div>
    );
  }

  const hasParts = bill.parts && bill.parts.length > 0;
  const hasLooseSections = bill.sections && bill.sections.length > 0;
  const hasStructure = hasParts || hasLooseSections;

  if (!hasStructure) {
    return (
      <div className="p-6 text-center text-text-secondary">
        <FileText className="h-12 w-12 mx-auto mb-4 text-text-tertiary" />
        <p className="text-lg font-semibold text-text-primary mb-2">
          No structured content
        </p>
        <p className="text-sm">
          This bill does not have structured text sections available.
        </p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="bill-text-viewer relative">
      {/* Text selection highlighter for sharing */}
      <TextHighlighter
        containerRef={containerRef as React.RefObject<HTMLElement>}
        locale={locale}
        billNumber={billNumber}
        session={session}
        onDiscuss={handleTextDiscuss}
        discussionsEnabled={!!sectionClickHandler}
      />

      {/* Version selector moved to sticky header in BillSplitView */}

      {/* Amendment events */}
      {showAmendments && bill.amendmentEvents && (
        <AmendmentTimeline events={bill.amendmentEvents} />
      )}

      {/* Parts */}
      {hasParts && (
        <div className="mb-6">
          {bill.parts.map((part) => (
            <PartView
              key={part.id}
              part={part}
              locale={locale}
              onSectionClick={sectionClickHandler}
              highlightAnchor={highlightValue}
            />
          ))}
        </div>
      )}

      {/* Loose sections (not in any part) */}
      {hasLooseSections && (
        <div className="space-y-2">
          {bill.sections.map((section) => (
            <SectionView
              key={section.id}
              section={section}
              locale={locale}
              onSectionClick={sectionClickHandler}
              highlightAnchor={highlightValue}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default BillTextViewer;
