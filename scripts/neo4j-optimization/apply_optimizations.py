#!/usr/bin/env python3
"""
Neo4j Database Optimization Script

Applies constraints, indexes, and full-text search to the FedMCP Neo4j database.

Usage:
    python apply_optimizations.py                    # Run all phases
    python apply_optimizations.py --phase 1          # Run Phase 1 only
    python apply_optimizations.py --phase 2          # Run Phase 2 only
    python apply_optimizations.py --verify           # Verification only
    python apply_optimizations.py --dry-run          # Show what would be done

Requirements:
    pip install neo4j python-dotenv
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Neo4jOptimizer:
    """Applies optimization scripts to Neo4j database."""

    def __init__(self, uri: str, username: str, password: str):
        """Initialize optimizer with Neo4j connection."""
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.script_dir = Path(__file__).parent

    def close(self):
        """Close Neo4j connection."""
        self.driver.close()

    def run_cypher_file(self, filename: str, description: str) -> bool:
        """
        Execute a Cypher script file.

        Args:
            filename: Name of .cypher file in script directory
            description: Human-readable description for logging

        Returns:
            True if successful, False otherwise
        """
        filepath = self.script_dir / filename
        if not filepath.exists():
            print(f"❌ Script not found: {filepath}")
            return False

        print(f"\n{'='*60}")
        print(f"📄 {description}")
        print(f"File: {filename}")
        print(f"{'='*60}")

        with open(filepath, 'r') as f:
            script = f.read()

        # Split script into individual statements
        statements = self._split_cypher_statements(script)

        with self.driver.session() as session:
            executed = 0
            failed = 0
            start_time = time.time()

            for i, statement in enumerate(statements, 1):
                statement = statement.strip()

                # Skip comments and empty statements
                if not statement or statement.startswith('//'):
                    continue

                # Skip documentation blocks
                if statement.startswith('--'):
                    continue

                try:
                    # Execute statement
                    result = session.run(statement)
                    summary = result.consume()

                    # Print progress for long-running operations
                    if 'CREATE' in statement.upper() or 'SHOW' in statement.upper():
                        if 'CONSTRAINT' in statement.upper():
                            print(f"✅ Created constraint")
                        elif 'INDEX' in statement.upper():
                            print(f"✅ Created index")
                        else:
                            print(f"✅ Statement {i} executed")

                    executed += 1

                except Exception as e:
                    # Check if error is benign (e.g., constraint already exists)
                    error_msg = str(e).lower()
                    if 'already exists' in error_msg or 'equivalent' in error_msg:
                        print(f"ℹ️  Already exists, skipping")
                    else:
                        print(f"❌ Error in statement {i}: {e}")
                        failed += 1

            elapsed = time.time() - start_time
            print(f"\n📊 Results:")
            print(f"   Executed: {executed} statements")
            print(f"   Failed: {failed} statements")
            print(f"   Time: {elapsed:.1f} seconds")

            return failed == 0

    def _split_cypher_statements(self, script: str) -> List[str]:
        """
        Split multi-statement Cypher script.

        Simple splitting by semicolons. More sophisticated parsing
        would handle semicolons within strings, but our scripts don't have that.
        """
        statements = []
        current = []

        for line in script.split('\n'):
            # Skip full-line comments
            if line.strip().startswith('//'):
                continue

            # Collect lines until semicolon
            current.append(line)

            if line.strip().endswith(';'):
                statements.append('\n'.join(current))
                current = []

        # Add any remaining content
        if current:
            statements.append('\n'.join(current))

        return statements

    def verify_optimizations(self) -> bool:
        """
        Verify that all optimizations were applied successfully.

        Returns:
            True if all optimizations are online and healthy
        """
        print(f"\n{'='*60}")
        print("🔍 VERIFICATION")
        print(f"{'='*60}")

        with self.driver.session() as session:
            # Check constraints
            result = session.run("SHOW CONSTRAINTS")
            constraints = list(result)
            print(f"\n✅ Constraints: {len(constraints)}")

            # Check indexes
            result = session.run("""
                CALL db.indexes()
                YIELD name, type, state, populationPercent
                RETURN count(*) as total,
                       sum(CASE WHEN state = 'ONLINE' THEN 1 ELSE 0 END) as online,
                       sum(CASE WHEN populationPercent = 100 THEN 1 ELSE 0 END) as populated
            """)
            index_stats = result.single()

            total = index_stats['total']
            online = index_stats['online']
            populated = index_stats['populated']

            print(f"✅ Indexes: {total} total")
            print(f"   Online: {online}/{total}")
            print(f"   Populated: {populated}/{total}")

            # Check for failed indexes
            result = session.run("""
                CALL db.indexes()
                YIELD name, state, populationPercent
                WHERE state <> 'ONLINE' OR populationPercent < 100
                RETURN name, state, populationPercent
            """)
            failed_indexes = list(result)

            if failed_indexes:
                print(f"\n⚠️  Issues found:")
                for idx in failed_indexes:
                    print(f"   - {idx['name']}: {idx['state']} ({idx['populationPercent']}% populated)")
                return False

            print(f"\n✅ All optimizations applied successfully!")
            return True

    def run_phase_1(self) -> bool:
        """Run Phase 1: Critical constraints and high-frequency indexes."""
        print(f"\n{'#'*60}")
        print("PHASE 1: CRITICAL OPTIMIZATIONS (Required for Production)")
        print(f"{'#'*60}")

        success = True

        success &= self.run_cypher_file(
            "01-constraints-critical.cypher",
            "Step 1: Creating Uniqueness Constraints"
        )

        success &= self.run_cypher_file(
            "02-indexes-high-frequency.cypher",
            "Step 2: Creating High-Frequency Property Indexes"
        )

        if success:
            print(f"\n✅ Phase 1 complete!")
        else:
            print(f"\n⚠️  Phase 1 completed with errors")

        return success

    def run_phase_2(self) -> bool:
        """Run Phase 2: Full-text and composite indexes."""
        print(f"\n{'#'*60}")
        print("PHASE 2: SEARCH & ANALYTICS OPTIMIZATIONS")
        print(f"{'#'*60}")

        success = True

        success &= self.run_cypher_file(
            "03-fulltext-indexes.cypher",
            "Step 3: Creating Full-Text Search Indexes"
        )

        success &= self.run_cypher_file(
            "04-composite-relationship-indexes.cypher",
            "Step 4: Creating Composite & Relationship Indexes"
        )

        if success:
            print(f"\n✅ Phase 2 complete!")
        else:
            print(f"\n⚠️  Phase 2 completed with errors")

        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Apply Neo4j optimizations to FedMCP database"
    )
    parser.add_argument(
        '--phase',
        type=int,
        choices=[1, 2],
        help="Run specific phase only (1=critical, 2=search/analytics)"
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help="Run verification only (no changes)"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be done without executing"
    )
    parser.add_argument(
        '--uri',
        default=os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687'),
        help="Neo4j connection URI"
    )
    parser.add_argument(
        '--username',
        default=os.getenv('NEO4J_USERNAME', 'neo4j'),
        help="Neo4j username"
    )
    parser.add_argument(
        '--password',
        default=os.getenv('NEO4J_PASSWORD', 'canadagpt2024'),
        help="Neo4j password"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("NEO4J DATABASE OPTIMIZATION")
    print("=" * 60)
    print(f"URI: {args.uri}")
    print(f"Username: {args.username}")
    print("=" * 60)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
        print("\nWould execute:")
        if not args.phase or args.phase == 1:
            print("  ✓ Phase 1: Constraints + High-Frequency Indexes")
        if not args.phase or args.phase == 2:
            print("  ✓ Phase 2: Full-Text + Composite Indexes")
        print("  ✓ Verification")
        return 0

    # Initialize optimizer
    optimizer = Neo4jOptimizer(args.uri, args.username, args.password)

    try:
        if args.verify:
            # Verification only
            success = optimizer.verify_optimizations()
        elif args.phase == 1:
            # Phase 1 only
            success = optimizer.run_phase_1()
            if success:
                optimizer.verify_optimizations()
        elif args.phase == 2:
            # Phase 2 only
            success = optimizer.run_phase_2()
            if success:
                optimizer.verify_optimizations()
        else:
            # Run all phases
            success = optimizer.run_phase_1()
            if success:
                success &= optimizer.run_phase_2()
            if success:
                optimizer.verify_optimizations()

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        return 1

    finally:
        optimizer.close()


if __name__ == '__main__':
    sys.exit(main())
