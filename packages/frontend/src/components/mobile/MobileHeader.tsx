/**
 * MobileHeader - Mobile-Optimized Header with Voice Search
 * Sticky header with integrated voice search and navigation
 */

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Menu, X, Mic } from 'lucide-react';
import { VoiceSearch } from '@/components/voice';

interface MobileHeaderProps {
  title?: string;
  showSearch?: boolean;
  onMenuClick?: () => void;
  locale?: string;
}

export function MobileHeader({
  title,
  showSearch = true,
  onMenuClick,
  locale = 'en',
}: MobileHeaderProps) {
  const router = useRouter();
  const [isSearchExpanded, setIsSearchExpanded] = useState(false);

  const handleSearch = (query: string) => {
    router.push(`/${locale}/search?q=${encodeURIComponent(query)}`);
    setIsSearchExpanded(false);
  };

  return (
    <header className="mobile-header">
      <div className="mobile-header-main">
        {onMenuClick && (
          <button
            onClick={onMenuClick}
            className="mobile-header-menu-button"
            aria-label="Menu"
          >
            <Menu className="h-6 w-6" />
          </button>
        )}

        {title && (
          <h1 className="mobile-header-title">{title}</h1>
        )}

        {showSearch && (
          <button
            onClick={() => setIsSearchExpanded(!isSearchExpanded)}
            className="mobile-header-search-button"
            aria-label="Search"
          >
            {isSearchExpanded ? (
              <X className="h-6 w-6" />
            ) : (
              <Mic className="h-6 w-6" />
            )}
          </button>
        )}
      </div>

      {isSearchExpanded && showSearch && (
        <div className="mobile-header-search">
          <VoiceSearch
            onSearch={handleSearch}
            placeholder="Search MPs, bills, debates..."
          />
        </div>
      )}
    </header>
  );
}
