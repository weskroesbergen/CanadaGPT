/**
 * Utility functions for Bill GANTT visualization
 */

export interface BillGanttData {
  number: string;
  session: string;
  title: string;
  title_fr: string;
  status: string;
  status_fr: string;
  bill_type: string;
  bill_type_fr: string;
  is_government_bill: boolean;
  originating_chamber: string;
  originating_chamber_fr: string;
  introduced_date: string;
  stage?: string;
  latest_event?: string;
  passed_house_first_reading?: string;
  passed_house_second_reading?: string;
  passed_house_third_reading?: string;
  passed_senate_first_reading?: string;
  passed_senate_second_reading?: string;
  passed_senate_third_reading?: string;
  royal_assent_date?: string;
  referredTo?: Array<{ code: string; name: string }>;
  sponsor?: { name: string; party: string };
  votesAggregate?: { count: number };
  hansardDebatesAggregate?: { count: number };
}

export interface LegislativeStage {
  name: string;
  date?: string;
  chamber: 'house' | 'senate' | 'committee';
  completed: boolean;
}

export type Swimlane = 'house' | 'committee' | 'senate';

/**
 * Calculate activity score based on Hansard mentions and votes
 * Higher score = more active bill
 */
export function calculateBillActivity(bill: BillGanttData): number {
  let score = 0;

  // Hansard debates (+5 points each)
  const hansardDebates = bill.hansardDebatesAggregate?.count || 0;
  score += hansardDebates * 5;

  // Votes (+10 points each)
  const votes = bill.votesAggregate?.count || 0;
  score += votes * 10;

  // Committee referral (+15 points)
  if (bill.referredTo && bill.referredTo.length > 0) {
    score += 15;
  }

  // Recency bonus (bills introduced recently get higher scores)
  // +1 point per day since introduction (max 90 days)
  if (bill.introduced_date) {
    const introducedDate = new Date(bill.introduced_date);
    const daysSince = Math.floor(
      (Date.now() - introducedDate.getTime()) / (1000 * 60 * 60 * 24)
    );
    const recencyBonus = Math.max(0, 90 - daysSince);
    score += recencyBonus;
  }

  // Stage advancement bonus (further along = more activity)
  const stageBonus = getStageProgress(bill) * 2;
  score += stageBonus;

  return score;
}

/**
 * Determine which swimlane a bill currently belongs to
 * Based on latest stage progression
 */
export function determineSwimlane(bill: BillGanttData): Swimlane {
  // Check if in committee (check status or referredTo)
  const statusLower = (bill.status || '').toLowerCase();
  if (
    statusLower.includes('committee') ||
    statusLower.includes('report stage')
  ) {
    return 'committee';
  }

  // Check Senate stages
  if (
    bill.passed_senate_third_reading ||
    bill.passed_senate_second_reading ||
    bill.passed_senate_first_reading ||
    statusLower.includes('senate')
  ) {
    return 'senate';
  }

  // Default to House
  return 'house';
}

/**
 * Calculate horizontal position (0-100%) based on stage progress
 * within the current swimlane
 */
export function calculateStagePosition(bill: BillGanttData): number {
  const swimlane = determineSwimlane(bill);

  if (swimlane === 'house') {
    // House progression: Introduced -> 1st -> 2nd -> 3rd (0-100%)
    if (bill.passed_house_third_reading) return 100;
    if (bill.passed_house_second_reading) return 66;
    if (bill.passed_house_first_reading) return 33;
    if (bill.introduced_date) return 10;
    return 0;
  } else if (swimlane === 'senate') {
    // Senate progression: 1st -> 2nd -> 3rd -> Royal Assent (0-100%)
    if (bill.royal_assent_date) return 100;
    if (bill.passed_senate_third_reading) return 75;
    if (bill.passed_senate_second_reading) return 50;
    if (bill.passed_senate_first_reading) return 25;
    return 5;
  } else {
    // Committee: centered around 50%
    const statusLower = (bill.status || '').toLowerCase();
    if (statusLower.includes('report stage')) return 75;
    return 50;
  }
}

/**
 * Get overall stage progress (0-100) across entire legislative process
 */
export function getStageProgress(bill: BillGanttData): number {
  let progress = 0;
  const stages = [
    bill.introduced_date, // 0
    bill.passed_house_first_reading, // 1
    bill.passed_house_second_reading, // 2
    bill.passed_house_third_reading, // 3
    bill.passed_senate_first_reading, // 4
    bill.passed_senate_second_reading, // 5
    bill.passed_senate_third_reading, // 6
    bill.royal_assent_date, // 7
  ];

  for (const stage of stages) {
    if (stage) progress++;
  }

  return progress;
}

/**
 * Build a timeline of legislative stages for a bill
 */
export function buildBillTimeline(bill: BillGanttData): LegislativeStage[] {
  const timeline: LegislativeStage[] = [];

  // House stages
  if (bill.introduced_date) {
    timeline.push({
      name: 'introduced',
      date: bill.introduced_date,
      chamber: 'house',
      completed: true,
    });
  }

  if (bill.passed_house_first_reading) {
    timeline.push({
      name: 'house_first_reading',
      date: bill.passed_house_first_reading,
      chamber: 'house',
      completed: true,
    });
  }

  if (bill.passed_house_second_reading) {
    timeline.push({
      name: 'house_second_reading',
      date: bill.passed_house_second_reading,
      chamber: 'house',
      completed: true,
    });
  }

  // Committee stages (if applicable)
  if (bill.referredTo && bill.referredTo.length > 0) {
    timeline.push({
      name: 'committee_review',
      chamber: 'committee',
      completed: !!(
        bill.passed_house_third_reading || bill.passed_senate_first_reading
      ),
    });
  }

  if (bill.passed_house_third_reading) {
    timeline.push({
      name: 'house_third_reading',
      date: bill.passed_house_third_reading,
      chamber: 'house',
      completed: true,
    });
  }

  // Senate stages
  if (bill.passed_senate_first_reading) {
    timeline.push({
      name: 'senate_first_reading',
      date: bill.passed_senate_first_reading,
      chamber: 'senate',
      completed: true,
    });
  }

  if (bill.passed_senate_second_reading) {
    timeline.push({
      name: 'senate_second_reading',
      date: bill.passed_senate_second_reading,
      chamber: 'senate',
      completed: true,
    });
  }

  if (bill.passed_senate_third_reading) {
    timeline.push({
      name: 'senate_third_reading',
      date: bill.passed_senate_third_reading,
      chamber: 'senate',
      completed: true,
    });
  }

  if (bill.royal_assent_date) {
    timeline.push({
      name: 'royal_assent',
      date: bill.royal_assent_date,
      chamber: 'senate',
      completed: true,
    });
  }

  return timeline;
}

/**
 * Filter and sort bills for GANTT display
 */
export function filterOrderPaperBills(
  bills: BillGanttData[],
  limit: number = 20
): BillGanttData[] {
  // Filter out bills with royal assent (completed bills)
  const activeBills = bills.filter((bill) => {
    const statusLower = (bill.status || '').toLowerCase();
    return !statusLower.includes('royal assent') && !bill.royal_assent_date;
  });

  // Sort by activity score (descending)
  const sorted = activeBills.sort((a, b) => {
    return calculateBillActivity(b) - calculateBillActivity(a);
  });

  // Return top N bills
  return sorted.slice(0, limit);
}

/**
 * Group bills by swimlane for visualization
 */
export function groupBillsBySwimlane(bills: BillGanttData[]): {
  house: BillGanttData[];
  committee: BillGanttData[];
  senate: BillGanttData[];
} {
  const grouped = {
    house: [] as BillGanttData[],
    committee: [] as BillGanttData[],
    senate: [] as BillGanttData[],
  };

  for (const bill of bills) {
    const swimlane = determineSwimlane(bill);
    grouped[swimlane].push(bill);
  }

  return grouped;
}
