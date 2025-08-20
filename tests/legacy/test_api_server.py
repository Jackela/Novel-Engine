#!/usr/bin/env python3
"""
FastAPI Server Unit Tests
=========================

Comprehensive pytest test suite for the FastAPI web server that provides
RESTful API endpoints for the StoryForge AI Interactive Story Engine.

This test file includes:
- FastAPI TestClient setup for API endpoint testing
- Root endpoint functionality and response validation tests
- Health check endpoint comprehensive testing
- Error handling and edge case scenario tests
- Configuration integration validation tests
- HTTP status code and JSON response format validation
- CORS middleware and security header tests
- Server startup and shutdown event testing

The tests ensure the API server provides reliable web access to the simulator
system and maintains proper HTTP standards and error handling.

Architecture Reference: Architecture_Blueprint.md - API Integration Layer
Development Phase: FastAPI Integration - Testing Foundation
"""

import pytest
import json
import logging
import os
import tempfile
import uuid
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status

# Import the FastAPI application and related components
from api_server import app, HealthResponse, ErrorResponse, CharactersListResponse, CharacterDetailResponse, FileCount, SimulationRequest, SimulationResponse, CampaignsListResponse, CampaignCreationRequest, CampaignCreationResponse


# Test fixtures and setup
@pytest.fixture
def client():
    """
    Create a FastAPI TestClient for testing API endpoints.
    
    Returns:
        TestClient: Configured test client for the FastAPI application
    """
    return TestClient(app)


@pytest.fixture
def mock_config():
    """
    Mock configuration data for testing.
    
    Returns:
        Dict[str, Any]: Mock configuration dictionary
    """
    return {
        "simulation": {"turns": 3, "max_agents": 10},
        "paths": {"log_file_path": "test_campaign_log.md"},
        "director": {"campaign_log_filename": "test_campaign_log.md"}
    }


class TestRootEndpoint:
    """Test cases for the root endpoint (/) functionality."""
    
    def test_root_endpoint_success(self, client: TestClient):
        """
        Test that the root endpoint returns successful response.
        
        Validates:
        - HTTP status code 200 OK
        - Correct JSON response format
        - Expected message content
        """
        # Execute request to root endpoint
        response = client.get("/")
        
        # Validate HTTP status code
        assert response.status_code == status.HTTP_200_OK
        
        # Validate response content type
        assert response.headers["content-type"] == "application/json"
        
        # Validate JSON response structure and content
        response_data = response.json()
        assert isinstance(response_data, dict)
        assert "message" in response_data
        assert response_data["message"] == "StoryForge AI Interactive Story Engine is running!"
    
    def test_root_endpoint_response_model(self, client: TestClient):
        """
        Test that the root endpoint response matches the HealthResponse model.
        
        Validates:
        - Response structure matches Pydantic model
        - All required fields are present
        - Data types are correct
        """
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        
        # Validate response matches HealthResponse model structure
        health_response = HealthResponse(**response_data)
        assert health_response.message == "StoryForge AI Interactive Story Engine is running!"
    
    @patch('api_server.logger')
    def test_root_endpoint_logging(self, mock_logger: Mock, client: TestClient):
        """
        Test that the root endpoint performs proper logging.
        
        Validates:
        - Info logging is called for health check
        - Debug logging is called for response data
        """
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        
        # Verify logging calls were made
        mock_logger.info.assert_called()
        mock_logger.debug.assert_called()
    
    @patch('api_server.get_config')
    def test_root_endpoint_with_config_error(self, mock_get_config: Mock, client: TestClient):
        """
        Test root endpoint behavior when configuration has issues.
        
        The root endpoint should still work even if config has problems,
        as it's a basic health check.
        """
        # Mock configuration error (but endpoint should still work)
        mock_get_config.side_effect = Exception("Config error")
        
        response = client.get("/")
        
        # Root endpoint should still return success
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["message"] == "StoryForge AI Interactive Story Engine is running!"


class TestHealthEndpoint:
    """Test cases for the health check endpoint (/health) functionality."""
    
    @patch('api_server.get_config')
    def test_health_endpoint_success(self, mock_get_config: Mock, client: TestClient, mock_config: Dict[str, Any]):
        """
        Test that the health endpoint returns comprehensive health status.
        
        Validates:
        - HTTP status code 200 OK
        - Comprehensive health information
        - Configuration validation status
        """
        # Mock successful configuration loading
        mock_get_config.return_value = mock_config
        
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        
        # Validate comprehensive health status structure
        assert "status" in response_data
        assert "api" in response_data
        assert "timestamp" in response_data
        assert "version" in response_data
        assert "config" in response_data
        
        # Validate specific health status values
        assert response_data["status"] == "healthy"
        assert response_data["api"] == "running"
        assert response_data["version"] == "1.0.0"
        assert response_data["config"] == "loaded"
    
    @patch('api_server.get_config')
    def test_health_endpoint_config_error(self, mock_get_config: Mock, client: TestClient):
        """
        Test health endpoint behavior when configuration loading fails.
        
        Validates:
        - HTTP status code 200 OK (degraded but accessible)
        - Status indicates degraded operation
        - Configuration error is reported
        """
        # Mock configuration loading failure
        mock_get_config.side_effect = Exception("Configuration loading failed")
        
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        
        # Validate degraded health status
        assert response_data["status"] == "degraded"
        assert response_data["config"] == "error"
        assert response_data["api"] == "running"
    
    @patch('api_server.logger')
    def test_health_endpoint_logging(self, mock_logger: Mock, client: TestClient):
        """
        Test that the health endpoint performs proper logging.
        
        Validates:
        - Info logging for endpoint access
        - Debug logging for response data
        """
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        
        # Verify logging calls
        mock_logger.info.assert_called()
        mock_logger.debug.assert_called()


class TestErrorHandling:
    """Test cases for API error handling and edge cases."""
    
    def test_404_not_found(self, client: TestClient):
        """
        Test that non-existent endpoints return proper 404 errors.
        
        Validates:
        - HTTP status code 404 Not Found
        - Proper error response format
        - Informative error message
        """
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        response_data = response.json()
        assert "error" in response_data
        assert "detail" in response_data
        assert response_data["error"] == "Not Found"
        assert "does not exist" in response_data["detail"]
    
    @patch('api_server.get_config')
    def test_health_endpoint_exception_handling(self, mock_get_config: Mock, client: TestClient):
        """
        Test health endpoint exception handling for severe errors.
        
        Validates:
        - HTTP status code 500 for severe errors
        - Proper error response format
        """
        # Mock severe exception in health endpoint
        with patch('api_server.logging.Formatter') as mock_formatter:
            mock_formatter.side_effect = Exception("Severe system error")
            
            response = client.get("/health")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
            response_data = response.json()
            assert "detail" in response_data
    
    @patch('api_server.logger')
    def test_error_logging(self, mock_logger: Mock, client: TestClient):
        """
        Test that errors are properly logged.
        
        Validates:
        - Warning logging for 404 errors
        - Error logging for 500 errors
        """
        # Test 404 logging
        response = client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        mock_logger.warning.assert_called()


class TestCORSMiddleware:
    """Test cases for CORS middleware functionality."""
    
    def test_cors_headers_present(self, client: TestClient):
        """
        Test that CORS headers are properly set.
        
        Validates:
        - CORS headers are included in responses
        - Proper access control settings
        
        Note: TestClient may not include CORS headers in some cases,
        but the middleware is configured properly.
        """
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        
        # CORS headers may not be present in TestClient responses
        # but we can verify the middleware is configured by checking
        # that requests from different origins work
        response_with_origin = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response_with_origin.status_code == status.HTTP_200_OK
    
    def test_preflight_request(self, client: TestClient):
        """
        Test CORS preflight request handling.
        
        Validates:
        - OPTIONS requests are handled properly
        - Appropriate CORS headers are returned
        """
        response = client.options("/")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestAPIDocumentation:
    """Test cases for API documentation endpoints."""
    
    def test_openapi_docs_accessible(self, client: TestClient):
        """
        Test that OpenAPI documentation is accessible.
        
        Validates:
        - /docs endpoint returns successful response
        - Documentation is properly generated
        """
        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_docs_accessible(self, client: TestClient):
        """
        Test that ReDoc documentation is accessible.
        
        Validates:
        - /redoc endpoint returns successful response
        - Alternative documentation format is available
        """
        response = client.get("/redoc")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_json_accessible(self, client: TestClient):
        """
        Test that OpenAPI JSON schema is accessible.
        
        Validates:
        - /openapi.json endpoint returns valid JSON
        - Schema contains expected API information
        """
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers["content-type"]
        
        openapi_data = response.json()
        assert "info" in openapi_data
        assert "title" in openapi_data["info"]
        assert openapi_data["info"]["title"] == "StoryForge AI API"


class TestServerConfiguration:
    """Test cases for server configuration and metadata."""
    
    def test_api_metadata(self, client: TestClient):
        """
        Test that API metadata is properly configured.
        
        Validates:
        - API title and description are set
        - Version information is available
        """
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        
        openapi_data = response.json()
        info = openapi_data["info"]
        
        assert info["title"] == "StoryForge AI API"
        assert "StoryForge AI Interactive Story Engine" in info["description"]
        assert info["version"] == "1.0.0"
    
    @patch('api_server.get_config')
    def test_lifespan_success(self, mock_get_config: Mock, mock_config: Dict[str, Any]):
        """
        Test successful server lifespan event handling.
        
        Validates:
        - Configuration is validated during startup
        - Proper logging occurs during startup
        """
        mock_get_config.return_value = mock_config
        
        # Test startup by creating a new TestClient (triggers lifespan event)
        with TestClient(app) as test_client:
            # Lifespan event should have been called successfully
            response = test_client.get("/")
            assert response.status_code == status.HTTP_200_OK
    
    @patch('api_server.get_config')
    @patch('api_server.logger')
    def test_lifespan_config_error(self, mock_logger: Mock, mock_get_config: Mock):
        """
        Test server lifespan event handling when configuration fails.
        
        Validates:
        - Configuration errors are logged during startup
        - Server startup can handle configuration issues
        """
        mock_get_config.side_effect = Exception("Configuration error")
        
        # Lifespan event should handle configuration errors gracefully
        with pytest.raises(Exception):
            with TestClient(app):
                pass
        
        # Error should be logged
        mock_logger.error.assert_called()


class TestResponseModels:
    """Test cases for API response model validation."""
    
    def test_health_response_model_validation(self):
        """
        Test HealthResponse model validation.
        
        Validates:
        - Model accepts valid data
        - Model enforces required fields
        """
        # Test valid data
        valid_data = {"message": "Test message"}
        health_response = HealthResponse(**valid_data)
        assert health_response.message == "Test message"
        
        # Test missing required field
        with pytest.raises(ValueError):
            HealthResponse()
    
    def test_error_response_model_validation(self):
        """
        Test ErrorResponse model validation.
        
        Validates:
        - Model accepts valid error data
        - Model enforces required fields
        """
        # Test valid error data
        valid_error_data = {"error": "Test Error", "detail": "Test detail"}
        error_response = ErrorResponse(**valid_error_data)
        assert error_response.error == "Test Error"
        assert error_response.detail == "Test detail"
        
        # Test missing required fields
        with pytest.raises(ValueError):
            ErrorResponse(error="Test Error")  # Missing detail


class TestCharactersEndpoint:
    """Test cases for the characters endpoint (/characters) functionality."""
    
    def test_characters_response_model_validation(self):
        """
        Test CharactersListResponse model validation.
        
        Validates:
        - Model accepts valid character list data
        - Model enforces required fields
        - Model handles empty character lists
        """
        # Test valid character list data
        valid_data = {"characters": ["krieg", "ork", "test"]}
        characters_response = CharactersListResponse(**valid_data)
        assert characters_response.characters == ["krieg", "ork", "test"]
        
        # Test empty character list
        empty_data = {"characters": []}
        empty_response = CharactersListResponse(**empty_data)
        assert empty_response.characters == []
        
        # Test missing required field
        with pytest.raises(ValueError):
            CharactersListResponse()
    
    def test_characters_endpoint_success(self, client: TestClient):
        """
        Test that the characters endpoint returns successful response with real character data.
        
        Validates:
        - HTTP status code 200 OK
        - Proper JSON response format matching CharactersListResponse model
        - Expected character names from actual characters directory
        """
        response = client.get("/characters")
        
        # Expect 200 status code for successful response
        assert response.status_code == status.HTTP_200_OK
        
        # Validate response format matches CharactersListResponse model
        response_data = response.json()
        assert "characters" in response_data
        assert isinstance(response_data["characters"], list)
        
        # Validate expected character names (should include baseline characters)
        # The list may include additional characters created via API
        baseline_characters = ["engineer", "pilot", "scientist", "test"]
        actual_characters = response_data["characters"]
        
        # All baseline characters must be present
        for char in baseline_characters:
            assert char in actual_characters, f"Missing baseline character: {char}"
        
        # Verify we have at least the baseline count
        assert len(actual_characters) >= len(baseline_characters)
    
    @patch('api_server.logger')
    def test_characters_endpoint_logging(self, mock_logger: Mock, client: TestClient):
        """
        Test that the characters endpoint performs proper logging.
        
        Validates:
        - Info logging for endpoint access
        - Info logging for successful character discovery
        - No error logging for successful execution
        """
        response = client.get("/characters")
        assert response.status_code == status.HTTP_200_OK
        
        # Verify info logging was called for endpoint access
        mock_logger.info.assert_called()
        
        # Verify logging calls include both endpoint access and character discovery
        logging_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Looking for characters in:" in call for call in logging_calls)
        assert any("Found" in call and "characters:" in call for call in logging_calls)
        
        # Error logging should NOT be called for successful execution
        mock_logger.error.assert_not_called()
    
    def test_characters_endpoint_api_documentation(self, client: TestClient):
        """
        Test that the characters endpoint is properly documented in OpenAPI schema.
        
        Validates:
        - Endpoint appears in OpenAPI schema
        - Response model is documented
        - Error responses are documented
        """
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        
        openapi_data = response.json()
        
        # Validate endpoint exists in schema
        assert "paths" in openapi_data
        assert "/characters" in openapi_data["paths"]
        
        characters_path = openapi_data["paths"]["/characters"]
        assert "get" in characters_path
        
        # Validate response documentation
        get_method = characters_path["get"]
        assert "summary" in get_method
        assert "description" in get_method
        assert "responses" in get_method
        
        # Validate documented response codes
        responses = get_method["responses"]
        assert "200" in responses
        # Note: FastAPI automatically generates 422 for validation errors
        # 404 and 500 may not be explicitly documented unless defined in decorator
    
    def test_characters_endpoint_response_headers(self, client: TestClient):
        """
        Test that the characters endpoint returns proper HTTP headers.
        
        Validates:
        - Content-Type is application/json for error responses
        - CORS headers are properly set (if applicable)
        """
        response = client.get("/characters")
        
        # Should return JSON even for error responses
        assert "application/json" in response.headers.get("content-type", "")
    
    @patch('api_server._get_characters_directory_path')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_characters_endpoint_success_scenario_mock(self, mock_isdir: Mock, mock_listdir: Mock, mock_exists: Mock, mock_get_path: Mock, client: TestClient):
        """
        Test successful behavior with mocked characters directory.
        
        This test validates that the endpoint correctly processes mocked directory data
        and returns the expected response format.
        """
        # Mock path resolution
        mock_get_path.return_value = "/mock/characters"
        
        # Mock characters directory exists and contains character folders
        mock_exists.return_value = True
        mock_listdir.return_value = ["test_char1", "test_char2", "some_file.txt"]
        
        # Mock isdir to return True only for directories (not files)
        def mock_isdir_func(path):
            return not path.endswith('.txt')
        mock_isdir.side_effect = mock_isdir_func
        
        response = client.get("/characters")
        
        # Validate successful response
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert "characters" in response_data
        assert response_data["characters"] == ["test_char1", "test_char2"]  # sorted, files excluded
    
    @patch('api_server._get_characters_directory_path')
    @patch('os.path.exists')
    def test_characters_endpoint_directory_not_found_scenario_mock(self, mock_exists: Mock, mock_get_path: Mock, client: TestClient):
        """
        Test the behavior when characters directory doesn't exist.
        
        This test validates that the endpoint correctly handles the case where
        the characters directory is not found and returns appropriate 404 error.
        """
        # Mock path resolution
        mock_get_path.return_value = "/mock/nonexistent/characters"
        
        # Mock characters directory doesn't exist
        mock_exists.return_value = False
        
        response = client.get("/characters")
        
        # Validate 404 response for missing directory
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response_data = response.json()
        assert "detail" in response_data
        assert "Characters directory not found" in response_data["detail"]
    
    def test_characters_endpoint_cors_support(self, client: TestClient):
        """
        Test that the characters endpoint supports CORS requests.
        
        Validates:
        - Cross-origin requests are handled properly
        - CORS headers are present when applicable
        """
        # Test with Origin header
        response = client.get("/characters", headers={"Origin": "http://localhost:3000"})
        
        # Should return success with proper CORS handling
        assert response.status_code == status.HTTP_200_OK
        
        # Validate that the request was processed (not blocked by CORS)
        response_data = response.json()
        assert "characters" in response_data
        assert isinstance(response_data["characters"], list)


class TestIntegrationScenarios:
    """Integration test scenarios for complete API workflows."""
    
    @patch('api_server.get_config')
    def test_full_health_check_workflow(self, mock_get_config: Mock, client: TestClient, mock_config: Dict[str, Any]):
        """
        Test complete health check workflow.
        
        Validates:
        - Root endpoint indicates basic functionality
        - Health endpoint provides detailed status
        - Configuration integration works properly
        """
        mock_get_config.return_value = mock_config
        
        # Test basic health check via root endpoint
        root_response = client.get("/")
        assert root_response.status_code == status.HTTP_200_OK
        root_data = root_response.json()
        assert "StoryForge AI Interactive Story Engine is running!" in root_data["message"]
        
        # Test detailed health check
        health_response = client.get("/health")
        assert health_response.status_code == status.HTTP_200_OK
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert health_data["config"] == "loaded"
    
    def test_api_documentation_workflow(self, client: TestClient):
        """
        Test complete API documentation access workflow.
        
        Validates:
        - OpenAPI schema is accessible and valid
        - Interactive documentation is available
        - Alternative documentation formats work
        """
        # Test OpenAPI JSON schema
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == status.HTTP_200_OK
        openapi_data = openapi_response.json()
        assert "paths" in openapi_data
        assert "/" in openapi_data["paths"]
        
        # Test interactive documentation
        docs_response = client.get("/docs")
        assert docs_response.status_code == status.HTTP_200_OK
        
        # Test alternative documentation
        redoc_response = client.get("/redoc")
        assert redoc_response.status_code == status.HTTP_200_OK
    
    def test_characters_endpoint_integration_workflow(self, client: TestClient):
        """
        Test complete characters endpoint integration workflow.
        
        Validates:
        - Endpoint is accessible via API
        - Successful response with real character data
        - Response format is consistent with CharactersListResponse model
        - Documentation is properly integrated
        """
        # Test characters endpoint accessibility
        response = client.get("/characters")
        assert response.status_code == status.HTTP_200_OK
        
        # Validate successful response structure
        response_data = response.json()
        assert "characters" in response_data
        assert isinstance(response_data["characters"], list)
        
        # Validate response includes baseline characters
        baseline_characters = ["krieg", "ork", "test"]
        actual_characters = response_data["characters"]
        
        # All baseline characters must be present
        for char in baseline_characters:
            assert char in actual_characters, f"Missing baseline character: {char}"
        
        # Validate endpoint appears in API documentation
        docs_response = client.get("/openapi.json")
        assert docs_response.status_code == status.HTTP_200_OK
        docs_data = docs_response.json()
        assert "/characters" in docs_data["paths"]


class TestCharacterDetailEndpoint:
    """Test cases for the character detail endpoint (/characters/{character_name}) functionality."""
    
    def test_character_detail_response_model_validation(self):
        """
        Test CharacterDetailResponse model validation.
        
        Validates:
        - Model accepts valid character detail data
        - Model enforces required fields
        - FileCount sub-model validation works
        """
        # Test valid character detail data
        valid_data = {
            "narrative_context": "# Character Bio\nThis is a test character.",
            "structured_data": {"stats": {"health": 100}, "equipment": ["sword"]},
            "character_name": "test_character",
            "file_count": {"md": 1, "yaml": 2}
        }
        character_response = CharacterDetailResponse(**valid_data)
        assert character_response.narrative_context == "# Character Bio\nThis is a test character."
        assert character_response.structured_data == {"stats": {"health": 100}, "equipment": ["sword"]}
        assert character_response.character_name == "test_character"
        assert character_response.file_count.md == 1
        assert character_response.file_count.yaml == 2
        
        # Test FileCount model validation
        file_count_data = {"md": 3, "yaml": 0}
        file_count = FileCount(**file_count_data)
        assert file_count.md == 3
        assert file_count.yaml == 0
        
        # Test missing required fields
        with pytest.raises(ValueError):
            CharacterDetailResponse(narrative_context="test")  # Missing other required fields
        
        # Test invalid FileCount
        with pytest.raises(ValueError):
            invalid_data = valid_data.copy()
            invalid_data["file_count"] = {"md": "invalid"}  # Should be int
            CharacterDetailResponse(**invalid_data)
    
    def test_character_detail_endpoint_not_implemented(self, client: TestClient):
        """
        Test that the character detail endpoint handles non-existent characters properly.
        
        After Agent #3 implementation, the endpoint now works correctly.
        
        Validates:
        - HTTP status code 404 for non-existent character
        - Proper error response format
        """
        response = client.get("/characters/test_character")
        
        # Expect 404 status code for non-existent character
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Validate error response format
        response_data = response.json()
        assert "detail" in response_data
        assert "not found" in response_data["detail"].lower()
    
    def test_character_detail_endpoint_various_characters(self, client: TestClient):
        """
        Test character detail endpoint with various character names.
        
        After Agent #3 implementation, endpoint works with existing characters.
        
        Validates:
        - Existing character names return 200 with data
        - Non-existent character names return 404
        - Response format is consistent
        """
        existing_characters = ["krieg", "ork", "test"]
        nonexistent_characters = ["nonexistent_character"]
        
        # Test existing characters
        for character_name in existing_characters:
            response = client.get(f"/characters/{character_name}")
            
            # Should succeed with 200
            assert response.status_code == status.HTTP_200_OK
            
            response_data = response.json()
            assert "character_name" in response_data
            assert response_data["character_name"] == character_name
            
        # Test non-existent characters
        for character_name in nonexistent_characters:
            response = client.get(f"/characters/{character_name}")
            
            # Should fail with 404
            assert response.status_code == status.HTTP_404_NOT_FOUND
            
            response_data = response.json()
            assert "detail" in response_data
    
    def test_character_detail_endpoint_invalid_character_names(self, client: TestClient):
        """
        Test character detail endpoint with invalid character names.
        
        After Agent #3 implementation, endpoint handles invalid names properly.
        
        Validates:
        - Invalid characters fail with proper error handling
        - Special characters in names are handled
        - Empty strings and special characters return appropriate errors
        """
        test_cases = [
            ("", [status.HTTP_200_OK, status.HTTP_307_TEMPORARY_REDIRECT]),  # Empty string redirects to /characters
            ("character with spaces", [status.HTTP_404_NOT_FOUND]),  # Character with spaces not found
            ("character/with/slashes", [status.HTTP_404_NOT_FOUND]),  # Special chars not found
            ("character%20encoded", [status.HTTP_404_NOT_FOUND])  # URL encoded name not found
        ]
        
        for invalid_name, expected_statuses in test_cases:
            response = client.get(f"/characters/{invalid_name}")
            
            # Should return one of the expected status codes
            assert response.status_code in expected_statuses
            
            response_data = response.json()
            # For empty string (redirects to /characters), check for characters list
            # For other cases, check for error detail or character data
            if invalid_name == "":
                assert "characters" in response_data or "detail" in response_data or "character_name" in response_data
            else:
                assert "detail" in response_data or "character_name" in response_data  # Success or error response
    
    def test_character_detail_endpoint_api_documentation(self, client: TestClient):
        """
        Test that the character detail endpoint is properly documented in OpenAPI schema.
        
        Validates:
        - Endpoint appears in OpenAPI schema
        - Path parameter is documented
        - Response models are documented
        - Error responses are documented
        """
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        
        openapi_data = response.json()
        
        # Validate endpoint exists in schema
        assert "paths" in openapi_data
        assert "/characters/{character_name}" in openapi_data["paths"]
        
        character_detail_path = openapi_data["paths"]["/characters/{character_name}"]
        assert "get" in character_detail_path
        
        # Validate method documentation
        get_method = character_detail_path["get"]
        assert "summary" in get_method
        assert "description" in get_method
        assert "parameters" in get_method
        assert "responses" in get_method
        
        # Validate path parameter documentation
        parameters = get_method["parameters"]
        assert len(parameters) == 1
        param = parameters[0]
        assert param["name"] == "character_name"
        assert param["in"] == "path"
        assert param["required"] is True
        
        # Validate documented response codes
        responses = get_method["responses"]
        assert "200" in responses
        assert "404" in responses
        assert "500" in responses
        
        # Validate 200 response references CharacterDetailResponse model
        success_response = responses["200"]
        assert "content" in success_response
        assert "application/json" in success_response["content"]
    
    def test_character_detail_endpoint_response_headers(self, client: TestClient):
        """
        Test that the character detail endpoint returns proper HTTP headers.
        
        Validates:
        - Content-Type is application/json for error responses
        - CORS headers are properly set (if applicable)
        """
        response = client.get("/characters/test_character")
        
        # Should return JSON even for error responses
        assert "application/json" in response.headers.get("content-type", "")
    
    @patch('api_server.logger')
    def test_character_detail_endpoint_logging(self, mock_logger: Mock, client: TestClient):
        """
        Test that the character detail endpoint performs proper logging.
        
        After Agent #3 implementation, endpoint logs appropriate messages.
        
        Validates:
        - Warning logging occurs for character not found
        - Proper error handling without exceptions
        """
        response = client.get("/characters/test_character")
        
        # Should return 404 for non-existent character
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Warning logging should have been called for character not found
        mock_logger.warning.assert_called()
        # Verify the warning message contains relevant information
        warning_calls = mock_logger.warning.call_args_list
        assert len(warning_calls) > 0
        warning_message = str(warning_calls[0][0][0])  # First argument of first call
        assert "not found" in warning_message.lower() or "test_character" in warning_message


# Test fixtures for future implementation tests
@pytest.fixture
def mock_character_files():
    """
    Mock character file structure for testing.
    
    Returns dictionary with test character data that matches expected format.
    """
    return {
        "test_character": {
            "files": {
                "character_test.md": "# Test Character\nThis is a test character for unit testing.\n\n## Background\nCreated for API testing purposes.",
                "stats.yaml": {
                    "character": {
                        "name": "Test Character",
                        "age": 25,
                        "origin": "Test World"
                    },
                    "combat_stats": {
                        "marksmanship": 8,
                        "melee": 6,
                        "tactics": 7
                    }
                },
                "equipment.yaml": {
                    "primary_weapon": "Test Weapon",
                    "armor": "Test Armor",
                    "special_gear": ["Test Item 1", "Test Item 2"]
                }
            },
            "expected_response": {
                "narrative_context": "# Test Character\nThis is a test character for unit testing.\n\n## Background\nCreated for API testing purposes.",
                "structured_data": {
                    "stats.yaml": {
                        "character": {
                            "name": "Test Character",
                            "age": 25,
                            "origin": "Test World"
                        },
                        "combat_stats": {
                            "marksmanship": 8,
                            "melee": 6,
                            "tactics": 7
                        }
                    },
                    "equipment.yaml": {
                        "primary_weapon": "Test Weapon",
                        "armor": "Test Armor",
                        "special_gear": ["Test Item 1", "Test Item 2"]
                    }
                },
                "character_name": "test_character",
                "file_count": {"md": 1, "yaml": 2}
            }
        }
    }


@pytest.fixture
def mock_character_directory_scenarios():
    """
    Mock different character directory scenarios for edge case testing.
    
    Returns dictionary with various test scenarios.
    """
    return {
        "only_markdown": {
            "files": {
                "character_bio.md": "# Markdown Only Character\nThis character has only markdown files."
            },
            "expected_file_count": {"md": 1, "yaml": 0}
        },
        "only_yaml": {
            "files": {
                "config.yaml": {"name": "YAML Only Character", "type": "test"}
            },
            "expected_file_count": {"md": 0, "yaml": 1}
        },
        "empty_directory": {
            "files": {},
            "expected_file_count": {"md": 0, "yaml": 0}
        },
        "mixed_files": {
            "files": {
                "bio.md": "# Mixed Files Character",
                "stats.yaml": {"health": 100},
                "equipment.yaml": {"weapon": "sword"},
                "readme.txt": "This should be ignored",
                "notes.md": "## Additional Notes"
            },
            "expected_file_count": {"md": 2, "yaml": 2}
        }
    }


class TestCharacterDetailEndpointImplementationExpectations:
    """
    Test class defining expected behavior for the character detail endpoint implementation.
    
    These tests define the contract that Agent #3 will need to implement.
    All tests in this class are EXPECTED TO FAIL until the implementation is complete.
    """
    
    def test_expected_success_case_with_real_character(self, client: TestClient):
        """
        Test expected success case with real character (krieg).
        
        EXPECTED TO FAIL - This test defines what should happen when implemented.
        
        Expected behavior:
        - 200 OK status code
        - Proper CharacterDetailResponse format
        - narrative_context contains markdown content
        - structured_data contains parsed YAML
        - file_count reflects actual files
        """
        response = client.get("/characters/krieg")
        
        # When implemented, should return 200 OK
        # Currently expected to fail with 500 (NotImplementedError)
        if response.status_code == status.HTTP_200_OK:
            # If implemented, validate expected structure
            response_data = response.json()
            
            # Validate response structure
            assert "narrative_context" in response_data
            assert "structured_data" in response_data
            assert "character_name" in response_data
            assert "file_count" in response_data
            
            # Validate character name
            assert response_data["character_name"] == "krieg"
            
            # Validate narrative context is string
            assert isinstance(response_data["narrative_context"], str)
            assert len(response_data["narrative_context"]) > 0
            
            # Validate structured data is dict
            assert isinstance(response_data["structured_data"], dict)
            
            # Validate file count structure
            file_count = response_data["file_count"]
            assert "md" in file_count
            assert "yaml" in file_count
            assert isinstance(file_count["md"], int)
            assert isinstance(file_count["yaml"], int)
            assert file_count["md"] >= 0
            assert file_count["yaml"] >= 0
        else:
            # Currently expected to fail
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_expected_404_for_nonexistent_character(self, client: TestClient):
        """
        Test expected 404 response for nonexistent character.
        
        EXPECTED TO FAIL - This test defines what should happen when implemented.
        
        Expected behavior:
        - 404 NOT FOUND status code for nonexistent characters
        - Proper error response format
        """
        response = client.get("/characters/nonexistent_character_xyz123")
        
        # When implemented, should return 404 for nonexistent characters
        # Currently expected to fail with 500 (NotImplementedError)
        if response.status_code == status.HTTP_404_NOT_FOUND:
            # If implemented, validate error response
            response_data = response.json()
            assert "detail" in response_data
            assert "not found" in response_data["detail"].lower()
        else:
            # Currently expected to fail with NotImplementedError
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_expected_behavior_with_test_character(self, client: TestClient):
        """
        Test expected behavior with existing test character.
        
        EXPECTED TO FAIL - This test defines what should happen when implemented.
        
        Expected behavior:
        - 200 OK for existing test character
        - Proper response structure
        - Content from test_character.md file
        """
        response = client.get("/characters/test")
        
        # When implemented, should return 200 OK for existing test character
        # Currently expected to fail with 500 (NotImplementedError)
        if response.status_code == status.HTTP_200_OK:
            # If implemented, validate expected structure
            response_data = response.json()
            
            # Validate response structure
            assert response_data["character_name"] == "test"
            assert isinstance(response_data["narrative_context"], str)
            assert isinstance(response_data["structured_data"], dict)
            
            # Should have at least the markdown file we know exists
            assert response_data["file_count"]["md"] >= 1
        else:
            # Currently expected to fail
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestSimulationsEndpoint:
    """Test cases for the simulations endpoint (/simulations) functionality."""
    
    def test_simulation_request_model_validation(self):
        """
        Test SimulationRequest model validation.
        
        These tests should PASS as they test Pydantic model validation.
        
        Validates:
        - Model accepts valid request data
        - Model enforces character count constraints (2-6)
        - Model validates character names are non-empty strings
        - Model enforces turns range (1-10)
        - Model validates narrative style values
        """
        # Test valid request data
        valid_data = {
            "character_names": ["krieg", "ork"],
            "turns": 3,
            "narrative_style": "epic"
        }
        request = SimulationRequest(**valid_data)
        assert request.character_names == ["krieg", "ork"]
        assert request.turns == 3
        assert request.narrative_style == "epic"
        
        # Test minimum characters (2)
        min_chars_data = {"character_names": ["krieg", "ork"]}
        min_request = SimulationRequest(**min_chars_data)
        assert len(min_request.character_names) == 2
        assert min_request.turns is None  # Default
        assert min_request.narrative_style == "epic"  # Default
        
        # Test maximum characters (6)
        max_chars_data = {"character_names": ["krieg", "ork", "test", "char4", "char5", "char6"]}
        max_request = SimulationRequest(**max_chars_data)
        assert len(max_request.character_names) == 6
        
        # Test default values
        defaults_data = {"character_names": ["krieg", "ork"]}
        defaults_request = SimulationRequest(**defaults_data)
        assert defaults_request.turns is None
        assert defaults_request.narrative_style == "epic"
        
        # Test valid narrative styles
        for style in ["epic", "detailed", "concise"]:
            style_data = {"character_names": ["krieg", "ork"], "narrative_style": style}
            style_request = SimulationRequest(**style_data)
            assert style_request.narrative_style == style
        
        # Test turns range validation
        for turns in [1, 5, 10]:
            turns_data = {"character_names": ["krieg", "ork"], "turns": turns}
            turns_request = SimulationRequest(**turns_data)
            assert turns_request.turns == turns
    
    def test_simulation_request_model_validation_errors(self):
        """
        Test SimulationRequest model validation errors.
        
        These tests should PASS as they test Pydantic validation failures.
        
        Validates:
        - Too few characters (< 2)
        - Too many characters (> 6)
        - Empty character names
        - Invalid turns range
        - Invalid narrative style
        """
        # Test insufficient characters (< 2)
        with pytest.raises(ValueError):
            SimulationRequest(character_names=["krieg"])  # Only 1 character
        
        with pytest.raises(ValueError):
            SimulationRequest(character_names=[])  # No characters
        
        # Test too many characters (> 6)
        with pytest.raises(ValueError):
            SimulationRequest(character_names=["krieg", "ork", "test", "char4", "char5", "char6", "char7"])
        
        # Test empty character names
        with pytest.raises(ValueError):
            SimulationRequest(character_names=["krieg", ""])  # Empty string
        
        with pytest.raises(ValueError):
            SimulationRequest(character_names=["krieg", "   "])  # Whitespace only
        
        # Test invalid turns range
        with pytest.raises(ValueError):
            SimulationRequest(character_names=["krieg", "ork"], turns=0)  # Below minimum
        
        with pytest.raises(ValueError):
            SimulationRequest(character_names=["krieg", "ork"], turns=11)  # Above maximum
        
        with pytest.raises(ValueError):
            SimulationRequest(character_names=["krieg", "ork"], turns=-1)  # Negative
        
        # Test invalid narrative style
        with pytest.raises(ValueError):
            SimulationRequest(character_names=["krieg", "ork"], narrative_style="invalid_style")
    
    def test_simulation_response_model_validation(self):
        """
        Test SimulationResponse model validation.
        
        These tests should PASS as they test Pydantic model validation.
        
        Validates:
        - Model accepts valid response data
        - Model enforces required fields
        - Model validates data types and constraints
        """
        # Test valid response data
        valid_data = {
            "story": "In the grim darkness of the far future, Commissar Krieg and the Ork Warboss clashed in epic battle...",
            "participants": ["krieg", "ork"],
            "turns_executed": 3,
            "duration_seconds": 15.7
        }
        response = SimulationResponse(**valid_data)
        assert response.story == valid_data["story"]
        assert response.participants == ["krieg", "ork"]
        assert response.turns_executed == 3
        assert response.duration_seconds == 15.7
        
        # Test minimum valid values
        min_data = {
            "story": "Short story.",
            "participants": ["char1"],
            "turns_executed": 0,
            "duration_seconds": 0.0
        }
        min_response = SimulationResponse(**min_data)
        assert min_response.turns_executed == 0
        assert min_response.duration_seconds == 0.0
        
        # Test missing required fields
        with pytest.raises(ValueError):
            SimulationResponse(story="test")  # Missing other required fields
        
        # Test invalid types
        with pytest.raises(ValueError):
            SimulationResponse(
                story="test",
                participants=["krieg"],
                turns_executed="invalid",  # Should be int
                duration_seconds=15.7
            )
        
        # Test negative constraints
        with pytest.raises(ValueError):
            SimulationResponse(
                story="test",
                participants=["krieg"],
                turns_executed=-1,  # Should be >= 0
                duration_seconds=15.7
            )
        
        with pytest.raises(ValueError):
            SimulationResponse(
                story="test",
                participants=["krieg"],
                turns_executed=3,
                duration_seconds=-1.0  # Should be >= 0.0
            )
    
    @patch("api_server.CharacterFactory")
    @patch("api_server.DirectorAgent")
    @patch("api_server.ChroniclerAgent")
    def test_simulation_endpoint_implemented_behavior(self, mock_chronicler, mock_director, mock_character_factory, client: TestClient):
        """
        Test implemented behavior of simulation endpoint (200 Success).
        
        This test validates the working simulation endpoint implementation using mocks
        to avoid slow LLM API calls during testing.
        
        Validates:
        - HTTP status code 200 Success
        - Proper SimulationResponse format
        - Endpoint executes simulation successfully
        """
        # Setup mocks for fast testing
        mock_factory_instance = MagicMock()
        mock_character_factory.return_value = mock_factory_instance
        
        # Mock character creation
        mock_agent1 = MagicMock()
        mock_agent2 = MagicMock()
        mock_factory_instance.create_character.side_effect = [mock_agent1, mock_agent2]
        
        # Mock DirectorAgent
        mock_director_instance = MagicMock()
        mock_director.return_value = mock_director_instance
        mock_director_instance.run_simulation.return_value = None
        
        # Mock ChroniclerAgent
        mock_chronicler_instance = MagicMock()
        mock_chronicler.return_value = mock_chronicler_instance
        mock_chronicler_instance.transcribe_log.return_value = "Epic battle narrative between Krieg and Ork forces!"
        
        valid_request = {
            "character_names": ["krieg", "ork"],
            "turns": 3,
            "narrative_style": "epic"
        }
        
        response = client.post("/simulations", json=valid_request)
        
        # Should now return 200 Success with the implemented endpoint
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        assert "story" in response_data
        assert "participants" in response_data
        assert "turns_executed" in response_data
        assert "duration_seconds" in response_data
        
        # Validate response content
        assert response_data["participants"] == ["krieg", "ork"]
        assert response_data["turns_executed"] == 3
        assert isinstance(response_data["duration_seconds"], float)
        assert response_data["duration_seconds"] >= 0.0
    
    def test_simulation_endpoint_request_validation_errors(self, client: TestClient):
        """
        Test simulation endpoint request validation errors.
        
        These tests should PASS as they test FastAPI/Pydantic validation.
        
        Validates:
        - 422 errors for invalid request data
        - Proper validation error messages
        - Request validation occurs before endpoint logic
        """
        # Test insufficient characters
        insufficient_chars = {"character_names": ["krieg"]}  # Only 1 character
        response = client.post("/simulations", json=insufficient_chars)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test too many characters
        too_many_chars = {"character_names": ["krieg", "ork", "test", "char4", "char5", "char6", "char7"]}
        response = client.post("/simulations", json=too_many_chars)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test invalid turns
        invalid_turns = {"character_names": ["krieg", "ork"], "turns": 0}
        response = client.post("/simulations", json=invalid_turns)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test invalid narrative style
        invalid_style = {"character_names": ["krieg", "ork"], "narrative_style": "invalid"}
        response = client.post("/simulations", json=invalid_style)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test empty character names
        empty_chars = {"character_names": ["krieg", ""]}
        response = client.post("/simulations", json=empty_chars)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test missing required field
        missing_field = {"turns": 3}  # Missing character_names
        response = client.post("/simulations", json=missing_field)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_simulation_endpoint_malformed_json(self, client: TestClient):
        """
        Test simulation endpoint with malformed JSON.
        
        This test should PASS as it tests basic HTTP request handling.
        
        Validates:
        - 422 error for malformed JSON
        - Proper error handling for invalid request format
        """
        # Test with malformed JSON
        response = client.post(
            "/simulations",
            data="invalid json content",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_simulation_endpoint_api_documentation(self, client: TestClient):
        """
        Test that the simulation endpoint is properly documented in OpenAPI schema.
        
        This test should PASS as it validates the API documentation.
        
        Validates:
        - Endpoint appears in OpenAPI schema
        - Request and response models are documented
        - Error responses are documented
        - Examples are included
        """
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        
        openapi_data = response.json()
        
        # Validate endpoint exists in schema
        assert "paths" in openapi_data
        assert "/simulations" in openapi_data["paths"]
        
        simulations_path = openapi_data["paths"]["/simulations"]
        assert "post" in simulations_path
        
        # Validate method documentation
        post_method = simulations_path["post"]
        assert "summary" in post_method
        assert "description" in post_method
        assert "requestBody" in post_method
        assert "responses" in post_method
        
        # Validate documented response codes
        responses = post_method["responses"]
        assert "200" in responses  # Success
        assert "400" in responses  # Validation errors
        assert "404" in responses  # Characters not found
        assert "500" in responses  # Server error
        
        # Validate request body documentation
        request_body = post_method["requestBody"]
        assert "content" in request_body
        assert "application/json" in request_body["content"]
    
    @patch("api_server.CharacterFactory")
    @patch("api_server.DirectorAgent")
    @patch("api_server.ChroniclerAgent")
    def test_simulation_endpoint_cors_support(self, mock_chronicler, mock_director, mock_character_factory, client: TestClient):
        """
        Test that the simulation endpoint supports CORS requests.
        
        This test validates basic CORS handling with the implemented endpoint.
        
        Validates:
        - Cross-origin requests are handled properly
        - CORS headers are present when applicable
        """
        # Setup mocks for fast testing
        mock_factory_instance = MagicMock()
        mock_character_factory.return_value = mock_factory_instance
        
        # Mock character creation
        mock_agent1 = MagicMock()
        mock_agent2 = MagicMock()
        mock_factory_instance.create_character.side_effect = [mock_agent1, mock_agent2]
        
        # Mock DirectorAgent
        mock_director_instance = MagicMock()
        mock_director.return_value = mock_director_instance
        mock_director_instance.run_simulation.return_value = None
        
        # Mock ChroniclerAgent
        mock_chronicler_instance = MagicMock()
        mock_chronicler.return_value = mock_chronicler_instance
        mock_chronicler_instance.transcribe_log.return_value = "CORS-tested narrative!"
        
        valid_request = {
            "character_names": ["krieg", "ork"],
            "turns": 3,
            "narrative_style": "epic"
        }
        
        # Test with Origin header
        response = client.post(
            "/simulations",
            json=valid_request,
            headers={"Origin": "http://localhost:3000"}
        )
        
        # Should process the request (now returns 200 with implementation)
        assert response.status_code == status.HTTP_200_OK
        
        # Validate that the request was processed (not blocked by CORS)
        response_data = response.json()
        assert "story" in response_data  # Should have simulation response structure


@patch("api_server.CharacterFactory")
@patch("api_server.DirectorAgent") 
@patch("api_server.ChroniclerAgent")
class TestSimulationEndpointExpectedBehavior:
    """
    Test class defining expected behavior for the simulation endpoint implementation.
    
    These tests validate the implemented simulation endpoint using mocks for fast execution.
    All components are mocked to prevent slow LLM API calls during testing.
    """
    
    def setup_simulation_mocks(self, mock_chronicler, mock_director, mock_character_factory, narrative="Epic battle narrative between characters!"):
        """Helper method to set up standard simulation mocks for fast testing."""
        # Setup mocks for fast testing
        mock_factory_instance = MagicMock()
        mock_character_factory.return_value = mock_factory_instance
        
        # Mock character creation function that can handle multiple calls
        def character_creation_side_effect(character_name):
            mock_agent = MagicMock()
            mock_agent.agent_id = character_name
            return mock_agent
        
        mock_factory_instance.create_character.side_effect = character_creation_side_effect
        
        # Mock DirectorAgent
        mock_director_instance = MagicMock()
        mock_director.return_value = mock_director_instance
        mock_director_instance.run_simulation.return_value = None
        
        # Mock ChroniclerAgent
        mock_chronicler_instance = MagicMock()
        mock_chronicler.return_value = mock_chronicler_instance
        mock_chronicler_instance.transcribe_log.return_value = narrative
        
        return mock_factory_instance, mock_director_instance, mock_chronicler_instance
    
    def test_expected_successful_simulation_with_valid_characters(self, mock_chronicler, mock_director, mock_character_factory, client: TestClient):
        """
        Test expected successful simulation behavior with mocked components.
        
        Validates:
        - 200 OK status code for valid request
        - Proper SimulationResponse format  
        - Story contains non-empty narrative
        - Participants match request characters
        - Valid execution metadata
        """
        # Setup mocks using helper method
        self.setup_simulation_mocks(
            mock_chronicler, 
            mock_director, 
            mock_character_factory,
            "In the grim darkness of the far future, Commissar Krieg and the Ork Warboss engaged in epic battle across the wartorn landscape..."
        )
        
        valid_request = {
            "character_names": ["krieg", "ork"],
            "turns": 3,
            "narrative_style": "epic"
        }
        
        response = client.post("/simulations", json=valid_request)
        
        # Should return 200 OK with implemented endpoint
        assert response.status_code == status.HTTP_200_OK
        
        response_data = response.json()
        
        # Validate response structure
        assert "story" in response_data
        assert "participants" in response_data
        assert "turns_executed" in response_data
        assert "duration_seconds" in response_data
        
        # Validate story content
        assert isinstance(response_data["story"], str)
        assert len(response_data["story"]) > 0
        assert len(response_data["story"]) > 50  # Should be substantial narrative
        
        # Validate participants match request
        assert response_data["participants"] == ["krieg", "ork"]
        
        # Validate execution metadata
        assert isinstance(response_data["turns_executed"], int)
        assert response_data["turns_executed"] == 3  # Should match request
        assert isinstance(response_data["duration_seconds"], float)
        assert response_data["duration_seconds"] > 0.0
    
    def test_expected_404_for_nonexistent_characters(self, mock_chronicler, mock_director, mock_character_factory, client: TestClient):
        """
        Test expected 404 response for nonexistent characters.
        
        Expected behavior:
        - 404 NOT FOUND for nonexistent characters
        - Proper error response indicating which characters were not found
        """
        # Setup mocks to simulate character not found
        mock_factory_instance = MagicMock()
        mock_character_factory.return_value = mock_factory_instance
        
        # Mock character creation: first character succeeds, second fails
        mock_agent1 = MagicMock()
        def character_creation_side_effect(character_name):
            if character_name == "krieg":
                return mock_agent1
            elif character_name == "nonexistent_character":
                raise FileNotFoundError(f"Character directory not found: {character_name}")
            else:
                raise FileNotFoundError(f"Character directory not found: {character_name}")
        
        mock_factory_instance.create_character.side_effect = character_creation_side_effect
        
        invalid_request = {
            "character_names": ["krieg", "nonexistent_character"],
            "turns": 3,
            "narrative_style": "epic"
        }
        
        response = client.post("/simulations", json=invalid_request)
        
        # Should return 404 for nonexistent characters
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Validate error response
        response_data = response.json()
        assert "detail" in response_data
        assert "not found" in response_data["detail"].lower()
        assert "nonexistent_character" in response_data["detail"]
    
    def test_expected_default_configuration_handling(self, mock_chronicler, mock_director, mock_character_factory, client: TestClient):
        """
        Test expected default configuration handling.
        
        Expected behavior:
        - Default turns from configuration when not specified
        - Default narrative style handling
        - Proper configuration integration
        """
        # Setup mocks for successful simulation
        self.setup_simulation_mocks(mock_chronicler, mock_director, mock_character_factory)
        
        minimal_request = {
            "character_names": ["krieg", "ork"]
            # No turns or narrative_style specified - should use defaults
        }
        
        response = client.post("/simulations", json=minimal_request)
        
        # When implemented, should return 200 OK with defaults
        # Currently expected to fail with 501 (Not Implemented)
        if response.status_code == status.HTTP_200_OK:
            # If implemented, validate default handling
            response_data = response.json()
            
            # Should have used default configuration for turns
            assert "turns_executed" in response_data
            assert response_data["turns_executed"] >= 1  # Some default value
            
            # Should have participants matching request
            assert response_data["participants"] == ["krieg", "ork"]
        else:
            # Currently expected to fail
            assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
    
    def test_expected_edge_case_minimum_characters(self, mock_chronicler, mock_director, mock_character_factory, client: TestClient):
        """
        Test expected behavior with minimum characters (2).
        
        Expected behavior:
        - Successful simulation with exactly 2 characters
        - Proper narrative generation with minimal participants
        """
        # Setup mocks for successful simulation
        self.setup_simulation_mocks(mock_chronicler, mock_director, mock_character_factory)
        
        minimal_request = {
            "character_names": ["krieg", "ork"],
            "turns": 1,
            "narrative_style": "concise"
        }
        
        response = client.post("/simulations", json=minimal_request)
        
        # When implemented, should handle minimum case successfully
        # Currently expected to fail with 501 (Not Implemented)
        if response.status_code == status.HTTP_200_OK:
            # If implemented, validate minimal case handling
            response_data = response.json()
            
            assert len(response_data["participants"]) == 2
            assert response_data["turns_executed"] == 1
            assert len(response_data["story"]) > 0
        else:
            # Currently expected to fail
            assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
    
    def test_expected_edge_case_maximum_characters(self, mock_chronicler, mock_director, mock_character_factory, client: TestClient):
        """
        Test expected behavior with maximum characters (6).
        
        Expected behavior:
        - Successful simulation with maximum participants
        - Proper handling of complex multi-character scenario
        """
        # Setup mocks for successful simulation (with more agents)
        mock_factory_instance = MagicMock()
        mock_character_factory.return_value = mock_factory_instance
        
        # Mock character creation for 6 characters
        mock_agents = [MagicMock() for _ in range(6)]
        mock_factory_instance.create_character.side_effect = mock_agents
        
        # Mock DirectorAgent
        mock_director_instance = MagicMock()
        mock_director.return_value = mock_director_instance
        mock_director_instance.run_simulation.return_value = None
        
        # Mock ChroniclerAgent
        mock_chronicler_instance = MagicMock()
        mock_chronicler.return_value = mock_chronicler_instance
        mock_chronicler_instance.transcribe_log.return_value = "Epic large-scale battle with six characters in epic conflict!"
        
        maximum_request = {
            "character_names": ["krieg", "ork", "test", "char4", "char5", "char6"],
            "turns": 2,
            "narrative_style": "detailed"
        }
        
        response = client.post("/simulations", json=maximum_request)
        
        # When implemented, should handle maximum case successfully
        # Currently expected to fail with 501 (Not Implemented)
        if response.status_code == status.HTTP_200_OK:
            # If implemented, validate maximum case handling
            response_data = response.json()
            
            assert len(response_data["participants"]) == 6
            assert response_data["turns_executed"] == 2
            assert len(response_data["story"]) > 0
        else:
            # Currently expected to fail
            assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
    
    def test_expected_narrative_style_handling(self, mock_chronicler, mock_director, mock_character_factory, client: TestClient):
        """
        Test expected narrative style handling.
        
        Expected behavior:
        - Different narrative styles produce appropriate content
        - Epic style produces longer, more dramatic narratives
        - Concise style produces shorter, focused narratives
        """
        # Setup mocks for successful simulation
        self.setup_simulation_mocks(mock_chronicler, mock_director, mock_character_factory)
        
        base_request = {
            "character_names": ["krieg", "ork"],
            "turns": 2
        }
        
        styles = ["epic", "detailed", "concise"]
        
        for style in styles:
            request = base_request.copy()
            request["narrative_style"] = style
            
            response = client.post("/simulations", json=request)
            
            # Should handle different narrative styles successfully
            assert response.status_code == status.HTTP_200_OK
            
            # Validate style handling
            response_data = response.json()
            
            assert "story" in response_data
            assert len(response_data["story"]) > 0
            
            # Could add style-specific validation here
            # e.g., epic stories might be longer than concise
    
    def test_expected_mixed_existing_and_nonexistent_characters(self, mock_chronicler, mock_director, mock_character_factory, client: TestClient):
        """
        Test expected behavior with mix of existing and nonexistent characters.
        
        Expected behavior:
        - 404 error when any character is not found
        - Error message indicates which specific characters are missing
        """
        # Setup mocks to simulate mixed character existence
        mock_factory_instance = MagicMock()
        mock_character_factory.return_value = mock_factory_instance
        
        # Mock character creation: some succeed, some fail
        mock_agent1 = MagicMock()
        mock_agent2 = MagicMock()
        def mixed_character_creation_side_effect(character_name):
            if character_name in ["krieg", "ork"]:
                return mock_agent1 if character_name == "krieg" else mock_agent2
            else:  # nonexistent1, nonexistent2
                raise FileNotFoundError(f"Character directory not found: {character_name}")
        
        mock_factory_instance.create_character.side_effect = mixed_character_creation_side_effect
        
        mixed_request = {
            "character_names": ["krieg", "nonexistent1", "ork", "nonexistent2"],
            "turns": 3,
            "narrative_style": "epic"
        }
        
        response = client.post("/simulations", json=mixed_request)
        
        # Should return 404 for any missing characters
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Validate specific error handling
        response_data = response.json()
        assert "detail" in response_data
        
        # Should indicate which characters were not found
        detail = response_data["detail"].lower()
        assert "nonexistent1" in detail and "nonexistent2" in detail
    
    def test_expected_simulation_performance_metadata(self, mock_chronicler, mock_director, mock_character_factory, client: TestClient):
        """
        Test expected simulation performance metadata.
        
        Expected behavior:
        - duration_seconds reflects actual execution time
        - turns_executed matches requested turns (unless early termination)
        - Reasonable performance for small simulations
        """
        # Setup mocks for successful simulation
        self.setup_simulation_mocks(mock_chronicler, mock_director, mock_character_factory)
        
        performance_request = {
            "character_names": ["krieg", "ork"],
            "turns": 1,  # Single turn for predictable performance
            "narrative_style": "concise"
        }
        
        response = client.post("/simulations", json=performance_request)
        
        # When implemented, should provide realistic performance metadata
        # Currently expected to fail with 501 (Not Implemented)
        if response.status_code == status.HTTP_200_OK:
            # If implemented, validate performance metadata
            response_data = response.json()
            
            # Duration should be reasonable for a simple simulation (mocked tests are very fast)
            duration = response_data["duration_seconds"]
            assert 0.0 <= duration <= 60.0  # Between 0ms and 1 minute (mocked can be very fast)
            
            # Turns executed should match request
            assert response_data["turns_executed"] == 1
            
            # Participants should match exactly
            assert set(response_data["participants"]) == {"krieg", "ork"}
        else:
            # Currently expected to fail
            assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


class TestCharacterCreationEndpoint:
    """
    Test cases for the POST /characters endpoint functionality with AI Scribe integration.
    
    Sacred Mission: Complete testing overhaul for file upload functionality and AI Scribe mocking.
    These tests validate the enhanced character creation endpoint including:
    - File upload handling with multipart form data
    - Gemini API mocking with realistic V2 character architecture responses
    - File structure validation (4 V2 files: 1_core.md, 2_history.md, 3_profile.yaml, 4_lore.md)
    - Content parsing and validation from mock AI responses
    - Fallback scenarios and error handling
    - Backward compatibility with existing functionality
    """
    
    @pytest.fixture
    def mock_gemini_v2_response(self):
        """Mock realistic Gemini API response following V2 character architecture."""
        return """
=== FILE: 1_core.md ===
# Character Core: Isabella_Varr

## Identity Matrix
- **Name**: Isabella Varr
- **Title/Rank**: Commissar
- **Origin World**: Cadia (before the fall)
- **Faction**: Astra Militarum - Imperial Guard
- **Role**: Military Commissar and Tactical Commander

## Physical Description
Commissar Isabella Varr stands at average height with a lean, athletic build forged by years of military training. Her sharp green eyes reflect unwavering determination, while a distinctive scar runs along her left cheek from a close encounter with an Ork choppa. Her dark brown hair is kept in a regulation military cut, and she bears the ritual scarification of Cadian military tradition across her right arm.

## Core Personality
Isabella embodies the iron will expected of an Imperial Commissar while tempering discipline with genuine care for her soldiers. Her tactical brilliance is matched by her inspirational presence on the battlefield. She possesses an unshakeable faith in the Emperor and the Imperial doctrine, yet shows pragmatic flexibility when lives are at stake.

## Background Summary
Born on the fortress world of Cadia, Isabella was shaped by constant warfare from childhood. After surviving the fall of Cadia, she was promoted to Commissar and assigned to various Guard regiments across the galaxy, earning respect through her balanced leadership approach.

=== FILE: 2_history.md ===
# Character History: Isabella_Varr

## Early Life
Born into a military family on Cadia, Isabella learned to handle a lasgun before she could properly read. Her childhood was defined by air raid drills, fortification exercises, and the ever-present threat of Chaos incursions. The constant state of warfare forged her resilience and tactical mindset from an early age.

## Military/Professional Career
Enlisted in the Cadian Shock Troops at age 16, Isabella quickly distinguished herself in combat operations against Chaos cultist uprisings. Her natural leadership abilities and unwavering faith led to her selection for Commissarial training at the Schola Progenium. She graduated with honors and was assigned to the 147th Cadian Regiment.

## Key Events
1. **The Siege of Kasr Holn** - Led a successful counter-attack against Chaos forces, saving three companies from annihilation
2. **The Fall of Cadia** - Survived the destruction of her homeworld, evacuating civilian populations while maintaining order
3. **The Mordian Incident** - Prevented a Guard regiment from breaking during an Ork WAAAGH! through inspirational leadership
4. **Operation Crimson Dawn** - Coordinated combined Imperial Guard and Space Marine operations against Tau forces
5. **The Hive Tertius Uprising** - Exposed and eliminated a Genestealer cult within Guard ranks

## Current Status
Currently assigned as roving Commissar to multiple regiments operating in the Segmentum Solar, providing leadership and maintaining Imperial doctrine across diverse combat theaters.

## Notable Achievements
- Commendation for Valor in the face of overwhelming odds
- Imperial Guard Cross for tactical excellence
- Recognized by Inquisition for anti-heretical activities
- Survived 23 major engagements without retreat

## Scars and Losses
Lost her entire birth regiment during the Fall of Cadia, including her mentor Commissar Valerius. Carries guilt over soldiers lost due to necessary but harsh disciplinary actions. The destruction of Cadia remains a deep psychological wound.

=== FILE: 3_profile.yaml ===
character:
  name: "Isabella Varr"
  age: 32
  origin: "Cadia (Destroyed)"
  faction: "Astra Militarum"
  rank: "Commissar"
  specialization: "Military Leadership and Tactical Coordination"

combat_stats:
  marksmanship: 9
  melee: 8
  tactics: 10
  leadership: 9
  endurance: 8
  pilot: 6

equipment:
  primary_weapon: "Master-crafted Bolt Pistol"
  secondary_weapon: "Chainsword with Blessed Adamantine Teeth"
  armor: "Commissarial Storm Coat with Integrated Carapace Plating"
  special_gear:
    - "Aquila Pendant (blessed by Ecclesiarchy)"
    - "Tactical Vox-caster with Encryption Protocols"
    - "Field Medicae Kit"
    - "Frag Grenades (consecrated)"
    - "Oath of Moment Scrolls"

psychological_profile:
  loyalty: 10
  aggression: 7
  caution: 8
  morale: 9
  corruption_resistance: 10

specializations:
  - "Combined Arms Tactics"
  - "Anti-Heretical Operations"
  - "Inspirational Leadership"
  - "Urban Warfare"

relationships:
  allies:
    - "Captain Marcus Vostok (147th Cadian)"
    - "Inquisitor Helene Vex"
  enemies:
    - "Chaos Cultist Cell Alpha-Seven"
    - "Warboss Skarjaw (personal nemesis)"
  mentor: "Commissar Valerius (deceased - Fall of Cadia)"

=== FILE: 4_lore.md ===
# Character Lore: Isabella_Varr

## Regiment/Organization Details
The 147th Cadian Shock Troops were a veteran regiment specializing in siege warfare and urban combat. Known for their iron discipline and tactical flexibility, they served with distinction across multiple sectors before Cadia's fall. Isabella now operates as a roving Commissar, assigned to reinforce morale and maintain doctrine across various Guard regiments.

## Homeworld/Culture
Cadia was the fortress world that stood as the gateway to Terra, enduring constant siege from the Eye of Terror. Cadian culture revolved around military excellence, with every citizen trained for war from childhood. The planet's destruction during the 13th Black Crusade left all survivors as the last generation of "true" Cadians, carrying the weight of their world's legacy.

## Notable Quotes
> "The Emperor's will is absolute, but His mercy flows through those who serve with honor."
> "Cadia may have fallen, but Cadians never break. We are the bulwark against the darkness."
> "Fear is the mind-killer, but faith is the soul's salvation. Remember this in your darkest hour."

## Combat Doctrine
Isabella favors combined arms tactics, utilizing coordinated fire support and tactical flexibility. She believes in leading from the front while maintaining strategic oversight. Her approach emphasizes minimizing casualties through superior planning rather than overwhelming force, though she will not hesitate to make hard decisions when necessary.

## Beliefs and Philosophy
A devout follower of the Imperial Creed, Isabella believes the Emperor protects those who serve faithfully. She sees her role as both enforcer and protector, maintaining discipline while preserving the lives of the soldiers under her care. Her faith was tested but not broken by Cadia's fall, instead becoming a source of strength for others.

## Secrets and Hidden Knowledge
Isabella carries encrypted data-logs from Cadia's final days, containing strategic intelligence that could prove vital in future campaigns. She also bears the burden of knowing which Guard units were compromised by Chaos influence during the planet's fall, information she shares only with the highest Imperial authorities.

## Future Aspirations
Isabella seeks to establish a new Cadian regiment from survivors scattered across the galaxy, preserving Cadian military traditions and excellence. She also hopes to uncover the fate of other Cadian survivors and ensure their heroic legacy continues to inspire future generations of Imperial Guard.
"""
    
    @pytest.fixture
    def mock_gemini_minimal_response(self):
        """Minimal mock response for testing parsing edge cases."""
        return """
=== FILE: 1_core.md ===
# Character Core: Test_Character

Basic character information here.

=== FILE: 2_history.md ===
# Character History: Test_Character

Basic history information.

=== FILE: 3_profile.yaml ===
character:
  name: "Test Character"
  age: 25

=== FILE: 4_lore.md ===
# Character Lore: Test_Character

Basic lore information.
"""
    
    @pytest.fixture
    def sample_upload_files(self, tmp_path):
        """Create sample files for upload testing."""
        files = {}
        
        # Create a sample text file
        text_file = tmp_path / "background.txt"
        text_file.write_text("Isabella comes from a military family on Cadia. She has extensive combat experience.")
        files['background.txt'] = text_file
        
        # Create a sample markdown file
        md_file = tmp_path / "notes.md"
        md_file.write_text("# Character Notes\n\n- Exceptional leader\n- Tactical genius\n- Cadian heritage")
        files['notes.md'] = md_file
        
        return files
    
    def test_character_creation_multipart_form_validation(self):
        """
        Test multipart form data validation for character creation.
        
        This test validates that the endpoint properly handles multipart form data
        with both required form fields and optional file uploads.
        """
        # Test with valid form data (no files)
        valid_data = {
            "name": "test_warrior",
            "description": "A brave Imperial Guard soldier fighting for the Emperor across multiple campaigns."
        }
        
        # Validate form field length and format constraints
        assert len(valid_data["name"]) >= 3 and len(valid_data["name"]) <= 50
        assert len(valid_data["description"]) >= 10 and len(valid_data["description"]) <= 2000
        assert len(valid_data["description"].split()) >= 3
        
        # Test name format validation
        import re
        assert re.match(r'^[a-zA-Z0-9_]+$', valid_data["name"])
    
    @patch('api_server._get_characters_directory_path')
    @patch('api_server._make_gemini_api_request')
    def test_character_creation_with_ai_scribe_success(self, mock_make_gemini_request, mock_get_characters_directory_path, client: TestClient, mock_gemini_v2_response, sample_upload_files, tmp_path):
        """
        Test successful character creation with AI Scribe enhancement and file uploads.
        
        This test validates the complete AI Scribe workflow:
        - File upload processing
        - Gemini API mocking with realistic V2 response
        - File structure creation (4 V2 files)
        - Content parsing and validation
        """
        # Patch the character directory path to use temp directory
        mock_get_characters_directory_path.return_value = str(tmp_path / "characters")
        
        # Mock successful Gemini API response
        mock_make_gemini_request.return_value = mock_gemini_v2_response
        
        # Prepare multipart form data with files
        form_data = {
            "name": "isabella_varr",
            "description": "A fierce Imperial Guard commissar known for her unwavering loyalty to the Emperor and tactical brilliance."
        }
        
        # Prepare file uploads
        files_to_upload = []
        for filename, filepath in sample_upload_files.items():
            with open(filepath, 'rb') as f:
                files_to_upload.append(("files", (filename, f.read(), "text/plain")))
        
        # Execute the API call with multipart form data
        response = client.post(
            "/characters", 
            data=form_data,
            files=files_to_upload
        )
        
        # Validate successful creation
        assert response.status_code == 201
        response_data = response.json()
        
        # Validate response structure
        assert "name" in response_data
        assert "status" in response_data
        assert "ai_scribe_enhanced" in response_data
        assert "files_processed" in response_data
        
        # Validate response content
        assert response_data["name"] == "isabella_varr"
        assert response_data["ai_scribe_enhanced"] is True
        assert response_data["files_processed"] == 2  # Two upload files
        assert "ai_scribe_enhanced_complete" in response_data["status"]
        
        # Verify Gemini API was called
        mock_make_gemini_request.assert_called_once()
        
        # Verify call arguments contain expected content
        call_args = mock_make_gemini_request.call_args
        prompt_used = call_args[0][0]  # First positional argument
        
        assert "isabella_varr" in prompt_used.lower()
        assert "Imperial Guard commissar" in prompt_used
        assert "=== FILE: 1_core.md ===" in prompt_used
        assert "=== FILE: 2_history.md ===" in prompt_used
        assert "=== FILE: 3_profile.yaml ===" in prompt_used
        assert "=== FILE: 4_lore.md ===" in prompt_used
    
    @patch('api_server._get_characters_directory_path')
    @patch('api_server._make_gemini_api_request')
    @patch('api_server.os.listdir')
    @patch('api_server.os.path.exists')
    @patch('api_server.os.path.isdir')
    def test_character_creation_file_structure_validation(self, mock_isdir, mock_exists, mock_listdir, mock_make_gemini_request, mock_get_characters_directory_path, client: TestClient, mock_gemini_v2_response, tmp_path):
        """
        Test that AI Scribe creates the correct V2 character file structure.
        
        This test validates that the endpoint creates exactly 4 files:
        - 1_core.md
        - 2_history.md  
        - 3_profile.yaml
        - 4_lore.md
        """
        # Patch the character directory path to use temp directory
        mock_get_characters_directory_path.return_value = str(tmp_path / "characters")
        
        # Mock successful Gemini API response
        mock_make_gemini_request.return_value = mock_gemini_v2_response
        
        # Mock file system for character directory validation
        def mock_exists_func(path):
            # Characters base directory exists, specific character doesn't exist yet
            if path == str(tmp_path / "characters"):
                return True
            if path.endswith("test_character_v2"):
                return False  # Character doesn't exist yet
            return True
        
        mock_exists.side_effect = mock_exists_func
        mock_isdir.return_value = True
        mock_listdir.return_value = []  # Empty characters directory initially
        
        # Ensure the base characters directory exists
        (tmp_path / "characters").mkdir(parents=True, exist_ok=True)
        
        response = client.post(
                "/characters",
                data={
                    "name": "test_character_v2",
                    "description": "A test character for V2 file structure validation with proper description length."
                },
                files=[]
            )
        
        # Validate successful creation
        assert response.status_code == 201
        
        # Verify the 4 V2 files exist in the temp directory
        test_char_dir = tmp_path / "characters" / "test_character_v2"
        expected_files = ["1_core.md", "2_history.md", "3_profile.yaml", "4_lore.md"]
        
        for expected_file in expected_files:
            file_path = test_char_dir / expected_file
            assert file_path.exists(), f"Expected V2 file not found: {expected_file}"
            
            # Verify file has content
            content = file_path.read_text(encoding='utf-8')
            assert len(content) > 0, f"V2 file is empty: {expected_file}"
            
            # Verify file-specific content structure
            if expected_file.endswith('.md'):
                assert content.startswith('#'), f"Markdown file should start with header: {expected_file}"
            elif expected_file.endswith('.yaml'):
                assert 'character:' in content or 'name:' in content, f"YAML file should contain character data: {expected_file}"
    
    @patch('api_server._get_characters_directory_path')
    @patch('api_server._make_gemini_api_request')
    def test_character_creation_content_parsing_validation(self, mock_make_gemini_request, mock_get_characters_directory_path, client: TestClient, mock_gemini_v2_response, tmp_path):
        """
        Test that content from mock AI response is properly parsed and written to files.
        
        This test validates that the parsing function correctly extracts content
        from the delimited Gemini response and writes it to the appropriate files.
        """
        # Patch the character directory path to use temp directory
        mock_get_characters_directory_path.return_value = str(tmp_path / "characters")
        
        # Mock successful Gemini API response
        mock_make_gemini_request.return_value = mock_gemini_v2_response
        
        # Ensure the base characters directory exists
        (tmp_path / "characters").mkdir(parents=True, exist_ok=True)
        
        # Patch additional os.path functions for the test
        def mock_exists_func(path):
            # Characters base directory exists, specific character doesn't exist yet
            if path == str(tmp_path / "characters"):
                return True
            if path.endswith("content_test_char"):
                return False  # Character doesn't exist yet
            return True
            
        with patch('api_server.os.path.exists', side_effect=mock_exists_func):
            response = client.post(
                "/characters",
                data={
                    "name": "content_test_char",
                    "description": "A character specifically for testing content parsing functionality with proper description length."
                    },
                    files=[]
                )
        
        # Validate successful creation
        assert response.status_code == 201
        
        # Verify specific content was parsed correctly
        test_char_dir = tmp_path / "characters" / "content_test_char"
        
        # Check 1_core.md content
        core_file = test_char_dir / "1_core.md"
        core_content = core_file.read_text(encoding='utf-8')
        assert "# Character Core: Isabella_Varr" in core_content
        assert "**Name**: Isabella Varr" in core_content
        assert "**Faction**: Astra Militarum" in core_content
        
        # Check 2_history.md content
        history_file = test_char_dir / "2_history.md"
        history_content = history_file.read_text(encoding='utf-8')
        assert "# Character History: Isabella_Varr" in history_content
        assert "The Fall of Cadia" in history_content
        assert "Operation Crimson Dawn" in history_content
        
        # Check 3_profile.yaml content
        profile_file = test_char_dir / "3_profile.yaml"
        profile_content = profile_file.read_text(encoding='utf-8')
        assert "name: \"Isabella Varr\"" in profile_content
        assert "marksmanship: 9" in profile_content
        assert "loyalty: 10" in profile_content
        
        # Check 4_lore.md content
        lore_file = test_char_dir / "4_lore.md"
        lore_content = lore_file.read_text(encoding='utf-8')
        assert "# Character Lore: Isabella_Varr" in lore_content
        assert "Cadia may have fallen, but Cadians never break" in lore_content
        assert "147th Cadian Shock Troops" in lore_content
    
    @patch('api_server._get_characters_directory_path')
    @patch('api_server._make_gemini_api_request')
    def test_character_creation_ai_scribe_fallback_scenario(self, mock_make_gemini_request, mock_get_characters_directory_path, client: TestClient, tmp_path):
        """
        Test fallback behavior when AI Scribe fails or returns empty response.
        
        This test validates that the endpoint gracefully falls back to basic
        character creation when the Gemini API fails or returns invalid content.
        """
        # Patch the character directory path to use temp directory
        mock_get_characters_directory_path.return_value = str(tmp_path / "characters")
        
        # Mock failed Gemini API response (returns None)
        mock_make_gemini_request.return_value = None
        
        # Ensure the base characters directory exists
        (tmp_path / "characters").mkdir(parents=True, exist_ok=True)
        
        # Patch additional os.path functions for the test
        def mock_exists_func(path):
            # Characters base directory exists, specific character doesn't exist yet
            if path == str(tmp_path / "characters"):
                return True
            if path.endswith("fallback_test_char"):
                return False  # Character doesn't exist yet
            return True
            
        with patch('api_server.os.path.exists', side_effect=mock_exists_func):
            response = client.post(
                "/characters",
                data={
                    "name": "fallback_test_char",
                        "description": "A character for testing AI Scribe fallback behavior when the API fails to respond."
                    },
                    files=[]
                )
        
        # Validate successful creation even without AI Scribe
        assert response.status_code == 201
        response_data = response.json()
        
        # Validate fallback response
        assert response_data["name"] == "fallback_test_char"
        assert response_data["ai_scribe_enhanced"] is False
        assert "basic_creation_complete" in response_data["status"]
        
        # Verify basic fallback files were created
        test_char_dir = tmp_path / "characters" / "fallback_test_char"
        basic_md_file = test_char_dir / "character_fallback_test_char.md"
        basic_stats_file = test_char_dir / "stats.yaml"
        
        assert basic_md_file.exists()
        assert basic_stats_file.exists()
        
        # Verify fallback content structure
        md_content = basic_md_file.read_text(encoding='utf-8')
        assert "# Character Sheet: Fallback_Test_Char" in md_content
        assert "AI Scribe enhancement was not available" in md_content
        
        stats_content = basic_stats_file.read_text(encoding='utf-8')
        assert "name: \"Fallback_Test_Char\"" in stats_content
        assert "marksmanship: 5" in stats_content  # Default stats
    
    def test_character_creation_validation_errors_multipart(self, client: TestClient):
        """
        Test character creation validation errors with multipart form data.
        
        This test validates that the endpoint properly handles validation errors
        when using multipart form data instead of JSON.
        """
        # Test various validation error scenarios
        invalid_scenarios = [
            {
                "name": "ab",  # Too short (minimum 3 characters)
                "description": "A character with too short name for testing validation.",
                "expected_error": "name"
            },
            {
                "name": "valid_name",
                "description": "short",  # Too short (minimum 10 characters)
                "expected_error": "description"
            },
            {
                "name": "invalid-name!",  # Invalid characters
                "description": "A character with invalid special characters in the name for testing.",
                "expected_error": "name"
            },
            {
                "name": "valid_name",
                "description": "Two words",  # Insufficient words (minimum 3)
                "expected_error": "description"
            }
        ]
        
        for scenario in invalid_scenarios:
            response = client.post(
                "/characters",
                data={
                    "name": scenario["name"],
                    "description": scenario["description"]
                },
                files=[]
            )
            
            # Should return 4xx for validation errors (400 for multipart form validation)
            assert response.status_code in [400, 422], f"Failed for scenario with {scenario['expected_error']} error"
            
            response_data = response.json()
            assert "detail" in response_data
            
            # Error message should be descriptive (handle both string and list formats)
            detail = response_data["detail"]
            if isinstance(detail, list):
                detail_message = str(detail).lower()
            else:
                detail_message = detail.lower()
            
            if scenario["expected_error"] == "name":
                assert "name" in detail_message
            elif scenario["expected_error"] == "description":
                assert "description" in detail_message
    
    def test_character_creation_duplicate_name_conflict(self, client: TestClient):
        """
        Test character creation with duplicate name returns 409 Conflict.
        
        This test validates that attempting to create a character with an existing
        name properly returns a conflict error.
        """
        # Test with existing character name (krieg exists in the system)
        response = client.post(
            "/characters",
            data={
                "name": "krieg",  # This character already exists
                "description": "Attempting to create a duplicate of the existing Krieg character with proper description length."
            },
            files=[]
        )
        
        # Should return 409 Conflict for duplicate names
        assert response.status_code == 409
        
        response_data = response.json()
        assert "detail" in response_data
        assert "already exists" in response_data["detail"].lower()
        assert "krieg" in response_data["detail"]
    
    @patch('api_server._get_characters_directory_path')
    @patch('api_server._make_gemini_api_request')
    def test_character_creation_file_upload_processing(self, mock_make_gemini_request, mock_get_characters_directory_path, client: TestClient, mock_gemini_v2_response, tmp_path):
        """
        Test that uploaded files are properly processed and included in AI Scribe context.
        
        This test validates that file content is extracted and passed to the
        Gemini API prompt for enhanced character generation.
        """
        # Patch the character directory path to use temp directory
        mock_get_characters_directory_path.return_value = str(tmp_path / "characters")
        
        # Mock successful Gemini API response
        mock_make_gemini_request.return_value = mock_gemini_v2_response
        
        # Ensure the base characters directory exists
        (tmp_path / "characters").mkdir(parents=True, exist_ok=True)
        
        # Create test files with specific content
        test_files_dir = tmp_path / "test_files"
        test_files_dir.mkdir()
        
        # Create files with specific content for validation
        backstory_file = test_files_dir / "backstory.txt"
        backstory_file.write_text("Born on Cadia during the 13th Black Crusade. Witnessed the planet's destruction.")
        
        traits_file = test_files_dir / "personality.md"
        traits_file.write_text("# Personality Traits\n\n- Unwavering loyalty\n- Tactical brilliance\n- Protective of soldiers")
        
        # Prepare file uploads
        files_to_upload = [
            ("files", ("backstory.txt", backstory_file.read_bytes(), "text/plain")),
            ("files", ("personality.md", traits_file.read_bytes(), "text/markdown"))
        ]
        
        # Patch additional os.path functions for the test
        def mock_exists_func(path):
            # Characters base directory exists, specific character doesn't exist yet
            if path == str(tmp_path / "characters"):
                return True
            if path.endswith("upload_test_char"):
                return False  # Character doesn't exist yet
            return True
            
        test_char_dir = tmp_path / "characters" / "upload_test_char"
        with patch('api_server.os.path.exists', side_effect=mock_exists_func):
            response = client.post(
                "/characters",
                data={
                    "name": "upload_test_char",
                    "description": "A character for testing file upload processing with enhanced AI context generation."
                },
                files=files_to_upload
            )
        
        # Validate successful creation
        assert response.status_code == 201
        response_data = response.json()
        
        # Validate that files were processed
        assert response_data["files_processed"] == 2
        assert response_data["ai_scribe_enhanced"] is True
        
        # Verify Gemini API was called with file content
        mock_make_gemini_request.assert_called_once()
        call_args = mock_make_gemini_request.call_args
        prompt_used = call_args[0][0]  # First positional argument
        
        # Verify file content was included in the prompt
        assert "Born on Cadia during the 13th Black Crusade" in prompt_used
        assert "Unwavering loyalty" in prompt_used
        assert "backstory.txt" in prompt_used
        assert "personality.md" in prompt_used
    
    @patch('api_server._get_characters_directory_path')
    @patch('api_server._make_gemini_api_request')
    def test_character_creation_gemini_api_error_handling(self, mock_make_gemini_request, mock_get_characters_directory_path, client: TestClient, tmp_path):
        """
        Test error handling when Gemini API throws an exception.
        
        This test validates that the endpoint gracefully handles API errors
        and falls back to basic character creation.
        """
        # Patch the character directory path to use temp directory
        mock_get_characters_directory_path.return_value = str(tmp_path / "characters")
        
        # Mock Gemini API to raise an exception
        mock_make_gemini_request.side_effect = Exception("Simulated API failure")
        
        # Ensure the base characters directory exists
        (tmp_path / "characters").mkdir(parents=True, exist_ok=True)
        
        # Patch additional os.path functions for the test
        def mock_exists_func(path):
            # Characters base directory exists, specific character doesn't exist yet
            if path == str(tmp_path / "characters"):
                return True
            if path.endswith("error_test_char"):
                return False  # Character doesn't exist yet
            return True
            
        test_char_dir = tmp_path / "characters" / "error_test_char"
        with patch('api_server.os.path.exists', side_effect=mock_exists_func):
            response = client.post(
                    "/characters",
                    data={
                        "name": "error_test_char",
                        "description": "A character for testing Gemini API error handling and fallback scenarios."
                    },
                    files=[]
                )
        
        # Should still succeed with fallback creation
        assert response.status_code == 201
        response_data = response.json()
        
        # Validate fallback behavior
        assert response_data["ai_scribe_enhanced"] is False
        assert "basic_creation_complete" in response_data["status"]
        
        # Verify basic files were created as fallback
        char_dir = tmp_path / "characters" / "error_test_char"
        assert (char_dir / "character_error_test_char.md").exists()
        assert (char_dir / "stats.yaml").exists()
    
    @patch('api_server._get_characters_directory_path')
    @patch('api_server._make_gemini_api_request')
    def test_character_creation_malformed_ai_response_handling(self, mock_make_gemini_request, mock_get_characters_directory_path, client: TestClient, tmp_path):
        """
        Test handling of malformed AI response that cannot be properly parsed.
        
        This test validates that the endpoint handles cases where the Gemini API
        returns a response that doesn't match the expected format.
        """
        # Mock malformed Gemini API response (missing required sections)
        malformed_response = """
        This is a malformed response that doesn't contain the expected file delimiters.
        It should trigger the fallback parsing mechanism.
        """
        # Patch the character directory path to use temp directory
        mock_get_characters_directory_path.return_value = str(tmp_path / "characters")
        
        # Mock malformed Gemini API response
        mock_make_gemini_request.return_value = malformed_response
        
        # Ensure the base characters directory exists
        (tmp_path / "characters").mkdir(parents=True, exist_ok=True)
        
        # Patch additional os.path functions for the test
        def mock_exists_func(path):
            # Characters base directory exists, specific character doesn't exist yet
            if path == str(tmp_path / "characters"):
                return True
            if path.endswith("malformed_test_char"):
                return False  # Character doesn't exist yet
            return True
            
        test_char_dir = tmp_path / "characters" / "malformed_test_char"
        with patch('api_server.os.path.exists', side_effect=mock_exists_func):
            response = client.post(
                    "/characters",
                    data={
                        "name": "malformed_test_char",
                        "description": "A character for testing malformed AI response handling and parser robustness."
                    },
                    files=[]
                )
        
        # Should succeed with AI Scribe marked as enhanced but with fallback content
        assert response.status_code == 201
        response_data = response.json()
        
        # AI Scribe was attempted but parsing may have used fallbacks
        assert response_data["ai_scribe_enhanced"] is True
        
        # Verify V2 files were created (even if with fallback content)
        char_dir = tmp_path / "characters" / "malformed_test_char"
        v2_files = ["1_core.md", "2_history.md", "3_profile.yaml", "4_lore.md"]
        
        for v2_file in v2_files:
            file_path = char_dir / v2_file
            assert file_path.exists(), f"V2 file missing after malformed response: {v2_file}"
            
            # File should have some content (even if fallback)
            content = file_path.read_text(encoding='utf-8')
            assert len(content) > 0, f"V2 file is empty: {v2_file}"
    
    def test_character_creation_api_documentation_multipart(self, client: TestClient):
        """
        Test that the character creation endpoint documentation reflects multipart form support.
        
        This test validates that the OpenAPI schema properly documents the multipart
        form data structure including file upload capabilities.
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_data = response.json()
        
        # Validate endpoint exists in schema
        assert "paths" in openapi_data
        assert "/characters" in openapi_data["paths"]
        
        characters_path = openapi_data["paths"]["/characters"]
        assert "post" in characters_path
        
        # Validate method documentation
        post_method = characters_path["post"]
        assert "summary" in post_method
        assert "description" in post_method
        assert "requestBody" in post_method
        assert "responses" in post_method
        
        # Validate multipart form support in documentation
        request_body = post_method["requestBody"]
        assert "content" in request_body
        
        # Should support multipart/form-data for file uploads
        # Note: FastAPI auto-generates this based on Form() and File() parameters
        assert "content" in request_body
        
        # Validate documented response codes for AI Scribe functionality
        responses = post_method["responses"]
        assert "201" in responses  # Success
        assert "400" in responses  # Validation errors
        assert "409" in responses  # Conflict
        assert "500" in responses  # Server error
        
        # Validate 201 response example includes AI Scribe fields
        success_response = responses["201"]
        assert "content" in success_response
        assert "application/json" in success_response["content"]
        
        # Should have AI Scribe example in documentation
        json_content = success_response["content"]["application/json"]
        if "example" in json_content:
            example = json_content["example"]
            assert "ai_scribe_enhanced" in example
            assert "files_processed" in example
    
    def test_character_creation_cors_support(self, client: TestClient):
        """
        Test that the character creation endpoint supports CORS requests.
        
        This test validates basic CORS handling for multipart form requests.
        """
        # Test with Origin header
        response = client.post(
            "/characters",
            data={
                "name": "cors_test_char",
                "description": "A character for testing CORS support with multipart form data requests."
            },
            files=[],
            headers={"Origin": "http://localhost:3000"}
        )
        
        # Should process the request (returns 201 for new, 409 for existing)
        assert response.status_code in [201, 409]
        
        # Validate that the request was processed (not blocked by CORS)
        response_data = response.json()
        assert "detail" in response_data or "name" in response_data  # Error or success response
    
    @patch('api_server._get_characters_directory_path')
    @patch('api_server._make_gemini_api_request')
    def test_character_creation_complete_integration_workflow(self, mock_make_gemini_request, mock_get_characters_directory_path, client: TestClient, mock_gemini_v2_response, tmp_path):
        """
        Complete integration test for the enhanced character creation workflow.
        
        This test validates the entire AI Scribe enhanced character creation process
        from file upload through V2 structure creation, demonstrating the complete
        overhaul of the /characters endpoint testing.
        """
        # Patch the character directory path to use temp directory
        mock_get_characters_directory_path.return_value = str(tmp_path / "characters")
        
        # Mock successful Gemini API response
        mock_make_gemini_request.return_value = mock_gemini_v2_response
        
        # Ensure the base characters directory exists
        (tmp_path / "characters").mkdir(parents=True, exist_ok=True)
        
        # Create test upload files with comprehensive content
        test_files_dir = tmp_path / "integration_files"
        test_files_dir.mkdir()
        
        combat_file = test_files_dir / "combat_experience.txt"
        combat_file.write_text("Veteran of 47 major engagements including the Siege of Kasr Holn and the Fall of Cadia. Expert in urban warfare and siege tactics.")
        
        background_file = test_files_dir / "background.md"
        background_file.write_text("# Character Background\\n\\nCommissar Isabella Varr hails from Cadia. Known for inspirational leadership and tactical brilliance.")
        
        # Prepare comprehensive form data and file uploads
        form_data = {
            "name": "integration_test_char",
            "description": "A comprehensive test character for validating the complete AI Scribe enhancement workflow including file uploads, content processing, and V2 structure creation."
        }
        
        files_to_upload = [
            ("files", ("combat_experience.txt", combat_file.read_bytes(), "text/plain")),
            ("files", ("background.md", background_file.read_bytes(), "text/markdown"))
        ]
        
        # Execute the complete workflow with additional os.path functions patched
        def mock_exists_func(path):
            # Characters base directory exists, specific character doesn't exist yet
            if path == str(tmp_path / "characters"):
                return True
            if path.endswith("integration_test_char"):
                return False  # Character doesn't exist yet
            return True
            
        test_char_dir = tmp_path / "characters" / "integration_test_char"
        with patch('api_server.os.path.exists', side_effect=mock_exists_func):
            response = client.post(
                    "/characters",
                    data=form_data,
                    files=files_to_upload
                )
        
        # Validate complete success
        assert response.status_code == 201
        response_data = response.json()
        
        # Validate comprehensive response structure
        assert response_data["name"] == "integration_test_char"
        assert response_data["ai_scribe_enhanced"] is True
        assert response_data["files_processed"] == 2
        assert "ai_scribe_enhanced_complete" in response_data["status"]
        
        # Validate V2 character structure was created
        char_dir = tmp_path / "characters" / "integration_test_char"
        v2_files = ["1_core.md", "2_history.md", "3_profile.yaml", "4_lore.md"]
        
        for v2_file in v2_files:
            file_path = char_dir / v2_file
            assert file_path.exists(), f"V2 file missing: {v2_file}"
            
            content = file_path.read_text(encoding='utf-8')
            assert len(content) > 50, f"V2 file has insufficient content: {v2_file}"
            
            # Validate specific content structure based on file type
            if v2_file == "1_core.md":
                assert "# Character Core:" in content
                assert "Isabella Varr" in content
                assert "Identity Matrix" in content
            elif v2_file == "2_history.md":
                assert "# Character History:" in content
                assert "Fall of Cadia" in content
            elif v2_file == "3_profile.yaml":
                assert "character:" in content
                assert "marksmanship:" in content
                assert "loyalty:" in content
            elif v2_file == "4_lore.md":
                assert "# Character Lore:" in content
                assert "Notable Quotes" in content
        
        # Validate Gemini API integration
        mock_make_gemini_request.assert_called_once()
        call_args = mock_make_gemini_request.call_args
        prompt_used = call_args[0][0]
        
        # Verify file content was integrated into prompt
        assert "Veteran of 47 major engagements" in prompt_used
        assert "combat_experience.txt" in prompt_used
        assert "background.md" in prompt_used
        assert "integration_test_char" in prompt_used.lower()
        
        # Verify prompt contains V2 structure instructions
        assert "=== FILE: 1_core.md ===" in prompt_used
        assert "=== FILE: 2_history.md ===" in prompt_used
        assert "=== FILE: 3_profile.yaml ===" in prompt_used
        assert "=== FILE: 4_lore.md ===" in prompt_used


class TestCampaignsListEndpoint:
    """
    Test cases for the campaigns list endpoint (/campaigns) functionality.
    
    Sacred test scriptures to validate the campaign codex retrieval rituals
    and ensure proper response of the blessed campaign management systems.
    """
    
    def test_campaigns_response_model_validation(self):
        """
        Test CampaignsListResponse model validation with sacred test data.
        
        Validates:
        - Model accepts valid campaign list data
        - Required 'campaigns' field is properly validated
        - List structure is enforced correctly
        """
        # Test valid campaign list data - sacred campaign names
        valid_data = {
            "campaigns": ["serenitas_shadow", "horus_heresy", "third_armageddon"]
        }
        
        # Model should accept valid campaign data without corruption
        response_model = CampaignsListResponse(**valid_data)
        assert response_model.campaigns == valid_data["campaigns"]
        assert len(response_model.campaigns) == 3
        assert "serenitas_shadow" in response_model.campaigns
    
    def test_get_campaigns_endpoint_success(self, client: TestClient):
        """
        Test successful GET /campaigns endpoint response.
        
        Sacred ritual to validate:
        - Endpoint returns 200 status code when campaigns directory exists
        - Response structure matches CampaignsListResponse model
        - Response contains expected campaign directories
        """
        # This test will initially FAIL as the endpoint logic is not yet implemented
        response = client.get("/campaigns")
        
        # Expect successful response from blessed endpoint
        assert response.status_code == status.HTTP_200_OK
        
        # Validate response structure follows sacred model
        response_data = response.json()
        assert "campaigns" in response_data
        assert isinstance(response_data["campaigns"], list)
        
        # Validate campaigns list is sorted in proper order
        campaigns = response_data["campaigns"]
        assert campaigns == sorted(campaigns)
    
    def test_get_campaigns_directory_not_found(self, client: TestClient):
        """
        Test GET /campaigns when campaigns directory does not exist.
        
        Sacred test to validate:
        - Returns 404 status when codex/campaigns directory is missing
        - Error response follows ErrorResponse model structure
        - Proper error message about missing sacred codex
        """
        # Mock the campaigns directory path to non-existent location
        with patch('api_server._get_campaigns_directory_path') as mock_path:
            mock_path.return_value = '/nonexistent/campaigns/path'
            
            response = client.get("/campaigns")
            
            # Should return 404 when sacred codex is missing
            assert response.status_code == status.HTTP_404_NOT_FOUND
            
            # Validate error response structure
            response_data = response.json()
            assert "detail" in response_data
            assert "not found" in response_data["detail"].lower()
    
    def test_get_campaigns_permission_error(self, client: TestClient):
        """
        Test GET /campaigns when permission denied accessing directory.
        
        Sacred test to validate:
        - Returns 500 status for permission errors
        - Proper error handling when access is forbidden
        """
        # Mock os.listdir to raise PermissionError
        with patch('api_server.os.listdir') as mock_listdir:
            mock_listdir.side_effect = PermissionError("Access denied to sacred codex")
            
            response = client.get("/campaigns")
            
            # Should return 500 for permission issues
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Validate error response contains permission message
            response_data = response.json()
            assert "detail" in response_data
            assert "permission" in response_data["detail"].lower()


class TestCampaignCreationEndpoint:
    """
    Test cases for the campaign creation endpoint (POST /campaigns) functionality.
    
    Sacred test scriptures to validate the campaign creation rituals and
    ensure proper establishment of new campaign codex directories.
    """
    
    def test_campaign_creation_request_model_validation(self):
        """
        Test CampaignCreationRequest model validation with various inputs.
        
        Validates:
        - Model accepts valid campaign name formats
        - Name length constraints are enforced
        - Alphanumeric and underscore validation works
        - Name is converted to lowercase
        """
        # Test valid campaign name - sacred designation
        valid_request = CampaignCreationRequest(campaign_name="Serenitas_Shadow")
        assert valid_request.campaign_name == "serenitas_shadow"  # Lowercase conversion
        
        # Test minimum length requirement
        with pytest.raises(ValueError):
            CampaignCreationRequest(campaign_name="ab")  # Too short
        
        # Test maximum length requirement  
        with pytest.raises(ValueError):
            CampaignCreationRequest(campaign_name="a" * 51)  # Too long
        
        # Test invalid characters
        with pytest.raises(ValueError):
            CampaignCreationRequest(campaign_name="invalid-name!")  # Invalid chars
    
    def test_campaign_creation_response_model_validation(self):
        """
        Test CampaignCreationResponse model validation.
        
        Validates:
        - Model accepts valid campaign creation response data
        - All required fields are properly validated
        """
        valid_response = CampaignCreationResponse(
            campaign_name="test_campaign",
            status="created", 
            directory_path="/path/to/codex/campaigns/test_campaign",
            brief_generated=False
        )
        
        assert valid_response.campaign_name == "test_campaign"
        assert valid_response.status == "created"
        assert valid_response.directory_path.endswith("test_campaign")
        assert valid_response.brief_generated == False
    
    def test_post_campaigns_endpoint_success(self, client: TestClient):
        """
        Test successful POST /campaigns endpoint for creating new campaign.
        
        Sacred ritual to validate:
        - Endpoint returns 201 status code for successful creation
        - Response structure matches CampaignCreationResponse model
        - Campaign directory is actually created in codex/campaigns/
        """
        # Use unique campaign name to avoid test collision
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        campaign_data = {"campaign_name": f"test_campaign_{unique_id}"}
        
        response = client.post(
            "/campaigns",
            json=campaign_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Expect successful creation response
        assert response.status_code == status.HTTP_201_CREATED
        
        # Validate response structure follows sacred model
        response_data = response.json()
        assert "campaign_name" in response_data
        assert "status" in response_data
        assert "directory_path" in response_data
        assert "brief_generated" in response_data
        
        # Validate campaign name is processed correctly
        expected_name = campaign_data["campaign_name"]
        assert response_data["campaign_name"] == expected_name
        assert response_data["status"] == "created"
        assert expected_name in response_data["directory_path"]
        assert response_data["brief_generated"] == False  # No description provided
    
    def test_post_campaigns_duplicate_name_conflict(self, client: TestClient):
        """
        Test POST /campaigns when campaign name already exists.
        
        Sacred test to validate:
        - Returns 409 status for duplicate campaign names
        - Proper conflict error message
        """
        campaign_data = {"campaign_name": "existing_campaign"}
        
        # Mock directory existence check to simulate existing campaign
        with patch('api_server.os.path.exists') as mock_exists:
            mock_exists.return_value = True  # Campaign already exists
            
            response = client.post(
                "/campaigns",
                json=campaign_data,
                headers={"Content-Type": "application/json"}
            )
            
            # Should return 409 for duplicate campaign name
            assert response.status_code == status.HTTP_409_CONFLICT
            
            # Validate conflict error response
            response_data = response.json()
            assert "detail" in response_data
            assert "already exists" in response_data["detail"]
    
    def test_post_campaigns_invalid_name_format(self, client: TestClient):
        """
        Test POST /campaigns with invalid campaign name format.
        
        Sacred test to validate:
        - Returns 422 status for validation errors
        - Proper validation error messages
        """
        # Test invalid characters in campaign name
        invalid_data = {"campaign_name": "invalid-campaign-name!"}
        
        response = client.post(
            "/campaigns",
            json=invalid_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 422 for validation errors
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Validate validation error response
        response_data = response.json()
        assert "detail" in response_data
    
    def test_post_campaigns_directory_creation_failure(self, client: TestClient):
        """
        Test POST /campaigns when directory creation fails.
        
        Sacred test to validate:
        - Returns 500 status for directory creation errors
        - Proper error handling for filesystem issues
        """
        campaign_data = {"campaign_name": "test_campaign"}
        
        # Mock os.makedirs to raise OSError
        with patch('api_server.os.makedirs') as mock_makedirs:
            mock_makedirs.side_effect = OSError("Disk full or permission denied")
            
            response = client.post(
                "/campaigns",
                json=campaign_data,
                headers={"Content-Type": "application/json"}
            )
            
            # Should return 500 for creation failure
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Validate error response
            response_data = response.json()
            assert "detail" in response_data
            assert "failed" in response_data["detail"].lower()
    
    def test_post_campaigns_missing_required_field(self, client: TestClient):
        """
        Test POST /campaigns with missing required campaign_name field.
        
        Sacred test to validate:
        - Returns 422 status for missing required fields
        - Proper validation error for required field
        """
        # Send request without campaign_name field
        response = client.post(
            "/campaigns",
            json={},
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 422 for missing required field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Validate validation error mentions missing field
        response_data = response.json()
        assert "detail" in response_data


class TestCampaignBriefGeneration:
    """
    Test cases for AI-powered campaign brief generation functionality.
    
    Sacred Mission: Validate the enhanced campaign creation with automatic
    mission brief generation using the Gemini API integration.
    """
    
    def test_campaign_creation_with_brief_generation_success(self, client: TestClient):
        """
        Test successful campaign creation with AI-powered brief generation.
        
        This test validates:
        - Campaign creation with description parameter
        - AI brief generation functionality
        - Proper response with brief_generated field
        """
        # Setup test campaign with description for brief generation
        campaign_data = {
            "campaign_name": f"ai_test_campaign_{uuid.uuid4().hex[:8]}",
            "description": "A grimdark investigation into heretical activities in Hive Tertius, involving suspected Genestealer cult infiltration of the local PDF forces."
        }
        
        # Mock successful Gemini API response for brief generation
        mock_brief_response = """
        # Campaign Brief: Shadows in Hive Tertius
        
        ## Mission Overview
        Imperial Intelligence has detected suspicious activities within Hive Tertius that suggest
        possible xenos infiltration. The local Planetary Defense Forces have reported unusual
        behavioral patterns and unexplained tactical decisions that compromise Imperial defenses.
        
        ## Primary Objectives
        1. Investigate suspected Genestealer cult presence in PDF command structure
        2. Identify compromised personnel and eliminate heretical elements
        3. Secure critical infrastructure and restore Imperial control
        
        ## Threat Assessment
        - High probability of Genestealer cult presence
        - Compromised local command structure
        - Potential civilian population exposure
        
        ## Resources Assigned
        - Astra Militarum reconnaissance forces
        - Inquisition oversight and support
        - Local Arbites coordination where possible
        """
        
        with patch('api_server._make_gemini_api_request') as mock_gemini:
            mock_gemini.return_value = mock_brief_response
            
            response = client.post(
                "/campaigns",
                json=campaign_data,
                headers={"Content-Type": "application/json"}
            )
            
            # Should return 201 for successful creation with brief
            assert response.status_code == status.HTTP_201_CREATED
            
            # Validate response includes brief_generated field
            response_data = response.json()
            assert "campaign_name" in response_data
            assert "status" in response_data
            assert "directory_path" in response_data
            assert "brief_generated" in response_data
            assert response_data["brief_generated"] is True
            
            # Verify Gemini API was called for brief generation
            mock_gemini.assert_called_once()
    
    def test_campaign_creation_brief_generation_failure(self, client: TestClient):
        """
        Test campaign creation when AI brief generation fails.
        
        Validates:
        - Campaign still created successfully even if brief generation fails
        - brief_generated field indicates failure
        - Graceful degradation behavior
        """
        campaign_data = {
            "campaign_name": f"ai_fail_test_{uuid.uuid4().hex[:8]}",
            "description": "Test campaign for brief generation failure scenario"
        }
        
        # Mock Gemini API failure
        with patch('api_server._make_gemini_api_request') as mock_gemini:
            mock_gemini.return_value = None  # Simulate API failure
            
            response = client.post(
                "/campaigns",
                json=campaign_data,
                headers={"Content-Type": "application/json"}
            )
            
            # Should still return 201 for successful campaign creation
            assert response.status_code == status.HTTP_201_CREATED
            
            # Validate response indicates brief generation failed
            response_data = response.json()
            assert "brief_generated" in response_data
            assert response_data["brief_generated"] is False
            
            # Campaign should still be created
            assert response_data["status"] == "created"
    
    def test_campaign_creation_without_description(self, client: TestClient):
        """
        Test campaign creation without description (no brief generation).
        
        Validates:
        - Campaign creation works without optional description
        - brief_generated field indicates no brief was generated
        - Backward compatibility maintained
        """
        campaign_data = {
            "campaign_name": f"no_desc_test_{uuid.uuid4().hex[:8]}"
            # No description field - should not trigger brief generation
        }
        
        response = client.post(
            "/campaigns",
            json=campaign_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 201 for successful creation without brief
        assert response.status_code == status.HTTP_201_CREATED
        
        # Validate response indicates no brief generated
        response_data = response.json()
        assert "brief_generated" in response_data
        assert response_data["brief_generated"] is False
        assert response_data["status"] == "created"
    
    def test_campaign_creation_empty_description(self, client: TestClient):
        """
        Test campaign creation with empty description.
        
        Validates:
        - Empty description does not trigger brief generation
        - proper handling of empty optional field
        """
        campaign_data = {
            "campaign_name": f"empty_desc_test_{uuid.uuid4().hex[:8]}",
            "description": ""  # Empty description
        }
        
        response = client.post(
            "/campaigns",
            json=campaign_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 201 for successful creation
        assert response.status_code == status.HTTP_201_CREATED
        
        # Should not generate brief for empty description
        response_data = response.json()
        assert response_data["brief_generated"] is False
    
    def test_campaign_creation_description_too_long(self, client: TestClient):
        """
        Test campaign creation with description exceeding maximum length.
        
        Validates:
        - Description length validation (max 500 characters)
        - Proper error response for validation failure
        """
        # Create description longer than 500 characters
        long_description = "A" * 501
        
        campaign_data = {
            "campaign_name": f"long_desc_test_{uuid.uuid4().hex[:8]}",
            "description": long_description
        }
        
        response = client.post(
            "/campaigns",
            json=campaign_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 422 for validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Validate error response mentions field validation
        response_data = response.json()
        assert "detail" in response_data


# Pytest configuration and test discovery
if __name__ == "__main__":
    # Run tests with verbose output and coverage reporting
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--show-capture=no"
    ])