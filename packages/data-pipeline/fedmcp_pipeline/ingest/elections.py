"""Election candidacy ingestion from PostgreSQL to Neo4j.

This module imports election candidacy data from the OpenParliament PostgreSQL database
into the Neo4j graph database.

Data Source: elections_candidacy table (21,246 records)
- Election results for candidates across 52 elections
- Vote totals, percentages, and elected status
- Links to politicians, parties, ridings

Neo4j Schema:
    Nodes:
        - Candidacy: Individual candidacy records with election results

    Relationships:
        - (Politician)-[:RAN_IN]->(Candidacy): Links politicians to their candidacies
        - (Candidacy)-[:IN_ELECTION]->(Election): Links candidacy to election
        - (Candidacy)-[:IN_RIDING]->(Riding): Links candidacy to riding
        - (Candidacy)-[:FOR_PARTY]->(Party): Links candidacy to party

    Indexes:
        - Candidacy(id): Unique constraint
        - Candidacy(election_id, riding_id): Composite index for lookups

Example:
    >>> from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
    >>> from fedmcp_pipeline.utils.postgres_client import PostgresClient
    >>>
    >>> neo4j = Neo4jClient(uri="bolt://localhost:7687", user="neo4j", password="password")
    >>> postgres = PostgresClient(dbname="openparliament", user="fedmcp", password="password")
    >>>
    >>> # Sample import (50 candidacies)
    >>> results = ingest_elections_sample(neo4j, postgres, candidacy_limit=50)
    >>>
    >>> # Full import (all 21,246 candidacies)
    >>> results = ingest_elections_full(neo4j, postgres)
"""

from typing import Optional, Dict, Any, List
from ..utils.neo4j_client import Neo4jClient
from ..utils.postgres_client import PostgresClient
from ..utils.progress import ProgressTracker, logger


def create_candidacy_schema(neo4j_client: Neo4jClient) -> None:
    """
    Create Neo4j schema for election candidacies.

    Creates:
        - Unique constraint on Candidacy.id
        - Index on Candidacy.election_id
        - Index on Candidacy.riding_id
        - Composite index on election_id + riding_id

    Args:
        neo4j_client: Neo4j client instance
    """
    logger.info("Creating candidacy schema...")

    # Create unique constraint on id
    neo4j_client.run_query("""
        CREATE CONSTRAINT candidacy_id IF NOT EXISTS
        FOR (c:Candidacy) REQUIRE c.id IS UNIQUE
    """)

    # Create index on election_id
    neo4j_client.run_query("""
        CREATE INDEX candidacy_election IF NOT EXISTS
        FOR (c:Candidacy) ON (c.election_id)
    """)

    # Create index on riding_id
    neo4j_client.run_query("""
        CREATE INDEX candidacy_riding IF NOT EXISTS
        FOR (c:Candidacy) ON (c.riding_id)
    """)

    # Create index on elected status
    neo4j_client.run_query("""
        CREATE INDEX candidacy_elected IF NOT EXISTS
        FOR (c:Candidacy) ON (c.elected)
    """)

    logger.info("✅ Candidacy schema created")


def ingest_election_candidacies(
    neo4j_client: Neo4jClient,
    postgres_client: PostgresClient,
    batch_size: int = 1000,
    limit: Optional[int] = None
) -> int:
    """
    Ingest election candidacies from PostgreSQL to Neo4j.

    Creates Candidacy nodes with properties:
        - id: Primary key from PostgreSQL
        - candidate_id: Foreign key to core_politician
        - riding_id: Foreign key to core_riding
        - party_id: Foreign key to core_party
        - election_id: Foreign key to elections_election
        - votetotal: Number of votes received
        - elected: Boolean indicating if candidate won
        - votepercent: Percentage of vote received

    Args:
        neo4j_client: Neo4j client instance
        postgres_client: PostgreSQL client instance
        batch_size: Number of records to process per batch (default: 1000)
        limit: Optional limit on total records to import

    Returns:
        Number of Candidacy nodes created
    """
    logger.info("Ingesting election candidacies from PostgreSQL...")

    # Fetch candidacies
    query = """
        SELECT
            id,
            candidate_id,
            riding_id,
            party_id,
            election_id,
            votetotal,
            elected,
            votepercent
        FROM elections_candidacy
        ORDER BY election_id DESC, riding_id
    """

    if limit:
        query += f" LIMIT {limit}"

    candidacies = postgres_client.execute_query(query)
    logger.info(f"Fetched {len(candidacies):,} candidacies from PostgreSQL")

    if not candidacies:
        logger.warning("No candidacies found in PostgreSQL")
        return 0

    # Process in batches
    progress = ProgressTracker(
        total=len(candidacies),
        desc="Creating Candidacy nodes",
        unit="candidacies"
    )

    total_created = 0

    for i in range(0, len(candidacies), batch_size):
        batch = candidacies[i:i + batch_size]

        # Convert any Decimal values to float for Neo4j compatibility
        from decimal import Decimal
        batch = [{
            k: float(v) if isinstance(v, Decimal) else v
            for k, v in record.items()
        } for record in batch]

        # Create Candidacy nodes
        cypher = """
        UNWIND $candidacies AS cand
        MERGE (c:Candidacy {id: cand.id})
        SET c.candidate_id = cand.candidate_id,
            c.riding_id = cand.riding_id,
            c.party_id = cand.party_id,
            c.election_id = cand.election_id,
            c.votetotal = cand.votetotal,
            c.elected = cand.elected,
            c.votepercent = cand.votepercent
        RETURN count(c) as created
        """

        result = neo4j_client.run_query(cypher, {"candidacies": batch})
        created = result[0]["created"] if result else 0
        total_created += created

        progress.update(len(batch))

    progress.close()
    logger.info(f"✅ Created {total_created:,} Candidacy nodes")

    return total_created


def link_candidacies_to_politicians(
    neo4j_client: Neo4jClient,
    batch_size: int = 5000
) -> int:
    """
    Create RAN_IN relationships between Politicians and Candidacies.

    Matches politicians by their PostgreSQL candidate_id stored on Candidacy nodes.

    Args:
        neo4j_client: Neo4j client instance
        batch_size: Number of relationships to create per batch

    Returns:
        Number of RAN_IN relationships created
    """
    logger.info("Creating RAN_IN relationships...")

    # Get count of candidacies
    count_result = neo4j_client.run_query("""
        MATCH (c:Candidacy)
        RETURN count(c) as total
    """)
    total = count_result[0]["total"] if count_result else 0

    if total == 0:
        logger.warning("No Candidacy nodes found")
        return 0

    logger.info(f"Found {total:,} Candidacy nodes to link")

    # Create relationships in batches
    cypher = """
    MATCH (c:Candidacy)
    WHERE c.candidate_id IS NOT NULL
    WITH c LIMIT $batch_size

    MATCH (p:Politician)
    WHERE p.postgres_id = c.candidate_id

    MERGE (p)-[r:RAN_IN]->(c)
    RETURN count(r) as created
    """

    progress = ProgressTracker(
        total=total,
        desc="Creating RAN_IN relationships",
        unit="links"
    )

    total_created = 0
    processed = 0

    while processed < total:
        result = neo4j_client.run_query(cypher, {"batch_size": batch_size})
        created = result[0]["created"] if result else 0

        if created == 0:
            break  # No more relationships to create

        total_created += created
        processed += created
        progress.update(created)

    progress.close()
    logger.info(f"✅ Created {total_created:,} RAN_IN relationships")

    return total_created


def enrich_candidacy_metadata(
    neo4j_client: Neo4jClient,
    postgres_client: PostgresClient,
    batch_size: int = 500
) -> int:
    """
    Enrich Candidacy nodes with election, riding, and party metadata.

    Adds properties like:
        - election_date, election_name
        - riding_name, riding_province
        - party_name, party_short_name

    Args:
        neo4j_client: Neo4j client instance
        postgres_client: PostgreSQL client instance
        batch_size: Number of records to process per batch

    Returns:
        Number of Candidacy nodes enriched
    """
    logger.info("Enriching candidacies with metadata...")

    # Fetch candidacies with joined metadata
    query = """
        SELECT
            c.id,
            e.date as election_date,
            r.name_en as riding_name,
            r.province as riding_province,
            p.name_en as party_name,
            p.short_name_en as party_short_name
        FROM elections_candidacy c
        LEFT JOIN elections_election e ON c.election_id = e.id
        LEFT JOIN core_riding r ON c.riding_id = r.id
        LEFT JOIN core_party p ON c.party_id = p.id
        ORDER BY c.id
    """

    candidacies = postgres_client.execute_query(query)
    logger.info(f"Fetched {len(candidacies):,} candidacies with metadata")

    if not candidacies:
        logger.warning("No candidacies found in PostgreSQL")
        return 0

    # Process in batches
    progress = ProgressTracker(
        total=len(candidacies),
        desc="Enriching Candidacy nodes",
        unit="candidacies"
    )

    total_enriched = 0

    for i in range(0, len(candidacies), batch_size):
        batch = candidacies[i:i + batch_size]

        # Convert dates to ISO format
        for cand in batch:
            if cand.get("election_date"):
                cand["election_date"] = cand["election_date"].isoformat()

        # Update Candidacy nodes with metadata
        cypher = """
        UNWIND $candidacies AS cand
        MATCH (c:Candidacy {id: cand.id})
        SET c.election_date = date(cand.election_date),
            c.riding_name = cand.riding_name,
            c.riding_province = cand.riding_province,
            c.party_name = cand.party_name,
            c.party_short_name = cand.party_short_name
        RETURN count(c) as enriched
        """

        result = neo4j_client.run_query(cypher, {"candidacies": batch})
        enriched = result[0]["enriched"] if result else 0
        total_enriched += enriched

        progress.update(len(batch))

    progress.close()
    logger.info(f"✅ Enriched {total_enriched:,} Candidacy nodes with metadata")

    return total_enriched


def ingest_elections_sample(
    neo4j_client: Neo4jClient,
    postgres_client: PostgresClient,
    candidacy_limit: int = 50
) -> Dict[str, int]:
    """
    Import a sample of election candidacies for testing.

    This function imports a small subset of candidacies (default: 50) to validate
    the import process before running the full import.

    Args:
        neo4j_client: Neo4j client instance
        postgres_client: PostgreSQL client instance
        candidacy_limit: Number of candidacies to import (default: 50)

    Returns:
        Dictionary with counts:
            - candidacies: Number of Candidacy nodes created
            - ran_in_links: Number of RAN_IN relationships created
            - enriched: Number of candidacies enriched with metadata
    """
    logger.info("=" * 80)
    logger.info(f"ELECTIONS SAMPLE IMPORT ({candidacy_limit} candidacies)")
    logger.info("=" * 80)

    results = {}

    # Create schema
    create_candidacy_schema(neo4j_client)

    # Import candidacies
    results["candidacies"] = ingest_election_candidacies(
        neo4j_client,
        postgres_client,
        limit=candidacy_limit
    )

    # Link to politicians
    results["ran_in_links"] = link_candidacies_to_politicians(neo4j_client)

    # Enrich with metadata
    results["enriched"] = enrich_candidacy_metadata(
        neo4j_client,
        postgres_client
    )

    logger.info("=" * 80)
    logger.info("✅ ELECTIONS SAMPLE IMPORT COMPLETE")
    logger.info("=" * 80)

    return results


def ingest_elections_full(
    neo4j_client: Neo4jClient,
    postgres_client: PostgresClient
) -> Dict[str, int]:
    """
    Import all election candidacies from PostgreSQL to Neo4j.

    This function imports all 21,246 candidacies from the OpenParliament database.

    Args:
        neo4j_client: Neo4j client instance
        postgres_client: PostgreSQL client instance

    Returns:
        Dictionary with counts:
            - candidacies: Number of Candidacy nodes created
            - ran_in_links: Number of RAN_IN relationships created
            - enriched: Number of candidacies enriched with metadata
    """
    logger.info("=" * 80)
    logger.info("ELECTIONS FULL IMPORT (21,246 candidacies)")
    logger.info("=" * 80)

    results = {}

    # Create schema
    create_candidacy_schema(neo4j_client)

    # Import all candidacies
    results["candidacies"] = ingest_election_candidacies(
        neo4j_client,
        postgres_client,
        limit=None
    )

    # Link to politicians
    results["ran_in_links"] = link_candidacies_to_politicians(neo4j_client)

    # Enrich with metadata
    results["enriched"] = enrich_candidacy_metadata(
        neo4j_client,
        postgres_client
    )

    logger.info("=" * 80)
    logger.info("✅ ELECTIONS FULL IMPORT COMPLETE")
    logger.info("=" * 80)

    return results
