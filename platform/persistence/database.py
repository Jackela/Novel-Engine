"""
Database Connection and Session Management
========================================

Core database infrastructure using SQLAlchemy with connection pooling,
transaction management, and health monitoring for Novel Engine platform.
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Optional, Any, Dict
from urllib.parse import urlparse

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError

from ..config.settings import get_database_settings
from ..monitoring.metrics import DatabaseMetrics

logger = logging.getLogger(__name__)

# Base class for all SQLAlchemy models
Base = declarative_base()


class DatabaseManager:
    """
    Centralized database connection and session management.
    
    Features:
    - Connection pooling with configurable pool sizes
    - Automatic reconnection on connection failures
    - Health monitoring and metrics collection
    - Transaction management with automatic rollback
    - Support for both sync and async operations
    """
    
    def __init__(self):
        self._engine: Optional[Engine] = None
        self._async_engine: Optional[Any] = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[async_sessionmaker] = None
        self._metrics = DatabaseMetrics()
        self._is_initialized = False
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize database connections with configuration."""
        if self._is_initialized:
            logger.warning("DatabaseManager already initialized")
            return
        
        settings = config or get_database_settings()
        
        # Create synchronous engine
        self._engine = create_engine(
            settings["url"],
            pool_size=settings.get("pool_size", 20),
            max_overflow=settings.get("max_overflow", 30),
            pool_timeout=settings.get("pool_timeout", 30),
            pool_recycle=settings.get("pool_recycle", 3600),
            pool_pre_ping=True,
            echo=settings.get("echo", False),
            echo_pool=settings.get("echo_pool", False)
        )
        
        # Create asynchronous engine
        async_url = settings["url"].replace("postgresql://", "postgresql+asyncpg://")
        self._async_engine = create_async_engine(
            async_url,
            pool_size=settings.get("pool_size", 20),
            max_overflow=settings.get("max_overflow", 30),
            pool_timeout=settings.get("pool_timeout", 30),
            pool_recycle=settings.get("pool_recycle", 3600),
            pool_pre_ping=True,
            echo=settings.get("echo", False)
        )
        
        # Create session factories
        self._session_factory = sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False
        )
        
        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        
        # Setup event listeners for monitoring
        self._setup_event_listeners()
        
        # Test connections
        await self._test_connections()
        
        self._is_initialized = True
        logger.info("DatabaseManager initialized successfully")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown database connections."""
        if not self._is_initialized:
            return
        
        logger.info("Shutting down DatabaseManager...")
        
        if self._engine:
            self._engine.dispose()
            logger.info("Synchronous database engine disposed")
        
        if self._async_engine:
            await self._async_engine.dispose()
            logger.info("Asynchronous database engine disposed")
        
        self._is_initialized = False
        logger.info("DatabaseManager shutdown complete")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a synchronous database session with automatic cleanup."""
        if not self._is_initialized or not self._session_factory:
            raise RuntimeError("DatabaseManager not initialized")
        
        session = self._session_factory()
        try:
            self._metrics.record_session_created()
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self._metrics.record_session_error()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
            self._metrics.record_session_closed()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an asynchronous database session with automatic cleanup."""
        if not self._is_initialized or not self._async_session_factory:
            raise RuntimeError("DatabaseManager not initialized")
        
        session = self._async_session_factory()
        try:
            self._metrics.record_session_created()
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            self._metrics.record_session_error()
            logger.error(f"Async database session error: {e}")
            raise
        finally:
            await session.close()
            self._metrics.record_session_closed()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of database connections."""
        health_status = {
            "status": "healthy",
            "sync_connection": False,
            "async_connection": False,
            "pool_status": {},
            "errors": []
        }
        
        # Test synchronous connection
        try:
            with self.get_session() as session:
                result = session.execute(text("SELECT 1")).fetchone()
                if result and result[0] == 1:
                    health_status["sync_connection"] = True
        except Exception as e:
            health_status["errors"].append(f"Sync connection failed: {str(e)}")
            health_status["status"] = "unhealthy"
        
        # Test asynchronous connection
        try:
            async with self.get_async_session() as session:
                result = await session.execute(text("SELECT 1"))
                row = result.fetchone()
                if row and row[0] == 1:
                    health_status["async_connection"] = True
        except Exception as e:
            health_status["errors"].append(f"Async connection failed: {str(e)}")
            health_status["status"] = "unhealthy"
        
        # Get pool status
        if self._engine and self._engine.pool:
            pool = self._engine.pool
            health_status["pool_status"] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalidated": pool.invalidated()
            }
        
        return health_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        return self._metrics.get_all_metrics()
    
    def _setup_event_listeners(self) -> None:
        """Setup SQLAlchemy event listeners for monitoring."""
        if not self._engine:
            return
        
        @event.listens_for(self._engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            self._metrics.record_connection_created()
            logger.debug("Database connection established")
        
        @event.listens_for(self._engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            self._metrics.record_connection_checkout()
        
        @event.listens_for(self._engine, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            self._metrics.record_connection_checkin()
        
        @event.listens_for(self._engine, "close")
        def on_close(dbapi_conn, connection_record):
            self._metrics.record_connection_closed()
            logger.debug("Database connection closed")
        
        @event.listens_for(self._engine, "close_detached")
        def on_close_detached(dbapi_conn):
            self._metrics.record_connection_closed()
            logger.debug("Detached database connection closed")
    
    async def _test_connections(self) -> None:
        """Test both synchronous and asynchronous connections."""
        # Test sync connection
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("Synchronous database connection test successful")
        except Exception as e:
            logger.error(f"Synchronous database connection test failed: {e}")
            raise
        
        # Test async connection
        try:
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
            logger.info("Asynchronous database connection test successful")
        except Exception as e:
            logger.error(f"Asynchronous database connection test failed: {e}")
            raise


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions for application use
async def initialize_database(config: Optional[Dict[str, Any]] = None) -> None:
    """Initialize the global database manager."""
    await db_manager.initialize(config)


async def shutdown_database() -> None:
    """Shutdown the global database manager."""
    await db_manager.shutdown()


def get_db_session() -> Session:
    """Get a synchronous database session (context manager)."""
    return db_manager.get_session()


def get_async_db_session() -> AsyncSession:
    """Get an asynchronous database session (async context manager)."""
    return db_manager.get_async_session()


async def get_database_health() -> Dict[str, Any]:
    """Get database health status."""
    return await db_manager.health_check()


def get_database_metrics() -> Dict[str, Any]:
    """Get database performance metrics."""
    return db_manager.get_metrics()