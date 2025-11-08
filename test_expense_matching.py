#!/usr/bin/env python3
"""Test expense name matching logic."""

import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "fedmcp" / "src"))

from fedmcp.clients.expenditure import MPExpenditureClient

print("=" * 80)
print("TESTING EXPENSE NAME MATCHING")
print("=" * 80)

# Get expense data for FY2026 Q1
expense_client = MPExpenditureClient()
try:
    print("\nFetching FY2026 Q1 expense data...")
    summary = expense_client.get_quarterly_summary(2026, 1)
    print(f"Found {len(summary)} MP expense records\n")

    # Look for Anita Anand
    print("Searching for 'Anand' in expense data...")
    for mp_exp in summary:
        if "Anand" in mp_exp.name or "anand" in mp_exp.name.lower():
            print(f"\nFound: '{mp_exp.name}'")
            print(f"  Total: ${mp_exp.total:,.2f}")

            # Show what the normalized name would be
            if "," in mp_exp.name:
                parts = mp_exp.name.split(",")
                if len(parts) == 2:
                    last_name = parts[0].strip()
                    first_name = parts[1].strip()
                    normalized = f"{first_name} {last_name}"
                    print(f"  Normalized to: '{normalized}'")
                    print(f"  Lowercase key: '{normalized.lower()}'")

            # The database has:
            # ID: anita-anand, Name: Anita Anand, Given: Anita, Family: Anand
            print(f"  Should match: 'anita anand' (database has 'Anita Anand')")

            db_match = "anita anand"
            csv_match = normalized.lower() if "," in mp_exp.name else mp_exp.name.lower()

            if db_match == csv_match:
                print(f"  ✅ MATCH!")
            else:
                print(f"  ❌ NO MATCH - DB: '{db_match}' vs CSV: '{csv_match}'")

    # Show first 5 expense records to see the format
    print("\n" + "-" * 80)
    print("Sample expense records (first 5):")
    for mp_exp in summary[:5]:
        # Normalize the name
        if "," in mp_exp.name:
            parts = mp_exp.name.split(",")
            if len(parts) == 2:
                last_name = parts[0].strip()
                first_name = parts[1].strip()
                normalized = f"{first_name} {last_name}"
            else:
                normalized = mp_exp.name.strip()
        else:
            normalized = mp_exp.name.strip()

        print(f"\n  CSV Name: '{mp_exp.name}'")
        print(f"  Normalized: '{normalized}'")
        print(f"  Lowercase Key: '{normalized.lower()}'")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
