#!/usr/bin/env python3
"""
Main API server for the Dynamic Context Engineering Framework.

This server unifies all API endpoints for the framework.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.core.system_orchestrator import SystemOrchestrator, OrchestratorConfig, OrchestratorMode
from src.api.character_api import create_character_api
from src.api.interaction_api import create_interaction_api
from src.api.story_generation_api import create_story_generation_api

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
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

global_orchestrator: Optional[SystemOrchestrator] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    global global_orchestrator
    logger.info("Starting API Server...")
    
    try:
        config = OrchestratorConfig(
            mode=OrchestratorMode.PRODUCTION,
            max_concurrent_agents=APIServerConfig().max_concurrent_agents,
            debug_logging=APIServerConfig().debug
        )
        global_orchestrator = SystemOrchestrator(database_path=APIServerConfig().database_path, config=config)
        await global_orchestrator.startup()
        logger.info("System Orchestrator started.")
        
        character_api = create_character_api(global_orchestrator)
        story_generation_api = create_story_generation_api(global_orchestrator)
        interaction_api = create_interaction_api(global_orchestrator)
        
        character_api._setup_routes()
        interaction_api.setup_routes(app)
        story_generation_api.setup_routes(app)
        
        app.state.orchestrator = global_orchestrator
        logger.info("All API components initialized.")
        
        yield
        
    finally:
        logger.info("Shutting down API Server...")
        if global_orchestrator:
            await global_orchestrator.shutdown()
            logger.info("System shutdown complete.")

def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""
    config = APIServerConfig()
    app = FastAPI(title="Dynamic Context Engineering Framework", version="1.0.0", lifespan=lifespan)
    
    app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})
    
    @app.get("/health", tags=["System"])
    async def health_check():
        """System health check."""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    return app

def main():
    """Main entry point for the API server."""
    config = APIServerConfig()
    logging.getLogger().setLevel(config.log_level.upper())
    app = create_app()
    os.makedirs("data", exist_ok=True)
    
    logger.info(f"Starting API server on {config.host}:{config.port}")
    uvicorn.run(app, host=config.host, port=config.port, log_level=config.log_level.lower(), reload=config.debug)

if __name__ == "__main__":
    main()

__all__ = ['create_app', 'main']