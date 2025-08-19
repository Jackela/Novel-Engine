#!/usr/bin/env python3
"""
Debug API startup to identify routing issues.
"""

import asyncio
import sys
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_api_startup():
    """Test API startup and route registration."""
    try:
        logger.info("Testing API startup...")
        
        # Import required modules
        from src.api.main_api_server import create_app
        
        # Create the app
        app = create_app()
        
        # Print all registered routes
        logger.info("Registered routes:")
        for route in app.routes:
            logger.info(f"  {route.methods} {route.path}")
        
        logger.info("API startup test completed successfully")
        
    except Exception as e:
        logger.error(f"API startup test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_api_startup())