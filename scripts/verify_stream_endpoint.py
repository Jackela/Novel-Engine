#!/usr/bin/env python3
"""Verification script for the narrative generation streaming endpoint.

Usage:
    # With server running:
    python scripts/verify_stream_endpoint.py

    # Or with MOCK_LLM flag:
    MOCK_LLM=true python scripts/verify_stream_endpoint.py

This script connects to the streaming endpoint and displays the received
SSE events in real-time.
"""

from __future__ import annotations

import json
import sys

import httpx


def verify_stream_endpoint(
    base_url: str = "http://localhost:8000",
    max_tokens: int = 300,
) -> bool:
    """Verify the narrative streaming endpoint works correctly.

    Args:
        base_url: Base URL of the API server.
        max_tokens: Maximum tokens to generate.

    Returns:
        True if verification passed, False otherwise.
    """
    endpoint = f"{base_url}/api/narrative/generate/stream"

    print("=" * 60)
    print("Narrative Stream Endpoint Verification")
    print("=" * 60)
    print(f"Endpoint: {endpoint}")
    print(f"Max tokens: {max_tokens}")
    print("-" * 60)

    try:
        with httpx.Client(timeout=30.0) as client:
            with client.stream(
                "POST",
                endpoint,
                json={"max_tokens": max_tokens},
            ) as response:
                if response.status_code != 200:
                    print(f"ERROR: Unexpected status code: {response.status_code}")
                    return False

                content_type = response.headers.get("content-type", "")
                if "text/event-stream" not in content_type:
                    print(f"ERROR: Unexpected content-type: {content_type}")
                    return False

                print("Connection established. Receiving stream...")
                print("-" * 60)

                chunk_count = 0
                total_chars = 0

                for line in response.iter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            event_type = data.get("type", "unknown")

                            if event_type == "chunk":
                                chunk_count += 1
                                content = data.get("content", "")
                                total_chars += len(content)
                                print(content)

                            elif event_type == "done":
                                print("-" * 60)
                                print("Stream completed!")
                                metadata = data.get("metadata", {})
                                print(f"Total chunks: {metadata.get('total_chunks', 'N/A')}")
                                print(
                                    f"Total characters: {metadata.get('total_characters', 'N/A')}"
                                )
                                print(
                                    f"Generation time: {metadata.get('generation_time_ms', 'N/A')}ms"
                                )
                                print(f"Mock mode: {metadata.get('mock_mode', 'N/A')}")

                            elif event_type == "error":
                                print(f"ERROR: {data.get('content', 'Unknown error')}")
                                return False

                        except json.JSONDecodeError as e:
                            print(f"ERROR: Failed to parse JSON: {e}")
                            print(f"Line: {line}")

                print("-" * 60)
                print(f"Verification PASSED: Received {chunk_count} chunks, {total_chars} chars")
                return True

    except httpx.ConnectError:
        print("ERROR: Could not connect to server.")
        print("Make sure the server is running with:")
        print("  python -m src.api.main_api_server")
        return False
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = verify_stream_endpoint()
    sys.exit(0 if success else 1)
