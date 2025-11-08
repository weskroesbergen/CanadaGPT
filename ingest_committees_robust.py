"""Ingest committee memberships from ourcommons.ca into Neo4j with robust error handling."""
import sys
from pathlib import Path
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from difflib import SequenceMatcher
import time
from requests.exceptions import ReadTimeout, ConnectionError

# Add fedmcp to path
sys.path.insert(0, str(Path.home() / "FedMCP/packages/fedmcp/src"))

from fedmcp.clients.committee_membership import CommitteeMembershipClient
from fedmcp.http import RateLimitedSession

# Load env
load_dotenv(Path.home() / "FedMCP/packages/data-pipeline/.env")

# Connect to Neo4j
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
)

print("=" * 80)
print("COMMITTEE MEMBERSHIP INGESTION (ROBUST VERSION)")
print("=" * 80)

# Committee codes to fetch
COMMITTEE_CODES = [
    "ACVA",  # Veterans Affairs
    "AGRI",  # Agriculture
    "CHPC",  # Canadian Heritage
    "CIIT",  # International Trade
    "CIMM",  # Immigration
    "ENVI",  # Environment
    "ETHI",  # Ethics
    "FAAE",  # Foreign Affairs
    "FINA",  # Finance
    "FOPO",  # Fisheries
    "HESA",  # Health
    "HUMA",  # Human Resources
    "INAN",  # Indigenous Affairs
    "INDU",  # Industry
    "JUST",  # Justice
    "LANG",  # Official Languages
    "NDDN",  # National Defence
    "OGGO",  # Government Operations
    "PACP",  # Public Accounts
    "PROC",  # Procedure and House Affairs
    "RNNR",  # Natural Resources
    "SECU",  # Public Safety
    "SRSR",  # Science and Research
    "TRAN",  # Transport
    "FEWO",  # Status of Women
]


def similarity_score(a: str, b: str) -> float:
    """Calculate similarity score between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_mp_by_name(session, member_name: str) -> str | None:
    """Find MP ID by name with fuzzy matching."""
    # Try exact match first
    result = session.run("""
        MATCH (mp:MP {name: $name})
        RETURN mp.id as mp_id
    """, name=member_name)

    record = result.single()
    if record:
        return record['mp_id']

    # Try fuzzy matching with all current MPs
    result = session.run("""
        MATCH (mp:MP)
        WHERE mp.current = true
        RETURN mp.id as mp_id, mp.name as mp_name
    """)

    best_match = None
    best_score = 0.8  # Minimum threshold

    for record in result:
        mp_name = record['mp_name']
        score = similarity_score(member_name, mp_name)
        if score > best_score:
            best_score = score
            best_match = record['mp_id']

    return best_match


def fetch_committee_with_retry(client, committee_code: str, max_retries: int = 3):
    """Fetch committee members with exponential backoff retry on timeout."""
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries}...")
            members = client.get_committee_members(committee_code)
            return members
        except (ReadTimeout, ConnectionError) as e:
            if attempt < max_retries - 1:
                wait_time = 10 * (2 ** attempt)  # 10s, 20s, 40s
                print(f"  ⚠️  Timeout on attempt {attempt + 1}. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                print(f"  ❌ Failed after {max_retries} attempts: {e}")
                raise


def ingest_committee_memberships():
    """Fetch and ingest committee memberships."""
    # Create client with very long timeout (180 seconds = 3 minutes)
    session_http = RateLimitedSession(default_timeout=180.0)
    client = CommitteeMembershipClient(session=session_http)

    total_members = 0
    total_matched = 0
    total_unmatched = 0
    total_relationships = 0
    failed_committees = []

    for idx, committee_code in enumerate(COMMITTEE_CODES, 1):
        print(f"\n{'='*80}")
        print(f"Processing committee {idx}/{len(COMMITTEE_CODES)}: {committee_code}")
        print(f"{'='*80}")

        try:
            # Fetch with retry logic
            members = fetch_committee_with_retry(client, committee_code, max_retries=3)
            print(f"✅ Fetched {len(members)} members")

            if not members:
                print(f"⚠️  No members found for {committee_code}")
                continue

            # Match members to MPs and create relationships
            with driver.session() as neo_session:
                matched_count = 0
                unmatched_count = 0

                # Track unique members (avoid duplicates)
                seen_members = set()

                for member in members:
                    # Skip duplicates
                    member_key = (member.name, member.role)
                    if member_key in seen_members:
                        continue
                    seen_members.add(member_key)

                    # Find matching MP
                    mp_id = find_mp_by_name(neo_session, member.name)

                    if mp_id:
                        # Create committee if it doesn't exist, then create SERVES_ON relationship
                        neo_session.run("""
                            MATCH (mp:MP {id: $mp_id})
                            MERGE (c:Committee {code: $code})
                            MERGE (mp)-[r:SERVES_ON]->(c)
                            SET r.role = $role
                        """, mp_id=mp_id, code=committee_code, role=member.role)

                        matched_count += 1
                        total_matched += 1
                        total_relationships += 1
                        print(f"  ✅ {member.name} → {mp_id} ({member.role})")
                    else:
                        unmatched_count += 1
                        total_unmatched += 1
                        print(f"  ❌ {member.name} ({member.role})")

                print(f"\n{committee_code} summary:")
                print(f"  Matched: {matched_count}")
                print(f"  Unmatched: {unmatched_count}")

                total_members += len(seen_members)

            # Add delay between committees to avoid overwhelming the server
            if idx < len(COMMITTEE_CODES):
                print(f"\nWaiting 5 seconds before next committee...")
                time.sleep(5)

        except Exception as e:
            print(f"❌ Error processing {committee_code}: {e}")
            failed_committees.append(committee_code)
            import traceback
            traceback.print_exc()
            # Continue with next committee
            continue

    print("\n" + "=" * 80)
    print("FINAL STATS")
    print("=" * 80)
    print(f"Total unique members processed: {total_members}")
    print(f"Successfully matched: {total_matched}")
    print(f"Unmatched: {total_unmatched}")
    print(f"Total relationships created: {total_relationships}")
    print(f"Failed committees: {len(failed_committees)}")

    if failed_committees:
        print(f"  {', '.join(failed_committees)}")

    # Verify relationships
    with driver.session() as session:
        result = session.run("""
            MATCH (mp:MP)-[r:SERVES_ON]->(c:Committee)
            RETURN count(r) as total_relationships
        """)
        db_count = result.single()['total_relationships']
        print(f"Verified relationships in DB: {db_count}")


if __name__ == "__main__":
    try:
        ingest_committee_memberships()
    finally:
        driver.close()

    print("\n✅ Committee membership ingestion complete!")
