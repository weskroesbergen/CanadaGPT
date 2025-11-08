#!/usr/bin/env python3
"""
Import 2023-present Hansard data from PostgreSQL to Neo4j.

This script:
1. Imports all documents from 2023-01-01 onwards
2. Imports all statements from 2023-01-01 onwards (~400K statements)
3. Creates PART_OF relationships (Statement → Document)
4. Creates MADE_BY relationships (Statement → MP)
5. Creates MENTIONS relationships (Statement → Bill)
6. Validates results and reports statistics
"""

import os
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.utils.config import Config
from fedmcp_pipeline.ingest.hansard import (
    ingest_hansard_documents,
    ingest_hansard_statements,
    link_statements_to_documents,
    link_statements_to_mps,
    link_statements_to_bills,
)


def get_statement_count_since_2023(pg_client):
    """Get count of statements since 2023-01-01 from PostgreSQL."""
    query = """
        SELECT COUNT(*) as count
        FROM hansards_statement
        WHERE time >= '2023-01-01'
          AND time < '4000-01-01'  -- Exclude corrupted dates
    """
    result = pg_client.execute_query(query, dict_cursor=True)
    return result[0]['count'] if result else 0


def get_document_ids_since_2023(pg_client):
    """Get unique document IDs for statements since 2023-01-01."""
    query = """
        SELECT DISTINCT document_id
        FROM hansards_statement
        WHERE time >= '2023-01-01'
          AND time < '4000-01-01'
          AND document_id IS NOT NULL
        ORDER BY document_id
    """
    results = pg_client.execute_query(query, dict_cursor=True)
    return [r['document_id'] for r in results]


def ingest_documents_by_ids(neo4j_client, postgres_client, document_ids, batch_size=1000):
    """Import specific documents by ID list."""
    from fedmcp_pipeline.utils.progress import logger, ProgressTracker

    if not document_ids:
        logger.warning("No document IDs provided")
        return 0

    logger.info(f"Ingesting {len(document_ids):,} documents...")

    # Build query with ID filter
    query = """
        SELECT
            id,
            date,
            number,
            session_id,
            document_type,
            source_id,
            downloaded,
            public,
            xml_source_url
        FROM hansards_document
        WHERE id = ANY(%s)
        ORDER BY date DESC
    """

    # Fetch documents
    documents = postgres_client.execute_query(query, params=(document_ids,), dict_cursor=True)
    logger.info(f"Fetched {len(documents):,} Hansard documents from PostgreSQL")

    if not documents:
        logger.warning("No Hansard documents found")
        return 0

    # Prepare data for batch insert
    documents_data = []
    for doc in documents:
        documents_data.append({
            "id": doc["id"],
            "date": doc["date"].isoformat() if doc["date"] else None,
            "number": doc["number"],
            "session_id": doc["session_id"],
            "document_type": doc["document_type"],
            "source_id": doc["source_id"],
            "downloaded": doc["downloaded"],
            "public": doc["public"],
            "xml_source_url": doc["xml_source_url"],
        })

    # Create nodes in Neo4j
    tracker = ProgressTracker(total=len(documents_data), desc="Creating Document nodes")

    cypher = """
        UNWIND $documents AS doc
        MERGE (d:Document {id: doc.id})
        SET d.date = doc.date,
            d.number = doc.number,
            d.session_id = doc.session_id,
            d.document_type = doc.document_type,
            d.source_id = doc.source_id,
            d.downloaded = doc.downloaded,
            d.public = doc.public,
            d.xml_source_url = doc.xml_source_url,
            d.updated_at = datetime()
        RETURN count(d) as created
    """

    created_total = 0
    for i in range(0, len(documents_data), batch_size):
        batch = documents_data[i:i + batch_size]
        result = neo4j_client.run_query(cypher, {"documents": batch})
        created = result[0]["created"] if result else 0
        created_total += created
        tracker.update(len(batch))

    tracker.close()
    logger.info(f"Created/updated {created_total:,} Document nodes in Neo4j")

    return created_total


def ingest_statements_since_2023(neo4j_client, postgres_client, batch_size=5000):
    """Import statements from 2023-01-01 onwards."""
    from fedmcp_pipeline.utils.progress import logger, ProgressTracker
    from fedmcp_pipeline.ingest.hansard import sanitize_statement_content

    logger.info("Ingesting Hansard statements from 2023-01-01 onwards...")

    # Build query with date filter
    query = """
        SELECT
            id,
            document_id,
            time,
            politician_id,
            member_id,
            who_en,
            who_fr,
            content_en,
            content_fr,
            h1_en,
            h1_fr,
            h2_en,
            h2_fr,
            h3_en,
            h3_fr,
            statement_type,
            wordcount,
            procedural,
            bill_debated_id,
            bill_debate_stage,
            slug
        FROM hansards_statement
        WHERE time >= '2023-01-01'
          AND time < '4000-01-01'  -- Exclude corrupted dates
        ORDER BY time DESC
    """

    # Fetch statements
    logger.info("Fetching statements from PostgreSQL...")
    statements = postgres_client.execute_query(query, dict_cursor=True)
    logger.info(f"Fetched {len(statements):,} Hansard statements from PostgreSQL")

    if not statements:
        logger.warning("No Hansard statements found")
        return 0

    # Prepare data for batch insert
    logger.info("Sanitizing statement content...")
    statements_data = []

    for stmt in statements:
        # Build raw statement data
        statement_data = {
            "id": stmt["id"],
            "document_id": stmt["document_id"],
            "time": stmt["time"],
            "politician_id": stmt["politician_id"],
            "member_id": stmt["member_id"],
            "who_en": stmt["who_en"],
            "who_fr": stmt["who_fr"],
            "content_en": stmt["content_en"] or "",
            "content_fr": stmt["content_fr"] or "",
            "h1_en": stmt["h1_en"],
            "h1_fr": stmt["h1_fr"],
            "h2_en": stmt["h2_en"],
            "h2_fr": stmt["h2_fr"],
            "h3_en": stmt["h3_en"],
            "h3_fr": stmt["h3_fr"],
            "statement_type": stmt["statement_type"],
            "wordcount": stmt["wordcount"],
            "procedural": stmt["procedural"],
            "bill_debated_id": stmt["bill_debated_id"],
            "bill_debate_stage": stmt["bill_debate_stage"],
            "slug": stmt["slug"],
        }

        # Sanitize content (strip HTML, validate dates)
        statement_data = sanitize_statement_content(statement_data)

        # Convert time to ISO format after sanitization
        if statement_data["time"]:
            statement_data["time"] = statement_data["time"].isoformat()

        statements_data.append(statement_data)

    # Create nodes in Neo4j with smaller batches (1000 instead of 5000)
    # to avoid transaction timeout
    logger.info("Creating Statement nodes in Neo4j...")
    effective_batch_size = 1000  # Smaller batches for large imports
    tracker = ProgressTracker(total=len(statements_data), desc="Creating Statement nodes")

    cypher = """
        UNWIND $statements AS stmt
        MERGE (s:Statement {id: stmt.id})
        SET s.document_id = stmt.document_id,
            s.time = stmt.time,
            s.politician_id = stmt.politician_id,
            s.member_id = stmt.member_id,
            s.who_en = stmt.who_en,
            s.who_fr = stmt.who_fr,
            s.content_en = stmt.content_en,
            s.content_fr = stmt.content_fr,
            s.h1_en = stmt.h1_en,
            s.h1_fr = stmt.h1_fr,
            s.h2_en = stmt.h2_en,
            s.h2_fr = stmt.h2_fr,
            s.h3_en = stmt.h3_en,
            s.h3_fr = stmt.h3_fr,
            s.statement_type = stmt.statement_type,
            s.wordcount = stmt.wordcount,
            s.procedural = stmt.procedural,
            s.bill_debated_id = stmt.bill_debated_id,
            s.bill_debate_stage = stmt.bill_debate_stage,
            s.slug = stmt.slug,
            s.updated_at = datetime()
        RETURN count(s) as created
    """

    created_total = 0
    for i in range(0, len(statements_data), effective_batch_size):
        batch = statements_data[i:i + effective_batch_size]
        try:
            result = neo4j_client.run_query(cypher, {"statements": batch})
            created = result[0]["created"] if result else 0
            created_total += created
            tracker.update(len(batch))
        except Exception as e:
            logger.error(f"Error processing batch {i//effective_batch_size + 1}: {e}")
            # Continue with next batch
            continue

    tracker.close()
    logger.info(f"Created/updated {created_total:,} Statement nodes in Neo4j")

    return created_total


def validate_import(neo4j_client):
    """Validate the import and return statistics."""
    stats = {}

    # Count statements
    result = neo4j_client.run_query("MATCH (s:Statement) RETURN count(s) as count")
    stats['statements'] = result[0]["count"] if result else 0

    # Count statements from 2023+
    result = neo4j_client.run_query(
        "MATCH (s:Statement) WHERE s.time >= '2023-01-01' RETURN count(s) as count"
    )
    stats['statements_2023_plus'] = result[0]["count"] if result else 0

    # Count documents
    result = neo4j_client.run_query("MATCH (d:Document) RETURN count(d) as count")
    stats['documents'] = result[0]["count"] if result else 0

    # Count PART_OF relationships
    result = neo4j_client.run_query("MATCH ()-[r:PART_OF]->() RETURN count(r) as count")
    stats['part_of'] = result[0]["count"] if result else 0

    # Count MADE_BY relationships
    result = neo4j_client.run_query("MATCH ()-[r:MADE_BY]->() RETURN count(r) as count")
    stats['made_by'] = result[0]["count"] if result else 0

    # Count MENTIONS relationships
    result = neo4j_client.run_query("MATCH ()-[r:MENTIONS]->() RETURN count(r) as count")
    stats['mentions'] = result[0]["count"] if result else 0

    # Get date range
    result = neo4j_client.run_query(
        "MATCH (s:Statement) WHERE s.time IS NOT NULL RETURN min(s.time) as min_date, max(s.time) as max_date"
    )
    if result:
        stats['min_date'] = str(result[0]["min_date"])[:10] if result[0]["min_date"] else None
        stats['max_date'] = str(result[0]["max_date"])[:10] if result[0]["max_date"] else None

    return stats


def main():
    """Main execution function."""
    start_time = datetime.now()

    print("=" * 80)
    print("HANSARD 2023-PRESENT IMPORT")
    print("=" * 80)
    print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Load configuration
    env_file = Path(__file__).parent / "packages" / "data-pipeline" / ".env"
    config = Config(env_file=env_file)

    # PostgreSQL connection parameters
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
    pg_db = os.getenv("POSTGRES_DB", "openparliament")
    pg_user = os.getenv("POSTGRES_USER", "fedmcp")
    pg_password = os.getenv("POSTGRES_PASSWORD", "fedmcp2024")

    # Connect to databases
    print("1. Connecting to databases...")
    pg_client = PostgresClient(
        dbname=pg_db,
        user=pg_user,
        password=pg_password,
        host=pg_host,
        port=pg_port
    )

    neo4j_client = Neo4jClient(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password
    )

    try:
        print("   ✅ Connected to PostgreSQL")
        print("   ✅ Connected to Neo4j")
        print()

        # Get expected counts
        print("2. Analyzing source data...")
        statement_count = get_statement_count_since_2023(pg_client)
        document_ids = get_document_ids_since_2023(pg_client)
        print(f"   Expected statements (2023+): {statement_count:,}")
        print(f"   Expected documents:          {len(document_ids):,}")
        print()

        # Import documents
        print("3. Importing documents...")
        print("-" * 80)
        docs_created = ingest_documents_by_ids(neo4j_client, pg_client, document_ids)
        print(f"✅ Imported {docs_created:,} documents")
        print()

        # Import statements
        print("4. Importing statements (this will take ~10-15 minutes)...")
        print("-" * 80)
        statements_created = ingest_statements_since_2023(neo4j_client, pg_client)
        print(f"✅ Imported {statements_created:,} statements")
        print()

        # Create PART_OF relationships
        print("5. Creating PART_OF relationships (Statement → Document)...")
        print("-" * 80)
        part_of_created = link_statements_to_documents(neo4j_client, batch_size=10000)
        print(f"✅ Created {part_of_created:,} PART_OF relationships")
        print()

        # Create MADE_BY relationships
        print("6. Creating MADE_BY relationships (Statement → MP)...")
        print("-" * 80)
        made_by_created = link_statements_to_mps(neo4j_client, batch_size=10000)
        print(f"✅ Created {made_by_created:,} MADE_BY relationships")
        print()

        # Create MENTIONS relationships
        print("7. Creating MENTIONS relationships (Statement → Bill)...")
        print("-" * 80)
        mentions_created = link_statements_to_bills(neo4j_client, batch_size=10000)
        print(f"✅ Created {mentions_created:,} MENTIONS relationships")
        print()

        # Validate results
        print("8. Validating import results...")
        stats = validate_import(neo4j_client)
        print(f"   Total Statements:       {stats['statements']:,}")
        print(f"   Statements (2023+):     {stats['statements_2023_plus']:,}")
        print(f"   Total Documents:        {stats['documents']:,}")
        print(f"   PART_OF relationships:  {stats['part_of']:,}")
        print(f"   MADE_BY relationships:  {stats['made_by']:,}")
        print(f"   MENTIONS relationships: {stats['mentions']:,}")
        print(f"   Date Range:             {stats.get('min_date', 'N/A')} to {stats.get('max_date', 'N/A')}")
        print()

        # Calculate duration
        end_time = datetime.now()
        duration = end_time - start_time
        minutes = int(duration.total_seconds() / 60)
        seconds = int(duration.total_seconds() % 60)

        # Print summary
        print("=" * 80)
        print("✅ IMPORT COMPLETE")
        print("=" * 80)
        print(f"Duration: {minutes} minutes, {seconds} seconds")
        print(f"Statements: {statements_created:,}")
        print(f"Documents: {docs_created:,}")
        print(f"PART_OF: {part_of_created:,}")
        print(f"MADE_BY: {made_by_created:,}")
        print(f"MENTIONS: {mentions_created:,}")
        print()

        # Sample queries
        print("=" * 80)
        print("VERIFICATION QUERIES")
        print("=" * 80)

        # Recent statements count by month
        print("\nStatements by Month (2024-2025):")
        print("-" * 80)
        query = """
            MATCH (s:Statement)
            WHERE s.time >= '2024-01-01'
            WITH substring(s.time, 0, 7) as month, count(s) as count
            RETURN month, count
            ORDER BY month DESC
            LIMIT 12
        """
        results = neo4j_client.run_query(query)
        for r in results:
            print(f"  {r['month']}: {r['count']:,} statements")

        # Top speakers in 2024
        print("\nTop Speakers in 2024:")
        print("-" * 80)
        query = """
            MATCH (mp:MP)<-[:MADE_BY]-(s:Statement)
            WHERE s.time >= '2024-01-01'
            WITH mp, count(s) as speech_count, sum(s.wordcount) as total_words
            RETURN mp.name, speech_count, total_words
            ORDER BY speech_count DESC
            LIMIT 10
        """
        results = neo4j_client.run_query(query)
        for r in results:
            words = r['total_words'] or 0
            print(f"  {r['mp.name']:30} {r['speech_count']:5} speeches | {words:8,} words")

        print()
        print("=" * 80)
        print("🎉 SUCCESS - Ready for GraphQL schema updates!")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR DURING IMPORT")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return 1

    finally:
        pg_client.close()
        neo4j_client.close()

    return 0


if __name__ == "__main__":
    exit(main())
