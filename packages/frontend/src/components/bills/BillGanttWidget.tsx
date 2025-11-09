/**
 * BillGanttWidget Component
 * Interactive GANTT-style visualization of Order Paper bills
 * Shows bills progressing through House, Committee, and Senate swimlanes
 */

'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@apollo/client';
import { useTranslations, useLocale } from 'next-intl';
import { Card } from '@canadagpt/design-system';
import { Loading } from '@/components/Loading';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { GET_ORDER_PAPER_GANTT } from '@/lib/ganttQueries';
import {
  filterOrderPaperBills,
  groupBillsBySwimlane,
  calculateStagePosition,
  type BillGanttData,
} from '@/lib/billGanttUtils';
import { BillSquare } from './BillSquare';

// Map bills to stage columns and tile them in a 3-row grid
interface BillPosition {
  column: number; // Stage column index
  row: number; // Row within column (0-2)
  col: number; // Column within stage (for multiple bills at same stage)
}

function assignBillsToGrid(
  bills: BillGanttData[],
  swimlaneType: 'house' | 'committee' | 'senate'
): Map<string, BillPosition> {
  const positions = new Map<string, BillPosition>();

  // Define stage columns for each swimlane
  const stageColumns: { [key: string]: number[] } = {
    house: [10, 33, 66, 95], // Intro, 1st, 2nd, Royal Assent
    committee: [50, 75, 95], // Committee, Report, Royal Assent
    senate: [25, 50, 75, 95], // 1st, 2nd, 3rd, Royal Assent
  };

  const columns = stageColumns[swimlaneType];

  // Group bills by their stage column
  const billsByColumn = new Map<number, BillGanttData[]>();
  columns.forEach((col) => billsByColumn.set(col, []));

  // Assign each bill to the nearest column
  for (const bill of bills) {
    const stagePos = calculateStagePosition(bill);

    // Find closest column
    let closestColumn = columns[0];
    let minDist = Math.abs(stagePos - columns[0]);

    for (const col of columns) {
      const dist = Math.abs(stagePos - col);
      if (dist < minDist) {
        minDist = dist;
        closestColumn = col;
      }
    }

    billsByColumn.get(closestColumn)?.push(bill);
  }

  // Tile bills within each column (3 rows × N columns)
  billsByColumn.forEach((columnBills, columnIndex) => {
    columnBills.forEach((bill, index) => {
      const row = index % 3; // 0, 1, or 2
      const col = Math.floor(index / 3); // Column offset within stage

      positions.set(`${bill.session}-${bill.number}`, {
        column: columnIndex,
        row,
        col,
      });
    });
  });

  return positions;
}

interface BillGanttWidgetProps {
  currentSession: string;
}

export function BillGanttWidget({ currentSession }: BillGanttWidgetProps) {
  const t = useTranslations('bills.gantt');
  const locale = useLocale();
  const [billLimit, setBillLimit] = useState(25);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const { data, loading, error } = useQuery(GET_ORDER_PAPER_GANTT, {
    variables: {
      session: currentSession,
      limit: 100,
    },
  });

  // Process and filter bills
  const displayBills = useMemo(() => {
    if (!data?.searchBills) return [];
    return filterOrderPaperBills(data.searchBills, billLimit);
  }, [data, billLimit]);

  const groupedBills = useMemo(() => {
    return groupBillsBySwimlane(displayBills);
  }, [displayBills]);

  if (error) {
    return null; // Silently fail if widget can't load
  }

  if (isCollapsed) {
    return (
      <Card className="mb-6 cursor-pointer" onClick={() => setIsCollapsed(false)}>
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-primary">
              {t('title')}
            </h2>
            <span className="text-sm text-secondary">
              ({displayBills.length} {t('activeBills')})
            </span>
          </div>
          <ChevronDown className="w-5 h-5 text-secondary" />
        </div>
      </Card>
    );
  }

  return (
    <Card className="mb-4">
      <div className="flex items-center justify-between mb-1.5 p-4 pb-0">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold text-primary">
            {t('title')}
          </h2>
          <span className="text-sm text-secondary">
            ({displayBills.length} {t('activeBills')})
          </span>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="#search-legislation"
            className="text-xs px-3 py-1.5 rounded-md border border-subtle hover:border-primary text-secondary hover:text-primary transition-colors flex items-center gap-1.5"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
            </svg>
            Search
          </a>
          <button
            onClick={() => setIsCollapsed(true)}
            className="text-secondary hover:text-primary transition-colors"
            aria-label={t('collapse')}
          >
            <ChevronUp className="w-4 h-4" />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-8 flex justify-center">
          <Loading />
        </div>
      ) : (
        <>
          <div className="px-4">
            {displayBills.length === 0 ? (
              <div className="text-center text-secondary py-4">
                {t('noBills')}
              </div>
            ) : (
              <div className="space-y-2">
                {/* Senate Swimlane - Red Chamber */}
                <Swimlane
                  name={t('senate')}
                  color="red"
                  bills={groupedBills.senate}
                  swimlaneType="senate"
                  stages={[
                    { label: t('stages.senateFirst'), position: 25 },
                    { label: t('stages.senateSecond'), position: 50 },
                    { label: t('stages.senateThird'), position: 75 },
                    { label: t('stages.royalAssent'), position: 95 },
                  ]}
                />

                {/* House Procedure Swimlane */}
                <Swimlane
                  name={t('houseProcedure')}
                  color="gray"
                  bills={groupedBills.committee}
                  swimlaneType="committee"
                  stages={[
                    { label: t('stages.committeeReview'), position: 50 },
                    { label: t('stages.reportStage'), position: 75 },
                    { label: t('stages.royalAssent'), position: 95 },
                  ]}
                />

                {/* House of Commons Swimlane - Green Chamber */}
                <Swimlane
                  name={t('house')}
                  color="green"
                  bills={groupedBills.house}
                  swimlaneType="house"
                  stages={[
                    { label: t('stages.introduced'), position: 10 },
                    { label: t('stages.houseFirst'), position: 33 },
                    { label: t('stages.houseSecond'), position: 66 },
                    { label: t('stages.royalAssent'), position: 95 },
                  ]}
                />
              </div>
            )}
          </div>

          {/* Controls at bottom */}
          <div className="px-4 pb-4 pt-3 border-t border-subtle">
            {/* Activity slider control */}
            <div className="flex items-center gap-3 mb-2">
              <label htmlFor="bill-limit" className="text-xs text-secondary whitespace-nowrap">
                Show Top {billLimit} Most Active
              </label>
              <input
                id="bill-limit"
                type="range"
                min="3"
                max="50"
                step="1"
                value={billLimit}
                onChange={(e) => setBillLimit(Number(e.target.value))}
                className="flex-1 h-1.5 bg-secondary rounded-lg appearance-none cursor-pointer accent-accent-red"
              />
            </div>

            {/* Color legend */}
            <div className="flex flex-wrap gap-2 text-xs">
              <div className="flex items-center gap-1">
                <div className="w-2.5 h-2.5 rounded-sm bg-green-500 border border-green-400" />
                <span className="text-secondary text-xs">{t('legend.government')}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2.5 h-2.5 rounded-sm bg-amber-500 border border-amber-400" />
                <span className="text-secondary text-xs">{t('legend.privateMember')}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2.5 h-2.5 rounded-sm bg-red-500 border border-red-400" />
                <span className="text-secondary text-xs">{t('legend.senateGov')}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2.5 h-2.5 rounded-sm bg-orange-500 border border-orange-400" />
                <span className="text-secondary text-xs">{t('legend.senatePublic')}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}

interface SwimlaneProps {
  name: string;
  color: 'red' | 'green' | 'gray';
  bills: BillGanttData[];
  swimlaneType: 'house' | 'committee' | 'senate';
  stages: Array<{ label: string; position: number }>;
}

function Swimlane({ name, color, bills, swimlaneType, stages }: SwimlaneProps) {
  const bgColor =
    color === 'red'
      ? 'bg-red-500/10 border-red-500/30'
      : color === 'green'
        ? 'bg-green-500/10 border-green-500/30'
        : 'bg-secondary/5 border-secondary/30';

  const textColor =
    color === 'red'
      ? 'text-red-400'
      : color === 'green'
        ? 'text-green-400'
        : 'text-secondary';

  // Calculate grid positions for bills
  const billPositions = useMemo(() => assignBillsToGrid(bills, swimlaneType), [bills, swimlaneType]);

  return (
    <div className={`border rounded-md ${bgColor}`}>
      {/* Swimlane header */}
      <div className="px-2 py-1 flex items-center justify-between">
        <h3 className={`text-xs font-semibold uppercase tracking-wide ${textColor}`}>
          {name}
        </h3>
        <span className="text-xs text-secondary">
          {bills.length}
        </span>
      </div>

      {/* Swimlane track with columns */}
      <div className="relative h-32 pb-8 overflow-visible">
        {/* Stage column dividers and labels */}
        {stages.map((stage, index) => (
          <div
            key={stage.label}
            className="absolute top-0 bottom-0"
            style={{ left: `${stage.position}%` }}
          >
            {/* Vertical divider */}
            <div className="absolute top-0 bottom-8 w-px bg-secondary/50 -translate-x-1/2" />

            {/* Stage label at bottom */}
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2">
              <span className="text-[10px] font-semibold text-primary whitespace-nowrap">
                {stage.label}
              </span>
            </div>
          </div>
        ))}

        {/* Bill squares in grid */}
        {bills.map((bill) => {
          const pos = billPositions.get(`${bill.session}-${bill.number}`);
          if (!pos) return null;

          return (
            <BillSquare
              key={`${bill.session}-${bill.number}`}
              bill={bill}
              gridPosition={pos}
              swimlane={swimlaneType}
            />
          );
        })}

        {bills.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs text-tertiary italic">No bills in this stage</span>
          </div>
        )}
      </div>
    </div>
  );
}
