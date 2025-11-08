"""Command-line interface for CanadaGPT data pipeline."""

import argparse
import sys
from pathlib import Path

from .utils.config import Config
from .utils.neo4j_client import Neo4jClient
from .utils.progress import logger

from .ingest.parliament import ingest_parliament_data
from .ingest.lobbying import ingest_lobbying_data
from .ingest.finances import ingest_financial_data

from .relationships.political import build_political_structure
from .relationships.legislative import build_legislative_relationships
from .relationships.lobbying import build_lobbying_network
from .relationships.financial import build_financial_flows


def run_full_pipeline(config: Config) -> None:
    """Run complete data ingestion pipeline."""
    logger.info("🚀 Starting FULL PIPELINE")
    logger.info(f"Neo4j URI: {config.neo4j_uri}")
    logger.info(f"Batch size: {config.batch_size:,}")
    logger.info("")

    with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as client:
        # Test connection
        client.test_connection()

        # 1. Parliament data
        ingest_parliament_data(client, batch_size=config.batch_size)

        # 2. Lobbying data
        ingest_lobbying_data(client, batch_size=config.batch_size)

        # 3. Financial data
        ingest_financial_data(client, batch_size=config.batch_size)

        # 4. Build relationships
        build_political_structure(client, batch_size=config.batch_size)
        build_legislative_relationships(client, batch_size=config.batch_size)
        build_lobbying_network(client, batch_size=config.batch_size)
        build_financial_flows(client, batch_size=config.batch_size)

        # 5. Show final stats
        stats = client.get_stats()
        logger.info("=" * 60)
        logger.success("✅ FULL PIPELINE COMPLETE")
        logger.info(f"Total nodes: {stats['total_nodes']:,}")
        logger.info(f"Total relationships: {stats['total_relationships']:,}")
        logger.info("")
        logger.info("Top node types:")
        for label, count in sorted(stats['node_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {label}: {count:,}")
        logger.info("")
        logger.info("Top relationship types:")
        for rel_type, count in sorted(stats['relationship_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {rel_type}: {count:,}")
        logger.info("=" * 60)


def run_parliament_only(config: Config) -> None:
    """Run only parliamentary data ingestion."""
    logger.info("🏛️  Starting PARLIAMENT INGESTION")

    with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as client:
        client.test_connection()
        ingest_parliament_data(client, batch_size=config.batch_size)
        build_political_structure(client, batch_size=config.batch_size)


def run_lobbying_only(config: Config) -> None:
    """Run only lobbying data ingestion."""
    logger.info("🤝 Starting LOBBYING INGESTION")

    with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as client:
        client.test_connection()
        ingest_lobbying_data(client, batch_size=config.batch_size)


def run_finances_only(config: Config) -> None:
    """Run only financial data ingestion."""
    logger.info("💰 Starting FINANCIAL INGESTION")

    with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as client:
        client.test_connection()
        ingest_financial_data(client, batch_size=config.batch_size)


def run_relationships_only(config: Config) -> None:
    """Build relationships only (assumes data already loaded)."""
    logger.info("🔗 Starting RELATIONSHIP BUILDING")

    with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as client:
        client.test_connection()
        build_political_structure(client, batch_size=config.batch_size)
        build_legislative_relationships(client, batch_size=config.batch_size)
        build_lobbying_network(client, batch_size=config.batch_size)
        build_financial_flows(client, batch_size=config.batch_size)


def test_connection(config: Config) -> None:
    """Test Neo4j connection and show database stats."""
    logger.info("🔍 Testing Neo4j connection...")

    with Neo4jClient(config.neo4j_uri, config.neo4j_user, config.neo4j_password) as client:
        info = client.test_connection()
        stats = client.get_stats()

        logger.info("")
        logger.success("✅ Connection successful!")
        logger.info(f"Server: {info['name']} {info['version']} ({info['edition']})")
        logger.info(f"Total nodes: {stats['total_nodes']:,}")
        logger.info(f"Total relationships: {stats['total_relationships']:,}")

        if stats['total_nodes'] > 0:
            logger.info("")
            logger.info("Node counts:")
            for label, count in sorted(stats['node_counts'].items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {label}: {count:,}")

        if stats['total_relationships'] > 0:
            logger.info("")
            logger.info("Relationship counts:")
            for rel_type, count in sorted(stats['relationship_counts'].items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {rel_type}: {count:,}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CanadaGPT Data Pipeline - Ingest Canadian government data into Neo4j",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline (initial load, ~4-6 hours)
  canadagpt-ingest --full

  # Test connection and show stats
  canadagpt-ingest --test

  # Ingest only parliament data
  canadagpt-ingest --parliament

  # Build only relationships (assumes data loaded)
  canadagpt-ingest --relationships

  # Validate configuration
  canadagpt-ingest --validate
        """,
    )

    # Pipeline modes (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--full", action="store_true", help="Run full pipeline (all data + relationships)")
    mode_group.add_argument("--parliament", action="store_true", help="Ingest only parliamentary data")
    mode_group.add_argument("--lobbying", action="store_true", help="Ingest only lobbying data")
    mode_group.add_argument("--finances", action="store_true", help="Ingest only financial data")
    mode_group.add_argument("--relationships", action="store_true", help="Build relationships only")
    mode_group.add_argument("--test", action="store_true", help="Test connection and show stats")
    mode_group.add_argument("--validate", action="store_true", help="Validate configuration")
    mode_group.add_argument("--incremental", action="store_true", help="Incremental update (TODO)")

    # Configuration options
    parser.add_argument("--env-file", type=Path, help="Path to .env file (default: auto-detect)")
    parser.add_argument("--batch-size", type=int, help="Batch size for Neo4j operations (default: 10000)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Load configuration
    try:
        config = Config(env_file=args.env_file)

        # Override batch size if specified
        if args.batch_size:
            config.batch_size = args.batch_size

        # Set log level
        if args.verbose:
            config.log_level = "DEBUG"

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.info("Create a .env file with NEO4J_URI and NEO4J_PASSWORD")
        logger.info("See .env.example for template")
        sys.exit(1)

    # Execute requested mode
    try:
        if args.validate:
            logger.info("Validating configuration...")
            config.validate()
            logger.success("✅ Configuration is valid")

        elif args.test:
            test_connection(config)

        elif args.full:
            run_full_pipeline(config)

        elif args.parliament:
            run_parliament_only(config)

        elif args.lobbying:
            run_lobbying_only(config)

        elif args.finances:
            run_finances_only(config)

        elif args.relationships:
            run_relationships_only(config)

        elif args.incremental:
            logger.error("Incremental mode not yet implemented")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
