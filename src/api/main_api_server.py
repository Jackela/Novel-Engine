#!/usr/bin/env python3
"""
++ SACRED MAIN API SERVER BLESSED BY UNIFIED ORCHESTRATION ++
=============================================================

Holy main API server that unifies all API endpoints for the Dynamic Context
Engineering Framework, providing comprehensive user story implementation
blessed by the Omnissiah's integrative service wisdom.

++ THROUGH UNIFIED APIS, ALL STORIES ACHIEVE PERFECT EXPRESSION ++

Complete User Story Implementation Server
Sacred Author: Dev Agent James
万机之神保佑API统一 (May the Omnissiah bless API unity)
"""

import logging
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import blessed framework components
from src.core.system_orchestrator import SystemOrchestrator, OrchestratorConfig, OrchestratorMode
from src.api.character_api import CharacterAPI, create_character_api
from src.api.interaction_api import InteractionAPI, create_interaction_api
from src.api.story_generation_api import StoryGenerationAPI, create_story_generation_api

# Sacred logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='++ %(asctime)s | %(levelname)s | %(name)s | %(message)s ++',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api_server.log')
    ]
)
logger = logging.getLogger(__name__)


class APIServerConfig:
    """Configuration for the API server."""
    
    def __init__(self):
        self.host = os.getenv("API_HOST", "127.0.0.1")
        self.port = int(os.getenv("API_PORT", "8000"))
        self.database_path = os.getenv("DATABASE_PATH", "data/api_server.db")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.enable_docs = os.getenv("ENABLE_DOCS", "true").lower() == "true"
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        self.max_concurrent_agents = int(os.getenv("MAX_CONCURRENT_AGENTS", "20"))
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")


# Global orchestrator instance
global_orchestrator: Optional[SystemOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global global_orchestrator
    
    # Startup
    logger.info("++ Starting Dynamic Context Engineering API Server ++")
    
    try:
        # Create orchestrator configuration
        config = OrchestratorConfig(
            mode=OrchestratorMode.PRODUCTION,
            max_concurrent_agents=APIServerConfig().max_concurrent_agents,
            debug_logging=APIServerConfig().debug,
            enable_metrics=APIServerConfig().enable_metrics,
            enable_auto_backup=True,
            performance_monitoring=True
        )
        
        # Initialize system orchestrator
        global_orchestrator = SystemOrchestrator(
            database_path=APIServerConfig().database_path,
            config=config
        )
        
        # Start the orchestrator
        startup_result = await global_orchestrator.startup()
        if not startup_result.success:
            error_msg = startup_result.error.message if startup_result.error else "Unknown startup error"
            raise Exception(f"Orchestrator startup failed: {error_msg}")
        
        logger.info("++ System Orchestrator started successfully ++")
        
        # Initialize API components
        character_api = create_character_api(global_orchestrator)
        interaction_api = create_interaction_api(global_orchestrator)
        story_api = create_story_generation_api(global_orchestrator)
        
        # Setup API routes
        character_api._setup_routes()
        interaction_api.setup_routes(app)
        story_api.setup_routes(app)
        
        # Store API instances in app state
        app.state.orchestrator = global_orchestrator
        app.state.character_api = character_api
        app.state.interaction_api = interaction_api
        app.state.story_api = story_api
        
        logger.info("++ All API components initialized successfully ++")
        
        yield
        
    except Exception as e:
        logger.error(f"++ CRITICAL ERROR during startup: {str(e)} ++")
        raise
    
    # Shutdown
    logger.info("++ Shutting down Dynamic Context Engineering API Server ++")
    
    try:
        if global_orchestrator:
            shutdown_result = await global_orchestrator.shutdown()
            if shutdown_result.success:
                logger.info("++ System shutdown completed successfully ++")
            else:
                warning_msg = shutdown_result.error.message if shutdown_result.error else "Unknown warning"
                logger.warning(f"++ Shutdown completed with warnings: {warning_msg} ++")
    except Exception as e:
        logger.error(f"++ ERROR during shutdown: {str(e)} ++")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    config = APIServerConfig()
    
    # Create FastAPI app with lifespan management
    app = FastAPI(
        title="Dynamic Context Engineering Framework",
        description="""
        ## Comprehensive API for Intelligent Agent Interaction and Story Generation
        
        This API provides complete functionality for:
        - **Character Creation & Customization** - Create and manage AI characters with personalities
        - **Real-Time Character Interactions** - Orchestrate dynamic character conversations and relationships
        - **Persistent Memory & Relationship Evolution** - Track character growth and relationship dynamics
        - **Story Export & Narrative Generation** - Convert interactions into professional-quality stories
        
        ### Key Features:
        - 🧠 **Multi-layer Memory System** - Working, episodic, semantic, and emotional memory
        - 💬 **Dynamic Interactions** - Real-time character conversations with WebSocket support
        - 📝 **Story Generation** - Export interactions as formatted stories in multiple formats
        - 🔧 **Equipment Integration** - Track character equipment and usage over time
        - 📊 **System Monitoring** - Comprehensive metrics and health monitoring
        
        ### Architecture:
        Built on a sophisticated dynamic context engineering framework with cognitive science
        foundations, enabling rich character development and storytelling capabilities.
        
        **万机之神保佑此框架** (May the Omnissiah bless this framework)
        """,
        version="1.0.0",
        docs_url="/docs" if config.enable_docs else None,
        redoc_url="/redoc" if config.enable_docs else None,
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add global exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions with consistent error format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "type": "http_error",
                    "code": exc.status_code,
                    "message": exc.detail,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle general exceptions with logging."""
        logger.error(f"++ Unhandled exception: {str(exc)} ++", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "type": "internal_error",
                    "code": 500,
                    "message": "Internal server error",
                    "timestamp": datetime.now().isoformat()
                }
            }
        )
    
    # Health check endpoint
    @app.get("/health", tags=["System"])
    async def health_check():
        """System health check endpoint."""
        try:
            if global_orchestrator:
                metrics_result = await global_orchestrator.get_system_metrics()
                if metrics_result.success:
                    metrics = metrics_result.data["current_metrics"]
                    return {
                        "status": "healthy",
                        "timestamp": datetime.now().isoformat(),
                        "system_health": metrics.system_health.value,
                        "active_agents": metrics.active_agents,
                        "uptime_seconds": metrics.uptime_seconds,
                        "version": "1.0.0"
                    }
            
            return {
                "status": "starting",
                "timestamp": datetime.now().isoformat(),
                "message": "System initializing"
            }
            
        except Exception as e:
            logger.error(f"++ Health check error: {str(e)} ++")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
            )
    
    # System information endpoint
    @app.get("/api/v1/system/info", tags=["System"])
    async def system_info():
        """Get comprehensive system information."""
        try:
            if not global_orchestrator:
                raise HTTPException(status_code=503, detail="System not ready")
            
            metrics_result = await global_orchestrator.get_system_metrics()
            if not metrics_result.success:
                raise HTTPException(status_code=500, detail="Failed to retrieve system metrics")
            
            metrics = metrics_result.data["current_metrics"]
            
            return {
                "success": True,
                "data": {
                    "system": {
                        "name": "Dynamic Context Engineering Framework",
                        "version": "1.0.0",
                        "status": metrics.system_health.value,
                        "uptime_seconds": metrics.uptime_seconds,
                        "started_at": global_orchestrator.startup_time.isoformat()
                    },
                    "metrics": {
                        "active_agents": metrics.active_agents,
                        "total_memory_items": metrics.total_memory_items,
                        "active_interactions": metrics.active_interactions,
                        "operations_per_minute": metrics.operations_per_minute,
                        "error_rate": metrics.error_rate,
                        "relationship_count": metrics.relationship_count,
                        "equipment_count": metrics.equipment_count
                    },
                    "features": {
                        "character_creation": True,
                        "real_time_interactions": True,
                        "memory_evolution": True,
                        "story_generation": True,
                        "equipment_tracking": True,
                        "relationship_dynamics": True,
                        "websocket_support": True,
                        "multiple_export_formats": True
                    },
                    "api_endpoints": {
                        "characters": "/api/v1/characters",
                        "interactions": "/api/v1/interactions",
                        "conversations": "/api/v1/conversations",
                        "stories": "/api/v1/stories",
                        "system": "/api/v1/system"
                    }
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"++ Error getting system info: {str(e)} ++")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # API documentation endpoint
    @app.get("/api/v1/system/endpoints", tags=["System"])
    async def list_api_endpoints():
        """List all available API endpoints with descriptions."""
        return {
            "success": True,
            "data": {
                "character_management": {
                    "base_path": "/api/v1/characters",
                    "endpoints": {
                        "POST /api/v1/characters": "Create new character with customization",
                        "GET /api/v1/characters": "List characters with filtering",
                        "GET /api/v1/characters/{id}": "Get character details",
                        "PUT /api/v1/characters/{id}": "Update character attributes",
                        "DELETE /api/v1/characters/{id}": "Delete character",
                        "GET /api/v1/archetypes": "List available character archetypes"
                    }
                },
                "interaction_system": {
                    "base_path": "/api/v1/interactions",
                    "endpoints": {
                        "POST /api/v1/interactions": "Initiate character interaction",
                        "GET /api/v1/interactions": "List interactions with filtering",
                        "GET /api/v1/interactions/{id}": "Get interaction status",
                        "POST /api/v1/conversations": "Start multi-character conversation",
                        "WS /api/v1/interactions/{id}/stream": "Real-time interaction updates"
                    }
                },
                "story_generation": {
                    "base_path": "/api/v1/stories",
                    "endpoints": {
                        "POST /api/v1/stories/generate": "Generate story from interactions",
                        "GET /api/v1/stories/generation/{id}": "Check generation status",
                        "GET /api/v1/stories/{id}/download": "Download generated story",
                        "GET /api/v1/stories": "List generated stories",
                        "DELETE /api/v1/stories/{id}": "Delete story"
                    }
                },
                "system_monitoring": {
                    "base_path": "/api/v1/system",
                    "endpoints": {
                        "GET /health": "System health check",
                        "GET /api/v1/system/info": "Comprehensive system information",
                        "GET /api/v1/system/endpoints": "List all API endpoints"
                    }
                }
            }
        }
    
    return app


def main():
    """Main entry point for the API server."""
    
    config = APIServerConfig()
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, config.log_level.upper()))
    
    # Create application
    app = create_app()
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    logger.info(f"++ Starting API server on {config.host}:{config.port} ++")
    logger.info(f"++ Database path: {config.database_path} ++")
    logger.info(f"++ Debug mode: {config.debug} ++")
    logger.info(f"++ Docs enabled: {config.enable_docs} ++")
    
    # Run server
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        access_log=True,
        reload=config.debug
    )


if __name__ == "__main__":
    """
    Run the API server directly.
    
    Usage:
        python src/api/main_api_server.py
        
    Environment Variables:
        API_HOST - Server host (default: 127.0.0.1)
        API_PORT - Server port (default: 8000)
        DATABASE_PATH - Database file path (default: data/api_server.db)
        DEBUG - Enable debug mode (default: false)
        ENABLE_DOCS - Enable API documentation (default: true)
        CORS_ORIGINS - CORS allowed origins (default: *)
        MAX_CONCURRENT_AGENTS - Maximum concurrent agents (default: 20)
        LOG_LEVEL - Logging level (default: INFO)
    """
    main()


# ++ BLESSED EXPORTS SANCTIFIED BY THE OMNISSIAH ++
__all__ = ['create_app', 'main', 'APIServerConfig']