"""Politician info ingestion from PostgreSQL to Neo4j.

This module imports politician biographical data from the OpenParliament PostgreSQL database
into the Neo4j graph database.

Data Sources:
- core_politician table (2,958 politicians)
- core_politicianinfo table (38,641 info records with 18 schema types)

The politician info is stored in an Entity-Attribute-Value (EAV) pattern where:
- schema: attribute type (email, phone, twitter_id, etc.)
- value: the actual value

Neo4j Schema:
    Updates to existing Politician nodes with additional properties

Example:
    >>> from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
    >>> from fedmcp_pipeline.utils.postgres_client import PostgresClient
    >>>
    >>> neo4j = Neo4jClient(uri="bolt://localhost:7687", user="neo4j", password="password")
    >>> postgres = PostgresClient(dbname="openparliament", user="fedmcp", password="password")
    >>>
    >>> # Sample import (10 politicians)
    >>> results = ingest_politician_info_sample(neo4j, postgres, limit=10)
    >>>
    >>> # Full import (all 2,958 politicians)
    >>> results = ingest_politician_info_full(neo4j, postgres)
"""

from typing import Optional, Dict, Any
from ..utils.neo4j_client import Neo4jClient
from ..utils.postgres_client import PostgresClient
from ..utils.progress import ProgressTracker, logger


def enrich_politician_info(
    neo4j_client: Neo4jClient,
    postgres_client: PostgresClient,
    batch_size: int = 500,
    limit: Optional[int] = None
) -> int:
    """
    Enrich existing Politician nodes with biographical info from PostgreSQL.

    Fetches politician info and adds properties like email, phone, twitter, website, etc.

    Args:
        neo4j_client: Neo4j client instance
        postgres_client: PostgreSQL client instance
        batch_size: Number of records to process per batch (default: 500)
        limit: Optional limit on total politicians to process

    Returns:
        Number of Politician nodes enriched
    """
    logger.info("Enriching politicians with biographical info...")

    # Fetch politicians with their info
    query = """
        SELECT
            p.id,
            p.slug,
            array_agg(
                jsonb_build_object(
                    'schema', pi.schema,
                    'value', pi.value
                )
            ) FILTER (WHERE pi.id IS NOT NULL) as info
        FROM core_politician p
        LEFT JOIN core_politicianinfo pi ON p.id = pi.politician_id
        GROUP BY p.id, p.slug
        ORDER BY p.id
    """

    if limit:
        query += f" LIMIT {limit}"

    politicians = postgres_client.execute_query(query)
    logger.info(f"Fetched {len(politicians):,} politicians from PostgreSQL")

    if not politicians:
        logger.warning("No politicians found in PostgreSQL")
        return 0

    # Process in batches
    progress = ProgressTracker(
        total=len(politicians),
        desc="Enriching Politician nodes",
        unit="politicians"
    )

    total_enriched = 0

    for i in range(0, len(politicians), batch_size):
        batch = politicians[i:i + batch_size]

        # Transform info array into property map
        for pol in batch:
            if pol.get("info"):
                # Convert array of schema/value pairs into a property dict
                props = {}
                for item in pol["info"]:
                    schema = item["schema"]
                    value = item["value"]

                    # Map schema names to Neo4j property names
                    # Use snake_case for consistency
                    props[schema] = value

                pol["properties"] = props
            else:
                pol["properties"] = {}

        # Update Politician nodes with info
        cypher = """
        UNWIND $politicians AS pol
        MATCH (p:Politician)
        WHERE p.postgres_id = pol.id
        SET p += pol.properties
        RETURN count(p) as enriched
        """

        result = neo4j_client.run_query(cypher, {"politicians": batch})
        enriched = result[0]["enriched"] if result else 0
        total_enriched += enriched

        progress.update(len(batch))

    progress.close()
    logger.info(f"✅ Enriched {total_enriched:,} Politician nodes")

    return total_enriched


def ingest_politician_info_sample(
    neo4j_client: Neo4jClient,
    postgres_client: PostgresClient,
    limit: int = 10
) -> Dict[str, int]:
    """
    Import a sample of politician info for testing.

    Args:
        neo4j_client: Neo4j client instance
        postgres_client: PostgreSQL client instance
        limit: Number of politicians to process (default: 10)

    Returns:
        Dictionary with counts:
            - politicians_enriched: Number of Politician nodes enriched
    """
    logger.info("=" * 80)
    logger.info(f"POLITICIAN INFO SAMPLE IMPORT ({limit} politicians)")
    logger.info("=" * 80)

    results = {}

    # Enrich politicians
    results["politicians_enriched"] = enrich_politician_info(
        neo4j_client,
        postgres_client,
        limit=limit
    )

    logger.info("=" * 80)
    logger.info("✅ POLITICIAN INFO SAMPLE IMPORT COMPLETE")
    logger.info("=" * 80)

    return results


def ingest_politician_info_full(
    neo4j_client: Neo4jClient,
    postgres_client: PostgresClient
) -> Dict[str, int]:
    """
    Import all politician info from PostgreSQL to Neo4j.

    This function enriches all 2,958 politician nodes with biographical info.

    Args:
        neo4j_client: Neo4j client instance
        postgres_client: PostgreSQL client instance

    Returns:
        Dictionary with counts:
            - politicians_enriched: Number of Politician nodes enriched
    """
    logger.info("=" * 80)
    logger.info("POLITICIAN INFO FULL IMPORT (2,958 politicians)")
    logger.info("=" * 80)

    results = {}

    # Enrich all politicians
    results["politicians_enriched"] = enrich_politician_info(
        neo4j_client,
        postgres_client,
        limit=None
    )

    logger.info("=" * 80)
    logger.info("✅ POLITICIAN INFO FULL IMPORT COMPLETE")
    logger.info("=" * 80)

    return results
