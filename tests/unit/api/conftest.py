"""Shared fixtures for API unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from starlette.datastructures import URL, Headers


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.app = MagicMock()
    request.app.state = MagicMock()
    request.url = URL("http://testserver/api/test")
    request.method = "GET"
    request.headers = Headers({})
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.state = MagicMock()
    request.state.processing_time = 0.1
    request.state.request_id = "test-request-id"
    request.cookies = {}
    return request


@pytest.fixture
def mock_fastapi_app():
    """Create a mock FastAPI app."""
    app = FastAPI()
    app.state = MagicMock()
    return app


@pytest.fixture
def mock_response():
    """Create a mock Response object."""
    response = MagicMock()
    response.set_cookie = MagicMock()
    return response
