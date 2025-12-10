'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useApolloClient } from '@apollo/client';
import { gql } from '@apollo/client';
import type { MentionSuggestion, MentionEntityType } from '@/components/mentions';

/**
 * GraphQL queries for mention search
 */
const SEARCH_MPS_FOR_MENTION = gql`
  query SearchMPsForMention($searchTerm: String!, $limit: Int) {
    searchMPs(searchTerm: $searchTerm, current: true, limit: $limit) {
      id
      name
      party
      riding
      photo_url
    }
  }
`;

const SEARCH_BILLS_FOR_MENTION = gql`
  query SearchBillsForMention($searchTerm: String!, $limit: Int) {
    searchBills(searchTerm: $searchTerm, limit: $limit) {
      id
      number
      session
      title
      title_fr
      status
      status_fr
    }
  }
`;

const SEARCH_COMMITTEES_FOR_MENTION = gql`
  query SearchCommitteesForMention($searchTerm: String, $limit: Int) {
    committees(
      where: {
        OR: [
          { code_CONTAINS: $searchTerm }
          { name_CONTAINS: $searchTerm }
        ]
      }
      options: { limit: $limit }
    ) {
      code
      name
      chamber
    }
  }
`;

const GET_RECENT_DEBATES_FOR_MENTION = gql`
  query GetRecentDebatesForMention($limit: Int) {
    documents(
      options: { limit: $limit, sort: [{ date: DESC }] }
    ) {
      id
      date
      number
      session_id
    }
  }
`;

const SEARCH_VOTES_FOR_MENTION = gql`
  query SearchVotesForMention($searchTerm: String, $limit: Int) {
    votes(
      where: {
        OR: [
          { description_CONTAINS: $searchTerm }
          { bill_number_CONTAINS: $searchTerm }
        ]
      }
      options: { limit: $limit, sort: [{ date: DESC }] }
    ) {
      id
      vote_number
      date
      result
      description
      bill_number
      session
    }
  }
`;

interface UseMentionSearchOptions {
  query: string;
  types?: MentionEntityType[];
  locale?: string;
  maxResults?: number;
  debounceMs?: number;
}

interface UseMentionSearchResult {
  suggestions: MentionSuggestion[];
  loading: boolean;
  error: Error | null;
}

/**
 * Hook for searching entities to mention
 * Queries multiple entity types and returns unified suggestions
 */
export function useMentionSearch({
  query,
  types = ['bill', 'mp', 'committee', 'vote', 'debate'],
  locale = 'en',
  maxResults = 8,
  debounceMs = 200,
}: UseMentionSearchOptions): UseMentionSearchResult {
  const client = useApolloClient();
  const [suggestions, setSuggestions] = useState<MentionSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Parse query to extract type prefix
  const { searchType, searchTerm } = useMemo(() => {
    const cleanQuery = query.startsWith('@') ? query.slice(1) : query;
    const colonIndex = cleanQuery.indexOf(':');

    if (colonIndex > 0) {
      const potentialType = cleanQuery.slice(0, colonIndex).toLowerCase();
      const validTypes: MentionEntityType[] = ['bill', 'mp', 'committee', 'vote', 'debate', 'petition'];

      if (validTypes.includes(potentialType as MentionEntityType)) {
        return {
          searchType: potentialType as MentionEntityType,
          searchTerm: cleanQuery.slice(colonIndex + 1),
        };
      }
    }

    return { searchType: null, searchTerm: cleanQuery };
  }, [query]);

  // Determine which types to search
  const typesToSearch = useMemo(() => {
    if (searchType) return [searchType];
    return types;
  }, [searchType, types]);

  // Search function
  const performSearch = useCallback(async () => {
    if (!searchTerm || searchTerm.length < 1) {
      setSuggestions([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const results: MentionSuggestion[] = [];
      const perTypeLimit = Math.ceil(maxResults / typesToSearch.length);

      // Search MPs
      if (typesToSearch.includes('mp')) {
        try {
          const { data } = await client.query({
            query: SEARCH_MPS_FOR_MENTION,
            variables: { searchTerm, limit: perTypeLimit },
            fetchPolicy: 'cache-first',
          });

          data?.searchMPs?.forEach((mp: any) => {
            results.push({
              type: 'mp',
              id: mp.id,
              label: mp.name,
              secondary: `${mp.riding} - ${mp.party}`,
              mentionString: `@mp:${mp.id}`,
              url: `/${locale}/mps/${mp.id}`,
              metadata: { party: mp.party, photo_url: mp.photo_url },
            });
          });
        } catch (e) {
          console.warn('MP search failed:', e);
        }
      }

      // Search Bills
      if (typesToSearch.includes('bill')) {
        try {
          const { data } = await client.query({
            query: SEARCH_BILLS_FOR_MENTION,
            variables: { searchTerm, limit: perTypeLimit },
            fetchPolicy: 'cache-first',
          });

          data?.searchBills?.forEach((bill: any) => {
            const title = locale === 'fr' && bill.title_fr ? bill.title_fr : bill.title;
            const status = locale === 'fr' && bill.status_fr ? bill.status_fr : bill.status;
            results.push({
              type: 'bill',
              id: bill.number,
              label: `Bill ${bill.number.toUpperCase()}`,
              secondary: title || status,
              mentionString: `@bill:${bill.number.toLowerCase()}`,
              url: `/${locale}/bills/${bill.session}/${bill.number}`,
              metadata: { session: bill.session, status },
            });
          });
        } catch (e) {
          console.warn('Bill search failed:', e);
        }
      }

      // Search Committees
      if (typesToSearch.includes('committee')) {
        try {
          const { data } = await client.query({
            query: SEARCH_COMMITTEES_FOR_MENTION,
            variables: { searchTerm: searchTerm.toUpperCase(), limit: perTypeLimit },
            fetchPolicy: 'cache-first',
          });

          data?.committees?.forEach((committee: any) => {
            results.push({
              type: 'committee',
              id: committee.code,
              label: committee.code,
              secondary: committee.name,
              mentionString: `@committee:${committee.code.toLowerCase()}`,
              url: `/${locale}/committees/${committee.code.toLowerCase()}`,
              metadata: { chamber: committee.chamber },
            });
          });
        } catch (e) {
          console.warn('Committee search failed:', e);
        }
      }

      // Search Votes
      if (typesToSearch.includes('vote')) {
        try {
          const { data } = await client.query({
            query: SEARCH_VOTES_FOR_MENTION,
            variables: { searchTerm, limit: perTypeLimit },
            fetchPolicy: 'cache-first',
          });

          data?.votes?.forEach((vote: any) => {
            const voteId = `${vote.session}-${vote.vote_number}`;
            results.push({
              type: 'vote',
              id: voteId,
              label: `Vote #${vote.vote_number}`,
              secondary: `${vote.description || vote.bill_number} - ${vote.result}`,
              mentionString: `@vote:${voteId}`,
              url: `/${locale}/votes/${vote.session}/${vote.vote_number}`,
              metadata: { date: vote.date, result: vote.result },
            });
          });
        } catch (e) {
          console.warn('Vote search failed:', e);
        }
      }

      // Get recent debates (no text search, just recent)
      if (typesToSearch.includes('debate') && searchTerm.match(/^\d{4}-\d{2}|\d{4}$/)) {
        try {
          const { data } = await client.query({
            query: GET_RECENT_DEBATES_FOR_MENTION,
            variables: { limit: perTypeLimit },
            fetchPolicy: 'cache-first',
          });

          data?.documents
            ?.filter((doc: any) => doc.date?.includes(searchTerm))
            ?.forEach((doc: any) => {
              results.push({
                type: 'debate',
                id: doc.date,
                label: doc.date,
                secondary: `Sitting #${doc.number}`,
                mentionString: `@debate:${doc.date}`,
                url: `/${locale}/debates/${doc.date}`,
                metadata: { session_id: doc.session_id },
              });
            });
        } catch (e) {
          console.warn('Debate search failed:', e);
        }
      }

      // Sort by relevance (exact matches first, then by type priority)
      const typePriority: Record<MentionEntityType, number> = {
        bill: 1,
        mp: 2,
        committee: 3,
        vote: 4,
        debate: 5,
        petition: 6,
      };

      results.sort((a, b) => {
        // Exact ID match first
        const aExact = a.id.toLowerCase() === searchTerm.toLowerCase();
        const bExact = b.id.toLowerCase() === searchTerm.toLowerCase();
        if (aExact && !bExact) return -1;
        if (!aExact && bExact) return 1;

        // Then by type priority
        return typePriority[a.type] - typePriority[b.type];
      });

      setSuggestions(results.slice(0, maxResults));
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Search failed'));
    } finally {
      setLoading(false);
    }
  }, [client, searchTerm, typesToSearch, locale, maxResults]);

  // Debounced search effect
  useEffect(() => {
    const timer = setTimeout(performSearch, debounceMs);
    return () => clearTimeout(timer);
  }, [performSearch, debounceMs]);

  return { suggestions, loading, error };
}

export default useMentionSearch;
