#!/usr/bin/env python3
"""Test script to verify legacy endpoints are working."""

import asyncio
import subprocess
import time
import requests
import json
import threading
import uvicorn
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.main_api_server import create_app

def start_server():
    """Start server in background thread."""
    try:
        app = create_app()
        config = uvicorn.Config(app, host='127.0.0.1', port=8001, log_level='error')
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        print(f"Server error: {e}")

def test_endpoints():
    """Test all API endpoints."""
    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(5)  # Wait for server to start

    try:
        print("Testing API Endpoints...")
        print("=" * 50)
        
        # Test root endpoint
        try:
            response = requests.get('http://127.0.0.1:8001/', timeout=5)
            print(f"Root endpoint: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Available endpoints: {list(data.get('endpoints', {}).keys())}")
        except Exception as e:
            print(f"Root endpoint failed: {e}")
        
        # Test health endpoint 
        try:
            response = requests.get('http://127.0.0.1:8001/health', timeout=5)
            print(f"Health check: {response.status_code}")
            if response.status_code == 200:
                print(f"  Status: {response.json().get('status', 'unknown')}")
        except Exception as e:
            print(f"Health check failed: {e}")
        
        # Test legacy characters listing
        try:
            response = requests.get('http://127.0.0.1:8001/characters', timeout=5)
            print(f"Legacy characters: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                characters = data.get("characters", [])
                print(f"  Found {len(characters)} characters: {characters}")
            else:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"Legacy characters failed: {e}")
        
        # Test specific character endpoints
        test_characters = ['engineer', 'pilot', 'scientist']
        for char in test_characters:
            try:
                response = requests.get(f'http://127.0.0.1:8001/characters/{char}', timeout=5)
                print(f"Character {char}: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"  Name: {data.get('name', 'unknown')}")
                else:
                    print(f"  Error: {response.text}")
            except Exception as e:
                print(f"Character {char} failed: {e}")
        
        # Test legacy story generation
        try:
            test_payload = {
                'character_names': ['engineer', 'pilot'],
                'turns': 2
            }
            response = requests.post('http://127.0.0.1:8001/simulations', json=test_payload, timeout=15)
            print(f"Legacy simulations: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                story_length = len(result.get("story", ""))
                turns = result.get("turns_executed", 0)
                duration = result.get("duration_seconds", 0)
                print(f"  Story generated: {story_length} chars, {turns} turns, {duration:.1f}s")
            else:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"Legacy simulations failed: {e}")
            
        print("=" * 50)
        print("Testing complete!")
            
    except Exception as e:
        print(f'Test suite failed: {e}')

if __name__ == "__main__":
    test_endpoints()