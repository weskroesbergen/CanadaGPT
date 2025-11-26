"""Neo4j client with batch operations support."""

from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable, AuthError

from .progress import logger


class Neo4jClient:
    """
    Neo4j client for batch data ingestion.

    Supports:
    - Batch CREATE/MERGE operations using UNWIND
    - Transaction management
    - Connection pooling
    - Error handling with retries
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 50,
    ):
        """
        Initialize Neo4j driver.

        Args:
            uri: Neo4j connection URI (e.g., neo4j+s://xxxxx.databases.neo4j.io)
            user: Username (usually "neo4j")
            password: Password
            max_connection_lifetime: Max lifetime of pooled connections (seconds)
            max_connection_pool_size: Max number of pooled connections
        """
        self.uri = uri
        self.user = user

        try:
            self.driver: Driver = GraphDatabase.driver(
                uri,
                auth=(user, password),
                max_connection_lifetime=max_connection_lifetime,
                max_connection_pool_size=max_connection_pool_size,
            )
            logger.debug(f"Neo4j driver created: {uri}")
        except Exception as e:
            logger.error(f"Failed to create Neo4j driver: {e}")
            raise

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection and return server info.

        Returns:
            Dict with server version, database name, etc.

        Raises:
            ServiceUnavailable: If Neo4j is unreachable
            AuthError: If credentials are invalid
        """
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    CALL dbms.components() YIELD name, versions, edition
                    RETURN name, versions[0] AS version, edition
                    """
                )
                record = result.single()
                info = {
                    "name": record["name"],
                    "version": record["version"],
                    "edition": record["edition"],
                }
                logger.info(f"Connected to Neo4j {info['version']} ({info['edition']})")
                return info
        except ServiceUnavailable as e:
            logger.error(f"Neo4j unreachable: {e}")
            raise
        except AuthError as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def close(self) -> None:
        """Close driver and release all connections."""
        if self.driver:
            self.driver.close()
            logger.debug("Neo4j driver closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ============================================
    # Batch Operations (UNWIND)
    # ============================================

    def batch_create_nodes(
        self,
        label: str,
        properties_list: List[Dict[str, Any]],
        batch_size: int = 10000,
    ) -> int:
        """
        Create nodes in batches using UNWIND.

        Args:
            label: Node label (e.g., "MP", "Bill")
            properties_list: List of property dicts for each node
            batch_size: Number of nodes per transaction

        Returns:
            Total number of nodes created

        Example:
            >>> client.batch_create_nodes("MP", [
            ...     {"id": "mp-1", "name": "Alice"},
            ...     {"id": "mp-2", "name": "Bob"},
            ... ])
        """
        total_created = 0

        query = f"""
        UNWIND $batch AS properties
        CREATE (n:{label})
        SET n = properties
        """

        with self.driver.session() as session:
            for i in range(0, len(properties_list), batch_size):
                batch = properties_list[i : i + batch_size]
                result = session.run(query, batch=batch)
                summary = result.consume()
                created = summary.counters.nodes_created
                total_created += created
                logger.debug(
                    f"Created {created} {label} nodes (batch {i // batch_size + 1})"
                )

        logger.info(f"Created {total_created:,} {label} nodes total")
        return total_created

    def batch_merge_nodes(
        self,
        label: str,
        properties_list: List[Dict[str, Any]],
        merge_keys: List[str],
        batch_size: int = 10000,
        max_retries: int = 3,
    ) -> int:
        """
        Merge nodes in batches (create if missing, update if exists).

        Args:
            label: Node label
            properties_list: List of property dicts
            merge_keys: Properties to match on (e.g., ["id"] or ["number", "session"])
            batch_size: Nodes per transaction
            max_retries: Maximum retry attempts for connection errors

        Returns:
            Total number of nodes created or updated

        Example:
            >>> client.batch_merge_nodes("MP", [
            ...     {"id": "mp-1", "name": "Alice", "party": "Liberal"},
            ... ], merge_keys=["id"])
        """
        import time
        total_processed = 0

        # Build MERGE clause dynamically based on merge_keys
        merge_props = ", ".join([f"{key}: properties.{key}" for key in merge_keys])
        query = f"""
        UNWIND $batch AS properties
        MERGE (n:{label} {{{merge_props}}})
        SET n += properties
        """

        for i in range(0, len(properties_list), batch_size):
            batch = properties_list[i : i + batch_size]

            for attempt in range(max_retries):
                try:
                    with self.driver.session() as session:
                        result = session.run(query, batch=batch)
                        summary = result.consume()
                        created = summary.counters.nodes_created
                        props_set = summary.counters.properties_set
                        total_processed += len(batch)
                        logger.debug(
                            f"Merged {label} nodes: {created} created, "
                            f"{props_set} properties set (batch {i // batch_size + 1})"
                        )
                    break  # Success, exit retry loop
                except ServiceUnavailable as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Connection error in batch_merge (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Batch merge failed after {max_retries} attempts: {e}")
                        raise

        logger.info(f"Merged {total_processed:,} {label} nodes total")
        return total_processed

    def batch_create_relationships(
        self,
        rel_type: str,
        relationships: List[Dict[str, Any]],
        from_label: str,
        to_label: str,
        from_key: str = "id",
        to_key: str = "id",
        batch_size: int = 10000,
    ) -> int:
        """
        Create relationships in batches using UNWIND.

        Args:
            rel_type: Relationship type (e.g., "MEMBER_OF", "VOTED")
            relationships: List of dicts with keys:
                - from_id: Source node ID
                - to_id: Target node ID
                - properties (optional): Relationship properties
            from_label: Source node label
            to_label: Target node label
            from_key: Property name for source node lookup (default: "id")
            to_key: Property name for target node lookup (default: "id")
            batch_size: Relationships per transaction

        Returns:
            Total number of relationships created

        Example:
            >>> client.batch_create_relationships("MEMBER_OF", [
            ...     {"from_id": "mp-1", "to_id": "liberal"},
            ...     {"from_id": "mp-2", "to_id": "conservative"},
            ... ], from_label="MP", to_label="Party")

            >>> # With relationship properties
            >>> client.batch_create_relationships("VOTED", [
            ...     {"from_id": "mp-1", "to_id": "vote-123", "properties": {"position": "yea"}},
            ... ], from_label="MP", to_label="Vote")
        """
        total_created = 0

        query = f"""
        UNWIND $batch AS rel
        MATCH (from:{from_label} {{{from_key}: rel.from_id}})
        MATCH (to:{to_label} {{{to_key}: rel.to_id}})
        CREATE (from)-[r:{rel_type}]->(to)
        SET r = COALESCE(rel.properties, {{}})
        """

        with self.driver.session() as session:
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i : i + batch_size]
                result = session.run(query, batch=batch)
                summary = result.consume()
                created = summary.counters.relationships_created
                total_created += created
                logger.debug(
                    f"Created {created} {rel_type} relationships (batch {i // batch_size + 1})"
                )

        logger.info(f"Created {total_created:,} {rel_type} relationships total")
        return total_created

    def batch_merge_relationships(
        self,
        rel_type: str,
        relationships: List[Dict[str, Any]],
        from_label: str,
        to_label: str,
        from_key: str = "id",
        to_key: str = "id",
        batch_size: int = 10000,
    ) -> int:
        """
        Merge relationships (create if missing, update if exists).

        Same signature as batch_create_relationships but uses MERGE instead of CREATE.
        """
        total_processed = 0

        query = f"""
        UNWIND $batch AS rel
        MATCH (from:{from_label} {{{from_key}: rel.from_id}})
        MATCH (to:{to_label} {{{to_key}: rel.to_id}})
        MERGE (from)-[r:{rel_type}]->(to)
        SET r += COALESCE(rel.properties, {{}})
        """

        with self.driver.session() as session:
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i : i + batch_size]
                result = session.run(query, batch=batch)
                summary = result.consume()
                created = summary.counters.relationships_created
                props_set = summary.counters.properties_set
                total_processed += len(batch)
                logger.debug(
                    f"Merged {rel_type} relationships: {created} created, "
                    f"{props_set} properties set (batch {i // batch_size + 1})"
                )

        logger.info(f"Merged {total_processed:,} {rel_type} relationships total")
        return total_processed

    # ============================================
    # Query Utilities
    # ============================================

    def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results as a list.

        Args:
            query: Cypher query string
            parameters: Query parameters (optional)
            max_retries: Maximum number of retry attempts for connection errors

        Returns:
            List of records as dictionaries

        Example:
            >>> result = client.run_query("MATCH (m:MP) RETURN count(m) AS count")
            >>> count = result[0]["count"]
        """
        import time

        for attempt in range(max_retries):
            try:
                with self.driver.session() as session:
                    result = session.run(query, parameters or {})
                    return [dict(record) for record in result]
            except ServiceUnavailable as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Connection failed after {max_retries} attempts: {e}")
                    raise

    def count_nodes(self, label: str) -> int:
        """Count nodes with given label."""
        result = self.run_query(f"MATCH (n:{label}) RETURN count(n) AS count")
        return result[0]["count"]

    def count_relationships(self, rel_type: str) -> int:
        """Count relationships of given type."""
        result = self.run_query(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count")
        return result[0]["count"]

    def clear_database(self, confirm: bool = False) -> None:
        """
        Delete all nodes and relationships.

        Args:
            confirm: Must be True to execute (safety check)

        WARNING: This is destructive! Use only for testing or clean slate.
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to clear database")

        logger.warning("Clearing entire database...")
        with self.driver.session() as session:
            # Delete in batches to avoid memory issues
            while True:
                result = session.run("MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(n) AS deleted")
                deleted = result.single()["deleted"]
                if deleted == 0:
                    break
                logger.debug(f"Deleted {deleted} nodes")

        logger.info("Database cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dict with node count, relationship count, labels, relationship types
        """
        with self.driver.session() as session:
            # Node count by label
            result = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count")
            node_counts = {record["label"]: record["count"] for record in result}

            # Relationship count by type
            result = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count")
            rel_counts = {record["type"]: record["count"] for record in result}

            # Total counts
            total_nodes = sum(node_counts.values())
            total_rels = sum(rel_counts.values())

            return {
                "total_nodes": total_nodes,
                "total_relationships": total_rels,
                "node_counts": node_counts,
                "relationship_counts": rel_counts,
            }
