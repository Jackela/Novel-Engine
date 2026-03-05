"""Connection Manager Module.

Manages Neo4j driver connections and connection pooling.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import structlog

from src.contexts.knowledge.application.ports.i_graph_store import GraphStoreError

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages Neo4j database connections."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "neo4j",
    ) -> None:
        """Initialize connection manager.

        Args:
            uri: Bolt connection URI
            user: Database username
            password: Database password
            database: Database name
        """
        self._uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD", "")
        self._database = database

        self._driver: Any = None
        self._connected = False

    def get_driver(self) -> Any:
        """Get or create Neo4j driver instance."""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(
                    self._uri,
                    auth=(self._user, self._password),
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=60,
                )
                self._connected = True
                logger.info(f"Connected to Neo4j at {self._uri}")
            except ImportError:
                raise GraphStoreError(
                    "neo4j package is not installed. Install with: pip install neo4j>=5.0.0",
                    code="DRIVER_NOT_AVAILABLE",
                    details={"uri": self._uri},
                )
            except Exception as e:
                raise GraphStoreError(
                    f"Failed to connect to Neo4j at {self._uri}",
                    code="CONNECTION_FAILED",
                    details={"error": str(e), "uri": self._uri},
                ) from e

        return self._driver

    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("Closed Neo4j connection")

    def is_connected(self) -> bool:
        """Check if connection is established."""
        return self._connected

    def health_check(self) -> bool:
        """Verify connection is healthy."""
        try:
            driver = self.get_driver()
            with driver.session(database=self._database) as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                return record is not None
        except Exception:
            return False

    def __enter__(self) -> ConnectionManager:
        """Context manager entry."""
        self.get_driver()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


__all__ = ["ConnectionManager"]
