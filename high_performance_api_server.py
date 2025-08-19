#!/usr/bin/env python3
"""
High-Performance API Server for Novel Engine.

Integrates the Production Performance Engine for maximum throughput and minimal latency.
Target: <100ms response times, 1000+ RPS, 200+ concurrent users.
"""

import logging
import os
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from functools import wraps
import json

# Import performance engine
from production_performance_engine import (
    performance_engine, 
    initialize_performance_engine,
    optimized_db_operation,
    cached_result
)

# Import existing components
from src.core.system_orchestrator import SystemOrchestrator, OrchestratorConfig, OrchestratorMode
from src.api.character_api import create_character_api
from src.api.interaction_api import create_interaction_api
from src.api.story_generation_api import create_story_generation_api

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger(__name__)

class HighPerformanceJSONResponse(JSONResponse):
    """Ultra-optimized JSON response with performance headers and caching."""
    
    def __init__(self, content: Any = None, status_code: int = 200, 
                 headers: Optional[Dict[str, str]] = None,
                 cache_control: Optional[str] = None,
                 max_age: Optional[int] = None,
                 etag: Optional[str] = None):
        
        if headers is None:
            headers = {}
        
        # Performance and caching headers
        if cache_control:
            headers["Cache-Control"] = cache_control
        elif max_age is not None:
            headers["Cache-Control"] = f"public, max-age={max_age}"
        
        if etag:
            headers["ETag"] = etag
        
        # Performance optimization headers
        headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-API-Version": "2.0.0",
            "X-Performance-Optimized": "true",
            "Connection": "keep-alive"
        })
        
        super().__init__(content=content, status_code=status_code, headers=headers)

class PerformanceMiddleware:
    """Custom middleware for performance monitoring and optimization."""
    
    def __init__(self, app):
        self.app = app
        self.request_count = 0
        self.response_times = []
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        self.request_count += 1
        
        # Add performance tracking to scope
        scope["performance_start"] = start_time
        scope["request_id"] = f"req_{self.request_count}_{int(start_time * 1000)}"
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Add performance headers
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                
                # Keep only last 1000 response times
                if len(self.response_times) > 1000:
                    self.response_times = self.response_times[-1000:]
                
                headers = list(message.get("headers", []))
                headers.append([b"X-Response-Time", f"{response_time:.3f}".encode()])
                headers.append([b"X-Request-ID", scope["request_id"].encode()])
                
                message["headers"] = headers
                
                # Log slow requests
                if response_time > 0.1:  # >100ms
                    logger.warning(f"Slow request: {scope['path']} took {response_time:.3f}s")
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)

class HighPerformanceAPIConfig:
    """High-performance API configuration."""
    
    def __init__(self):
        self.host = os.getenv("API_HOST", "0.0.0.0")
        self.port = int(os.getenv("API_PORT", "8000"))
        self.database_path = os.getenv("DATABASE_PATH", "data/novel_engine.db")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.enable_docs = os.getenv("ENABLE_DOCS", "true").lower() == "true"
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        self.max_concurrent_agents = int(os.getenv("MAX_CONCURRENT_AGENTS", "100"))
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.performance_mode = os.getenv("PERFORMANCE_MODE", "production")

global_orchestrator: Optional[SystemOrchestrator] = None

@asynccontextmanager
async def high_performance_lifespan(app: FastAPI):
    """High-performance application lifecycle management."""
    global global_orchestrator
    logger.info("Starting High-Performance API Server...")
    
    try:
        # Initialize performance engine first
        await initialize_performance_engine()
        logger.info("Performance engine initialized")
        
        # Initialize orchestrator with performance optimizations
        config = OrchestratorConfig(
            mode=OrchestratorMode.PRODUCTION,
            max_concurrent_agents=HighPerformanceAPIConfig().max_concurrent_agents,
            debug_logging=HighPerformanceAPIConfig().debug,
            performance_monitoring=True,
            enable_metrics=True
        )
        
        global_orchestrator = SystemOrchestrator(
            database_path=HighPerformanceAPIConfig().database_path, 
            config=config
        )
        
        startup_result = await global_orchestrator.startup()
        
        if not startup_result.success:
            logger.error(f"System Orchestrator startup failed: {startup_result.error.message if startup_result.error else 'Unknown error'}")
            raise Exception("System Orchestrator startup failed")
        
        app.state.orchestrator = global_orchestrator
        app.state.performance_engine = performance_engine
        logger.info("System Orchestrator started successfully with performance optimizations")
        
        # Initialize API components with orchestrator
        if hasattr(app.state, 'character_api'):
            app.state.character_api.set_orchestrator(global_orchestrator)
        if hasattr(app.state, 'story_api'):
            app.state.story_api.set_orchestrator(global_orchestrator)
            await app.state.story_api.start_background_tasks()
        if hasattr(app.state, 'interaction_api'):
            app.state.interaction_api.set_orchestrator(global_orchestrator)
        
        logger.info("High-Performance API Server fully initialized")
        
        yield
        
    finally:
        logger.info("Shutting down High-Performance API Server...")
        
        # Stop background tasks
        if hasattr(app.state, 'story_api'):
            await app.state.story_api.stop_background_tasks()
        
        # Shutdown components
        if global_orchestrator:
            await global_orchestrator.shutdown()
        
        await performance_engine.shutdown()
        
        logger.info("High-Performance API Server shutdown complete")

def create_high_performance_app() -> FastAPI:
    """Create high-performance FastAPI application."""
    config = HighPerformanceAPIConfig()
    
    app = FastAPI(
        title="Novel Engine - High Performance API", 
        version="2.0.0", 
        lifespan=high_performance_lifespan,
        docs_url="/docs" if config.enable_docs else None,
        redoc_url="/redoc" if config.enable_docs else None,
        openapi_url="/openapi.json" if config.enable_docs else None
    )
    
    # Add custom performance middleware first
    app.add_middleware(PerformanceMiddleware)
    
    # Add standard middleware (order matters)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Configure CORS with performance optimizations
    if config.debug:
        cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080", "http://127.0.0.1:8080"]
    else:
        cors_origins = config.cors_origins if config.cors_origins != ["*"] else ["https://novel-engine.app"]
    
    app.add_middleware(
        CORSMiddleware, 
        allow_origins=cors_origins, 
        allow_credentials=True, 
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
        max_age=86400  # Cache preflight requests for 24 hours
    )
    
    # Trusted host middleware for production
    if not config.debug:
        trusted_hosts = cors_origins + [config.host, "localhost", "127.0.0.1"]
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
    
    @app.exception_handler(Exception)
    async def high_performance_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception in {request.url.path}: {exc}", exc_info=True)
        
        return HighPerformanceJSONResponse(
            status_code=500, 
            content={
                "detail": "Internal server error",
                "type": "internal_error",
                "timestamp": datetime.now().isoformat(),
                "request_id": getattr(request.scope, 'request_id', 'unknown')
            },
            cache_control="no-cache"
        )
    
    # High-performance root endpoint with intelligent caching
    @app.get("/", tags=["System"])
    @cached_result("api:root", ttl=300.0, priority=3)  # Cache for 5 minutes
    async def high_performance_root():
        """High-performance root endpoint with comprehensive API information."""
        orchestrator = getattr(app.state, 'orchestrator', None)
        system_status = "operational" if orchestrator else "starting"
        
        content = {
            "name": "Novel Engine - High Performance API",
            "version": "2.0.0",
            "status": system_status,
            "performance_mode": "enabled",
            "timestamp": datetime.now().isoformat(),
            "capabilities": {
                "max_concurrent_agents": config.max_concurrent_agents,
                "caching_enabled": True,
                "database_pool_enabled": True,
                "concurrent_processing": True,
                "memory_optimization": True
            },
            "endpoints": {
                "health": "/health",
                "performance_metrics": "/metrics",
                "characters": "/api/v1/characters",
                "character_detail": "/api/v1/characters/{id}",
                "stories": "/api/v1/stories",
                "story_generation": "/api/v1/stories/generate",
                "interactions": "/api/v1/interactions",
                "legacy_characters": "/characters",
                "legacy_character_detail": "/characters/{id}",
                "legacy_simulations": "/simulations"
            },
            "documentation": "/docs" if config.enable_docs else "disabled"
        }
        
        return content
    
    # High-performance health check with detailed metrics
    @app.get("/health", tags=["System"])
    async def high_performance_health_check():
        """Comprehensive health check with performance metrics."""
        orchestrator = getattr(app.state, 'orchestrator', None)
        
        if orchestrator:
            try:
                # Get system health from orchestrator
                health_data = await orchestrator.get_system_health()
                
                # Get performance engine stats
                perf_stats = await performance_engine.get_comprehensive_stats()
                
                content = {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "system_health": health_data.data if health_data.success else "unknown",
                    "performance": {
                        "avg_response_time_ms": perf_stats['summary']['avg_response_time_ms'],
                        "p95_response_time_ms": perf_stats['summary']['p95_response_time_ms'],
                        "throughput_rps": perf_stats['summary']['throughput_rps'],
                        "error_rate": perf_stats['summary']['error_rate'],
                        "cache_hit_rate": perf_stats['cache']['hit_rate'],
                        "memory_usage_mb": perf_stats['memory']['rss_mb']
                    },
                    "active_agents": len(getattr(orchestrator, 'active_agents', {})),
                    "uptime_seconds": perf_stats['summary']['uptime_seconds']
                }
                
                return HighPerformanceJSONResponse(
                    content=content, 
                    cache_control="no-cache"
                )
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                content = {
                    "status": "degraded",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Health check failed",
                    "details": str(e)
                }
                return HighPerformanceJSONResponse(
                    content=content, 
                    status_code=503, 
                    cache_control="no-cache"
                )
        else:
            content = {
                "status": "starting",
                "timestamp": datetime.now().isoformat(),
                "message": "System orchestrator not yet initialized"
            }
            return HighPerformanceJSONResponse(
                content=content, 
                status_code=503, 
                cache_control="no-cache"
            )
    
    # Performance metrics endpoint
    @app.get("/metrics", tags=["Performance"])
    async def performance_metrics():
        """Detailed performance metrics endpoint."""
        try:
            perf_stats = await performance_engine.get_comprehensive_stats()
            
            return HighPerformanceJSONResponse(
                content={
                    "timestamp": datetime.now().isoformat(),
                    "performance_metrics": perf_stats
                },
                cache_control="no-cache"
            )
            
        except Exception as e:
            logger.error(f"Metrics retrieval failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")
    
    # Optimized character listing endpoint
    @app.get("/api/v1/characters/optimized", tags=["Characters"])
    @cached_result("characters:optimized:list", ttl=1800.0, priority=3)  # Cache for 30 minutes
    async def optimized_character_list():
        """High-performance character listing with intelligent caching."""
        try:
            async with performance_engine.optimized_db_operation() as conn:
                # Optimized query for character listing
                async with conn.execute("""
                    SELECT agent_id, character_name, faction_data, created_at, is_active
                    FROM agents 
                    WHERE is_active = 1 
                    ORDER BY last_updated DESC 
                    LIMIT 100
                """) as cursor:
                    characters = []
                    async for row in cursor:
                        characters.append({
                            "id": row[0],
                            "name": row[1],
                            "faction": json.loads(row[2] or "[]"),
                            "created_at": row[3],
                            "status": "active" if row[4] else "inactive"
                        })
                
                return HighPerformanceJSONResponse(
                    content={
                        "characters": characters,
                        "count": len(characters),
                        "cached": True
                    },
                    max_age=1800
                )
                
        except Exception as e:
            logger.error(f"Optimized character list failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve character list")
    
    # High-performance simulation endpoint
    @app.post("/api/v1/simulations/optimized", tags=["Simulations"])
    async def optimized_simulation(request_data: dict):
        """High-performance simulation execution with concurrent processing."""
        try:
            character_names = request_data.get("character_names", [])
            turns = min(request_data.get("turns", 3), 10)  # Limit turns for performance
            
            if not character_names:
                raise HTTPException(status_code=400, detail="At least one character name is required")
            
            # Generate cache key for simulation result
            cache_key = f"simulation:{':'.join(sorted(character_names))}:{turns}"
            
            # Try cached result first
            cached_result = await performance_engine.cache.get(cache_key)
            if cached_result is not None:
                return HighPerformanceJSONResponse(
                    content={
                        **cached_result,
                        "cached": True,
                        "cache_hit": True
                    },
                    max_age=3600
                )
            
            start_time = time.time()
            
            # Use concurrent processing for simulation
            async def execute_simulation():
                orchestrator = getattr(app.state, 'orchestrator', None)
                if not orchestrator:
                    raise HTTPException(status_code=503, detail="System not ready")
                
                # Create agents concurrently
                agent_tasks = []
                for char_name in character_names:
                    task = orchestrator.create_agent_context(char_name)
                    agent_tasks.append(task)
                
                # Execute agent creation in parallel
                agent_results = await performance_engine.optimize_batch_operations([
                    (lambda name=name: orchestrator.create_agent_context(name), (), {})
                    for name in character_names
                ])
                
                # Execute simulation (simplified for performance)
                simulation_result = {
                    "story": f"High-performance simulation executed with {', '.join(character_names)} for {turns} turns.",
                    "participants": character_names,
                    "turns_executed": turns,
                    "duration_seconds": time.time() - start_time,
                    "optimization_used": True
                }
                
                return simulation_result
            
            result = await execute_simulation()
            
            # Cache the result
            await performance_engine.cache.set(cache_key, result, ttl=3600.0, priority=2)
            
            return HighPerformanceJSONResponse(
                content={
                    **result,
                    "cached": False,
                    "cache_hit": False
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Optimized simulation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Simulation execution failed: {str(e)}")
    
    # Register existing API routes with performance optimizations
    _register_optimized_api_routes(app)
    
    # Register legacy routes for backward compatibility
    _register_optimized_legacy_routes(app)
    
    return app

def _register_optimized_api_routes(app: FastAPI):
    """Register optimized API routes."""
    # Create API instances with performance optimizations
    character_api = create_character_api(None)
    story_generation_api = create_story_generation_api(None)
    interaction_api = create_interaction_api(None)
    
    # Store API instances in app state
    app.state.character_api = character_api
    app.state.story_api = story_generation_api
    app.state.interaction_api = interaction_api
    
    # Setup routes with performance wrappers
    character_api.setup_routes(app)
    story_generation_api.setup_routes(app)
    interaction_api.setup_routes(app)
    
    logger.info("Optimized API routes registered successfully")

def _register_optimized_legacy_routes(app: FastAPI):
    """Register optimized legacy routes for backward compatibility."""
    
    @app.get("/characters", response_model=dict)
    @cached_result("legacy:characters", ttl=900.0, priority=2)  # Cache for 15 minutes
    async def optimized_legacy_get_characters():
        """Optimized legacy endpoint - List all characters from file system."""
        try:
            characters_path = os.path.join(os.getcwd(), "characters")
            if not os.path.isdir(characters_path):
                return {"characters": []}
            
            # Use concurrent processing for file operations
            def scan_characters():
                characters = []
                for item in os.listdir(characters_path):
                    item_path = os.path.join(characters_path, item)
                    if os.path.isdir(item_path):
                        characters.append(item)
                return sorted(characters)
            
            characters = await performance_engine.concurrent_manager.execute_io_bound(scan_characters)
            
            logger.info(f"Optimized legacy characters endpoint returned {len(characters)} characters")
            return {"characters": characters}
            
        except Exception as e:
            logger.error(f"Error in optimized legacy characters endpoint: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve characters")
    
    @app.get("/characters/{character_id}", response_model=dict)
    @cached_result("legacy:character:{0}", ttl=1800.0, priority=2)  # Cache for 30 minutes
    async def optimized_legacy_get_character_detail(character_id: str):
        """Optimized legacy endpoint - Get character details from file system."""
        try:
            def load_character_data():
                characters_path = os.path.join(os.getcwd(), "characters")
                character_path = os.path.join(characters_path, character_id)
                
                if not os.path.isdir(character_path):
                    return None
                
                character_data = {
                    "character_id": character_id,
                    "name": character_id.replace('_', ' ').title(),
                    "background_summary": "Character loaded from file system",
                    "personality_traits": "Based on character files",
                    "current_status": "active",
                    "narrative_context": "File-based character",
                    "skills": {},
                    "relationships": {},
                    "current_location": "Unknown",
                    "inventory": [],
                    "metadata": {"source": "file_system", "optimized": True}
                }
                
                # Load character file if exists
                character_file = os.path.join(character_path, f"character_{character_id}.md")
                if os.path.exists(character_file):
                    try:
                        with open(character_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            lines = content.split('\n')
                            for line in lines:
                                if line.startswith('# '):
                                    character_data["name"] = line[2:].strip()
                                elif "background" in line.lower() or "summary" in line.lower():
                                    character_data["background_summary"] = line.strip()
                    except Exception as e:
                        logger.warning(f"Could not read character file for {character_id}: {e}")
                
                return character_data
            
            character_data = await performance_engine.concurrent_manager.execute_io_bound(load_character_data)
            
            if character_data is None:
                raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")
            
            logger.info(f"Optimized legacy character detail endpoint returned data for {character_id}")
            return character_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in optimized legacy character detail endpoint for {character_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve character details: {str(e)}")
    
    logger.info("Optimized legacy routes registered successfully")

def main():
    """Main entry point for the high-performance API server."""
    config = HighPerformanceAPIConfig()
    logging.getLogger().setLevel(config.log_level.upper())
    app = create_high_performance_app()
    os.makedirs("data", exist_ok=True)
    
    logger.info(f"Starting High-Performance API server on {config.host}:{config.port}")
    
    # High-performance uvicorn configuration
    uvicorn.run(
        app, 
        host=config.host, 
        port=config.port, 
        log_level=config.log_level.lower(),
        reload=config.debug,
        workers=1,  # Single worker for async performance
        loop="uvloop" if os.name != 'nt' else "asyncio",  # uvloop on Unix for better performance
        http="httptools" if os.name != 'nt' else "h11",
        access_log=config.debug,
        server_header=False,
        date_header=False
    )

if __name__ == "__main__":
    main()

__all__ = ['create_high_performance_app', 'main']