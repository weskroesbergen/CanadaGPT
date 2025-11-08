#!/usr/bin/env python3
"""
Import seating plan data into Neo4j

This script:
1. Reads seating_plan.json from scraper
2. Connects to Neo4j database
3. Matches PersonId to parl_mp_id in MP nodes
4. Updates MP nodes with seating coordinates
5. Reports matches, mismatches, and updates

Usage:
    python3 import_seating_plan.py [seating_plan.json]
"""

import json
import sys
import os
from neo4j import GraphDatabase

# Neo4j connection from environment variables
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


class SeatingPlanImporter:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        self.driver.close()

    def import_seating_plan(self, seating_file: str):
        """Import seating plan from JSON file"""
        print(f"Reading seating plan from {seating_file}...")

        with open(seating_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        seats = data.get('seats', [])
        print(f"✓ Loaded {len(seats)} seats")

        matched = 0
        updated = 0
        not_found = []
        errors = []

        with self.driver.session() as session:
            for i, seat in enumerate(seats, 1):
                try:
                    person_id = seat['person_id']
                    mp_name = seat['mp_name']

                    # Try to match by parl_mp_id first, then by name
                    result = session.run("""
                        MATCH (mp:MP)
                        WHERE mp.parl_mp_id = $person_id
                           OR mp.name = $mp_name
                        RETURN mp.id as id, mp.name as name, mp.parl_mp_id as parl_mp_id
                        LIMIT 1
                    """, person_id=person_id, mp_name=mp_name)

                    record = result.single()

                    if record:
                        matched += 1
                        mp_id = record['id']
                        db_name = record['name']
                        db_parl_id = record['parl_mp_id']

                        # Update the MP node with seating information
                        update_result = session.run("""
                            MATCH (mp:MP {id: $mp_id})
                            SET mp.parl_mp_id = $person_id,
                                mp.seat_row = $seat_row,
                                mp.seat_column = $seat_column,
                                mp.bench_section = $bench_section,
                                mp.seat_visual_x = $seat_visual_x,
                                mp.seat_visual_y = $seat_visual_y
                            RETURN mp.id as id
                        """,
                            mp_id=mp_id,
                            person_id=person_id,
                            seat_row=seat.get('seat_row'),
                            seat_column=seat.get('seat_column'),
                            bench_section=seat.get('bench_section'),
                            seat_visual_x=seat.get('seat_visual_x'),
                            seat_visual_y=seat.get('seat_visual_y')
                        )

                        if update_result.single():
                            updated += 1
                            if i <= 5 or i % 50 == 0:
                                print(f"  [{i}/{len(seats)}] Updated: {mp_name} (ID: {person_id}) → {db_name}")
                    else:
                        not_found.append({
                            'name': mp_name,
                            'person_id': person_id
                        })
                        if len(not_found) <= 10:
                            print(f"  ⚠ Not found: {mp_name} (PersonId: {person_id})")

                except Exception as e:
                    errors.append({
                        'name': mp_name,
                        'person_id': person_id,
                        'error': str(e)
                    })
                    print(f"  ✗ Error processing {mp_name}: {e}")

        # Print summary
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Total seats in file:     {len(seats)}")
        print(f"Matched to MPs:          {matched}")
        print(f"Updated in database:     {updated}")
        print(f"Not found in database:   {len(not_found)}")
        print(f"Errors:                  {len(errors)}")

        if not_found:
            print(f"\n⚠ {len(not_found)} MPs from seating plan not found in database:")
            for mp in not_found[:10]:
                print(f"  - {mp['name']} (PersonId: {mp['person_id']})")
            if len(not_found) > 10:
                print(f"  ... and {len(not_found) - 10} more")

        if errors:
            print(f"\n✗ {len(errors)} errors occurred:")
            for err in errors[:5]:
                print(f"  - {err['name']}: {err['error']}")

        print("\n✓ Seating plan import complete!")

        return {
            'total': len(seats),
            'matched': matched,
            'updated': updated,
            'not_found': len(not_found),
            'errors': len(errors)
        }

    def verify_import(self):
        """Verify that MPs have seating data"""
        print("\nVerifying import...")

        with self.driver.session() as session:
            # Count MPs with seating data
            result = session.run("""
                MATCH (mp:MP)
                WHERE mp.seat_row IS NOT NULL
                RETURN count(mp) as count
            """)
            count = result.single()['count']

            print(f"✓ {count} MPs have seating coordinates")

            # Show sample
            result = session.run("""
                MATCH (mp:MP)
                WHERE mp.seat_row IS NOT NULL
                RETURN mp.name as name,
                       mp.party as party,
                       mp.parl_mp_id as person_id,
                       mp.seat_row as row,
                       mp.seat_column as col,
                       mp.bench_section as section
                ORDER BY mp.seat_row, mp.seat_column
                LIMIT 5
            """)

            print("\nSample MPs with seating data:")
            for record in result:
                print(f"  - {record['name']} ({record['party']})")
                print(f"    PersonId: {record['person_id']}, Row {record['row']}, Col {record['col']}, {record['section']}")


def main():
    # Get seating plan file from args or use default
    seating_file = sys.argv[1] if len(sys.argv) > 1 else "seating_plan.json"

    if not os.path.exists(seating_file):
        print(f"✗ Error: Seating plan file not found: {seating_file}")
        print("\nRun scrape_seating_plan.py first to generate the file.")
        return 1

    print("="*60)
    print("SEATING PLAN IMPORTER")
    print("="*60)
    print(f"Neo4j URI:      {NEO4J_URI}")
    print(f"Neo4j User:     {NEO4J_USERNAME}")
    print(f"Seating file:   {seating_file}")
    print("="*60)
    print()

    try:
        importer = SeatingPlanImporter(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

        # Import seating plan
        stats = importer.import_seating_plan(seating_file)

        # Verify the import
        importer.verify_import()

        importer.close()

        # Return error code if there were issues
        if stats['not_found'] > 20 or stats['errors'] > 5:
            print("\n⚠ Warning: Significant number of mismatches or errors")
            return 1

        return 0

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
