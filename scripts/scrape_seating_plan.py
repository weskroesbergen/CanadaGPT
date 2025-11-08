#!/usr/bin/env python3
"""
Scrape House of Commons seating plan from ourcommons.ca

This script:
1. Fetches the floorplan page HTML
2. Extracts all seat buttons with aria-label (MP name) and data-person-id (PersonId)
3. Determines seat positions based on grid structure
4. Identifies government vs opposition benches
5. Outputs structured JSON file with complete seating layout

Output: seating_plan.json
"""

import re
import json
import urllib.request
from html.parser import HTMLParser
from typing import List, Dict, Optional

FLOORPLAN_URL = "https://www.ourcommons.ca/members/en/floorplan"


class SeatParser(HTMLParser):
    """HTML parser to extract seat information from floorplan page"""

    def __init__(self):
        super().__init__()
        self.seats: List[Dict] = []
        self.in_table = False
        self.in_caption = False
        self.current_caption = ""
        self.current_row_num = 0
        self.current_side = ""  # "left" (opposition) or "right" (government)
        self.seat_position = 0  # Position within the visual grid

    def handle_starttag(self, tag: str, attrs: List[tuple]):
        attrs_dict = dict(attrs)

        # Track table captions to determine side and row
        if tag == "caption":
            self.in_caption = True
            self.current_caption = ""

        # Extract seat buttons from gridview
        if tag == "button" and "floorplan-cell" in attrs_dict.get("class", ""):
            aria_label = attrs_dict.get("aria-label", "")
            data_person_id = attrs_dict.get("data-person-id", "")
            background_color = ""

            # Extract background color from style attribute
            style = attrs_dict.get("style", "")
            color_match = re.search(r'background-color:(#[0-9A-Fa-f]+)', style)
            if color_match:
                background_color = color_match.group(1)

            if aria_label and data_person_id:
                seat = {
                    "mp_name": aria_label.strip(),
                    "person_id": int(data_person_id),
                    "party_color": background_color,
                    "position_index": self.seat_position
                }
                self.seats.append(seat)
                self.seat_position += 1

    def handle_data(self, data: str):
        if self.in_caption:
            self.current_caption += data.strip()

    def handle_endtag(self, tag: str):
        if tag == "caption":
            self.in_caption = False
            # Determine side and row from caption text
            self._parse_caption(self.current_caption)

    def _parse_caption(self, caption: str):
        """Extract row number and side from table caption"""
        caption_lower = caption.lower()

        # Determine side
        if "speaker's left" in caption_lower or "speaker's chair" in caption_lower:
            self.current_side = "opposition"
        elif "speaker's right" in caption_lower:
            self.current_side = "government"

        # Extract row number
        if "first row" in caption_lower:
            self.current_row_num = 1
        elif "second row" in caption_lower:
            self.current_row_num = 2
        elif "third row" in caption_lower:
            self.current_row_num = 3
        elif "fourth row" in caption_lower:
            self.current_row_num = 4
        elif "fifth row" in caption_lower:
            self.current_row_num = 5
        elif "sixth row" in caption_lower:
            self.current_row_num = 6


def assign_visual_coordinates(seats: List[Dict]) -> List[Dict]:
    """
    Assign SVG coordinates to seats based on their layout.

    Layout:
    - Opposition (top): y = 60-380
    - Speaker (center): y = 400 (middle)
    - Government (bottom): y = 420-740

    Width: 1400px, seats distributed evenly in rows
    """
    # Use smaller spacing for compact layout
    SEATS_PER_ROW = 30
    ROW_HEIGHT = 53
    SEAT_WIDTH = 46

    # Opposition benches (rows 1-6) at top
    opposition_y_start = 60
    # Government benches (rows 1-6) at bottom
    government_y_start = 420
    # Speaker at center
    speaker_x = 700  # Center of 1400px width
    speaker_y = 400

    for i, seat in enumerate(seats):
        # Check if this is the Speaker (already marked by table parser)
        if seat.get("bench_section") == "speaker":
            seat["seat_visual_x"] = float(speaker_x)
            seat["seat_visual_y"] = float(speaker_y)
            continue

        # Determine row and column based on position
        row = i // SEATS_PER_ROW
        col = i % SEATS_PER_ROW

        # Calculate X coordinate (same for both sides)
        x = 100 + (col * SEAT_WIDTH)

        # First ~170 seats are opposition (top), rest are government (bottom)
        if i < 170:  # Rough split - opposition side
            y = opposition_y_start + (row * ROW_HEIGHT)
            if not seat.get("bench_section"):  # Only set if not already set
                seat["bench_section"] = "opposition"
            seat["seat_row"] = row + 1
        else:  # Government side
            y = government_y_start + ((row - 6) * ROW_HEIGHT)
            if not seat.get("bench_section"):
                seat["bench_section"] = "government"
            seat["seat_row"] = row - 5

        seat["seat_column"] = col + 1
        seat["seat_visual_x"] = float(x)
        seat["seat_visual_y"] = float(y)

    return seats


def parse_table_structure(html: str) -> Dict[str, any]:
    """
    Parse the table structure to get accurate row/side assignments
    Returns mapping of MP names to their row and side
    """
    mp_locations = {}

    # Find all table sections
    table_pattern = r'<caption[^>]*>(.*?)</caption>.*?<tbody>(.*?)</tbody>'
    tables = re.findall(table_pattern, html, re.DOTALL)

    for caption, tbody in tables:
        # Determine side and row from caption
        caption_lower = caption.lower()

        side = "unknown"

        # Check for Speaker first
        if "speaker's chair" in caption_lower or "in the speaker" in caption_lower:
            side = "speaker"
        elif "speaker's left" in caption_lower:
            side = "opposition"
        elif "speaker's right" in caption_lower:
            side = "government"

        # Extract row number
        row_num = 0
        if "first row" in caption_lower:
            row_num = 1
        elif "second row" in caption_lower:
            row_num = 2
        elif "third row" in caption_lower:
            row_num = 3
        elif "fourth row" in caption_lower:
            row_num = 4
        elif "fifth row" in caption_lower:
            row_num = 5
        elif "sixth row" in caption_lower:
            row_num = 6

        # Extract MP names from this table
        # Pattern: <td>name</td>
        name_pattern = r'<td>\s*(?:Hon\.\s+)?([A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)?)\s*</td>'
        mp_names = re.findall(name_pattern, tbody)

        for idx, name in enumerate(mp_names, 1):
            name_clean = re.sub(r'\s+', ' ', name.strip())
            mp_locations[name_clean] = {
                "side": side,
                "row": row_num if side != "speaker" else 0,
                "column": idx if side != "speaker" else 0
            }

    return mp_locations


def main():
    print(f"Fetching seating plan from {FLOORPLAN_URL}...")

    try:
        # Fetch the page
        with urllib.request.urlopen(FLOORPLAN_URL) as response:
            html = response.read().decode('utf-8')

        print(f"✓ Downloaded {len(html)} bytes")

        # Parse the table structure for accurate positioning
        print("Parsing table structure for row/side assignments...")
        mp_locations = parse_table_structure(html)
        print(f"✓ Found {len(mp_locations)} MPs in table structure")

        # Parse seats from gridview buttons
        print("Parsing seat buttons from gridview...")
        parser = SeatParser()
        parser.feed(html)

        print(f"✓ Found {len(parser.seats)} seats with PersonId")

        # Match seats to table locations
        print("Matching seats to table positions...")
        matched_count = 0
        speaker_identified = False
        for seat in parser.seats:
            mp_name = seat["mp_name"]
            if mp_name in mp_locations:
                loc = mp_locations[mp_name]
                seat["bench_section"] = loc["side"]
                seat["seat_row"] = loc["row"]
                seat["seat_column"] = loc["column"]
                matched_count += 1
                if loc["side"] == "speaker":
                    speaker_identified = True

        print(f"✓ Matched {matched_count} seats to table positions")

        # Fallback: Identify Speaker by name if table parsing didn't work
        if not speaker_identified:
            print("Table parsing didn't identify Speaker, using name matching...")
            # Common Speaker names to check
            speaker_candidates = ["Francis Scarpaleggia", "Greg Fergus"]
            for seat in parser.seats:
                if seat["mp_name"] in speaker_candidates:
                    seat["bench_section"] = "speaker"
                    seat["seat_row"] = 0
                    seat["seat_column"] = 0
                    speaker_identified = True
                    print(f"✓ Identified Speaker: {seat['mp_name']}")
                    break

        # Assign visual coordinates
        print("Calculating SVG coordinates...")
        seats = assign_visual_coordinates(parser.seats)

        # Add party mapping from colors
        party_colors = {
            "#002395": "Conservative",  # Blue
            "#D71920": "Liberal",       # Red
            "#33B2CC": "Bloc Québécois", # Light blue
            "#F37021": "NDP",           # Orange
            "#3D9B35": "Green Party",   # Green
        }

        for seat in seats:
            color = seat.get("party_color", "")
            seat["party_guess"] = party_colors.get(color, "Unknown")

        # Create output structure
        output = {
            "source_url": FLOORPLAN_URL,
            "total_seats": len(seats),
            "seats": seats
        }

        # Write to JSON file
        output_file = "seating_plan.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Seating plan saved to {output_file}")
        print(f"  Total seats: {len(seats)}")
        print(f"  Opposition: {sum(1 for s in seats if s.get('bench_section') == 'opposition')}")
        print(f"  Government: {sum(1 for s in seats if s.get('bench_section') == 'government')}")
        print(f"  Speaker: {sum(1 for s in seats if s.get('bench_section') == 'speaker')}")

        # Show sample
        print("\nSample seats:")
        for seat in seats[:3]:
            print(f"  - {seat['mp_name']} (ID: {seat['person_id']}, {seat.get('party_guess', 'Unknown')})")
            print(f"    Position: Row {seat.get('seat_row', '?')}, Col {seat.get('seat_column', '?')}, {seat.get('bench_section', 'unknown')}")

        return 0

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
