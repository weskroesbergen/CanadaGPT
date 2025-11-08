/**
 * Committees list page
 */

'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@apollo/client';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Loading } from '@/components/Loading';
import { Card } from '@canadagpt/design-system';
import { GET_COMMITTEES } from '@/lib/queries';
import { Users, Building2, Landmark, Search, SortAsc, SortDesc } from 'lucide-react';

interface Committee {
  code: string;
  name: string;
  mandate?: string;
  chamber: string;
  membersAggregate: {
    count: number;
  };
}

type ChamberFilter = 'all' | 'House' | 'Senate';
type SortOption = 'name' | 'members';

// Committee type colors based on code patterns
const getCommitteeColor = (code: string, chamber: string) => {
  if (chamber === 'Senate') {
    return {
      bg: 'bg-purple-500/10',
      icon: 'text-purple-600',
      border: 'hover:border-purple-500',
      badge: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
    };
  }

  // House committees - color by category
  if (code.includes('ETHI') || code.includes('JUST') || code.includes('SECU')) {
    return {
      bg: 'bg-blue-500/10',
      icon: 'text-blue-600',
      border: 'hover:border-blue-500',
      badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
    };
  }
  if (code.includes('FINA') || code.includes('INDU') || code.includes('OGGO')) {
    return {
      bg: 'bg-green-500/10',
      icon: 'text-green-600',
      border: 'hover:border-green-500',
      badge: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
    };
  }
  if (code.includes('HEAL') || code.includes('HUMA') || code.includes('ESPE')) {
    return {
      bg: 'bg-rose-500/10',
      icon: 'text-rose-600',
      border: 'hover:border-rose-500',
      badge: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300'
    };
  }
  if (code.includes('ENVI') || code.includes('AGRI') || code.includes('FISH')) {
    return {
      bg: 'bg-emerald-500/10',
      icon: 'text-emerald-600',
      border: 'hover:border-emerald-500',
      badge: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
    };
  }
  if (code.includes('FOPO') || code.includes('TRAN') || code.includes('CIIT')) {
    return {
      bg: 'bg-amber-500/10',
      icon: 'text-amber-600',
      border: 'hover:border-amber-500',
      badge: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
    };
  }

  // Default red for other committees
  return {
    bg: 'bg-accent-red/10',
    icon: 'text-accent-red',
    border: 'hover:border-accent-red',
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
  };
};

export default function CommitteesPage() {
  const { data, loading, error } = useQuery(GET_COMMITTEES);
  const [chamberFilter, setChamberFilter] = useState<ChamberFilter>('all');
  const [sortBy, setSortBy] = useState<SortOption>('name');
  const [sortAsc, setSortAsc] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const committees: Committee[] = data?.committees || [];

  // Filter and sort committees
  const filteredCommittees = useMemo(() => {
    let filtered = committees;

    // Apply chamber filter
    if (chamberFilter !== 'all') {
      filtered = filtered.filter(c => c.chamber === chamberFilter);
    }

    // Apply search
    if (searchTerm) {
      filtered = filtered.filter(c =>
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.mandate?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply sort
    filtered = [...filtered].sort((a, b) => {
      if (sortBy === 'name') {
        return sortAsc
          ? a.name.localeCompare(b.name)
          : b.name.localeCompare(a.name);
      } else {
        const aCount = a.membersAggregate.count;
        const bCount = b.membersAggregate.count;
        return sortAsc ? aCount - bCount : bCount - aCount;
      }
    });

    return filtered;
  }, [committees, chamberFilter, searchTerm, sortBy, sortAsc]);

  const houseChamberCount = committees.filter(c => c.chamber === 'House').length;
  const senateChamberCount = committees.filter(c => c.chamber === 'Senate').length;

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 page-container">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-text-primary mb-2">Parliamentary Committees</h1>
          <p className="text-text-secondary">Browse {committees.length} committees studying key issues</p>
        </div>

        {/* Search and Filters */}
        <div className="mb-6 space-y-4">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-text-tertiary" />
            <input
              type="text"
              placeholder="Search committees..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-bg-secondary border border-border-primary rounded-lg
                       focus:outline-none focus:ring-2 focus:ring-accent-red focus:border-transparent
                       text-text-primary placeholder-text-tertiary"
            />
          </div>

          {/* Filter and Sort Controls */}
          <div className="flex flex-wrap gap-3 items-center">
            {/* Chamber Filter */}
            <div className="flex gap-2">
              <button
                onClick={() => setChamberFilter('all')}
                className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2
                  ${chamberFilter === 'all'
                    ? 'bg-accent-red text-white shadow-md'
                    : 'bg-bg-secondary text-text-secondary hover:bg-bg-tertiary'
                  }`}
              >
                <Building2 className="h-4 w-4" />
                All ({committees.length})
              </button>
              <button
                onClick={() => setChamberFilter('House')}
                className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2
                  ${chamberFilter === 'House'
                    ? 'bg-green-600 text-white shadow-md'
                    : 'bg-bg-secondary text-text-secondary hover:bg-bg-tertiary'
                  }`}
              >
                <Landmark className="h-4 w-4" />
                House ({houseChamberCount})
              </button>
              <button
                onClick={() => setChamberFilter('Senate')}
                className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2
                  ${chamberFilter === 'Senate'
                    ? 'bg-purple-600 text-white shadow-md'
                    : 'bg-bg-secondary text-text-secondary hover:bg-bg-tertiary'
                  }`}
              >
                <Building2 className="h-4 w-4" />
                Senate ({senateChamberCount})
              </button>
            </div>

            {/* Sort Controls */}
            <div className="ml-auto flex gap-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="px-3 py-2 bg-bg-secondary border border-border-primary rounded-lg
                         text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-red"
              >
                <option value="name">Sort by Name</option>
                <option value="members">Sort by Members</option>
              </select>
              <button
                onClick={() => setSortAsc(!sortAsc)}
                className="px-3 py-2 bg-bg-secondary border border-border-primary rounded-lg
                         text-text-secondary hover:bg-bg-tertiary transition-colors"
                title={sortAsc ? 'Sort Ascending' : 'Sort Descending'}
              >
                {sortAsc ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Results count */}
          {searchTerm && (
            <p className="text-sm text-text-secondary">
              Found {filteredCommittees.length} committee{filteredCommittees.length !== 1 ? 's' : ''}
            </p>
          )}
        </div>

        {/* Committees Grid */}
        {loading ? (
          <Loading />
        ) : error ? (
          <Card className="p-8 text-center">
            <p className="text-text-secondary">Error loading committees: {error.message}</p>
          </Card>
        ) : filteredCommittees.length === 0 ? (
          <Card className="p-12 text-center">
            <Users className="h-12 w-12 text-text-tertiary mx-auto mb-4" />
            <p className="text-lg text-text-secondary mb-2">
              {searchTerm ? 'No committees match your search' : 'No committees found'}
            </p>
            <p className="text-sm text-text-tertiary">
              {searchTerm ? 'Try a different search term' : 'Committee data is being ingested'}
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredCommittees.map((committee) => {
              const colors = getCommitteeColor(committee.code, committee.chamber);

              return (
                <Card
                  key={committee.code}
                  elevated
                  className={`h-full ${colors.border} transition-all cursor-pointer transform hover:scale-[1.02]`}
                  onClick={() => window.location.href = `/committees/${committee.code}`}
                >
                  <div className="flex items-start gap-3 mb-3">
                    <div className={`flex-shrink-0 w-12 h-12 ${colors.bg} rounded-lg flex items-center justify-center`}>
                      <Users className={`h-6 w-6 ${colors.icon}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-text-primary mb-1 line-clamp-2 leading-tight">
                        {committee.name}
                      </h3>
                      <p className="text-xs text-text-tertiary font-mono">{committee.code}</p>
                    </div>
                  </div>

                  {committee.mandate && (
                    <p className="text-sm text-text-secondary mb-3 line-clamp-3 leading-relaxed">
                      {committee.mandate}
                    </p>
                  )}

                  <div className="flex items-center gap-3 text-xs">
                    <div className="flex items-center gap-1 text-text-tertiary">
                      <Users className="h-3.5 w-3.5" />
                      <span className="font-medium">{committee.membersAggregate.count}</span>
                      <span>members</span>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full font-medium ${colors.badge}`}>
                      {committee.chamber}
                    </span>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
