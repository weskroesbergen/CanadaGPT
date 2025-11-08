#!/usr/bin/env python3
"""
Analyze Hansard statements and create conversation threading relationships.

This script infers conversation threads from existing statement data by analyzing:
- statement_type: "question", "answer", "interjection"
- time: chronological proximity within topics
- h2_en/h2_fr: topic grouping
- document_id: debate session grouping

It creates REPLIES_TO relationships in Neo4j and populates:
- thread_id: Unique identifier for conversation groups
- parent_statement_id: Which statement this replies to
- sequence_in_thread: Order within conversation (0 = root)

Usage:
    python scripts/analyze_conversation_threads.py [--limit N] [--document-id ID] [--dry-run]

Options:
    --limit N: Only process first N statements (for testing)
    --document-id ID: Process only specific document (for testing)
    --dry-run: Show what would be created without making changes
    --time-threshold SECONDS: Max time between statements in same thread (default: 300)
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import uuid

# Add packages to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "data-pipeline"))

from dotenv import load_dotenv
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient
from fedmcp_pipeline.utils.config import Config


class ConversationAnalyzer:
    """Analyzes statements and creates conversation threading."""

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        postgres_client: PostgresClient,
        time_threshold: int = 300,  # 5 minutes in seconds
        dry_run: bool = False
    ):
        self.neo4j = neo4j_client
        self.postgres = postgres_client
        self.time_threshold = time_threshold
        self.dry_run = dry_run
        self.stats = {
            'total_statements': 0,
            'threads_created': 0,
            'replies_created': 0,
            'root_statements': 0,
        }

    def fetch_statements_for_analysis(
        self,
        document_id: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch statements from PostgreSQL ordered by document, topic, and time.
        """
        where_clauses = ["time < '4000-01-01'"]  # Exclude corrupted dates
        params = []

        if document_id:
            where_clauses.append("document_id = %s")
            params.append(document_id)

        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        limit_sql = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT
                id,
                document_id,
                time,
                politician_id,
                h1_en,
                h2_en,
                h3_en,
                statement_type,
                wordcount,
                procedural,
                who_en
            FROM hansards_statement
            WHERE 1=1 {where_sql}
            ORDER BY document_id, h2_en, time
            {limit_sql}
        """

        print(f"Fetching statements from PostgreSQL...")
        statements = self.postgres.execute_query(query, params=tuple(params) if params else None, dict_cursor=True)
        print(f"Fetched {len(statements)} statements")
        self.stats['total_statements'] = len(statements)
        return statements

    def group_statements_by_context(
        self,
        statements: List[Dict[str, Any]]
    ) -> Dict[Tuple[int, str], List[Dict[str, Any]]]:
        """
        Group statements by (document_id, h2_en) to identify conversation contexts.
        """
        groups = defaultdict(list)

        for stmt in statements:
            # Skip statements without document or topic
            if not stmt.get('document_id') or not stmt.get('h2_en'):
                continue

            key = (stmt['document_id'], stmt['h2_en'])
            groups[key].append(stmt)

        print(f"Grouped into {len(groups)} conversation contexts")
        return groups

    def analyze_group_for_threads(
        self,
        statements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze a group of statements and identify conversation threads.

        Returns list of thread structures:
        [
            {
                'thread_id': 'uuid',
                'root_statement_id': 12345,
                'statements': [
                    {'id': 12345, 'sequence': 0, 'parent_id': None},
                    {'id': 12346, 'sequence': 1, 'parent_id': 12345},
                    {'id': 12347, 'sequence': 2, 'parent_id': 12345},
                ]
            },
            ...
        ]
        """
        if not statements:
            return []

        threads = []
        current_thread = None
        last_question_time = None
        last_question_id = None

        for stmt in statements:
            stmt_id = stmt['id']
            stmt_type = stmt.get('statement_type', '').lower()
            stmt_time = stmt.get('time')

            # Questions always start new threads
            if stmt_type == 'question':
                # Finalize previous thread
                if current_thread:
                    threads.append(current_thread)

                # Start new thread
                thread_id = str(uuid.uuid4())
                current_thread = {
                    'thread_id': thread_id,
                    'root_statement_id': stmt_id,
                    'statements': [
                        {'id': stmt_id, 'sequence': 0, 'parent_id': None}
                    ]
                }
                last_question_time = stmt_time
                last_question_id = stmt_id
                self.stats['root_statements'] += 1

            # Answers and interjections may belong to current thread
            elif stmt_type in ('answer', 'interjection') and current_thread:
                # Check time proximity
                time_diff = None
                if stmt_time and last_question_time:
                    time_diff = (stmt_time - last_question_time).total_seconds()

                # Add to thread if within time threshold
                if time_diff is not None and time_diff <= self.time_threshold:
                    current_thread['statements'].append({
                        'id': stmt_id,
                        'sequence': len(current_thread['statements']),
                        'parent_id': last_question_id  # Reply to the question
                    })
                else:
                    # Too far apart, start new thread
                    if current_thread:
                        threads.append(current_thread)

                    thread_id = str(uuid.uuid4())
                    current_thread = {
                        'thread_id': thread_id,
                        'root_statement_id': stmt_id,
                        'statements': [
                            {'id': stmt_id, 'sequence': 0, 'parent_id': None}
                        ]
                    }
                    last_question_time = stmt_time
                    last_question_id = stmt_id
                    self.stats['root_statements'] += 1

            # Other statement types start standalone threads
            elif stmt_type not in ('answer', 'interjection'):
                # Finalize previous thread
                if current_thread:
                    threads.append(current_thread)

                # Single-statement thread
                thread_id = str(uuid.uuid4())
                current_thread = {
                    'thread_id': thread_id,
                    'root_statement_id': stmt_id,
                    'statements': [
                        {'id': stmt_id, 'sequence': 0, 'parent_id': None}
                    ]
                }
                last_question_time = stmt_time
                last_question_id = stmt_id
                self.stats['root_statements'] += 1

        # Finalize last thread
        if current_thread:
            threads.append(current_thread)

        return threads

    def create_threading_relationships(
        self,
        threads: List[Dict[str, Any]]
    ) -> int:
        """
        Create REPLIES_TO relationships and update thread fields in Neo4j.
        Returns number of relationships created.
        """
        relationships_created = 0

        for thread in threads:
            thread_id = thread['thread_id']
            statements = thread['statements']

            # Update each statement with thread metadata
            for stmt in statements:
                stmt_id = str(stmt['id'])
                sequence = stmt['sequence']
                parent_id = str(stmt['parent_id']) if stmt['parent_id'] else None

                # Update statement node
                update_query = """
                MATCH (s:Statement {id: $stmt_id})
                SET s.thread_id = $thread_id,
                    s.sequence_in_thread = $sequence,
                    s.parent_statement_id = $parent_id
                """

                if not self.dry_run:
                    self.neo4j.run_query(update_query, {
                        'stmt_id': stmt_id,
                        'thread_id': thread_id,
                        'sequence': sequence,
                        'parent_id': parent_id
                    })

                # Create REPLIES_TO relationship if this is a reply
                if parent_id:
                    reply_query = """
                    MATCH (child:Statement {id: $child_id})
                    MATCH (parent:Statement {id: $parent_id})
                    MERGE (child)-[:REPLIES_TO]->(parent)
                    """

                    if not self.dry_run:
                        self.neo4j.run_query(reply_query, {
                            'child_id': stmt_id,
                            'parent_id': parent_id
                        })

                    relationships_created += 1

        self.stats['replies_created'] = relationships_created
        return relationships_created

    def analyze_and_thread(
        self,
        document_id: Optional[int] = None,
        limit: Optional[int] = None
    ):
        """
        Main method to analyze statements and create threading.
        """
        print("\n" + "=" * 80)
        print("HANSARD CONVERSATION THREADING ANALYSIS")
        print("=" * 80)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Time threshold: {self.time_threshold} seconds")
        if document_id:
            print(f"Document filter: {document_id}")
        if limit:
            print(f"Statement limit: {limit}")
        print()

        # Step 1: Fetch statements
        statements = self.fetch_statements_for_analysis(document_id, limit)

        if not statements:
            print("No statements to process.")
            return

        # Step 2: Group by conversation context
        groups = self.group_statements_by_context(statements)

        # Step 3: Analyze each group for threads
        all_threads = []
        for (doc_id, topic), group_statements in groups.items():
            threads = self.analyze_group_for_threads(group_statements)
            all_threads.extend(threads)
            print(f"  Document {doc_id} / {topic[:50]}... → {len(threads)} threads")

        self.stats['threads_created'] = len(all_threads)

        print(f"\nTotal threads identified: {len(all_threads)}")

        # Step 4: Create relationships in Neo4j
        if not self.dry_run:
            print("\nCreating threading relationships in Neo4j...")
            relationships_created = self.create_threading_relationships(all_threads)
            print(f"Created {relationships_created} REPLIES_TO relationships")
        else:
            print("\nDRY RUN - Would create threading relationships")
            # Calculate how many would be created
            total_replies = sum(
                len([s for s in thread['statements'] if s['parent_id']])
                for thread in all_threads
            )
            print(f"Would create {total_replies} REPLIES_TO relationships")

        # Print statistics
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)
        print(f"Total statements analyzed: {self.stats['total_statements']:,}")
        print(f"Conversation contexts: {len(groups):,}")
        print(f"Threads created: {self.stats['threads_created']:,}")
        print(f"Root statements: {self.stats['root_statements']:,}")
        print(f"Reply relationships: {self.stats['replies_created']:,}")
        avg_thread_size = (
            self.stats['total_statements'] / self.stats['threads_created']
            if self.stats['threads_created'] > 0 else 0
        )
        print(f"Average thread size: {avg_thread_size:.1f} statements")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze conversation threads in Hansard statements"
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Only process first N statements (for testing)'
    )
    parser.add_argument(
        '--document-id',
        type=int,
        help='Process only specific document (for testing)'
    )
    parser.add_argument(
        '--time-threshold',
        type=int,
        default=300,
        help='Max seconds between statements in same thread (default: 300)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without making changes'
    )

    args = parser.parse_args()

    # Load environment
    load_dotenv(PROJECT_ROOT / "packages" / "data-pipeline" / ".env")

    # Initialize clients
    env_file = PROJECT_ROOT / "packages" / "data-pipeline" / ".env"
    config = Config(env_file=env_file)

    # PostgreSQL connection parameters
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
    pg_db = os.getenv("POSTGRES_DB", "openparliament")
    pg_user = os.getenv("POSTGRES_USER", "fedmcp")
    pg_password = os.getenv("POSTGRES_PASSWORD", "fedmcp2024")

    neo4j = Neo4jClient(
        config.neo4j_uri,
        config.neo4j_user,
        config.neo4j_password
    )
    # PostgresClient signature: dbname, user, password, host, port
    postgres = PostgresClient(
        dbname=pg_db,
        user=pg_user,
        password=pg_password,
        host=pg_host,
        port=pg_port
    )

    try:
        # Create analyzer
        analyzer = ConversationAnalyzer(
            neo4j,
            postgres,
            time_threshold=args.time_threshold,
            dry_run=args.dry_run
        )

        # Run analysis
        analyzer.analyze_and_thread(
            document_id=args.document_id,
            limit=args.limit
        )

    finally:
        # Cleanup
        neo4j.close()
        postgres.close()

    print("\n✅ Threading analysis complete!")


if __name__ == "__main__":
    main()
