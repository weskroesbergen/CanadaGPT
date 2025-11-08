"""Financial data ingestion: MP expenses, contracts, grants, donations."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add fedmcp package to path
FEDMCP_PATH = Path(__file__).parent.parent.parent.parent / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.expenditure import MPExpenditureClient

from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger


def ingest_financial_data(neo4j_client: Neo4jClient, batch_size: int = 10000) -> Dict[str, int]:
    """
    Ingest financial data: MP expenses, contracts, grants, donations.

    Args:
        neo4j_client: Neo4j client
        batch_size: Batch size for operations

    Returns:
        Dict with counts of created entities
    """
    logger.info("=" * 60)
    logger.info("FINANCIAL DATA INGESTION")
    logger.info("=" * 60)

    stats = {}

    # Build MP name -> ID mapping from database
    logger.info("Building MP name -> ID mapping...")
    mp_mapping = {}
    mp_query_result = neo4j_client.run_query("""
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
    logger.info(f"Mapped {len(mp_mapping):,} MP names to IDs")

    # 1. MP Expenses
    logger.info("Fetching MP expenses...")
    expense_client = MPExpenditureClient()

    # Get expenses for recent quarters (2024-2025)
    expenses_data = []
    skipped_count = 0
    for fiscal_year in [2024, 2025, 2026]:
        for quarter in [1, 2, 3, 4]:
            try:
                logger.debug(f"Fetching FY {fiscal_year} Q{quarter}...")
                summary = expense_client.get_quarterly_summary(fiscal_year, quarter)

                for mp_expenses in summary:
                    # Skip vacant seats
                    if mp_expenses.name == "Vacant":
                        continue

                    # Parse name from "LastName, FirstName" format to "FirstName LastName"
                    # Example: "Aboultaif,  Ziad" -> "Ziad Aboultaif"
                    # Also strip honorifics like "Hon.", "Dr.", "Rt. Hon.", etc.
                    if "," in mp_expenses.name:
                        parts = mp_expenses.name.split(",")
                        if len(parts) == 2:
                            last_name = parts[0].strip()
                            first_name = parts[1].strip()
                            normalized_name = f"{first_name} {last_name}"
                        else:
                            normalized_name = mp_expenses.name.strip()
                    else:
                        normalized_name = mp_expenses.name.strip()

                    # Strip honorifics/titles from the name
                    # Common titles: "Hon.", "Rt. Hon.", "Dr.", "Rev.", "Prof."
                    honorifics = ["Hon.", "Rt. Hon.", "Dr.", "Rev.", "Prof.", "Mr.", "Mrs.", "Ms.", "Miss"]
                    for honorific in honorifics:
                        normalized_name = normalized_name.replace(honorific, "").strip()
                    # Clean up extra spaces
                    normalized_name = " ".join(normalized_name.split())

                    # Look up MP ID from name
                    mp_name_key = normalized_name.lower()
                    mp_id = mp_mapping.get(mp_name_key)

                    if not mp_id:
                        logger.debug(f"Could not find MP ID for: {mp_expenses.name} (normalized: {normalized_name})")
                        skipped_count += 1
                        continue

                    # Create separate expense records for each category
                    categories = [
                        ("salaries", mp_expenses.salaries, "Staff salaries and benefits"),
                        ("travel", mp_expenses.travel, "Travel expenses"),
                        ("hospitality", mp_expenses.hospitality, "Hospitality and events"),
                        ("contracts", mp_expenses.contracts, "Contract services"),
                    ]

                    for category, amount, description in categories:
                        if amount > 0:  # Only create records for non-zero expenses
                            expense_props = {
                                "id": f"exp-{mp_id}-{fiscal_year}-q{quarter}-{category}",
                                "mp_id": mp_id,
                                "fiscal_year": fiscal_year,
                                "quarter": quarter,
                                "category": category,
                                "amount": amount,
                                "description": description,
                                "updated_at": datetime.utcnow().isoformat(),
                            }
                            expenses_data.append(expense_props)

            except Exception as e:
                logger.warning(f"Could not fetch FY {fiscal_year} Q{quarter}: {e}")
                continue

    logger.info(f"Found {len(expenses_data):,} expense records ({skipped_count} MPs skipped due to name mismatch)")

    if expenses_data:
        stats["expenses"] = neo4j_client.batch_merge_nodes("Expense", expenses_data, merge_keys=["id"], batch_size=batch_size)
        logger.info(f"Created/updated {stats['expenses']:,} expense nodes")

        # Create INCURRED relationships between MPs and Expenses
        logger.info("Creating INCURRED relationships...")
        rel_query = """
        MATCH (e:Expense)
        MATCH (m:MP {id: e.mp_id})
        MERGE (m)-[:INCURRED]->(e)
        """
        neo4j_client.run_query(rel_query)
        logger.info("✅ Created INCURRED relationships")
    else:
        stats["expenses"] = 0

    # TODO: Contracts, grants, donations (requires additional data sources)
    stats["contracts"] = 0
    stats["grants"] = 0
    stats["donations"] = 0

    logger.info("=" * 60)
    logger.success("✅ FINANCIAL DATA INGESTION COMPLETE")
    logger.info(f"Expenses: {stats['expenses']:,}")
    logger.info(f"Contracts: {stats['contracts']:,} (TODO)")
    logger.info(f"Grants: {stats['grants']:,} (TODO)")
    logger.info(f"Donations: {stats['donations']:,} (TODO)")
    logger.info("=" * 60)

    return stats
