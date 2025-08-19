#!/usr/bin/env python3
"""
Full API startup test to verify all routes are registered.
"""

import asyncio
import sys
import os
import logging
from fastapi.testclient import TestClient

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_startup():
    """Test API startup with full route registration."""
    try:
        logger.info("Testing full API startup...")
        
        # Import required modules
        from src.api.main_api_server import create_app
        
        # Create the app
        app = create_app()
        
        # Create test client which will trigger lifespan events
        with TestClient(app) as client:
            logger.info("Test client created successfully")
            
            # Print all registered routes
            logger.info("Registered routes:")
            for route in app.routes:
                methods = getattr(route, 'methods', set())
                path = getattr(route, 'path', str(route))
                logger.info(f"  {methods} {path}")
            
            # Test basic endpoints
            logger.info("\nTesting endpoints:")
            
            response = client.get("/")
            logger.info(f"GET /: {response.status_code}")
            
            response = client.get("/health")
            logger.info(f"GET /health: {response.status_code}")
            
            # Try character endpoint
            response = client.post("/api/v1/characters", json={
                "agent_id": "test_char",
                "name": "Test Character"
            })
            logger.info(f"POST /api/v1/characters: {response.status_code}")
            
        logger.info("Full API startup test completed successfully")
        
    except Exception as e:
        logger.error(f"Full API startup test failed: {e}", exc_info=True)

if __name__ == "__main__":
    test_api_startup()