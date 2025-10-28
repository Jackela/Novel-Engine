#!/usr/bin/env python3
"""
Novel Engine Turn Orchestration Service

Main entry point for the turn orchestration REST API service.
Provides the complete M9 Orchestration milestone implementation with:

- 5-phase turn pipeline (World Update, Subjective Brief, Interaction, Event Integration, Narrative Integration)
- Saga pattern with compensation for reliability
- REST API endpoint: POST /v1/turns:run
- Comprehensive error handling and monitoring
- AI Gateway integration for narrative generation
- Cross-context coordination with Novel Engine
"""

import logging
import os
import sys
from pathlib import Path

# Add the contexts/orchestration directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

import uvicorn

from api.turn_api import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        (
            logging.FileHandler("orchestration.log")
            if os.environ.get("LOG_FILE")
            else logging.NullHandler()
        ),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for the Turn Orchestration service.

    Starts the FastAPI application with uvicorn server providing:
    - POST /v1/turns:run - Main turn execution endpoint
    - GET /v1/turns/{turn_id}/status - Turn status monitoring
    - GET /v1/health - Service health check
    - GET /v1/turns - List active turns
    - DELETE /v1/turns/{turn_id} - Cleanup turn resources
    """
    logger.info("Starting Novel Engine Turn Orchestration Service")

    # Configuration from environment variables
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    log_level = os.environ.get("LOG_LEVEL", "info").lower()
    reload = os.environ.get("RELOAD", "false").lower() == "true"
    workers = int(os.environ.get("WORKERS", 1))

    logger.info(
        f"Configuration: host={host}, port={port}, log_level={log_level}, reload={reload}, workers={workers}"
    )

    try:
        # Start the uvicorn server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=log_level,
            reload=reload,
            workers=(workers if not reload else 1),  # Multiple workers don't work with reload
            access_log=True,
            server_header=False,
            date_header=False,
        )

    except KeyboardInterrupt:
        logger.info("Service shutdown requested by user")
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
