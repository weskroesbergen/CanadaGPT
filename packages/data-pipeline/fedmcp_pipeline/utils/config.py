"""Configuration management for data pipeline."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Config:
    """Configuration loaded from environment variables."""

    def __init__(self, env_file: Optional[Path] = None):
        """
        Load configuration from .env file and environment variables.

        Args:
            env_file: Path to .env file (optional, defaults to .env in current directory)
        """
        if env_file is None:
            # Look for .env in current directory, then parent directories
            current = Path.cwd()
            for parent in [current, *current.parents]:
                env_path = parent / ".env"
                if env_path.exists():
                    env_file = env_path
                    break

        if env_file and env_file.exists():
            load_dotenv(env_file)

        # Neo4j connection (required)
        self.neo4j_uri = os.getenv("NEO4J_URI")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD")

        if not self.neo4j_uri or not self.neo4j_password:
            raise ValueError(
                "NEO4J_URI and NEO4J_PASSWORD must be set in environment or .env file"
            )

        # PostgreSQL connection (optional, uses POSTGRES_URI or DATABASE_URL)
        self.postgres_uri = os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL")

        # CanLII API (optional)
        self.canlii_api_key = os.getenv("CANLII_API_KEY")

        # Pipeline configuration
        self.batch_size = int(os.getenv("BATCH_SIZE", "10000"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.incremental_lookback_days = int(os.getenv("INCREMENTAL_LOOKBACK_DAYS", "7"))

    def validate(self) -> None:
        """Validate configuration and test Neo4j connection."""
        from .neo4j_client import Neo4jClient

        client = Neo4jClient(self.neo4j_uri, self.neo4j_user, self.neo4j_password)
        try:
            client.test_connection()
            print(f"✅ Neo4j connection successful: {self.neo4j_uri}")
        finally:
            client.close()

    def __repr__(self) -> str:
        return (
            f"Config(neo4j_uri={self.neo4j_uri[:30]}..., "
            f"batch_size={self.batch_size}, "
            f"log_level={self.log_level}, "
            f"canlii_api_key={'***' if self.canlii_api_key else None})"
        )
