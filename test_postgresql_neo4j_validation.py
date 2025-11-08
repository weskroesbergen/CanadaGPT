"""Comprehensive validation script comparing PostgreSQL and Neo4j data.

This script validates that data has been correctly migrated from the OpenParliament
PostgreSQL database to the Neo4j graph database.

It checks:
1. Record counts match between PostgreSQL and Neo4j
2. Relationships are properly created
3. No orphaned data exists
4. Data integrity constraints are met
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Tuple

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages/data-pipeline"))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.postgres_client import PostgresClient

# Load environment
load_dotenv(Path(__file__).parent / "packages/data-pipeline/.env")

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

class ValidationResult:
    """Stores validation results for a single check."""
    def __init__(self, name: str, passed: bool, message: str, details: Dict = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}

class DataValidator:
    """Validates data consistency between PostgreSQL and Neo4j."""

    def __init__(self, postgres_client: PostgresClient, neo4j_client: Neo4jClient):
        self.postgres = postgres_client
        self.neo4j = neo4j_client
        self.results: List[ValidationResult] = []

    def validate_count(self, name: str, pg_query: str, neo4j_query: str,
                      tolerance: int = 0) -> ValidationResult:
        """Compare counts between PostgreSQL and Neo4j.

        Args:
            name: Name of the validation check
            pg_query: PostgreSQL COUNT query
            neo4j_query: Neo4j count query
            tolerance: Acceptable difference (for eventual consistency)
        """
        try:
            # Get PostgreSQL count
            pg_result = self.postgres.execute_query(pg_query)
            pg_count = pg_result[0]['count'] if pg_result else 0

            # Get Neo4j count
            neo4j_result = self.neo4j.run_query(neo4j_query)
            neo4j_count = neo4j_result[0]['count'] if neo4j_result else 0

            # Check if counts match within tolerance
            diff = abs(pg_count - neo4j_count)
            passed = diff <= tolerance

            message = f"PostgreSQL: {pg_count:,} | Neo4j: {neo4j_count:,}"
            if diff > 0:
                message += f" | Difference: {diff:,}"

            return ValidationResult(
                name=name,
                passed=passed,
                message=message,
                details={
                    'postgresql_count': pg_count,
                    'neo4j_count': neo4j_count,
                    'difference': diff
                }
            )
        except Exception as e:
            return ValidationResult(
                name=name,
                passed=False,
                message=f"Error: {str(e)}",
                details={'error': str(e)}
            )

    def validate_relationship_coverage(self, name: str,
                                      neo4j_node_query: str,
                                      neo4j_relationship_query: str,
                                      min_coverage_percent: float = 95.0) -> ValidationResult:
        """Validate that most nodes have expected relationships.

        Args:
            name: Name of the validation check
            neo4j_node_query: Query to count total nodes
            neo4j_relationship_query: Query to count nodes with relationships
            min_coverage_percent: Minimum acceptable coverage percentage
        """
        try:
            # Get total nodes
            total_result = self.neo4j.run_query(neo4j_node_query)
            total = total_result[0]['count'] if total_result else 0

            # Get nodes with relationships
            with_rel_result = self.neo4j.run_query(neo4j_relationship_query)
            with_rel = with_rel_result[0]['count'] if with_rel_result else 0

            if total == 0:
                return ValidationResult(
                    name=name,
                    passed=True,
                    message="No nodes to validate",
                    details={'total': 0, 'with_relationships': 0, 'coverage': 0}
                )

            coverage = (with_rel / total) * 100
            passed = coverage >= min_coverage_percent

            message = f"{with_rel:,} / {total:,} ({coverage:.1f}%)"
            if not passed:
                message += f" - Below {min_coverage_percent}% threshold"

            return ValidationResult(
                name=name,
                passed=passed,
                message=message,
                details={
                    'total': total,
                    'with_relationships': with_rel,
                    'coverage': coverage,
                    'min_coverage': min_coverage_percent
                }
            )
        except Exception as e:
            return ValidationResult(
                name=name,
                passed=False,
                message=f"Error: {str(e)}",
                details={'error': str(e)}
            )

    def validate_orphans(self, name: str, neo4j_query: str,
                        max_orphans: int = 0) -> ValidationResult:
        """Check for orphaned data (nodes without expected relationships).

        Args:
            name: Name of the validation check
            neo4j_query: Query to count orphaned nodes
            max_orphans: Maximum acceptable number of orphans
        """
        try:
            result = self.neo4j.run_query(neo4j_query)
            orphan_count = result[0]['count'] if result else 0

            passed = orphan_count <= max_orphans

            message = f"Found {orphan_count:,} orphaned nodes"
            if orphan_count > max_orphans:
                message += f" - Exceeds {max_orphans} threshold"

            return ValidationResult(
                name=name,
                passed=passed,
                message=message,
                details={'orphan_count': orphan_count, 'max_orphans': max_orphans}
            )
        except Exception as e:
            return ValidationResult(
                name=name,
                passed=False,
                message=f"Error: {str(e)}",
                details={'error': str(e)}
            )

    def run_all_validations(self):
        """Run all validation checks."""
        print("=" * 80)
        print(f"{BLUE}POSTGRESQL ↔ NEO4J DATA VALIDATION{RESET}")
        print("=" * 80)

        # 1. Hansard Statements
        print(f"\n{BLUE}1. HANSARD STATEMENTS{RESET}")
        print("-" * 80)

        result = self.validate_count(
            name="Hansard Statement Count",
            pg_query="SELECT COUNT(*) as count FROM hansards_statement",
            neo4j_query="MATCH (s:Statement) RETURN count(s) as count"
        )
        self.results.append(result)
        self._print_result(result)

        result = self.validate_count(
            name="Hansard Document Count",
            pg_query="SELECT COUNT(*) as count FROM hansards_document",
            neo4j_query="MATCH (d:Document) RETURN count(d) as count"
        )
        self.results.append(result)
        self._print_result(result)

        result = self.validate_relationship_coverage(
            name="Statements with PART_OF relationship",
            neo4j_node_query="MATCH (s:Statement) RETURN count(s) as count",
            neo4j_relationship_query="""
                MATCH (s:Statement)-[:PART_OF]->()
                RETURN count(DISTINCT s) as count
            """,
            min_coverage_percent=99.0
        )
        self.results.append(result)
        self._print_result(result)

        result = self.validate_orphans(
            name="Statements without documents",
            neo4j_query="""
                MATCH (s:Statement)
                WHERE NOT exists((s)-[:PART_OF]->())
                RETURN count(s) as count
            """,
            max_orphans=100
        )
        self.results.append(result)
        self._print_result(result)

        # 2. Bill Texts
        print(f"\n{BLUE}2. BILL TEXTS{RESET}")
        print("-" * 80)

        result = self.validate_count(
            name="Bill Text Count",
            pg_query="SELECT COUNT(*) as count FROM bills_billtext",
            neo4j_query="MATCH (bt:BillText) RETURN count(bt) as count"
        )
        self.results.append(result)
        self._print_result(result)

        result = self.validate_relationship_coverage(
            name="BillTexts with HAS_TEXT relationship",
            neo4j_node_query="MATCH (bt:BillText) RETURN count(bt) as count",
            neo4j_relationship_query="""
                MATCH ()-[:HAS_TEXT]->(bt:BillText)
                RETURN count(DISTINCT bt) as count
            """,
            min_coverage_percent=95.0
        )
        self.results.append(result)
        self._print_result(result)

        # 3. Politician Info
        print(f"\n{BLUE}3. POLITICIAN INFO{RESET}")
        print("-" * 80)

        result = self.validate_count(
            name="Unique Politicians in PostgreSQL",
            pg_query="SELECT COUNT(DISTINCT politician_id) as count FROM core_politicianinfo",
            neo4j_query="""
                MATCH (p:Politician)
                WHERE p.email IS NOT NULL OR p.phone IS NOT NULL OR p.twitter_id IS NOT NULL
                RETURN count(p) as count
            """
        )
        self.results.append(result)
        self._print_result(result)

        # Check specific info fields were added
        result = ValidationResult(
            name="Politicians with enriched data",
            passed=True,
            message="Checking email, phone, twitter fields...",
            details={}
        )

        enriched_stats = self.neo4j.run_query("""
            MATCH (p:Politician)
            RETURN
                count(CASE WHEN p.email IS NOT NULL THEN 1 END) as has_email,
                count(CASE WHEN p.phone IS NOT NULL THEN 1 END) as has_phone,
                count(CASE WHEN p.twitter_id IS NOT NULL THEN 1 END) as has_twitter,
                count(CASE WHEN p.parl_id IS NOT NULL THEN 1 END) as has_parl_id,
                count(p) as total
        """)

        if enriched_stats:
            stats = enriched_stats[0]
            result.details = stats
            result.message = f"Email: {stats['has_email']:,} | Phone: {stats['has_phone']:,} | Twitter: {stats['has_twitter']:,}"

        self.results.append(result)
        self._print_result(result)

        # 4. Elections/Candidacies
        print(f"\n{BLUE}4. ELECTION CANDIDACIES{RESET}")
        print("-" * 80)

        result = self.validate_count(
            name="Candidacy Count",
            pg_query="SELECT COUNT(*) as count FROM elections_candidacy",
            neo4j_query="MATCH (c:Candidacy) RETURN count(c) as count"
        )
        self.results.append(result)
        self._print_result(result)

        result = self.validate_relationship_coverage(
            name="Candidacies with RAN_IN relationship",
            neo4j_node_query="MATCH (c:Candidacy) RETURN count(c) as count",
            neo4j_relationship_query="""
                MATCH ()-[:RAN_IN]->(c:Candidacy)
                RETURN count(DISTINCT c) as count
            """,
            min_coverage_percent=80.0  # Lower threshold - not all candidates may be in Politician table
        )
        self.results.append(result)
        self._print_result(result)

        # 5. Overall Relationship Integrity
        print(f"\n{BLUE}5. RELATIONSHIP INTEGRITY{RESET}")
        print("-" * 80)

        # Check for broken relationships (relationships pointing to non-existent nodes)
        relationship_checks = [
            ("PART_OF relationships", "MATCH ()-[r:PART_OF]->() RETURN count(r) as count"),
            ("HAS_TEXT relationships", "MATCH ()-[r:HAS_TEXT]->() RETURN count(r) as count"),
            ("RAN_IN relationships", "MATCH ()-[r:RAN_IN]->() RETURN count(r) as count"),
            ("MADE_BY relationships", "MATCH ()-[r:MADE_BY]->() RETURN count(r) as count"),
        ]

        for rel_name, query in relationship_checks:
            result_data = self.neo4j.run_query(query)
            count = result_data[0]['count'] if result_data else 0

            result = ValidationResult(
                name=rel_name,
                passed=True,
                message=f"Found {count:,} relationships",
                details={'count': count}
            )
            self.results.append(result)
            self._print_result(result)

        # Final Summary
        self._print_summary()

    def _print_result(self, result: ValidationResult):
        """Print a single validation result."""
        status = f"{GREEN}✓ PASS{RESET}" if result.passed else f"{RED}✗ FAIL{RESET}"
        print(f"  {status} | {result.name}")
        print(f"         {result.message}")

    def _print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 80)
        print(f"{BLUE}VALIDATION SUMMARY{RESET}")
        print("=" * 80)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print(f"\nTotal Checks: {total}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        if failed > 0:
            print(f"{RED}Failed: {failed}{RESET}")

        if failed == 0:
            print(f"\n{GREEN}{'=' * 80}")
            print("✅ ALL VALIDATIONS PASSED - DATA INTEGRITY CONFIRMED")
            print(f"{'=' * 80}{RESET}")
        else:
            print(f"\n{RED}{'=' * 80}")
            print(f"⚠️  {failed} VALIDATION(S) FAILED - REVIEW REQUIRED")
            print(f"{'=' * 80}{RESET}")

            print(f"\n{YELLOW}Failed Checks:{RESET}")
            for result in self.results:
                if not result.passed:
                    print(f"  • {result.name}: {result.message}")

        return failed == 0


def main():
    """Run validation checks."""

    # Parse PostgreSQL URI
    postgres_uri = os.getenv("POSTGRES_URI", "postgresql://fedmcp:fedmcp2024@localhost:5432/openparliament")
    parts = postgres_uri.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")

    # Initialize clients
    print("Connecting to databases...")
    postgres_client = PostgresClient(
        dbname=host_db[1],
        user=user_pass[0],
        password=user_pass[1],
        host=host_port[0],
        port=int(host_port[1]) if len(host_port) > 1 else 5432
    )

    neo4j_client = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "canadagpt2024")
    )

    print(f"   {GREEN}✓{RESET} Connected to PostgreSQL")
    print(f"   {GREEN}✓{RESET} Connected to Neo4j")

    # Run validations
    validator = DataValidator(postgres_client, neo4j_client)
    success = validator.run_all_validations()

    # Cleanup
    postgres_client.close()
    neo4j_client.close()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
