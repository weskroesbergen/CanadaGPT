'use client';

import React, {
  useState,
  useCallback,
  useEffect,
  useRef,
} from 'react';
import {
  Link as LinkIcon,
  MessageSquare,
  Twitter,
  Share2,
  Check,
  X,
} from 'lucide-react';

/**
 * Text selection data
 */
export interface TextSelection {
  /** Selected text content */
  text: string;
  /** Section anchor ID containing the selection */
  sectionAnchorId: string;
  /** Character offset from start of section */
  startOffset: number;
  /** Character offset to end of selection */
  endOffset: number;
  /** Selection range coordinates for positioning popup */
  rect: DOMRect;
}

/**
 * Highlight data for URL encoding
 */
export interface HighlightData {
  /** Section reference (e.g., "s2.1.a") */
  section: string;
  /** Start character offset */
  start: number;
  /** End character offset */
  end: number;
}

interface TextHighlighterProps {
  /** Container ref to monitor for text selection */
  containerRef: React.RefObject<HTMLElement>;
  /** Current locale */
  locale: string;
  /** Bill number for sharing context */
  billNumber: string;
  /** Session for sharing context */
  session: string;
  /** Callback when "Discuss" is clicked */
  onDiscuss?: (selection: TextSelection) => void;
  /** Callback when a link is copied */
  onCopyLink?: (url: string) => void;
  /** Whether discussions are enabled */
  discussionsEnabled?: boolean;
}

/**
 * Share menu popup component
 */
const ShareMenu: React.FC<{
  selection: TextSelection;
  position: { top: number; left: number };
  locale: string;
  onCopyLink: () => void;
  onDiscuss?: () => void;
  onTwitterShare: () => void;
  onClose: () => void;
  linkCopied: boolean;
  discussionsEnabled: boolean;
}> = ({
  selection,
  position,
  locale,
  onCopyLink,
  onDiscuss,
  onTwitterShare,
  onClose,
  linkCopied,
  discussionsEnabled,
}) => {
  // Truncate text for display
  const displayText =
    selection.text.length > 100
      ? selection.text.slice(0, 100) + '...'
      : selection.text;

  return (
    <div
      className="
        fixed z-50
        bg-bg-elevated
        border border-border-subtle
        rounded-lg shadow-lg
        overflow-hidden
        animate-in fade-in slide-in-from-bottom-2 duration-200
      "
      style={{
        top: position.top,
        left: position.left,
        transform: 'translateX(-50%)',
      }}
    >
      {/* Selected text preview */}
      <div className="px-3 py-2 bg-bg-overlay border-b border-border-subtle">
        <p className="text-xs text-text-tertiary italic line-clamp-2 max-w-xs">
          "{displayText}"
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex items-center">
        {/* Copy Link */}
        <button
          onClick={onCopyLink}
          className="
            flex items-center gap-2 px-4 py-3
            text-sm text-text-secondary
            hover:bg-bg-secondary
            transition-colors
            border-r border-border-subtle
          "
          title={locale === 'fr' ? 'Copier le lien' : 'Copy link'}
        >
          {linkCopied ? (
            <>
              <Check className="h-4 w-4 text-green-500" />
              <span className="text-green-400">
                {locale === 'fr' ? 'Copié!' : 'Copied!'}
              </span>
            </>
          ) : (
            <>
              <LinkIcon className="h-4 w-4" />
              <span>{locale === 'fr' ? 'Lien' : 'Link'}</span>
            </>
          )}
        </button>

        {/* Discuss */}
        {discussionsEnabled && onDiscuss && (
          <button
            onClick={onDiscuss}
            className="
              flex items-center gap-2 px-4 py-3
              text-sm text-text-secondary
              hover:bg-bg-secondary
              transition-colors
              border-r border-border-subtle
            "
            title={locale === 'fr' ? 'Discuter' : 'Discuss'}
          >
            <MessageSquare className="h-4 w-4" />
            <span>{locale === 'fr' ? 'Discuter' : 'Discuss'}</span>
          </button>
        )}

        {/* Twitter */}
        <button
          onClick={onTwitterShare}
          className="
            flex items-center gap-2 px-4 py-3
            text-sm text-text-secondary
            hover:bg-bg-secondary
            transition-colors
            border-r border-border-subtle
          "
          title={locale === 'fr' ? 'Partager sur X' : 'Share on X'}
        >
          <Twitter className="h-4 w-4" />
          <span className="hidden sm:inline">X</span>
        </button>

        {/* Close */}
        <button
          onClick={onClose}
          className="
            p-3
            text-text-tertiary
            hover:bg-bg-secondary
            hover:text-text-primary
            transition-colors
          "
          title={locale === 'fr' ? 'Fermer' : 'Close'}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

/**
 * Find the section element containing a node
 */
function findSectionAncestor(node: Node): HTMLElement | null {
  let current: Node | null = node;

  while (current) {
    if (current instanceof HTMLElement) {
      // Look for data-section-id attribute
      const sectionId = current.getAttribute('data-section-id');
      if (sectionId) {
        return current;
      }

      // Also check id attribute for section anchors
      const id = current.getAttribute('id');
      if (id && (id.startsWith('s') || id.startsWith('part-'))) {
        return current;
      }
    }
    current = current.parentNode;
  }

  return null;
}

/**
 * Calculate character offset within section element
 */
function getCharacterOffset(
  sectionElement: HTMLElement,
  targetNode: Node,
  targetOffset: number
): number {
  const walker = document.createTreeWalker(
    sectionElement,
    NodeFilter.SHOW_TEXT,
    null
  );

  let offset = 0;
  let node: Node | null;

  while ((node = walker.nextNode())) {
    if (node === targetNode) {
      return offset + targetOffset;
    }
    offset += node.textContent?.length || 0;
  }

  return offset;
}

/**
 * TextHighlighter - Substack-style text selection and sharing
 *
 * Features:
 * - Detects text selection within bill sections
 * - Shows share menu with options: Copy link, Discuss, Share to Twitter
 * - Generates URLs with highlight parameters
 * - Supports keyboard shortcuts
 */
export const TextHighlighter: React.FC<TextHighlighterProps> = ({
  containerRef,
  locale,
  billNumber,
  session,
  onDiscuss,
  onCopyLink,
  discussionsEnabled = true,
}) => {
  const [selection, setSelection] = useState<TextSelection | null>(null);
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number } | null>(null);
  const [linkCopied, setLinkCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  /**
   * Handle text selection change
   */
  const handleSelectionChange = useCallback(() => {
    const sel = window.getSelection();

    // Check if we have a valid selection
    if (
      !sel ||
      sel.isCollapsed ||
      !sel.rangeCount ||
      !containerRef.current
    ) {
      return;
    }

    const range = sel.getRangeAt(0);
    const selectedText = sel.toString().trim();

    // Ignore very short selections
    if (selectedText.length < 3) {
      return;
    }

    // Check if selection is within our container
    if (!containerRef.current.contains(range.commonAncestorContainer)) {
      return;
    }

    // Find the section containing the selection
    const sectionElement = findSectionAncestor(range.commonAncestorContainer);
    if (!sectionElement) {
      return;
    }

    // Get section anchor ID
    const sectionAnchorId =
      sectionElement.getAttribute('data-section-id') ||
      sectionElement.getAttribute('id') ||
      '';

    // Calculate character offsets
    const startOffset = getCharacterOffset(
      sectionElement,
      range.startContainer,
      range.startOffset
    );
    const endOffset = getCharacterOffset(
      sectionElement,
      range.endContainer,
      range.endOffset
    );

    // Get selection bounding rect for positioning
    const rect = range.getBoundingClientRect();

    setSelection({
      text: selectedText,
      sectionAnchorId,
      startOffset,
      endOffset,
      rect,
    });

    // Position menu above selection
    setMenuPosition({
      top: rect.top + window.scrollY - 10,
      left: rect.left + rect.width / 2 + window.scrollX,
    });

    setLinkCopied(false);
  }, [containerRef]);

  /**
   * Generate highlight URL
   */
  const generateHighlightUrl = useCallback((): string => {
    if (!selection) return window.location.href;

    const baseUrl = `${window.location.origin}/${locale}/bills/${session}/${billNumber.toLowerCase()}`;
    const highlightParam = `${selection.sectionAnchorId}:${selection.startOffset}-${selection.endOffset}`;

    return `${baseUrl}?hl=${encodeURIComponent(highlightParam)}`;
  }, [selection, locale, session, billNumber]);

  /**
   * Copy link to clipboard
   */
  const handleCopyLink = useCallback(async () => {
    const url = generateHighlightUrl();

    try {
      await navigator.clipboard.writeText(url);
      setLinkCopied(true);
      onCopyLink?.(url);

      // Reset after 2 seconds
      setTimeout(() => setLinkCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy link:', err);
    }
  }, [generateHighlightUrl, onCopyLink]);

  /**
   * Handle discuss button click
   */
  const handleDiscuss = useCallback(() => {
    if (selection && onDiscuss) {
      onDiscuss(selection);
      setSelection(null);
      setMenuPosition(null);
    }
  }, [selection, onDiscuss]);

  /**
   * Share to Twitter/X
   */
  const handleTwitterShare = useCallback(() => {
    if (!selection) return;

    const url = generateHighlightUrl();
    const text = `"${selection.text.slice(0, 200)}${selection.text.length > 200 ? '...' : ''}"`;
    const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;

    window.open(twitterUrl, '_blank', 'width=550,height=420');
  }, [selection, generateHighlightUrl]);

  /**
   * Close menu
   */
  const handleClose = useCallback(() => {
    setSelection(null);
    setMenuPosition(null);
  }, []);

  /**
   * Listen for selection changes
   */
  useEffect(() => {
    document.addEventListener('selectionchange', handleSelectionChange);
    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
    };
  }, [handleSelectionChange]);

  /**
   * Close menu on click outside
   */
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(e.target as Node)
      ) {
        // Small delay to allow for selection to complete
        setTimeout(() => {
          const sel = window.getSelection();
          if (!sel || sel.isCollapsed) {
            handleClose();
          }
        }, 100);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [handleClose]);

  /**
   * Close menu on escape key
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleClose]);

  // Don't render if no selection
  if (!selection || !menuPosition) {
    return null;
  }

  return (
    <div ref={menuRef}>
      <ShareMenu
        selection={selection}
        position={menuPosition}
        locale={locale}
        onCopyLink={handleCopyLink}
        onDiscuss={discussionsEnabled ? handleDiscuss : undefined}
        onTwitterShare={handleTwitterShare}
        onClose={handleClose}
        linkCopied={linkCopied}
        discussionsEnabled={discussionsEnabled}
      />
    </div>
  );
};

export default TextHighlighter;
