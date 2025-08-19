#!/usr/bin/env python3
"""Test API endpoints to diagnose story generation failures."""

import requests
import time
import threading
import uvicorn
from api_server import app

def start_server():
    """Start server in background thread."""
    uvicorn.run(app, host='127.0.0.1', port=8001, log_level='error')

def test_endpoints():
    """Test all API endpoints."""
    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(3)  # Wait for server to start

    try:
        # Test basic health check
        response = requests.get('http://127.0.0.1:8001/health', timeout=5)
        print(f'Health check: {response.status_code} - {response.json()}')
        
        # Test characters listing
        response = requests.get('http://127.0.0.1:8001/characters', timeout=5)
        print(f'Characters: {response.status_code} - {len(response.json().get("characters", []))} characters')
        
        # Test story generation - the failing endpoint
        test_payload = {
            'character_names': ['engineer', 'pilot'],
            'turns': 2
        }
        response = requests.post('http://127.0.0.1:8001/simulations', json=test_payload, timeout=10)
        print(f'Story generation: {response.status_code}')
        if response.status_code != 200:
            print(f'Error details: {response.text}')
        else:
            result = response.json()
            print(f'Story generated: {len(result.get("story", ""))} chars, {result.get("turns_executed", 0)} turns')
            
    except Exception as e:
        print(f'Test failed: {e}')

if __name__ == "__main__":
    test_endpoints()