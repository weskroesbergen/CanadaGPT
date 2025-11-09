/**
 * Utility functions for fetching committee data from OpenParliament API
 */

const OPENPARLIAMENT_API_BASE = 'https://api.openparliament.ca';

export interface CommitteeMeeting {
  date: string;
  number: number;
  in_camera: boolean;
  has_evidence: boolean;
  committee_url?: string;
  meeting_url?: string;
}

/**
 * Fetch committee meetings from OpenParliament API
 * @param committeeCode - Committee code (e.g., "ETHI", "FINA")
 * @param limit - Maximum number of meetings to return
 */
export async function fetchCommitteeMeetings(
  committeeCode: string,
  limit: number = 20
): Promise<CommitteeMeeting[]> {
  try {
    const url = `${OPENPARLIAMENT_API_BASE}/committees/meetings/?committee=${committeeCode.toLowerCase()}&limit=${limit}`;

    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'CanadaGPT (https://canadagpt.ca)'
      }
    });

    if (!response.ok) {
      console.error(`Failed to fetch committee meetings: ${response.status} ${response.statusText}`);
      return [];
    }

    const data = await response.json();

    // OpenParliament API returns: { objects: [...], pagination: {...} }
    const meetings = data.objects || [];

    return meetings.map((meeting: any) => ({
      date: meeting.date,
      number: meeting.number,
      in_camera: meeting.in_camera || false,
      has_evidence: meeting.has_evidence || false,
      committee_url: meeting.committee_url,
      meeting_url: meeting.url
    }));
  } catch (error) {
    console.error('Error fetching committee meetings:', error);
    return [];
  }
}
