#!/usr/bin/env python3
"""Check Document node coverage in production Neo4j database."""

import os
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient

def check_coverage():
    """Query Neo4j for Document node coverage."""

    # Get Neo4j credentials from environment
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not neo4j_uri or not neo4j_password:
        print("ERROR: NEO4J_URI and NEO4J_PASSWORD must be set")
        sys.exit(1)

    print(f"Connecting to Neo4j: {neo4j_uri}")

    # Create Neo4j client
    neo4j = Neo4jClient(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password
    )

    try:
        # Test connection
        neo4j.test_connection()

        # Query 1: Total Document count
        query1 = """
            MATCH (d:Document)
            RETURN count(d) as total_docs
        """
        result = neo4j.run_query(query1)
        total = result[0]["total_docs"] if result else 0
        print(f"\n📊 Total Document nodes: {total:,}")

        if total == 0:
            print("\n⚠️  NO DOCUMENT NODES FOUND!")
            print("This explains why the /debates page is empty.")
            print("Historical bulk import has NOT been run.")
            return

        # Query 2: Date range
        query2 = """
            MATCH (d:Document)
            WHERE d.date IS NOT NULL
            RETURN
                min(d.date) as earliest,
                max(d.date) as latest
        """
        result = neo4j.run_query(query2)
        if result:
            print(f"\n📅 Date range:")
            print(f"   Earliest: {result[0]['earliest']}")
            print(f"   Latest:   {result[0]['latest']}")

        # Query 3: Public vs private documents
        query3 = """
            MATCH (d:Document)
            RETURN
                d.public as public,
                count(d) as count
            ORDER BY public DESC
        """
        result = neo4j.run_query(query3)
        print(f"\n🔓 Public/Private breakdown:")
        for row in result:
            status = "Public" if row["public"] else "Private"
            print(f"   {status}: {row['count']:,}")

        # Query 4: Document type breakdown
        query4 = """
            MATCH (d:Document)
            WHERE d.document_type IS NOT NULL
            RETURN
                d.document_type as type,
                count(d) as count
            ORDER BY count DESC
        """
        result = neo4j.run_query(query4)
        print(f"\n📝 Document type breakdown:")
        for row in result:
            doc_type = "House Debates" if row["type"] == "D" else "Committee Evidence" if row["type"] == "E" else row["type"]
            print(f"   {doc_type} ({row['type']}): {row['count']:,}")

        # Query 5: November 2025 specifically
        query5 = """
            MATCH (d:Document)
            WHERE d.date >= '2025-11-01' AND d.date < '2025-12-01'
            RETURN count(d) as nov_2025_count
        """
        result = neo4j.run_query(query5)
        nov_count = result[0]["nov_2025_count"] if result else 0
        print(f"\n🗓️  November 2025 documents: {nov_count}")

        # Query 6: Recent documents (last 30 days)
        query6 = """
            MATCH (d:Document)
            WHERE d.date >= date() - duration({days: 30})
            RETURN
                d.date as date,
                d.document_type as type,
                d.public as public,
                d.id as id
            ORDER BY d.date DESC
            LIMIT 10
        """
        result = neo4j.run_query(query6)
        print(f"\n🕐 Most recent 10 documents:")
        for row in result:
            doc_type = "D" if row["type"] == "D" else "E"
            public = "✓" if row["public"] else "✗"
            print(f"   {row['date']} | Type:{doc_type} | Public:{public} | ID:{row['id']}")

        # Query 7: Statement count
        query7 = """
            MATCH (s:Statement)
            RETURN count(s) as total_statements
        """
        result = neo4j.run_query(query7)
        stmt_count = result[0]["total_statements"] if result else 0
        print(f"\n💬 Total Statement nodes: {stmt_count:,}")

        # Query 8: Relationship counts
        query8 = """
            MATCH (s:Statement)-[:PART_OF]->(d:Document)
            RETURN count(*) as part_of_rels
        """
        result = neo4j.run_query(query8)
        rel_count = result[0]["part_of_rels"] if result else 0
        print(f"\n🔗 Statement->Document relationships: {rel_count:,}")

    except Exception as e:
        print(f"\n❌ Error querying Neo4j: {e}")
        import traceback
        traceback.print_exc()
    finally:
        neo4j.close()

if __name__ == "__main__":
    check_coverage()
