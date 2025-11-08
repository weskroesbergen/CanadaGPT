#!/usr/bin/env python3
"""Investigate name mismatch between expense CSV and MP database."""

import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "fedmcp" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp.clients.expenditure import MPExpenditureClient
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient

# Connect to Neo4j
config = type('Config', (), {
    'neo4j_uri': 'bolt://localhost:7687',
    'neo4j_user': 'neo4j',
    'neo4j_password': 'canadagpt2024'
})()

client = Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password)

# Get MPs from database
print("=" * 80)
print("INVESTIGATING NAME MISMATCH")
print("=" * 80)

# Get Anita Anand specifically
print("\n1. Checking Anita Anand in database:")
anita_query = """
MATCH (m:MP)
WHERE m.name CONTAINS 'Anand' OR m.id CONTAINS 'anand'
RETURN m.id, m.name, m.given_name, m.family_name, m.riding
"""
anita_results = client.run_query(anita_query)
for record in anita_results:
    print(f"  ID: {record['id']}")
    print(f"  Name: {record['name']}")
    print(f"  Given: {record.get('given_name')}")
    print(f"  Family: {record.get('family_name')}")
    print(f"  Riding: {record.get('riding')}")
    print()

# Get sample of MP names from database
print("\n2. Sample MP names from database (first 10):")
sample_query = """
MATCH (m:MP)
RETURN m.id, m.name, m.given_name, m.family_name
LIMIT 10
"""
sample_results = client.run_query(sample_query)
for record in sample_results:
    print(f"  {record['name']:40} (ID: {record['id']:30} Given: {record.get('given_name', 'N/A'):15} Family: {record.get('family_name', 'N/A')})")

# Get expense data for FY2026 Q1
print("\n3. Fetching expense data for FY2026 Q1:")
expense_client = MPExpenditureClient()
try:
    summary = expense_client.get_quarterly_summary(2026, 1)
    print(f"  Found {len(summary)} MP expense records")

    # Look for Anita Anand in expense data
    print("\n4. Looking for Anand in expense data:")
    for mp_exp in summary:
        if "Anand" in mp_exp.name or "anand" in mp_exp.name.lower():
            print(f"  Found: '{mp_exp.name}' - Total: ${mp_exp.total:,.2f}")

            # Show what the normalized name would be
            if "," in mp_exp.name:
                parts = mp_exp.name.split(",")
                if len(parts) == 2:
                    last_name = parts[0].strip()
                    first_name = parts[1].strip()
                    normalized = f"{first_name} {last_name}"
                    print(f"    Normalized to: '{normalized}'")

    # Show first 10 expense names to see format
    print("\n5. Sample expense names (first 10):")
    for mp_exp in summary[:10]:
        # Parse name
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

        print(f"  CSV: '{mp_exp.name:40}' -> Normalized: '{normalized}'")

except Exception as e:
    print(f"  Error: {e}")

# Build mapping like the import does
print("\n6. Building name mapping (like import does):")
mp_mapping = {}
mp_query_result = client.run_query("""
    MATCH (m:MP)
    RETURN m.id AS id, m.name AS name, m.given_name AS given_name, m.family_name AS family_name
""")
for record in mp_query_result:
    mp_id = record.get("id")
    name = record.get("name")
    # Store by full name
    if name:
        mp_mapping[name.lower()] = mp_id
    # Also store by "FirstName LastName" format for better matching
    given = record.get("given_name", "")
    family = record.get("family_name", "")
    if given and family:
        mp_mapping[f"{given} {family}".lower()] = mp_id

print(f"  Created mapping with {len(mp_mapping)} entries")

# Test Anita Anand lookup
print("\n7. Testing Anita Anand lookup:")
test_names = [
    "Anand, Anita",
    "Anand,  Anita",  # with extra space
    "Anita Anand",
]
for test_name in test_names:
    # Normalize like the code does
    if "," in test_name:
        parts = test_name.split(",")
        if len(parts) == 2:
            last_name = parts[0].strip()
            first_name = parts[1].strip()
            normalized = f"{first_name} {last_name}"
        else:
            normalized = test_name.strip()
    else:
        normalized = test_name.strip()

    mp_id = mp_mapping.get(normalized.lower())
    status = "✅ FOUND" if mp_id else "❌ NOT FOUND"
    print(f"  '{test_name}' -> '{normalized}' -> {status} (ID: {mp_id})")

# Check what keys exist for "anand"
print("\n8. All mapping keys containing 'anand':")
for key in sorted(mp_mapping.keys()):
    if 'anand' in key:
        print(f"  '{key}' -> {mp_mapping[key]}")

client.close()
print("\n" + "=" * 80)
