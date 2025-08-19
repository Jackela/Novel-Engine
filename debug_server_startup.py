#!/usr/bin/env python3
"""
Debug server startup to check route registration.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.main_api_server import main

if __name__ == "__main__":
    # Set debug environment
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    # Run the main server function
    main()