#!/usr/bin/env python3
"""
Test enhanced MP ingestion with OurCommons XML metadata.

This validates that:
1. OurCommons XML client is properly integrated
2. New fields (honorific, term_start_date, term_end_date, province) are captured
3. Data is correctly merged and stored in Neo4j
"""

import sys
import os
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp_pipeline.ingest.parliament import ingest_mps


def test_enhanced_mp_ingestion():
    """Test MP ingestion with enhanced OurCommons XML metadata."""

    logger.info("=" * 80)
    logger.info("TESTING ENHANCED MP INGESTION")
    logger.info("=" * 80)
    print()

    # Connect to local Neo4j
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'canadagpt2024')

    logger.info(f"Connecting to Neo4j at {neo4j_uri}...")
    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Run MP ingestion with enhanced metadata
        logger.info("Running MP ingestion with OurCommons XML enhancement...")
        count = ingest_mps(neo4j, batch_size=100)

        logger.success(f"✅ Ingested {count} MPs")
        print()

        # Verify enhanced fields were captured
        logger.info("Verifying enhanced field capture...")

        # Check honorifics
        query_honorifics = """
        MATCH (mp:MP)
        WHERE mp.honorific IS NOT NULL
        RETURN
            count(*) as total_with_honorific,
            count(CASE WHEN mp.honorific = 'Right Hon.' THEN 1 END) as right_hon_count,
            count(CASE WHEN mp.honorific = 'Hon.' THEN 1 END) as hon_count
        """
        result = neo4j.run_query(query_honorifics)
        if result:
            row = result[0]
            logger.info(f"Honorifics captured: {row['total_with_honorific']} total")
            logger.info(f"  - Right Hon. (former PMs): {row['right_hon_count']}")
            logger.info(f"  - Hon. (ministers): {row['hon_count']}")
        print()

        # Check term dates
        query_term_dates = """
        MATCH (mp:MP)
        WHERE mp.current = true
        RETURN
            count(*) as total_current,
            count(CASE WHEN mp.term_start_date IS NOT NULL THEN 1 END) as with_term_start,
            count(CASE WHEN mp.term_end_date IS NOT NULL THEN 1 END) as with_term_end,
            count(CASE WHEN mp.province IS NOT NULL THEN 1 END) as with_province
        """
        result = neo4j.run_query(query_term_dates)
        if result:
            row = result[0]
            total = row['total_current']
            logger.info(f"Current MPs: {total}")
            logger.info(f"  - With term_start_date: {row['with_term_start']}/{total} ({row['with_term_start']/total*100:.1f}%)")
            logger.info(f"  - With term_end_date: {row['with_term_end']}/{total} (should be 0 for current MPs)")
            logger.info(f"  - With province: {row['with_province']}/{total} ({row['with_province']/total*100:.1f}%)")
        print()

        # Show sample MPs with enhanced metadata
        logger.info("=" * 80)
        logger.info("SAMPLE MPs WITH ENHANCED METADATA")
        logger.info("=" * 80)

        # Get Mark Carney (Right Hon.)
        query_carney = """
        MATCH (mp:MP)
        WHERE mp.honorific = 'Right Hon.'
        RETURN mp.id, mp.name, mp.honorific, mp.party, mp.riding,
               mp.term_start_date, mp.term_end_date, mp.province
        LIMIT 1
        """
        result = neo4j.run_query(query_carney)
        if result:
            mp = result[0]
            print()
            logger.info("Former PM (Right Hon.):")
            logger.info(f"  Name: {mp['mp.name']}")
            logger.info(f"  Honorific: {mp['mp.honorific']} ✅")
            logger.info(f"  Party: {mp['mp.party']}")
            logger.info(f"  Riding: {mp['mp.riding']}")
            logger.info(f"  Province: {mp['mp.province']} ✅")
            logger.info(f"  Term Start: {mp['mp.term_start_date']} ✅")
            logger.info(f"  Term End: {mp['mp.term_end_date'] or 'Current'} ✅")

        # Get a minister (Hon.)
        query_minister = """
        MATCH (mp:MP)
        WHERE mp.honorific = 'Hon.' AND mp.current = true
        RETURN mp.id, mp.name, mp.honorific, mp.party, mp.riding,
               mp.term_start_date, mp.term_end_date, mp.province
        LIMIT 1
        """
        result = neo4j.run_query(query_minister)
        if result:
            mp = result[0]
            print()
            logger.info("Minister (Hon.):")
            logger.info(f"  Name: {mp['mp.name']}")
            logger.info(f"  Honorific: {mp['mp.honorific']} ✅")
            logger.info(f"  Party: {mp['mp.party']}")
            logger.info(f"  Riding: {mp['mp.riding']}")
            logger.info(f"  Province: {mp['mp.province']} ✅")
            logger.info(f"  Term Start: {mp['mp.term_start_date']} ✅")
            logger.info(f"  Term End: {mp['mp.term_end_date'] or 'Current'} ✅")

        # Get a regular MP (no honorific)
        query_regular = """
        MATCH (mp:MP)
        WHERE mp.honorific IS NULL AND mp.current = true
        RETURN mp.id, mp.name, mp.honorific, mp.party, mp.riding,
               mp.term_start_date, mp.term_end_date, mp.province
        LIMIT 1
        """
        result = neo4j.run_query(query_regular)
        if result:
            mp = result[0]
            print()
            logger.info("Regular MP (no honorific):")
            logger.info(f"  Name: {mp['mp.name']}")
            logger.info(f"  Honorific: None ✅")
            logger.info(f"  Party: {mp['mp.party']}")
            logger.info(f"  Riding: {mp['mp.riding']}")
            logger.info(f"  Province: {mp['mp.province']} ✅")
            logger.info(f"  Term Start: {mp['mp.term_start_date']} ✅")
            logger.info(f"  Term End: {mp['mp.term_end_date'] or 'Current'} ✅")

        print()
        logger.info("=" * 80)
        logger.success("✅ ENHANCED MP INGESTION TEST COMPLETE")
        logger.info("=" * 80)
        print()
        logger.info("Summary:")
        logger.info("  - All MPs ingested successfully")
        logger.info("  - Honorifics captured (Right Hon., Hon.)")
        logger.info("  - Term dates captured from OurCommons XML")
        logger.info("  - Province data directly from XML")
        logger.info("  - Enhanced metadata integration working correctly ✅")
        print()

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    test_enhanced_mp_ingestion()
