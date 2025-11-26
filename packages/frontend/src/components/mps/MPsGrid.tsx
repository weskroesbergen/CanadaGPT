/**
 * MPsGrid - Optimized MP Grid with Infinite Scroll
 *
 * Performance optimizations:
 * - Server-side initial data (no loading spinner)
 * - Offset-based pagination for infinite scroll
 * - Server-side party filtering
 * - Lazy image loading
 */

'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useQuery } from '@apollo/client';
import { useTranslations } from 'next-intl';
import { Search, Crown, Eye, EyeOff, Loader2 } from 'lucide-react';
import { PAGINATED_MPS, COUNT_MPS } from '@/lib/queries';
import { MPCard, MPCardData } from '@/components/MPCard';
import { PartyFilterButtons } from '@/components/PartyFilterButtons';
import { Card } from '@canadagpt/design-system';
import { useAuth } from '@/contexts/AuthContext';
import { MyMPSection } from './MyMPSection';

interface MPsGridProps {
  initialMPs: MPCardData[];
  initialCount: number;
}

const PAGE_SIZE = 24;

export function MPsGrid({ initialMPs, initialCount }: MPsGridProps) {
  const t = useTranslations('mps');
  const { user } = useAuth();

  // State
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [partyFilter, setPartyFilter] = useState<string[]>([]);
  const [cabinetOnly, setCabinetOnly] = useState(false);
  const [mps, setMPs] = useState<MPCardData[]>(initialMPs);
  const [totalCount, setTotalCount] = useState(initialCount);
  const [offset, setOffset] = useState(initialMPs.length);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(initialMPs.length < initialCount);

  // My MP section visibility - use localStorage as source of truth for immediate feedback
  const [showMyMP, setShowMyMP] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('showMyMPSection');
      if (stored !== null) {
        return stored === 'true';
      }
    }
    // Default to true if no localStorage value
    return true;
  });

  // Sync localStorage with server value on initial load (only once)
  const [hasInitialized, setHasInitialized] = useState(false);
  useEffect(() => {
    if (!hasInitialized && user?.show_my_mp_section !== undefined) {
      // Only sync from server if localStorage doesn't have a value yet
      const stored = localStorage.getItem('showMyMPSection');
      if (stored === null) {
        setShowMyMP(user.show_my_mp_section);
        localStorage.setItem('showMyMPSection', String(user.show_my_mp_section));
      }
      setHasInitialized(true);
    }
  }, [user?.show_my_mp_section, hasInitialized]);

  // Intersection observer ref for infinite scroll
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // Debounce search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Determine if we have active filters
  const hasFilters = debouncedSearch || partyFilter.length > 0 || cabinetOnly;

  // Query variables
  const queryVariables = {
    parties: partyFilter.length > 0 ? partyFilter : null,
    current: true,
    cabinetOnly: cabinetOnly || null,
    searchTerm: debouncedSearch || null,
  };

  // Count query for filtered results
  const { data: countData } = useQuery(COUNT_MPS, {
    variables: queryVariables,
    skip: !hasFilters,
  });

  // Query for filtered data (first page)
  const { data, loading, refetch } = useQuery(PAGINATED_MPS, {
    variables: {
      ...queryVariables,
      limit: PAGE_SIZE,
      offset: 0,
    },
    skip: !hasFilters,
    notifyOnNetworkStatusChange: true,
  });

  // Reset when filters change
  useEffect(() => {
    if (hasFilters) {
      if (data?.paginatedMPs) {
        setMPs(data.paginatedMPs);
        setOffset(data.paginatedMPs.length);
        const count = countData?.countMPs?.count ?? data.paginatedMPs.length;
        setTotalCount(count);
        setHasMore(data.paginatedMPs.length < count);
      }
    } else {
      // Reset to initial data when filters cleared
      setMPs(initialMPs);
      setTotalCount(initialCount);
      setOffset(initialMPs.length);
      setHasMore(initialMPs.length < initialCount);
    }
  }, [data, countData, hasFilters, initialMPs, initialCount]);

  // Load more function for infinite scroll
  const loadMore = useCallback(async () => {
    if (isLoadingMore || !hasMore) return;

    setIsLoadingMore(true);

    try {
      const result = await refetch({
        ...queryVariables,
        limit: PAGE_SIZE,
        offset: offset,
      });

      if (result.data?.paginatedMPs) {
        const newMPs = result.data.paginatedMPs;
        setMPs(prev => [...prev, ...newMPs]);
        setOffset(prev => prev + newMPs.length);
        setHasMore(offset + newMPs.length < totalCount);
      }
    } catch (error) {
      console.error('Error loading more MPs:', error);
    } finally {
      setIsLoadingMore(false);
    }
  }, [refetch, queryVariables, isLoadingMore, hasMore, offset, totalCount]);

  // Intersection observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoadingMore && !loading) {
          loadMore();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => observer.disconnect();
  }, [loadMore, hasMore, isLoadingMore, loading]);

  // Toggle My MP section - update localStorage immediately for instant feedback
  const toggleMyMP = async () => {
    const newValue = !showMyMP;
    setShowMyMP(newValue);

    // Always save to localStorage for immediate persistence
    localStorage.setItem('showMyMPSection', String(newValue));

    // If logged in, also sync to server (fire and forget, don't block UI)
    if (user) {
      try {
        await fetch('/api/user/profile', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ show_my_mp_section: newValue }),
        });
        // Don't need to updateSession since we're using localStorage as source of truth
      } catch (error) {
        console.error('Failed to sync show_my_mp_section to server:', error);
        // Don't revert - localStorage is the source of truth
      }
    }
  };

  const showingCount = mps.length;

  return (
    <>
      {/* Header with Toggle */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <h1 className="text-4xl font-bold text-text-primary">{t('title')}</h1>
        </div>

        <button
          onClick={toggleMyMP}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all bg-bg-secondary border-2 border-border-subtle hover:border-accent-red text-text-primary"
          title={showMyMP ? 'Hide My MP section' : 'Show My MP section'}
        >
          {showMyMP ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          <span className="hidden sm:inline">My MP</span>
        </button>
      </div>

      <p className="text-text-secondary mb-8">
        {t('subtitle', { count: totalCount })}
        {showingCount < totalCount && (
          <span className="text-text-tertiary"> ({t('showing', { count: showingCount })})</span>
        )}
      </p>

      {/* My MP Section */}
      {showMyMP && (
        <div className="mb-8">
          <MyMPSection />
        </div>
      )}

      {/* Filters */}
      <div className="mb-6 space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-text-tertiary" />
            <input
              type="text"
              placeholder={t('search.placeholder')}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-bg-secondary border border-border-subtle rounded-lg text-text-primary placeholder-text-tertiary focus:border-accent-red focus:outline-none transition-colors"
            />
          </div>

          {/* Cabinet filter */}
          <button
            onClick={() => setCabinetOnly(!cabinetOnly)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
              cabinetOnly
                ? 'bg-accent-red text-white border-2 border-accent-red'
                : 'bg-bg-secondary text-text-primary border-2 border-border-subtle hover:border-accent-red'
            }`}
          >
            <Crown className="h-4 w-4" />
            {t('filters.cabinet')}
          </button>
        </div>

        {/* Party Filter Buttons */}
        <PartyFilterButtons
          selected={partyFilter}
          onSelect={(parties) => setPartyFilter(parties)}
        />
      </div>

      {/* Loading State for initial filter change */}
      {loading && mps.length === 0 && (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-accent-red" />
        </div>
      )}

      {/* MPs Grid */}
      {mps.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mps.map((mp) => (
            <MPCard key={mp.id} mp={mp} />
          ))}
        </div>
      )}

      {/* No Results */}
      {mps.length === 0 && !loading && (
        <Card>
          <p className="text-text-secondary text-center">{t('search.noResults')}</p>
        </Card>
      )}

      {/* Infinite Scroll Trigger */}
      <div ref={loadMoreRef} className="h-20 flex items-center justify-center">
        {isLoadingMore && (
          <div className="flex items-center gap-2 text-text-secondary">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>{t('loadingMore')}</span>
          </div>
        )}
        {!hasMore && mps.length > 0 && (
          <p className="text-text-tertiary text-sm">
            {t('allLoaded', { count: totalCount })}
          </p>
        )}
      </div>
    </>
  );
}
