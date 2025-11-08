"""PostgreSQL client for OpenParliament database access."""

from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from psycopg2.pool import SimpleConnectionPool

from .progress import logger


class PostgresClient:
    """
    PostgreSQL client for OpenParliament data access.

    Supports:
    - Connection pooling
    - Named tuple results (dict-like access)
    - Batch operations
    - Transaction management
    """

    def __init__(
        self,
        dbname: str,
        user: str,
        password: str,
        host: str = "localhost",
        port: int = 5432,
        min_connections: int = 1,
        max_connections: int = 10,
    ):
        """
        Initialize PostgreSQL connection pool.

        Args:
            dbname: Database name (e.g., "openparliament")
            user: Username
            password: Password
            host: Database host (default: localhost)
            port: Database port (default: 5432)
            min_connections: Minimum pooled connections
            max_connections: Maximum pooled connections
        """
        self.dbname = dbname
        self.user = user
        self.host = host
        self.port = port

        try:
            self.pool = SimpleConnectionPool(
                min_connections,
                max_connections,
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port,
            )
            logger.debug(f"PostgreSQL pool created: {host}:{port}/{dbname}")
        except psycopg2.Error as e:
            logger.error(f"Failed to create PostgreSQL pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager).

        Usage:
            with client.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM table")
                    results = cur.fetchall()
        """
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: bool = True,
        dict_cursor: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL query to execute
            params: Query parameters (tuple)
            fetch: Whether to fetch results (default: True)
            dict_cursor: Use RealDictCursor for dict-like access (default: True)

        Returns:
            List of result rows as dictionaries (if dict_cursor=True) or tuples
        """
        with self.get_connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            with conn.cursor(cursor_factory=cursor_factory) as cur:
                cur.execute(query, params)
                if fetch:
                    results = cur.fetchall()
                    return [dict(row) for row in results] if dict_cursor else results
                return []

    def execute_batch(
        self,
        query: str,
        data: List[Tuple],
        page_size: int = 1000,
    ) -> int:
        """
        Execute a batch INSERT/UPDATE operation.

        Args:
            query: SQL query with placeholders (e.g., "INSERT INTO table VALUES (%s, %s)")
            data: List of tuples containing row data
            page_size: Batch size for execution

        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, query, data, page_size=page_size)
                conn.commit()
                return cur.rowcount

    def get_table_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.

        Args:
            table_name: Name of the table (must be in public schema)

        Returns:
            Row count
        """
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.execute_query(query, dict_cursor=True)
        return result[0]['count'] if result else 0

    def get_table_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all tables in the public schema.

        Returns:
            List of dicts with table_name, row_count, size
        """
        query = """
        SELECT
            schemaname,
            tablename as table_name,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """
        return self.execute_query(query, dict_cursor=True)

    def close(self):
        """Close all connections in the pool."""
        if self.pool:
            self.pool.closeall()
            logger.debug(f"PostgreSQL pool closed: {self.host}:{self.port}/{self.dbname}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
