"""Bill text ingestion from PostgreSQL to Neo4j.

This module imports bill text data from the OpenParliament PostgreSQL database
into the Neo4j graph database.

Data Source: bills_billtext table (5,280 records)
- Full text of bills in English and French
- Bill summaries
- Links to bills_bill table

Neo4j Schema:
    Nodes:
        - BillText: Full text and summaries of bills

    Relationships:
        - (Bill)-[:HAS_TEXT]->(BillText): Links bills to their full text

    Indexes:
        - BillText(id): Unique constraint
        - BillText(docid): Index for lookups
        - Full-text index on text_en, text_fr, summary_en

Example:
    >>> from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
    >>> from fedmcp_pipeline.utils.postgres_client import PostgresClient
    >>>
    >>> neo4j = Neo4jClient(uri="bolt://localhost:7687", user="neo4j", password="password")
    >>> postgres = PostgresClient(dbname="openparliament", user="fedmcp", password="password")
    >>>
    >>> # Sample import (10 bill texts)
    >>> results = ingest_bill_text_sample(neo4j, postgres, text_limit=10)
    >>>
    >>> # Full import (all 5,280 bill texts)
    >>> results = ingest_bill_text_full(neo4j, postgres)
"""

from typing import Optional, Dict, Any, List
from ..utils.neo4j_client import Neo4jClient
from ..utils.postgres_client import PostgresClient
from ..utils.progress import ProgressTracker, logger


def create_bill_text_schema(neo4j_client: Neo4jClient) -> None:
    """
    Create Neo4j schema for bill texts.

    Creates:
        - Unique constraint on BillText.id
        - Index on BillText.docid
        - Full-text index on text_en
        - Full-text index on text_fr
        - Full-text index on summary_en

    Args:
        neo4j_client: Neo4j client instance
    """
    logger.info("Creating bill text schema...")

    # Create unique constraint on id
    neo4j_client.run_query("""
        CREATE CONSTRAINT bill_text_id IF NOT EXISTS
        FOR (bt:BillText) REQUIRE bt.id IS UNIQUE
    """)

    # Create index on docid
    neo4j_client.run_query("""
        CREATE INDEX bill_text_docid IF NOT EXISTS
        FOR (bt:BillText) ON (bt.docid)
    """)

    # Create full-text indexes
    try:
        neo4j_client.run_query("""
            CREATE FULLTEXT INDEX bill_text_en IF NOT EXISTS
            FOR (bt:BillText) ON EACH [bt.text_en]
        """)
    except Exception as e:
        logger.warning(f"Full-text index bill_text_en may already exist: {e}")

    try:
        neo4j_client.run_query("""
            CREATE FULLTEXT INDEX bill_text_fr IF NOT EXISTS
            FOR (bt:BillText) ON EACH [bt.text_fr]
        """)
    except Exception as e:
        logger.warning(f"Full-text index bill_text_fr may already exist: {e}")

    try:
        neo4j_client.run_query("""
            CREATE FULLTEXT INDEX bill_text_summary IF NOT EXISTS
            FOR (bt:BillText) ON EACH [bt.summary_en]
        """)
    except Exception as e:
        logger.warning(f"Full-text index bill_text_summary may already exist: {e}")

    logger.info("✅ Bill text schema created")


def ingest_bill_texts(
    neo4j_client: Neo4jClient,
    postgres_client: PostgresClient,
    batch_size: int = 1000,
    limit: Optional[int] = None
) -> int:
    """
    Ingest bill texts from PostgreSQL to Neo4j.

    Creates BillText nodes with properties:
        - id: Primary key from PostgreSQL
        - bill_id: Foreign key to bills_bill
        - docid: Document ID
        - text_en: Full text in English
        - text_fr: Full text in French
        - summary_en: Summary in English
        - created: Timestamp when text was created

    Args:
        neo4j_client: Neo4j client instance
        postgres_client: PostgreSQL client instance
        batch_size: Number of records to process per batch (default: 1000)
        limit: Optional limit on total records to import

    Returns:
        Number of BillText nodes created
    """
    logger.info("Ingesting bill texts from PostgreSQL...")

    # Fetch bill texts
    query = """
        SELECT
            id,
            bill_id,
            docid,
            created,
            text_en,
            text_fr,
            summary_en
        FROM bills_billtext
        ORDER BY id
    """

    if limit:
        query += f" LIMIT {limit}"

    bill_texts = postgres_client.execute_query(query)
    logger.info(f"Fetched {len(bill_texts):,} bill texts from PostgreSQL")

    if not bill_texts:
        logger.warning("No bill texts found in PostgreSQL")
        return 0

    # Process in batches
    progress = ProgressTracker(
        total=len(bill_texts),
        desc="Creating BillText nodes",
        unit="texts"
    )

    total_created = 0

    for i in range(0, len(bill_texts), batch_size):
        batch = bill_texts[i:i + batch_size]

        # Convert timestamps to ISO format
        for text in batch:
            if text.get("created"):
                text["created"] = text["created"].isoformat()

        # Create BillText nodes
        cypher = """
        UNWIND $bill_texts AS bt
        MERGE (text:BillText {id: bt.id})
        SET text.bill_id = bt.bill_id,
            text.docid = bt.docid,
            text.created = datetime(bt.created),
            text.text_en = bt.text_en,
            text.text_fr = bt.text_fr,
            text.summary_en = bt.summary_en
        RETURN count(text) as created
        """

        result = neo4j_client.run_query(cypher, {"bill_texts": batch})
        created = result[0]["created"] if result else 0
        total_created += created

        progress.update(len(batch))

    progress.close()
    logger.info(f"✅ Created {total_created:,} BillText nodes")

    return total_created


def link_texts_to_bills(
    neo4j_client: Neo4jClient,
    batch_size: int = 5000
) -> int:
    """
    Create HAS_TEXT relationships between Bills and BillTexts.

    Matches bills by their PostgreSQL bill_id stored on BillText nodes.

    Args:
        neo4j_client: Neo4j client instance
        batch_size: Number of relationships to create per batch

    Returns:
        Number of HAS_TEXT relationships created
    """
    logger.info("Creating HAS_TEXT relationships...")

    # Get count of bill texts
    count_result = neo4j_client.run_query("""
        MATCH (bt:BillText)
        RETURN count(bt) as total
    """)
    total = count_result[0]["total"] if count_result else 0

    if total == 0:
        logger.warning("No BillText nodes found")
        return 0

    logger.info(f"Found {total:,} BillText nodes to link")

    # Create relationships in batches
    cypher = """
    MATCH (bt:BillText)
    WHERE bt.bill_id IS NOT NULL
    WITH bt LIMIT $batch_size

    MATCH (b:Bill)
    WHERE b.postgres_id = bt.bill_id

    MERGE (b)-[r:HAS_TEXT]->(bt)
    RETURN count(r) as created
    """

    progress = ProgressTracker(
        total=total,
        desc="Creating HAS_TEXT relationships",
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
    logger.info(f"✅ Created {total_created:,} HAS_TEXT relationships")

    return total_created


def ingest_bill_text_sample(
    neo4j_client: Neo4jClient,
    postgres_client: PostgresClient,
    text_limit: int = 10
) -> Dict[str, int]:
    """
    Import a sample of bill texts for testing.

    This function imports a small subset of bill texts (default: 10) to validate
    the import process before running the full import.

    Args:
        neo4j_client: Neo4j client instance
        postgres_client: PostgreSQL client instance
        text_limit: Number of bill texts to import (default: 10)

    Returns:
        Dictionary with counts:
            - bill_texts: Number of BillText nodes created
            - has_text_links: Number of HAS_TEXT relationships created
    """
    logger.info("=" * 80)
    logger.info(f"BILL TEXT SAMPLE IMPORT ({text_limit} texts)")
    logger.info("=" * 80)

    results = {}

    # Create schema
    create_bill_text_schema(neo4j_client)

    # Import bill texts
    results["bill_texts"] = ingest_bill_texts(
        neo4j_client,
        postgres_client,
        limit=text_limit
    )

    # Link to bills
    results["has_text_links"] = link_texts_to_bills(neo4j_client)

    logger.info("=" * 80)
    logger.info("✅ BILL TEXT SAMPLE IMPORT COMPLETE")
    logger.info("=" * 80)

    return results


def ingest_bill_text_full(
    neo4j_client: Neo4jClient,
    postgres_client: PostgresClient
) -> Dict[str, int]:
    """
    Import all bill texts from PostgreSQL to Neo4j.

    This function imports all 5,280 bill texts from the OpenParliament database.

    Args:
        neo4j_client: Neo4j client instance
        postgres_client: PostgreSQL client instance

    Returns:
        Dictionary with counts:
            - bill_texts: Number of BillText nodes created
            - has_text_links: Number of HAS_TEXT relationships created
    """
    logger.info("=" * 80)
    logger.info("BILL TEXT FULL IMPORT (5,280 texts)")
    logger.info("=" * 80)

    results = {}

    # Create schema
    create_bill_text_schema(neo4j_client)

    # Import all bill texts
    results["bill_texts"] = ingest_bill_texts(
        neo4j_client,
        postgres_client,
        limit=None
    )

    # Link to bills
    results["has_text_links"] = link_texts_to_bills(neo4j_client)

    logger.info("=" * 80)
    logger.info("✅ BILL TEXT FULL IMPORT COMPLETE")
    logger.info("=" * 80)

    return results
