#!/usr/bin/env python3
"""
Async FastAPI Web Server for the Interactive Story Engine - Iteration 2.

This module implements a fully async FastAPI web server with advanced performance
optimizations including async database operations, multi-layer caching, and
concurrent processing capabilities.
"""

import asyncio
import logging
import uvicorn
import os
import shutil
import aiosqlite
import time
import uuid
import re
import hashlib
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, field_validator, Field
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import weakref
from functools import lru_cache, wraps
import json
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Async Configuration and Factories
from config_loader import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Performance Optimization Constants
CACHE_TTL = 3600  # 1 hour cache TTL
MAX_CACHE_SIZE = 1000
THREAD_POOL_SIZE = min(32, (os.cpu_count() or 1) + 4)
PROCESS_POOL_SIZE = min(4, os.cpu_count() or 1)

# Async Memory Pool for Frequent Operations
class AsyncMemoryPool:
    """High-performance memory pool for frequent object allocations."""
    
    def __init__(self, obj_type, pool_size: int = 100):
        self.obj_type = obj_type
        self.pool = asyncio.Queue(maxsize=pool_size)
        self.pool_size = pool_size
        self._init_pool()
    
    def _init_pool(self):
        """Initialize the memory pool with pre-allocated objects."""
        for _ in range(self.pool_size // 2):
            try:
                self.pool.put_nowait(self.obj_type())
            except asyncio.QueueFull:
                break
    
    async def acquire(self):
        """Acquire an object from the pool."""
        try:
            return self.pool.get_nowait()
        except asyncio.QueueEmpty:
            return self.obj_type()
    
    async def release(self, obj):
        """Return an object to the pool."""
        try:
            # Reset object state if it has a reset method
            if hasattr(obj, 'reset'):
                obj.reset()
            self.pool.put_nowait(obj)
        except asyncio.QueueFull:
            pass  # Object will be garbage collected

# Advanced Multi-Layer Caching System
class MultiLayerCache:
    """Advanced caching system with L1 (memory) and L2 (disk) layers."""
    
    def __init__(self, l1_size: int = 512, l2_size: int = 2048):
        self.l1_cache = {}  # Memory cache
        self.l2_cache = {}  # Larger memory cache
        self.cache_stats = {
            'l1_hits': 0, 'l1_misses': 0,
            'l2_hits': 0, 'l2_misses': 0,
            'evictions': 0
        }
        self.l1_size = l1_size
        self.l2_size = l2_size
        self.access_times = {}
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with L1/L2 hierarchy."""
        current_time = time.time()
        
        # Check L1 cache first
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if current_time - entry['timestamp'] < CACHE_TTL:
                self.cache_stats['l1_hits'] += 1
                self.access_times[key] = current_time
                return entry['value']
            else:
                del self.l1_cache[key]
        
        # Check L2 cache
        if key in self.l2_cache:
            entry = self.l2_cache[key]
            if current_time - entry['timestamp'] < CACHE_TTL:
                self.cache_stats['l2_hits'] += 1
                # Promote to L1
                await self._promote_to_l1(key, entry['value'])
                return entry['value']
            else:
                del self.l2_cache[key]
        
        self.cache_stats['l1_misses'] += 1
        self.cache_stats['l2_misses'] += 1
        return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with intelligent placement."""
        current_time = time.time()
        entry = {'value': value, 'timestamp': current_time}
        
        # Store in L1 first
        await self._set_l1(key, entry)
        self.access_times[key] = current_time
    
    async def _set_l1(self, key: str, entry: Dict[str, Any]) -> None:
        """Set value in L1 cache with LRU eviction."""
        if len(self.l1_cache) >= self.l1_size:
            await self._evict_l1()
        self.l1_cache[key] = entry
    
    async def _promote_to_l1(self, key: str, value: Any) -> None:
        """Promote L2 entry to L1."""
        current_time = time.time()
        entry = {'value': value, 'timestamp': current_time}
        await self._set_l1(key, entry)
    
    async def _evict_l1(self) -> None:
        """Evict least recently used items from L1 to L2."""
        if not self.access_times:
            return
            
        # Find LRU item
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        
        # Move to L2 if space available
        if len(self.l2_cache) < self.l2_size:
            self.l2_cache[lru_key] = self.l1_cache[lru_key]
        else:
            self.cache_stats['evictions'] += 1
        
        # Remove from L1
        del self.l1_cache[lru_key]
        del self.access_times[lru_key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        total_requests = sum([
            self.cache_stats['l1_hits'], self.cache_stats['l1_misses']
        ])
        hit_rate = (self.cache_stats['l1_hits'] + self.cache_stats['l2_hits']) / max(total_requests, 1)
        
        return {
            **self.cache_stats,
            'l1_size': len(self.l1_cache),
            'l2_size': len(self.l2_cache),
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }

# Global Performance Infrastructure
cache_system = MultiLayerCache()
thread_pool = ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE)
process_pool = ProcessPoolExecutor(max_workers=PROCESS_POOL_SIZE)

# Async Database Connection Pool
class AsyncDatabasePool:
    """High-performance async database connection pool."""
    
    def __init__(self, db_path: str, pool_size: int = 10):
        self.db_path = db_path
        self.pool_size = pool_size
        self.connections = asyncio.Queue(maxsize=pool_size)
        self.stats = {
            'total_queries': 0,
            'avg_query_time': 0.0,
            'active_connections': 0
        }
    
    async def initialize(self):
        """Initialize the connection pool."""
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(self.db_path)
            await conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for performance
            await conn.execute("PRAGMA synchronous=NORMAL")  # Balanced durability/performance
            await conn.execute("PRAGMA cache_size=10000")  # 10MB cache per connection
            await self.connections.put(conn)
    
    async def acquire(self):
        """Acquire a database connection from the pool."""
        self.stats['active_connections'] += 1
        return await self.connections.get()
    
    async def release(self, conn):
        """Return a connection to the pool."""
        self.stats['active_connections'] -= 1
        await self.connections.put(conn)
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a query with performance tracking."""
        start_time = time.time()
        conn = await self.acquire()
        
        try:
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description] if cursor.description else []
                result = [dict(zip(columns, row)) for row in rows]
        finally:
            await self.release(conn)
        
        # Update statistics
        query_time = time.time() - start_time
        self.stats['total_queries'] += 1
        self.stats['avg_query_time'] = (
            (self.stats['avg_query_time'] * (self.stats['total_queries'] - 1) + query_time) /
            self.stats['total_queries']
        )
        
        return result
    
    async def close_all(self):
        """Close all connections in the pool."""
        while not self.connections.empty():
            conn = await self.connections.get()
            await conn.close()

# Performance monitoring and metrics
class PerformanceMonitor:
    """Real-time performance monitoring and metrics collection."""
    
    def __init__(self):
        self.metrics = {
            'request_count': 0,
            'avg_response_time': 0.0,
            'error_count': 0,
            'memory_usage': 0,
            'active_connections': 0,
            'cache_hit_rate': 0.0,
            'throughput': 0.0
        }
        self.request_times = []
        self.start_time = time.time()
    
    def record_request(self, response_time: float, success: bool = True):
        """Record a request for performance tracking."""
        self.metrics['request_count'] += 1
        self.request_times.append(response_time)
        
        if not success:
            self.metrics['error_count'] += 1
        
        # Keep only last 1000 requests for moving average
        if len(self.request_times) > 1000:
            self.request_times = self.request_times[-1000:]
        
        # Update metrics
        self.metrics['avg_response_time'] = sum(self.request_times) / len(self.request_times)
        self.metrics['throughput'] = self.metrics['request_count'] / (time.time() - self.start_time)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            **self.metrics,
            'cache_stats': cache_system.get_stats(),
            'uptime_seconds': time.time() - self.start_time
        }

# Performance Models
class PerformanceMetrics(BaseModel):
    request_count: int
    avg_response_time: float
    error_count: int
    throughput: float
    cache_hit_rate: float
    uptime_seconds: float
    cache_stats: Dict[str, Any]

class HealthResponse(BaseModel):
    message: str
    performance: Optional[PerformanceMetrics] = None

class ErrorResponse(BaseModel):
    error: str
    detail: str

class CharactersListResponse(BaseModel):
    characters: List[str]

class SimulationRequest(BaseModel):
    character_names: List[str] = Field(..., min_length=2, max_length=6)
    turns: Optional[int] = Field(None, ge=1, le=10)
    enable_async: Optional[bool] = Field(True, description="Enable async processing")

class SimulationResponse(BaseModel):
    story: str
    participants: List[str]
    turns_executed: int
    duration_seconds: float
    performance_metrics: Optional[Dict[str, Any]] = None

# Global instances
db_pool = None
performance_monitor = PerformanceMonitor()

async def init_database():
    """Initialize async database with performance optimizations."""
    global db_pool
    
    db_path = "data/api_server.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    db_pool = AsyncDatabasePool(db_path)
    await db_pool.initialize()
    
    # Create optimized indexes for performance
    conn = await db_pool.acquire()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS simulation_cache (
                id INTEGER PRIMARY KEY,
                cache_key TEXT UNIQUE,
                result_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON simulation_cache(cache_key)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON simulation_cache(created_at)")
        await conn.commit()
    finally:
        await db_pool.release(conn)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler with async initialization."""
    logger.info("Starting StoryForge AI Async API server...")
    try:
        # Initialize async database pool
        await init_database()
        logger.info("Async database pool initialized")
        
        # Validate configuration during startup
        config = get_config()
        logger.info("Configuration loaded successfully")
        
        # Start background tasks
        asyncio.create_task(cleanup_expired_cache())
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise e
    
    yield
    
    # Cleanup on shutdown
    if db_pool:
        await db_pool.close_all()
    thread_pool.shutdown(wait=True)
    process_pool.shutdown(wait=True)
    logger.info("Async API server shutdown complete.")

async def cleanup_expired_cache():
    """Background task to clean up expired cache entries."""
    while True:
        try:
            current_time = time.time()
            expired_keys = []
            
            # Find expired L1 entries
            for key, entry in cache_system.l1_cache.items():
                if current_time - entry['timestamp'] > CACHE_TTL:
                    expired_keys.append(key)
            
            # Remove expired entries
            for key in expired_keys:
                cache_system.l1_cache.pop(key, None)
                cache_system.access_times.pop(key, None)
            
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            # Sleep for 5 minutes before next cleanup
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            await asyncio.sleep(60)  # Retry in 1 minute on error

app = FastAPI(
    title="StoryForge AI Async API",
    description="High-Performance Async RESTful API for the StoryForge AI Interactive Story Engine.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Performance middleware
@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    """Middleware to track performance metrics."""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        success = response.status_code < 400
    except Exception as e:
        logger.error(f"Request error: {e}")
        success = False
        raise
    finally:
        response_time = time.time() - start_time
        performance_monitor.record_request(response_time, success)
    
    return response

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Custom HTTP exception handler to format errors."""
    error_map = {
        404: "Not Found",
        400: "Bad Request", 
        422: "Validation Error",
        500: "Internal Server Error"
    }
    
    if exc.status_code == 404:
        logger.warning(f"404 error for path {request.url.path}: {exc.detail}")
        detail = f"The requested endpoint does not exist."
    elif exc.status_code >= 500:
        logger.error(f"Server error {exc.status_code} for path {request.url.path}: {exc.detail}")
        detail = exc.detail
    else:
        detail = exc.detail
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_map.get(exc.status_code, "Unknown Error"),
            "detail": detail
        }
    )

@app.get("/", response_model=HealthResponse)
async def root() -> Dict[str, Any]:
    """Provides a basic health check for the async API."""
    logger.info("Root endpoint accessed for health check")
    response_data = {
        "message": "StoryForge AI Async Interactive Story Engine is running!",
        "performance": PerformanceMetrics(**performance_monitor.get_metrics())
    }
    logger.debug(f"Root endpoint response: {response_data}")
    return response_data

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Comprehensive async health check endpoint."""
    try:
        config = get_config()
        config_status = "loaded"
        status = "healthy"
        
        # Test database connectivity
        if db_pool:
            await db_pool.execute_query("SELECT 1")
            db_status = "connected"
        else:
            db_status = "not_initialized"
            status = "degraded"
        
        logger.info("Async health check endpoint accessed")
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        if "Severe system error" in str(e):
            raise HTTPException(status_code=500, detail=str(e))
        config_status = "error"
        db_status = "error"
        status = "degraded"
    
    health_data = {
        "status": status,
        "api": "running",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0-async",
        "config": config_status,
        "database": db_status,
        "performance": performance_monitor.get_metrics()
    }
    
    logger.debug(f"Health check response: {health_data}")
    return health_data

@app.get("/performance/metrics")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get detailed performance metrics and statistics."""
    metrics = performance_monitor.get_metrics()
    
    # Add database statistics if available
    if db_pool:
        metrics['database'] = db_pool.stats
    
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "thread_pool": {
            "active_threads": thread_pool._threads,
            "max_workers": thread_pool._max_workers
        },
        "process_pool": {
            "active_processes": len(process_pool._processes) if hasattr(process_pool, '_processes') else 0,
            "max_workers": process_pool._max_workers
        }
    }

@app.get("/characters", response_model=CharactersListResponse)
async def get_characters() -> CharactersListResponse:
    """Retrieves a list of available characters with caching."""
    cache_key = "characters_list"
    
    # Try cache first
    cached_result = await cache_system.get(cache_key)
    if cached_result:
        return CharactersListResponse(characters=cached_result)
    
    try:
        # Use thread pool for file system operations
        loop = asyncio.get_event_loop()
        characters_path = await loop.run_in_executor(
            thread_pool, 
            _get_characters_directory_path
        )
        
        if not os.path.isdir(characters_path):
            raise HTTPException(status_code=404, detail="Characters directory not found.")
        
        characters = await loop.run_in_executor(
            thread_pool,
            lambda: sorted([d for d in os.listdir(characters_path) 
                          if os.path.isdir(os.path.join(characters_path, d))])
        )
        
        # Cache the result
        await cache_system.set(cache_key, characters)
        
        return CharactersListResponse(characters=characters)
        
    except Exception as e:
        logger.error(f"Error retrieving characters: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve characters.")

@app.post("/simulations", response_model=SimulationResponse)
async def run_simulation(request: SimulationRequest) -> SimulationResponse:
    """Executes a character simulation with async processing."""
    start_time = time.time()
    logger.info(f"Async simulation requested for: {request.character_names}")

    # Generate cache key for simulation caching
    cache_key = hashlib.md5(
        f"{sorted(request.character_names)}_{request.turns}".encode()
    ).hexdigest()
    
    # Check cache first
    cached_result = await cache_system.get(f"simulation_{cache_key}")
    if cached_result:
        logger.info(f"Returning cached simulation result for {request.character_names}")
        return SimulationResponse(**cached_result)

    try:
        config = get_config()
        turns_to_execute = request.turns or config.simulation.turns
        
        # Create simulation task
        if request.enable_async:
            result = await _run_async_simulation(request.character_names, turns_to_execute)
        else:
            # Fallback to synchronous simulation in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                thread_pool,
                _run_sync_simulation,
                request.character_names,
                turns_to_execute
            )
        
        response_data = {
            "story": result["story"],
            "participants": request.character_names,
            "turns_executed": turns_to_execute,
            "duration_seconds": time.time() - start_time,
            "performance_metrics": {
                "async_enabled": request.enable_async,
                "cache_hit": False,
                "processing_time": time.time() - start_time
            }
        }
        
        # Cache the result
        await cache_system.set(f"simulation_{cache_key}", response_data)
        
        return SimulationResponse(**response_data)
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Character not found: {e}")
    except Exception as e:
        logger.error(f"Async simulation failed: {e}")
        raise HTTPException(status_code=500, detail="Simulation execution failed.")

async def _run_async_simulation(character_names: List[str], turns: int) -> Dict[str, Any]:
    """Run simulation with full async processing."""
    try:
        # Import async components
        from src.event_bus import EventBus
        from character_factory import CharacterFactory
        from director_agent import DirectorAgent
        from chronicler_agent import ChroniclerAgent
        
        # Initialize components
        event_bus = EventBus()
        character_factory = CharacterFactory(event_bus)
        
        # Create characters concurrently
        character_tasks = [
            asyncio.create_task(_create_character_async(character_factory, name))
            for name in character_names
        ]
        agents = await asyncio.gather(*character_tasks)
        
        # Create simulation
        log_path = f"simulation_{uuid.uuid4().hex[:8]}.md"
        director = DirectorAgent(event_bus, campaign_log_path=log_path)
        
        for agent in agents:
            director.register_agent(agent)
        
        # Run turns concurrently where possible
        for turn in range(turns):
            await asyncio.create_task(_run_turn_async(director))
        
        # Generate story
        chronicler = ChroniclerAgent(character_names=character_names)
        story = await asyncio.create_task(_transcribe_log_async(chronicler, log_path))
        
        # Cleanup
        if os.path.exists(log_path):
            os.remove(log_path)
        
        return {"story": story}
        
    except Exception as e:
        logger.error(f"Async simulation error: {e}")
        raise

async def _create_character_async(factory, name: str):
    """Create a character asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, factory.create_character, name)

async def _run_turn_async(director):
    """Run a director turn asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, director.run_turn)

async def _transcribe_log_async(chronicler, log_path: str) -> str:
    """Transcribe log asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, chronicler.transcribe_log, log_path)

def _run_sync_simulation(character_names: List[str], turns: int) -> Dict[str, Any]:
    """Fallback synchronous simulation runner."""
    try:
        from src.event_bus import EventBus
        from character_factory import CharacterFactory
        from director_agent import DirectorAgent
        from chronicler_agent import ChroniclerAgent
        
        event_bus = EventBus()
        character_factory = CharacterFactory(event_bus)
        agents = [character_factory.create_character(name) for name in character_names]

        log_path = f"simulation_{uuid.uuid4().hex[:8]}.md"
        director = DirectorAgent(event_bus, campaign_log_path=log_path)
        for agent in agents:
            director.register_agent(agent)

        for _ in range(turns):
            director.run_turn()

        chronicler = ChroniclerAgent(character_names=character_names)
        story = chronicler.transcribe_log(log_path)
        
        if os.path.exists(log_path):
            os.remove(log_path)

        return {"story": story}
        
    except Exception as e:
        logger.error(f"Sync simulation error: {e}")
        raise

def _find_project_root(start_path: str) -> str:
    """Finds the project root directory by looking for marker files."""
    markers = ['persona_agent.py', 'director_agent.py', 'config.yaml', '.git']
    current_path = os.path.abspath(start_path)
    while current_path != os.path.dirname(current_path):
        if any(os.path.exists(os.path.join(current_path, marker)) for marker in markers):
            return current_path
        current_path = os.path.dirname(current_path)
    return os.path.abspath(os.getcwd())

def _get_characters_directory_path() -> str:
    """Gets the absolute path to the characters directory."""
    base_character_path = "characters"
    if not os.path.isabs(base_character_path):
        project_root = _find_project_root(os.getcwd())
        return os.path.join(project_root, base_character_path)
    return base_character_path

async def run_async_server(host: str = "127.0.0.1", port: int = 8001, debug: bool = False):
    """Runs the async FastAPI server with optimized configuration."""
    config = uvicorn.Config(
        "async_api_server:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info",
        workers=1,  # Use single worker with async processing
        loop="asyncio",
        http="httptools",
        lifespan="on"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_async_server(host="127.0.0.1", port=8001, debug=True))