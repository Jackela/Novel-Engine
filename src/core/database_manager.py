#!/usr/bin/env python3
"""
Database Connection Pool Manager
===============================

Enterprise-grade database connection management with connection pooling,
health monitoring, and automatic failover.
"""

import asyncio
import aiosqlite
import logging
import time
import threading
from typing import Dict, List, Optional, Any, AsyncContextManager, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
import json

from .config_manager import ConfigurationManager
from .error_handler import CentralizedErrorHandler, ErrorContext, ErrorCategory

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    REDIS = "redis"


class ConnectionState(Enum):
    """Database connection states."""
    IDLE = "idle"
    ACTIVE = "active"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


@dataclass
class DatabaseConfig:
    """Database configuration parameters."""
    database_type: DatabaseType = DatabaseType.SQLITE
    connection_string: str = "data/novel_engine.db"
    min_pool_size: int = 2
    max_pool_size: int = 20
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0  # 5 minutes
    health_check_interval: float = 60.0  # 1 minute
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_wal_mode: bool = True
    enable_foreign_keys: bool = True
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    cache_size: int = 10000
    temp_store: str = "memory"
    busy_timeout: int = 30000  # 30 seconds


@dataclass
class ConnectionMetrics:
    """Connection performance metrics."""
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    average_query_time: float = 0.0
    last_error: Optional[str] = None
    last_health_check: Optional[datetime] = None
    health_status: bool = True


class DatabaseConnection:
    """Managed database connection wrapper."""
    
    def __init__(self, connection: aiosqlite.Connection, config: DatabaseConfig):
        """Initialize database connection wrapper."""
        self.connection = connection
        self.config = config
        self.state = ConnectionState.IDLE
        self.metrics = ConnectionMetrics()
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        self._last_activity = datetime.now()
        
    async def initialize(self) -> None:
        """Initialize connection with database-specific settings."""
        try:
            if self.config.database_type == DatabaseType.SQLITE:
                await self._initialize_sqlite()
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.debug("Database connection initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    async def _initialize_sqlite(self) -> None:
        """Initialize SQLite-specific settings."""
        settings = [
            f"PRAGMA journal_mode = {self.config.journal_mode}",
            f"PRAGMA synchronous = {self.config.synchronous}",
            f"PRAGMA cache_size = {self.config.cache_size}",
            f"PRAGMA temp_store = {self.config.temp_store}",
            f"PRAGMA busy_timeout = {self.config.busy_timeout}",
        ]
        
        if self.config.enable_foreign_keys:
            settings.append("PRAGMA foreign_keys = ON")
        
        for setting in settings:
            try:
                await self.connection.execute(setting)
                logger.debug(f"Applied SQLite setting: {setting}")
            except Exception as e:
                logger.warning(f"Failed to apply SQLite setting {setting}: {e}")
        
        await self.connection.commit()
    
    async def execute(self, query: str, parameters: tuple = None) -> aiosqlite.Cursor:
        """Execute query with metrics tracking."""
        async with self._lock:
            self.state = ConnectionState.ACTIVE
            self._last_activity = datetime.now()
            
            start_time = time.time()
            try:
                cursor = await self.connection.execute(query, parameters or ())
                execution_time = time.time() - start_time
                
                # Update metrics
                self.metrics.total_queries += 1
                self.metrics.successful_queries += 1
                self.metrics.last_used = datetime.now()
                
                # Update average query time
                if self.metrics.total_queries == 1:
                    self.metrics.average_query_time = execution_time
                else:
                    current_avg = self.metrics.average_query_time
                    total_queries = self.metrics.total_queries
                    self.metrics.average_query_time = (
                        (current_avg * (total_queries - 1) + execution_time) / total_queries
                    )
                
                return cursor
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                # Update error metrics
                self.metrics.total_queries += 1
                self.metrics.failed_queries += 1
                self.metrics.last_error = str(e)
                
                logger.error(f"Query execution failed: {e}")
                raise
                
            finally:
                self.state = ConnectionState.IDLE
    
    async def executemany(self, query: str, parameters: List[tuple]) -> aiosqlite.Cursor:
        """Execute many queries with metrics tracking."""
        async with self._lock:
            self.state = ConnectionState.ACTIVE
            self._last_activity = datetime.now()
            
            start_time = time.time()
            try:
                cursor = await self.connection.executemany(query, parameters)
                execution_time = time.time() - start_time
                
                # Update metrics
                batch_size = len(parameters)
                self.metrics.total_queries += batch_size
                self.metrics.successful_queries += batch_size
                self.metrics.last_used = datetime.now()
                
                # Update average query time (per query in batch)
                avg_time_per_query = execution_time / batch_size if batch_size > 0 else 0
                if self.metrics.total_queries == batch_size:
                    self.metrics.average_query_time = avg_time_per_query
                else:
                    current_avg = self.metrics.average_query_time
                    total_queries = self.metrics.total_queries
                    self.metrics.average_query_time = (
                        (current_avg * (total_queries - batch_size) + execution_time) / total_queries
                    )
                
                return cursor
                
            except Exception as e:
                batch_size = len(parameters)
                
                # Update error metrics
                self.metrics.total_queries += batch_size
                self.metrics.failed_queries += batch_size
                self.metrics.last_error = str(e)
                
                logger.error(f"Batch query execution failed: {e}")
                raise
                
            finally:
                self.state = ConnectionState.IDLE
    
    async def commit(self) -> None:
        """Commit transaction."""
        async with self._lock:
            await self.connection.commit()
    
    async def rollback(self) -> None:
        """Rollback transaction."""
        async with self._lock:
            await self.connection.rollback()
    
    async def close(self) -> None:
        """Close connection and cleanup."""
        async with self._lock:
            self.state = ConnectionState.CLOSED
            
            # Cancel health check task
            if self._health_check_task and not self._health_check_task.done():
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Close connection
            await self.connection.close()
            logger.debug("Database connection closed")
    
    async def health_check(self) -> bool:
        """Perform connection health check."""
        try:
            async with self._lock:
                # Simple query to test connection
                cursor = await self.connection.execute("SELECT 1")
                await cursor.fetchone()
                
                self.metrics.health_status = True
                self.metrics.last_health_check = datetime.now()
                
                return True
                
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            self.metrics.health_status = False
            self.metrics.last_error = str(e)
            self.state = ConnectionState.UNHEALTHY
            return False
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while self.state != ConnectionState.CLOSED:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if self.state == ConnectionState.CLOSED:
                    break
                
                await self.health_check()
                
                # Check for idle timeout
                idle_time = (datetime.now() - self._last_activity).total_seconds()
                if idle_time > self.config.idle_timeout:
                    logger.debug(f"Connection idle for {idle_time}s, marking for cleanup")
                    self.state = ConnectionState.UNHEALTHY
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        return (self.state in [ConnectionState.IDLE, ConnectionState.ACTIVE] and 
                self.metrics.health_status)
    
    @property
    def is_idle(self) -> bool:
        """Check if connection is idle."""
        return self.state == ConnectionState.IDLE
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection metrics."""
        return {
            'state': self.state.value,
            'created_at': self.metrics.created_at.isoformat(),
            'last_used': self.metrics.last_used.isoformat(),
            'total_queries': self.metrics.total_queries,
            'successful_queries': self.metrics.successful_queries,
            'failed_queries': self.metrics.failed_queries,
            'success_rate': (
                self.metrics.successful_queries / self.metrics.total_queries 
                if self.metrics.total_queries > 0 else 0.0
            ),
            'average_query_time': self.metrics.average_query_time,
            'health_status': self.metrics.health_status,
            'last_health_check': (
                self.metrics.last_health_check.isoformat() 
                if self.metrics.last_health_check else None
            ),
            'last_error': self.metrics.last_error
        }


class DatabaseConnectionPool:
    """
    Database connection pool manager.
    
    Features:
    - Connection pooling with min/max limits
    - Health monitoring and automatic recovery
    - Connection lifecycle management
    - Performance metrics and monitoring
    - Automatic connection cleanup
    """
    
    def __init__(self, config: DatabaseConfig, 
                 error_handler: Optional[CentralizedErrorHandler] = None):
        """Initialize connection pool."""
        self.config = config
        self.error_handler = error_handler
        
        # Connection pool
        self._available_connections: List[DatabaseConnection] = []
        self._active_connections: Dict[int, DatabaseConnection] = {}
        self._connection_counter = 0
        
        # Pool management
        self._pool_lock = asyncio.Lock()
        self._initialization_lock = asyncio.Lock()
        self._initialized = False
        self._closed = False
        
        # Background tasks
        self._maintenance_task: Optional[asyncio.Task] = None
        
        # Metrics
        self._pool_metrics = {
            'total_connections_created': 0,
            'total_connections_closed': 0,
            'peak_active_connections': 0,
            'total_queries_executed': 0,
            'average_pool_utilization': 0.0,
            'connection_wait_times': []
        }
        
        logger.info(f"Database connection pool initialized for {config.database_type.value}")
    
    async def initialize(self) -> None:
        """Initialize connection pool."""
        async with self._initialization_lock:
            if self._initialized:
                return
            
            # Create minimum number of connections
            for _ in range(self.config.min_pool_size):
                try:
                    connection = await self._create_connection()
                    self._available_connections.append(connection)
                    self._pool_metrics['total_connections_created'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to create initial connection: {e}")
                    if self.error_handler:
                        error_context = ErrorContext(
                            component="DatabaseConnectionPool",
                            operation="initialize",
                            metadata={'database_type': self.config.database_type.value}
                        )
                        await self.error_handler.handle_error(e, error_context)
                    raise
            
            # Start maintenance task
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())
            
            self._initialized = True
            logger.info(f"Connection pool initialized with {len(self._available_connections)} connections")
    
    async def get_connection(self) -> AsyncContextManager[DatabaseConnection]:
        """Get connection from pool with context manager."""
        return self._connection_context()
    
    @asynccontextmanager
    async def _connection_context(self) -> DatabaseConnection:
        """Connection context manager."""
        connection = await self._acquire_connection()
        try:
            yield connection
        finally:
            await self._release_connection(connection)
    
    async def _acquire_connection(self) -> DatabaseConnection:
        """Acquire connection from pool."""
        if not self._initialized:
            await self.initialize()
        
        wait_start = time.time()
        
        async with self._pool_lock:
            # Try to get available connection
            while self._available_connections:
                connection = self._available_connections.pop(0)
                
                # Check if connection is healthy
                if connection.is_healthy:
                    connection_id = id(connection)
                    self._active_connections[connection_id] = connection
                    
                    # Update metrics
                    active_count = len(self._active_connections)
                    if active_count > self._pool_metrics['peak_active_connections']:
                        self._pool_metrics['peak_active_connections'] = active_count
                    
                    wait_time = time.time() - wait_start
                    self._pool_metrics['connection_wait_times'].append(wait_time)
                    if len(self._pool_metrics['connection_wait_times']) > 1000:
                        self._pool_metrics['connection_wait_times'] = self._pool_metrics['connection_wait_times'][-1000:]
                    
                    return connection
                else:
                    # Connection is unhealthy, close it
                    await self._close_connection(connection)
            
            # No available connections, create new one if under max limit
            total_connections = len(self._available_connections) + len(self._active_connections)
            
            if total_connections < self.config.max_pool_size:
                try:
                    connection = await self._create_connection()
                    connection_id = id(connection)
                    self._active_connections[connection_id] = connection
                    
                    self._pool_metrics['total_connections_created'] += 1
                    
                    # Update peak active connections
                    active_count = len(self._active_connections)
                    if active_count > self._pool_metrics['peak_active_connections']:
                        self._pool_metrics['peak_active_connections'] = active_count
                    
                    wait_time = time.time() - wait_start
                    self._pool_metrics['connection_wait_times'].append(wait_time)
                    
                    return connection
                    
                except Exception as e:
                    logger.error(f"Failed to create new connection: {e}")
                    raise
            
            # Pool exhausted, wait for connection to become available
            logger.warning("Connection pool exhausted, waiting for available connection")
            
            # Wait with timeout
            timeout = self.config.connection_timeout
            end_time = time.time() + timeout
            
            while time.time() < end_time:
                await asyncio.sleep(0.1)  # Small delay
                
                # Check for available connections
                if self._available_connections:
                    # Retry acquisition
                    return await self._acquire_connection()
            
            raise RuntimeError(f"Connection pool timeout after {timeout}s")
    
    async def _release_connection(self, connection: DatabaseConnection) -> None:
        """Release connection back to pool."""
        async with self._pool_lock:
            connection_id = id(connection)
            
            if connection_id in self._active_connections:
                del self._active_connections[connection_id]
                
                # Check if connection is still healthy
                if connection.is_healthy and not self._closed:
                    self._available_connections.append(connection)
                else:
                    # Connection is unhealthy or pool is closed, close it
                    await self._close_connection(connection)
    
    async def _create_connection(self) -> DatabaseConnection:
        """Create new database connection."""
        if self.config.database_type == DatabaseType.SQLITE:
            # Ensure database directory exists
            db_path = Path(self.config.connection_string)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            raw_connection = await aiosqlite.connect(
                self.config.connection_string,
                timeout=self.config.connection_timeout
            )
            
            connection = DatabaseConnection(raw_connection, self.config)
            await connection.initialize()
            
            return connection
        
        else:
            raise NotImplementedError(f"Database type {self.config.database_type.value} not implemented")
    
    async def _close_connection(self, connection: DatabaseConnection) -> None:
        """Close and cleanup connection."""
        try:
            await connection.close()
            self._pool_metrics['total_connections_closed'] += 1
            
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
    
    async def close_pool(self) -> None:
        """Close all connections and shutdown pool."""
        async with self._pool_lock:
            self._closed = True
            
            # Cancel maintenance task
            if self._maintenance_task and not self._maintenance_task.done():
                self._maintenance_task.cancel()
                try:
                    await self._maintenance_task
                except asyncio.CancelledError:
                    pass
            
            # Close all available connections
            for connection in self._available_connections:
                await self._close_connection(connection)
            
            self._available_connections.clear()
            
            # Close all active connections
            for connection in self._active_connections.values():
                await self._close_connection(connection)
            
            self._active_connections.clear()
            
            logger.info("Database connection pool closed")
    
    async def _maintenance_loop(self) -> None:
        """Background maintenance for connection pool."""
        while not self._closed:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                if self._closed:
                    break
                
                await self._perform_maintenance()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection pool maintenance error: {e}")
    
    async def _perform_maintenance(self) -> None:
        """Perform connection pool maintenance."""
        async with self._pool_lock:
            # Remove unhealthy connections from available pool
            healthy_connections = []
            
            for connection in self._available_connections:
                if connection.is_healthy:
                    healthy_connections.append(connection)
                else:
                    await self._close_connection(connection)
            
            self._available_connections = healthy_connections
            
            # Ensure minimum pool size
            current_total = len(self._available_connections) + len(self._active_connections)
            
            if current_total < self.config.min_pool_size:
                connections_needed = self.config.min_pool_size - current_total
                
                for _ in range(connections_needed):
                    try:
                        connection = await self._create_connection()
                        self._available_connections.append(connection)
                        self._pool_metrics['total_connections_created'] += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to create maintenance connection: {e}")
                        break
            
            # Update pool utilization metrics
            if current_total > 0:
                utilization = len(self._active_connections) / current_total
                current_avg = self._pool_metrics['average_pool_utilization']
                # Simple moving average
                self._pool_metrics['average_pool_utilization'] = (current_avg * 0.9 + utilization * 0.1)
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status."""
        total_connections = len(self._available_connections) + len(self._active_connections)
        
        return {
            'total_connections': total_connections,
            'available_connections': len(self._available_connections),
            'active_connections': len(self._active_connections),
            'min_pool_size': self.config.min_pool_size,
            'max_pool_size': self.config.max_pool_size,
            'pool_utilization': (
                len(self._active_connections) / total_connections 
                if total_connections > 0 else 0.0
            ),
            'initialized': self._initialized,
            'closed': self._closed
        }
    
    def get_pool_metrics(self) -> Dict[str, Any]:
        """Get pool performance metrics."""
        wait_times = self._pool_metrics['connection_wait_times']
        
        return {
            'total_connections_created': self._pool_metrics['total_connections_created'],
            'total_connections_closed': self._pool_metrics['total_connections_closed'],
            'peak_active_connections': self._pool_metrics['peak_active_connections'],
            'average_pool_utilization': self._pool_metrics['average_pool_utilization'],
            'average_wait_time': sum(wait_times) / len(wait_times) if wait_times else 0.0,
            'max_wait_time': max(wait_times) if wait_times else 0.0,
            'total_wait_samples': len(wait_times)
        }
    
    def get_connection_metrics(self) -> List[Dict[str, Any]]:
        """Get metrics for all connections."""
        all_connections = list(self._available_connections) + list(self._active_connections.values())
        return [conn.get_metrics() for conn in all_connections]


class DatabaseManager:
    """
    Central database manager with multiple connection pools.
    
    Features:
    - Multiple database support
    - Connection pool management
    - Health monitoring
    - Performance metrics
    - Configuration integration
    """
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None,
                 error_handler: Optional[CentralizedErrorHandler] = None):
        """Initialize database manager."""
        self.config_manager = config_manager
        self.error_handler = error_handler
        
        # Connection pools
        self._pools: Dict[str, DatabaseConnectionPool] = {}
        self._default_pool_name = "default"
        
        # Manager state
        self._initialized = False
        self._lock = asyncio.Lock()
        
        logger.info("Database manager initialized")
    
    async def initialize(self) -> None:
        """Initialize database manager."""
        async with self._lock:
            if self._initialized:
                return
            
            # Create default pool from configuration
            await self._create_default_pool()
            
            self._initialized = True
            logger.info("Database manager initialization complete")
    
    async def _create_default_pool(self) -> None:
        """Create default database pool from configuration."""
        # Get database configuration
        if self.config_manager:
            database_config_dict = self.config_manager.get_section("database")
        else:
            database_config_dict = {}
        
        # Create database config
        config = DatabaseConfig(
            database_type=DatabaseType.SQLITE,
            connection_string=database_config_dict.get("url", "data/novel_engine.db"),
            min_pool_size=database_config_dict.get("min_pool_size", 2),
            max_pool_size=database_config_dict.get("max_pool_size", 20),
            connection_timeout=database_config_dict.get("timeout", 30.0)
        )
        
        # Create and initialize pool
        pool = DatabaseConnectionPool(config, self.error_handler)
        await pool.initialize()
        
        self._pools[self._default_pool_name] = pool
        logger.info(f"Default database pool created: {config.connection_string}")
    
    async def add_pool(self, name: str, config: DatabaseConfig) -> None:
        """Add named database pool."""
        async with self._lock:
            if name in self._pools:
                raise ValueError(f"Pool {name} already exists")
            
            pool = DatabaseConnectionPool(config, self.error_handler)
            await pool.initialize()
            
            self._pools[name] = pool
            logger.info(f"Database pool '{name}' added")
    
    async def get_connection(self, pool_name: Optional[str] = None) -> AsyncContextManager[DatabaseConnection]:
        """Get connection from specified or default pool."""
        if not self._initialized:
            await self.initialize()
        
        pool_name = pool_name or self._default_pool_name
        
        if pool_name not in self._pools:
            raise ValueError(f"Pool '{pool_name}' not found")
        
        pool = self._pools[pool_name]
        return await pool.get_connection()
    
    async def execute_query(
        self,
        query: str,
        parameters: tuple = None,
        pool_name: Optional[str] = None
    ) -> aiosqlite.Cursor:
        """Execute query on specified or default pool."""
        async with await self.get_connection(pool_name) as conn:
            return await conn.execute(query, parameters)
    
    async def execute_transaction(
        self,
        queries: List[tuple],  # List of (query, parameters) tuples
        pool_name: Optional[str] = None
    ) -> bool:
        """Execute multiple queries in a transaction."""
        async with await self.get_connection(pool_name) as conn:
            try:
                for query, parameters in queries:
                    await conn.execute(query, parameters)
                
                await conn.commit()
                return True
                
            except Exception as e:
                await conn.rollback()
                logger.error(f"Transaction failed: {e}")
                raise
    
    async def close_all_pools(self) -> None:
        """Close all database pools."""
        async with self._lock:
            for name, pool in self._pools.items():
                try:
                    await pool.close_pool()
                    logger.info(f"Closed database pool: {name}")
                except Exception as e:
                    logger.error(f"Error closing pool {name}: {e}")
            
            self._pools.clear()
            self._initialized = False
    
    def get_pool_status(self, pool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get status of specified or all pools."""
        if pool_name:
            if pool_name not in self._pools:
                raise ValueError(f"Pool '{pool_name}' not found")
            return {pool_name: self._pools[pool_name].get_pool_status()}
        
        # Return all pool statuses
        return {
            name: pool.get_pool_status() 
            for name, pool in self._pools.items()
        }
    
    def get_pool_metrics(self, pool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for specified or all pools."""
        if pool_name:
            if pool_name not in self._pools:
                raise ValueError(f"Pool '{pool_name}' not found")
            return {pool_name: self._pools[pool_name].get_pool_metrics()}
        
        # Return all pool metrics
        return {
            name: pool.get_pool_metrics() 
            for name, pool in self._pools.items()
        }
    
    async def health_check(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all pools."""
        health_results = {}
        
        for name, pool in self._pools.items():
            try:
                # Test connection from pool
                async with await pool.get_connection() as conn:
                    await conn.health_check()
                
                health_results[name] = {
                    'healthy': True,
                    'status': pool.get_pool_status(),
                    'metrics': pool.get_pool_metrics()
                }
                
            except Exception as e:
                health_results[name] = {
                    'healthy': False,
                    'error': str(e),
                    'status': pool.get_pool_status()
                }
        
        return health_results


# Global database manager instance
_global_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _global_database_manager
    if _global_database_manager is None:
        _global_database_manager = DatabaseManager()
    return _global_database_manager


async def get_database_connection(pool_name: Optional[str] = None) -> AsyncContextManager[DatabaseConnection]:
    """Get database connection from global manager."""
    return await get_database_manager().get_connection(pool_name)


@asynccontextmanager
async def database_manager_context(db_manager: DatabaseManager):
    """Context manager for database manager lifecycle."""
    try:
        await db_manager.initialize()
        yield db_manager
    finally:
        await db_manager.close_all_pools()