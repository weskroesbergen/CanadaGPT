"""Clean up OpenParliament data from Neo4j before re-running sample imports.

This script removes all data that was imported from the OpenParliament PostgreSQL database,
allowing for a clean re-import with the fixed linking functions.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient

# Load environment
load_dotenv(Path(__file__).parent / "packages/data-pipeline/.env")

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

print("=" * 80)
print(f"{BLUE}CLEANING UP OPENPARLIAMENT DATA FROM NEO4J{RESET}")
print("=" * 80)
print()
print(f"{YELLOW}This will delete:{RESET}")
print("  • All Hansard Statement and Document nodes")
print("  • All BillText nodes")
print("  • All Candidacy nodes")
print("  • All politician contact info (email, phone, twitter)")
print("  • All related relationships (PART_OF, HAS_TEXT, RAN_IN, MADE_BY, MENTIONS)")
print()
print(f"{YELLOW}WARNING: This will NOT delete:{RESET}")
print("  • Politician nodes (base data)")
print("  • Bill nodes (base data)")
print("  • Other data imported through different mechanisms")
print()

# Connect to Neo4j
neo4j_client = Neo4jClient(
    uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    user=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "canadagpt2024")
)

print(f"{BLUE}Connected to Neo4j{RESET}")
print()

# Skip counting - just delete directly
print(f"{BLUE}1. Skipping count (data may not exist yet){RESET}")
print()

# Delete data
print(f"{BLUE}2. Deleting OpenParliament data...{RESET}")

# Delete Hansard data
print("   Deleting Statements and Documents...")
result = neo4j_client.run_query("""
    MATCH (s:Statement)
    DETACH DELETE s
    RETURN count(*) as deleted
""")
deleted_statements = result[0]['deleted'] if result else 0
print(f"      {GREEN}✓{RESET} Deleted {deleted_statements:,} Statements")

result = neo4j_client.run_query("""
    MATCH (d:Document)
    DELETE d
    RETURN count(*) as deleted
""")
deleted_documents = result[0]['deleted'] if result else 0
print(f"      {GREEN}✓{RESET} Deleted {deleted_documents:,} Documents")

# Delete BillText data
print("   Deleting BillTexts...")
result = neo4j_client.run_query("""
    MATCH (bt:BillText)
    DETACH DELETE bt
    RETURN count(*) as deleted
""")
deleted_bill_texts = result[0]['deleted'] if result else 0
print(f"      {GREEN}✓{RESET} Deleted {deleted_bill_texts:,} BillTexts")

# Delete Candidacy data
print("   Deleting Candidacies...")
result = neo4j_client.run_query("""
    MATCH (c:Candidacy)
    DETACH DELETE c
    RETURN count(*) as deleted
""")
deleted_candidacies = result[0]['deleted'] if result else 0
print(f"      {GREEN}✓{RESET} Deleted {deleted_candidacies:,} Candidacies")

# Clear politician enrichment data (but keep Politician nodes)
print("   Clearing politician contact info...")
result = neo4j_client.run_query("""
    MATCH (p:Politician)
    WHERE p.email IS NOT NULL OR p.phone IS NOT NULL OR p.twitter_id IS NOT NULL
       OR p.parl_id IS NOT NULL OR p.alternate_name IS NOT NULL
    REMOVE p.email, p.phone, p.twitter_id, p.parl_id, p.alternate_name
    RETURN count(p) as cleared
""")
cleared_politicians = result[0]['cleared'] if result else 0
print(f"      {GREEN}✓{RESET} Cleared contact info from {cleared_politicians:,} Politicians")

print()
print(f"{GREEN}{'=' * 80}")
print("✅ CLEANUP COMPLETE")
print(f"{'=' * 80}{RESET}")
print()
print(f"{BLUE}Summary:{RESET}")
print(f"  • Deleted {deleted_statements:,} Statement nodes")
print(f"  • Deleted {deleted_documents:,} Document nodes")
print(f"  • Deleted {deleted_bill_texts:,} BillText nodes")
print(f"  • Deleted {deleted_candidacies:,} Candidacy nodes")
print(f"  • Cleared {cleared_politicians:,} politician contact records")
print(f"  • Deleted all associated relationships")
print()
print(f"{BLUE}Next step:{RESET} Run test_sample_imports.py to test sample imports with fixed code")
print()

# Close connection
neo4j_client.close()
