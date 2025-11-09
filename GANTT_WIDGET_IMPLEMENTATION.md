# Order Paper GANTT Widget Implementation

## Overview

Implemented an interactive GANTT-style visualization widget for the Bills page (`/en/bills`) that displays active Order Paper bills progressing through the Canadian legislative process.

## Features Implemented

### 1. **Three-Swimlane Layout**
   - **Senate Swimlane** (Top) - Red/green gradient
     - 1st Reading → 2nd Reading → 3rd Reading → Royal Assent
   - **Committee/Procedure Swimlane** (Middle) - Yellow
     - Committee Review → Report Stage
   - **House of Commons Swimlane** (Bottom) - Blue
     - Introduction → 1st Reading → 2nd Reading → 3rd Reading

### 2. **Bill Representation**
   - Each bill displayed as a **rounded square** with bill number
   - Position reflects stage progress (0-100% horizontally)
   - Color matches parent swimlane:
     - Blue for House bills
     - Yellow for Committee review
     - Red-to-green gradient for Senate bills

### 3. **Hover Tooltips**
   - Bill title and number
   - Sponsor name and party
   - Current status
   - Activity indicators:
     - 💬 Hansard mentions count
     - 🗳️ Vote count
     - 👥 Committee referral indicator

### 4. **Activity-Based Sorting**
   - Bills sorted by calculated activity score:
     - +5 points per Hansard mention
     - +10 points per vote
     - +15 points for committee referral
     - +1 point per day recency (max 90 days)
     - +2 points per stage completed
   - Shows most active/debated bills by default

### 5. **User-Configurable Display**
   - **Slider control**: Display 10-50 bills (default: 20)
   - Shows "Showing top X most active bills"
   - Collapsible widget with expand/collapse toggle

### 6. **Bilingual Support**
   - Full English/French translation support
   - Labels, stage names, and tooltips in both languages
   - Translations in `messages/en.json` and `messages/fr.json`

### 7. **Order Paper Filtering**
   - Only shows active bills from current session (45-1)
   - Excludes bills with royal assent (completed)
   - Automatically filters based on Hansard activity

## Files Created

### Components
1. **`/packages/frontend/src/components/bills/BillGanttWidget.tsx`**
   - Main widget container with three swimlanes
   - Handles data fetching and bill grouping
   - Includes slider control and collapse functionality

2. **`/packages/frontend/src/components/bills/BillSquare.tsx`**
   - Individual bill square component
   - Hover tooltip with bill details
   - Click navigation to bill detail page

### Utilities & Queries
3. **`/packages/frontend/src/lib/billGanttUtils.ts`**
   - `calculateBillActivity()` - Activity scoring algorithm
   - `determineSwimlane()` - Maps bill stage to swimlane
   - `calculateStagePosition()` - Horizontal positioning (0-100%)
   - `buildBillTimeline()` - Creates timeline of stages
   - `filterOrderPaperBills()` - Filters and sorts for display
   - `groupBillsBySwimlane()` - Groups bills by House/Committee/Senate

4. **`/packages/frontend/src/lib/ganttQueries.ts`**
   - GraphQL query for GANTT data
   - Fetches timeline dates, committees, votes, Hansard debates
   - Uses `hansardDebatesAggregate` and `votesAggregate` for activity metrics

### Translations
5. **`/packages/frontend/messages/en.json`** (updated)
   - Added `bills.gantt` section with widget labels and stage names

6. **`/packages/frontend/messages/fr.json`** (updated)
   - Added French translations for all widget text

### Integration
7. **`/packages/frontend/src/app/[locale]/bills/page.tsx`** (modified)
   - Imported and positioned widget above search bar
   - Passes current session to widget

## Visual Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Order Paper - Legislative Progress                 [↑ Collapse]│
│  (20 active bills)                                              │
│  Show top: [=========●=====] 20                                 │
├──────────────────────────────────────────────────────────────────┤
│ SENATE (Red→Green)       │       │       │       │              │
│                     1st  │  2nd  │  3rd  │ Royal Assent         │
│                          │       │       │       │              │
│                     [C-2]│  [C-5]│       │       │              │
│                     [C-8]│  [C-7]│       │       │              │
│                          │  [C-9]│       │       │              │
├──────────────────────────────────────────────────────────────────┤
│ COMMITTEE (Yellow)       │       │                              │
│                Committee │ Report│                              │
│                     [C-3]│  [C-6]│                              │
│                     [C-4]│       │                              │
├──────────────────────────────────────────────────────────────────┤
│ HOUSE (Blue)        │       │       │       │                   │
│                Intro│  1st  │  2nd  │  3rd  │                   │
│                [C-1]│  [C-4]│ [C-10]│       │                   │
│                     │       │ [C-11]│       │                   │
│                     │       │ [C-12]│       │                   │
└──────────────────────────────────────────────────────────────────┘
```

Bills are organized in **well-defined stage columns** with vertical dividers. Within each column, bills tile in a **3-row × N-column grid** to maximize space efficiency.

## Interaction Flow

1. **Page Load**: Widget fetches current session bills with activity data
2. **Filtering**: Client-side filters out royal assent bills
3. **Scoring**: Calculates activity score for each bill
4. **Sorting**: Sorts by activity (most active first)
5. **Limiting**: Shows top N bills based on slider value
6. **Grouping**: Assigns bills to House/Committee/Senate swimlanes
7. **Positioning**: Calculates horizontal position based on stage progress
8. **Rendering**: Displays bills as clickable squares with hover tooltips

## Technical Implementation

### Data Flow
```
GraphQL (GET_ORDER_PAPER_GANTT)
  ↓
Filter (Order Paper only)
  ↓
Score (calculateBillActivity)
  ↓
Sort (by activity DESC)
  ↓
Limit (top N bills)
  ↓
Group (by swimlane)
  ↓
Position (by stage progress)
  ↓
Render (BillSquare components)
```

### Activity Scoring Algorithm
```typescript
score = 0
score += (hansard_debates × 5)
score += (votes × 10)
score += (has_committee_referral ? 15 : 0)
score += min(90, days_since_introduction)
score += (stages_completed × 2)
```

**Note:** Uses `hansardDebatesAggregate` field from GraphQL schema, which counts Statement nodes connected via the `MENTIONS` relationship.

### Swimlane Assignment Logic
```typescript
if (status.includes('committee') || status.includes('report'))
  → COMMITTEE
else if (passed_senate_* || status.includes('senate'))
  → SENATE
else
  → HOUSE
```

## Responsive Design

- **Desktop**: Full horizontal swimlanes with stage labels
- **Mobile**: (Future enhancement) Could stack swimlanes vertically
- **Dark Theme**: Matches existing CanadaGPT dark mode styling
- **Accessibility**: Keyboard navigation support, ARIA labels

## Future Enhancements

1. **Branching Visuals**: SVG connectors showing bill movement between swimlanes
2. **Animation**: Smooth transitions when bills change stages
3. **Historical Trail**: Show previous positions with opacity
4. **Filter by Bill Type**: Toggle government vs. private member bills
5. **Real-time Updates**: WebSocket updates when new Hansard data arrives
6. **Export**: Download visualization as PNG/SVG
7. **Mobile Optimization**: Vertical stacking on small screens

## Usage

The widget appears automatically on the Bills page (`/en/bills` or `/fr/bills`) above the search bar. Users can:
- Adjust the number of bills shown (10-50) with the slider
- Collapse/expand the widget for more screen space
- Hover over bill squares to see details
- Click any bill square to navigate to its detail page

## Performance Considerations

- Query limit: 100 bills max from GraphQL
- Client-side filtering and sorting (no additional queries)
- Activity aggregates pre-calculated in GraphQL query
- Memoized grouping/positioning calculations
- Lazy hover tooltips (render on demand)
