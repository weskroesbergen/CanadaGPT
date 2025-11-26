/**
 * useCommitteeActivity Hook
 *
 * Tracks committee viewing activity and new meeting indicators
 * Uses bookmark metadata to store visit state across devices
 */

import { useCallback, useMemo } from 'react';
import { useBookmarks } from './useBookmarks';
import { useAuth } from '@/contexts/AuthContext';

export interface CommitteeActivity {
  code: string;
  latestMeetingNumber: number | null;
  latestMeetingDate: string | null;
  totalMeetings: number;
  lastViewedMeetingNumber: number | null;
  lastViewedAt: string | null;
  newMeetingsCount: number;
}

export function useCommitteeActivity() {
  const { user } = useAuth();
  const { bookmarks, updateBookmark, getBookmark } = useBookmarks();

  /**
   * Get all bookmarked committees
   */
  const bookmarkedCommittees = useMemo(() => {
    return bookmarks.filter((b) => b.item_type === 'committee');
  }, [bookmarks]);

  /**
   * Calculate new meetings count for a committee
   */
  const getNewMeetingsCount = useCallback(
    (committeeCode: string, currentLatestMeetingNumber?: number | null): number => {
      const bookmark = getBookmark('committee', committeeCode);
      if (!bookmark) return 0; // Only track bookmarked committees
      if (!currentLatestMeetingNumber) return 0; // No meetings data

      const lastViewed = bookmark.metadata?.last_meeting_number as number | undefined;
      if (!lastViewed) {
        // Never viewed - show all meetings as new
        return currentLatestMeetingNumber;
      }

      return Math.max(0, currentLatestMeetingNumber - lastViewed);
    },
    [getBookmark]
  );

  /**
   * Mark committee as viewed
   * Updates the bookmark metadata with latest meeting info
   */
  const markCommitteeViewed = useCallback(
    async (
      committeeCode: string,
      meetingNumber?: number,
      totalMeetings?: number
    ): Promise<void> => {
      const bookmark = getBookmark('committee', committeeCode);
      if (!bookmark) return; // Only track bookmarked committees

      // Optimistic update
      await updateBookmark(bookmark.id, {
        metadata: {
          ...bookmark.metadata,
          last_visit: new Date().toISOString(),
          last_meeting_number: meetingNumber ?? bookmark.metadata?.last_meeting_number,
          total_meetings: totalMeetings ?? bookmark.metadata?.total_meetings,
        },
      });
    },
    [getBookmark, updateBookmark]
  );

  /**
   * Get activity data for a specific committee
   */
  const getCommitteeActivity = useCallback(
    (
      committeeCode: string,
      latestMeetingNumber?: number | null,
      latestMeetingDate?: string | null,
      totalMeetings?: number
    ): CommitteeActivity | null => {
      const bookmark = getBookmark('committee', committeeCode);
      if (!bookmark) return null;

      const lastViewedMeetingNumber = (bookmark.metadata?.last_meeting_number as number) ?? null;
      const lastViewedAt = (bookmark.metadata?.last_visit as string) ?? null;

      return {
        code: committeeCode,
        latestMeetingNumber: latestMeetingNumber ?? null,
        latestMeetingDate: latestMeetingDate ?? null,
        totalMeetings: totalMeetings ?? 0,
        lastViewedMeetingNumber,
        lastViewedAt,
        newMeetingsCount: getNewMeetingsCount(committeeCode, latestMeetingNumber),
      };
    },
    [getBookmark, getNewMeetingsCount]
  );

  /**
   * Get all bookmarked committees with activity data
   */
  const bookmarkedCommitteesWithActivity = useMemo(() => {
    return bookmarkedCommittees.map((bookmark) => ({
      bookmark,
      activity: getCommitteeActivity(bookmark.item_id),
    }));
  }, [bookmarkedCommittees, getCommitteeActivity]);

  /**
   * Check if a committee is being tracked (bookmarked)
   */
  const isTracking = useCallback(
    (committeeCode: string): boolean => {
      return bookmarkedCommittees.some((b) => b.item_id === committeeCode);
    },
    [bookmarkedCommittees]
  );

  return {
    // State
    bookmarkedCommittees,
    bookmarkedCommitteesWithActivity,
    isAuthenticated: !!user,

    // Actions
    markCommitteeViewed,
    getNewMeetingsCount,
    getCommitteeActivity,
    isTracking,
  };
}
