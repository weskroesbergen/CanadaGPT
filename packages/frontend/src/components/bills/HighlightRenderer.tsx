'use client';

import React, { useEffect, useCallback } from 'react';
import type { HighlightParams } from '@/lib/highlights/highlightUrl';

interface HighlightRendererProps {
  /** Container ref to apply highlights to */
  containerRef: React.RefObject<HTMLElement>;
  /** Highlight params from URL */
  highlight: HighlightParams | null;
  /** Callback after highlight is applied */
  onHighlightApplied?: () => void;
  /** Callback if highlight fails to apply */
  onHighlightFailed?: (reason: string) => void;
  /** Custom highlight class */
  highlightClass?: string;
}

/**
 * Default highlight styles
 */
const DEFAULT_HIGHLIGHT_CLASS = `
  bg-yellow-200 dark:bg-yellow-800/50
  border-b-2 border-yellow-400 dark:border-yellow-600
  rounded-sm px-0.5
  transition-colors duration-300
`;

/**
 * Find section element by ID
 */
function findSectionElement(
  container: HTMLElement,
  sectionId: string
): HTMLElement | null {
  // Try data-section-id attribute first
  let element = container.querySelector<HTMLElement>(
    `[data-section-id="${sectionId}"]`
  );

  // Fallback to id attribute
  if (!element) {
    element = container.querySelector<HTMLElement>(`#${CSS.escape(sectionId)}`);
  }

  return element;
}

/**
 * Get text content and create a mapping of text positions to DOM nodes
 */
interface TextNodeMapping {
  node: Text;
  start: number;
  end: number;
}

function getTextNodeMappings(element: HTMLElement): TextNodeMapping[] {
  const mappings: TextNodeMapping[] = [];
  const walker = document.createTreeWalker(
    element,
    NodeFilter.SHOW_TEXT,
    null
  );

  let offset = 0;
  let node: Node | null;

  while ((node = walker.nextNode())) {
    const textNode = node as Text;
    const length = textNode.textContent?.length || 0;

    if (length > 0) {
      mappings.push({
        node: textNode,
        start: offset,
        end: offset + length,
      });
      offset += length;
    }
  }

  return mappings;
}

/**
 * Apply highlight to text range using Range API
 */
function applyHighlight(
  mappings: TextNodeMapping[],
  startOffset: number,
  endOffset: number,
  highlightClass: string
): HTMLElement | null {
  // Find start and end nodes
  let startNode: Text | null = null;
  let startNodeOffset = 0;
  let endNode: Text | null = null;
  let endNodeOffset = 0;

  for (const mapping of mappings) {
    if (!startNode && startOffset >= mapping.start && startOffset < mapping.end) {
      startNode = mapping.node;
      startNodeOffset = startOffset - mapping.start;
    }

    if (endOffset > mapping.start && endOffset <= mapping.end) {
      endNode = mapping.node;
      endNodeOffset = endOffset - mapping.start;
    }
  }

  if (!startNode || !endNode) {
    return null;
  }

  try {
    // Create a range
    const range = document.createRange();
    range.setStart(startNode, startNodeOffset);
    range.setEnd(endNode, endNodeOffset);

    // Create highlight wrapper
    const highlightSpan = document.createElement('mark');
    highlightSpan.className = highlightClass;
    highlightSpan.setAttribute('data-highlight', 'true');

    // Wrap the range contents
    range.surroundContents(highlightSpan);

    return highlightSpan;
  } catch (err) {
    // surroundContents fails if range crosses element boundaries
    // In that case, we need a more complex approach
    console.warn('Could not apply highlight with surroundContents:', err);

    // Try highlighting each text node individually
    return applyHighlightAcrossNodes(
      mappings,
      startOffset,
      endOffset,
      highlightClass
    );
  }
}

/**
 * Apply highlight across multiple text nodes (handles cross-element selections)
 */
function applyHighlightAcrossNodes(
  mappings: TextNodeMapping[],
  startOffset: number,
  endOffset: number,
  highlightClass: string
): HTMLElement | null {
  let firstHighlight: HTMLElement | null = null;

  for (const mapping of mappings) {
    // Skip nodes outside the range
    if (mapping.end <= startOffset || mapping.start >= endOffset) {
      continue;
    }

    // Calculate the portion of this node to highlight
    const highlightStart = Math.max(0, startOffset - mapping.start);
    const highlightEnd = Math.min(
      mapping.node.textContent?.length || 0,
      endOffset - mapping.start
    );

    if (highlightEnd <= highlightStart) continue;

    try {
      const range = document.createRange();
      range.setStart(mapping.node, highlightStart);
      range.setEnd(mapping.node, highlightEnd);

      const highlightSpan = document.createElement('mark');
      highlightSpan.className = highlightClass;
      highlightSpan.setAttribute('data-highlight', 'true');

      range.surroundContents(highlightSpan);

      if (!firstHighlight) {
        firstHighlight = highlightSpan;
      }
    } catch (err) {
      console.warn('Could not highlight text node:', err);
    }
  }

  return firstHighlight;
}

/**
 * Remove existing highlights from container
 */
function clearHighlights(container: HTMLElement): void {
  const highlights = container.querySelectorAll('[data-highlight="true"]');

  highlights.forEach((highlight) => {
    const parent = highlight.parentNode;
    if (parent) {
      while (highlight.firstChild) {
        parent.insertBefore(highlight.firstChild, highlight);
      }
      parent.removeChild(highlight);
    }
  });

  // Normalize text nodes (merge adjacent ones)
  container.normalize();
}

/**
 * HighlightRenderer - Applies URL-based highlights to bill text
 *
 * Features:
 * - Reads highlight params from URL
 * - Applies visual highlighting to specified text range
 * - Scrolls highlighted text into view
 * - Cleans up existing highlights before applying new ones
 * - Handles cross-element selections
 */
export const HighlightRenderer: React.FC<HighlightRendererProps> = ({
  containerRef,
  highlight,
  onHighlightApplied,
  onHighlightFailed,
  highlightClass = DEFAULT_HIGHLIGHT_CLASS,
}) => {
  const applyHighlightFromParams = useCallback(() => {
    if (!highlight || !containerRef.current) {
      return;
    }

    const container = containerRef.current;

    // Clear any existing highlights first
    clearHighlights(container);

    // Find the section element
    const sectionElement = findSectionElement(container, highlight.section);
    if (!sectionElement) {
      onHighlightFailed?.(`Section "${highlight.section}" not found`);
      return;
    }

    // Get text node mappings for the section
    const mappings = getTextNodeMappings(sectionElement);
    const totalLength = mappings.reduce(
      (sum, m) => sum + (m.end - m.start),
      0
    );

    // Validate highlight range
    if (highlight.start < 0 || highlight.end > totalLength) {
      onHighlightFailed?.(
        `Invalid highlight range: ${highlight.start}-${highlight.end} (section length: ${totalLength})`
      );
      return;
    }

    // Apply the highlight
    const highlightElement = applyHighlight(
      mappings,
      highlight.start,
      highlight.end,
      highlightClass.trim()
    );

    if (highlightElement) {
      // Scroll highlight into view with some padding
      setTimeout(() => {
        highlightElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }, 100);

      onHighlightApplied?.();
    } else {
      onHighlightFailed?.('Failed to apply highlight');
    }
  }, [highlight, containerRef, highlightClass, onHighlightApplied, onHighlightFailed]);

  // Apply highlight when params change or container is ready
  useEffect(() => {
    if (!highlight) return;

    // Wait for container to be populated
    const observer = new MutationObserver(() => {
      if (containerRef.current?.querySelector(`#${CSS.escape(highlight.section)}`)) {
        observer.disconnect();
        applyHighlightFromParams();
      }
    });

    if (containerRef.current) {
      // Try applying immediately
      const sectionElement = findSectionElement(containerRef.current, highlight.section);
      if (sectionElement) {
        applyHighlightFromParams();
      } else {
        // Watch for changes
        observer.observe(containerRef.current, {
          childList: true,
          subtree: true,
        });
      }
    }

    return () => {
      observer.disconnect();
    };
  }, [highlight, containerRef, applyHighlightFromParams]);

  // Cleanup highlights when component unmounts or highlight changes
  useEffect(() => {
    return () => {
      if (containerRef.current) {
        clearHighlights(containerRef.current);
      }
    };
  }, [containerRef, highlight]);

  // This component doesn't render anything visible
  return null;
};

export default HighlightRenderer;
