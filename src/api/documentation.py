#!/usr/bin/env python3
"""
API Documentation Generation System.

Provides comprehensive OpenAPI specification generation, interactive documentation,
and API guides with examples and integration instructions.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse
import json

from .response_models import *
from .versioning import APIVersion

logger = logging.getLogger(__name__)

class DocumentationGenerator:
    """Generate comprehensive API documentation."""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    def generate_openapi_schema(self, version: str = "1.1.0") -> Dict[str, Any]:
        """Generate enhanced OpenAPI schema with comprehensive documentation."""
        
        if self.app.openapi_schema:
            return self.app.openapi_schema
        
        openapi_schema = get_openapi(
            title="Novel Engine API",
            version=version,
            description=self._get_api_description(),
            routes=self.app.routes,
            tags=self._get_tags_metadata()
        )
        
        # Enhance schema with additional information
        openapi_schema = self._enhance_openapi_schema(openapi_schema)
        
        self.app.openapi_schema = openapi_schema
        return openapi_schema
    
    def _get_api_description(self) -> str:
        """Get comprehensive API description."""
        return """
# Novel Engine API

The Novel Engine API provides comprehensive endpoints for character management, 
story generation, and interactive narrative experiences. This RESTful API enables 
developers to integrate advanced AI-driven storytelling capabilities into their applications.

## Key Features

- **Character Management**: Create, customize, and manage AI characters with detailed personalities
- **Story Generation**: Generate dynamic stories through character interactions
- **Real-time Interactions**: WebSocket-based real-time character interactions
- **Health Monitoring**: Comprehensive system health and performance monitoring
- **Versioning**: Full API versioning with backward compatibility
- **Error Handling**: Standardized error responses with detailed information

## Authentication

Currently, the API operates in open mode for development. Production deployments
will require API key authentication.

## Rate Limiting

The API implements rate limiting to ensure fair usage:
- **Development**: 1000 requests per hour per IP
- **Production**: Custom limits based on subscription tier

## Response Format

All API responses follow a standardized format:

```json
{
  "status": "success|error|partial|pending",
  "data": { /* response payload */ },
  "error": { /* error information if status is error */ },
  "metadata": {
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "uuid",
    "api_version": "1.1",
    "server_time": 0.123
  }
}
```

## Error Handling

Errors are returned with appropriate HTTP status codes and detailed information:

- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation errors
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server-side errors
- **503 Service Unavailable**: System temporarily unavailable

## WebSocket Connections

Real-time features use WebSocket connections:

- **Story Generation Progress**: `/api/v1/stories/progress/{generation_id}`
- **Character Interactions**: `/api/v1/interactions/ws/{interaction_id}`

## SDK and Libraries

Official SDKs are available for:
- Python: `pip install novel-engine-python`
- JavaScript/TypeScript: `npm install novel-engine-js`
- Java: Maven/Gradle support available

## Support

- **Documentation**: https://docs.novel-engine.app
- **Support**: support@novel-engine.app
- **GitHub**: https://github.com/novel-engine/api
        """
    
    def _get_tags_metadata(self) -> List[Dict[str, Any]]:
        """Get tags metadata for API organization."""
        return [
            {
                "name": "System",
                "description": "System health, version info, and API metadata endpoints"
            },
            {
                "name": "Characters",
                "description": "Character creation, management, and customization endpoints"
            },
            {
                "name": "Stories",
                "description": "Story generation, export, and narrative management endpoints"
            },
            {
                "name": "Interactions",
                "description": "Real-time character interactions and conversation management"
            },
            {
                "name": "Monitoring",
                "description": "Performance metrics, monitoring, and observability endpoints"
            }
        ]
    
    def _enhance_openapi_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance OpenAPI schema with additional information."""
        
        # Add servers information
        schema["servers"] = [
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.novel-engine.app",
                "description": "Production server"
            }
        ]
        
        # Add contact and license information
        schema["info"]["contact"] = {
            "name": "Novel Engine API Support",
            "url": "https://novel-engine.app/support",
            "email": "support@novel-engine.app"
        }
        
        schema["info"]["license"] = {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
        
        # Add external documentation
        schema["externalDocs"] = {
            "description": "Full API Documentation",
            "url": "https://docs.novel-engine.app"
        }
        
        # Enhance security schemes
        schema["components"]["securitySchemes"] = {
            "APIKeyHeader": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key for authenticated requests"
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token for authenticated requests"
            }
        }
        
        # Add response examples
        self._add_response_examples(schema)
        
        # Add request examples
        self._add_request_examples(schema)
        
        return schema
    
    def _add_response_examples(self, schema: Dict[str, Any]):
        """Add response examples to schema."""
        
        # Example successful character creation response
        character_success_example = {
            "status": "success",
            "data": {
                "agent_id": "aragorn_ranger",
                "name": "Aragorn",
                "status": "active",
                "created_at": "2024-01-01T12:00:00Z",
                "background_summary": "A skilled ranger and heir to the throne of Gondor",
                "skills": {
                    "combat": 0.9,
                    "leadership": 0.8,
                    "tracking": 0.95
                }
            },
            "metadata": {
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456",
                "api_version": "1.1",
                "server_time": 0.045
            }
        }
        
        # Example error response
        error_example = {
            "status": "error",
            "data": None,
            "error": {
                "type": "validation_error",
                "message": "Character name is required",
                "detail": "The 'name' field cannot be empty",
                "field": "name"
            },
            "metadata": {
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123457",
                "api_version": "1.1",
                "server_time": 0.012
            }
        }
        
        # Add examples to components
        if "examples" not in schema["components"]:
            schema["components"]["examples"] = {}
        
        schema["components"]["examples"].update({
            "CharacterSuccessResponse": {
                "summary": "Successful character creation",
                "value": character_success_example
            },
            "ValidationErrorResponse": {
                "summary": "Validation error example",
                "value": error_example
            }
        })
    
    def _add_request_examples(self, schema: Dict[str, Any]):
        """Add request examples to schema."""
        
        # Character creation request example
        character_request_example = {
            "agent_id": "aragorn_ranger",
            "name": "Aragorn",
            "background_summary": "A skilled ranger and heir to the throne of Gondor",
            "personality_traits": "Brave, noble, skilled in combat and leadership",
            "skills": {
                "combat": 0.9,
                "leadership": 0.8,
                "tracking": 0.95,
                "diplomacy": 0.7
            },
            "current_location": "Rivendell",
            "metadata": {
                "source": "tolkien",
                "category": "hero"
            }
        }
        
        # Story generation request example
        story_request_example = {
            "characters": ["aragorn_ranger", "legolas_elf", "gimli_dwarf"],
            "title": "The Fellowship's Journey"
        }
        
        # Add examples to components
        schema["components"]["examples"].update({
            "CharacterCreationRequest": {
                "summary": "Create a new character",
                "value": character_request_example
            },
            "StoryGenerationRequest": {
                "summary": "Generate a story with multiple characters",
                "value": story_request_example
            }
        })

def setup_enhanced_docs(app: FastAPI):
    """Setup enhanced API documentation."""
    
    doc_generator = DocumentationGenerator(app)
    
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Custom Swagger UI with enhanced styling."""
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Interactive API Documentation",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            swagger_favicon_url="https://novel-engine.app/favicon.ico"
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        """Custom ReDoc documentation."""
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - API Reference",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
            redoc_favicon_url="https://novel-engine.app/favicon.ico"
        )
    
    @app.get("/api/openapi.json", include_in_schema=False)
    async def get_openapi_json():
        """Get OpenAPI schema as JSON."""
        return doc_generator.generate_openapi_schema()
    
    @app.get("/api/documentation", include_in_schema=False)
    async def get_api_guide():
        """Get comprehensive API integration guide."""
        return HTMLResponse(content=_generate_integration_guide())
    
    # Override default OpenAPI schema generation
    def custom_openapi():
        """
        Generate custom OpenAPI schema with enhanced documentation.
        
        Returns:
            Enhanced OpenAPI schema dictionary
        """
        return doc_generator.generate_openapi_schema()
    
    app.openapi = custom_openapi
    
    logger.info("Enhanced API documentation initialized")

def _generate_integration_guide() -> str:
    """Generate HTML integration guide."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Novel Engine API - Integration Guide</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 10px; margin-bottom: 30px; }
            .section { margin-bottom: 40px; }
            .code-block { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 5px; padding: 15px; overflow-x: auto; }
            .endpoint { background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 10px 0; }
            .method { display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; color: white; margin-right: 10px; }
            .get { background: #4caf50; }
            .post { background: #ff9800; }
            .put { background: #2196f3; }
            .delete { background: #f44336; }
            .toc { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 30px; }
            .toc ul { list-style-type: none; padding-left: 20px; }
            .toc a { text-decoration: none; color: #667eea; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Novel Engine API Integration Guide</h1>
            <p>Complete guide for integrating with the Novel Engine API</p>
        </div>

        <div class="toc">
            <h2>Table of Contents</h2>
            <ul>
                <li><a href="#quick-start">Quick Start</a></li>
                <li><a href="#authentication">Authentication</a></li>
                <li><a href="#characters">Character Management</a></li>
                <li><a href="#stories">Story Generation</a></li>
                <li><a href="#websockets">Real-time Features</a></li>
                <li><a href="#error-handling">Error Handling</a></li>
                <li><a href="#rate-limiting">Rate Limiting</a></li>
                <li><a href="#sdks">SDKs and Libraries</a></li>
            </ul>
        </div>

        <div class="section" id="quick-start">
            <h2>Quick Start</h2>
            <p>Get started with the Novel Engine API in minutes:</p>
            
            <h3>1. Check System Health</h3>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/health</code>
            </div>
            <div class="code-block">
curl -X GET "http://localhost:8000/health"
            </div>

            <h3>2. Create a Character</h3>
            <div class="endpoint">
                <span class="method post">POST</span> <code>/api/v1/characters</code>
            </div>
            <div class="code-block">
curl -X POST "http://localhost:8000/api/v1/characters" \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_id": "wizard_gandalf",
    "name": "Gandalf the Grey",
    "background_summary": "A wise wizard of Middle-earth",
    "personality_traits": "Wise, patient, powerful, caring",
    "skills": {
      "magic": 0.95,
      "wisdom": 0.9,
      "leadership": 0.8
    }
  }'
            </div>

            <h3>3. Generate a Story</h3>
            <div class="endpoint">
                <span class="method post">POST</span> <code>/api/v1/stories/generate</code>
            </div>
            <div class="code-block">
curl -X POST "http://localhost:8000/api/v1/stories/generate" \\
  -H "Content-Type: application/json" \\
  -d '{
    "characters": ["wizard_gandalf"],
    "title": "The Wizard's Tale"
  }'
            </div>
        </div>

        <div class="section" id="authentication">
            <h2>Authentication</h2>
            <p>The Novel Engine API supports multiple authentication methods:</p>
            
            <h3>API Key Authentication</h3>
            <div class="code-block">
curl -X GET "http://localhost:8000/api/v1/characters" \\
  -H "X-API-Key: your-api-key-here"
            </div>

            <h3>Bearer Token Authentication</h3>
            <div class="code-block">
curl -X GET "http://localhost:8000/api/v1/characters" \\
  -H "Authorization: Bearer your-jwt-token-here"
            </div>
        </div>

        <div class="section" id="characters">
            <h2>Character Management</h2>
            
            <h3>Create Character</h3>
            <div class="endpoint">
                <span class="method post">POST</span> <code>/api/v1/characters</code>
            </div>
            
            <h3>List Characters</h3>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/api/v1/characters</code>
            </div>
            
            <h3>Get Character Details</h3>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/api/v1/characters/{character_id}</code>
            </div>
            
            <h3>Update Character</h3>
            <div class="endpoint">
                <span class="method put">PUT</span> <code>/api/v1/characters/{character_id}</code>
            </div>
        </div>

        <div class="section" id="stories">
            <h2>Story Generation</h2>
            
            <h3>Generate Story</h3>
            <div class="endpoint">
                <span class="method post">POST</span> <code>/api/v1/stories/generate</code>
            </div>
            
            <h3>Check Generation Status</h3>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/api/v1/stories/status/{generation_id}</code>
            </div>
        </div>

        <div class="section" id="websockets">
            <h2>Real-time Features</h2>
            <p>The API provides WebSocket endpoints for real-time updates:</p>
            
            <h3>Story Generation Progress</h3>
            <div class="code-block">
const ws = new WebSocket('ws://localhost:8000/api/v1/stories/progress/story_12345678');

ws.onmessage = function(event) {
    const progress = JSON.parse(event.data);
    console.log(`Progress: ${progress.progress}% - ${progress.stage}`);
};
            </div>
        </div>

        <div class="section" id="error-handling">
            <h2>Error Handling</h2>
            <p>All errors follow a standardized format:</p>
            
            <div class="code-block">
{
  "status": "error",
  "data": null,
  "error": {
    "type": "validation_error",
    "message": "Character name is required",
    "detail": "The 'name' field cannot be empty",
    "field": "name"
  },
  "metadata": {
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_123456",
    "api_version": "1.1",
    "server_time": 0.012
  }
}
            </div>
        </div>

        <div class="section" id="rate-limiting">
            <h2>Rate Limiting</h2>
            <p>The API implements rate limiting to ensure fair usage:</p>
            <ul>
                <li><strong>Development</strong>: 1000 requests per hour per IP</li>
                <li><strong>Production</strong>: Custom limits based on subscription</li>
            </ul>
            
            <p>Rate limit headers are included in responses:</p>
            <div class="code-block">
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
            </div>
        </div>

        <div class="section" id="sdks">
            <h2>SDKs and Libraries</h2>
            
            <h3>Python SDK</h3>
            <div class="code-block">
pip install novel-engine-python

from novel_engine import NovelEngineClient

client = NovelEngineClient(api_key="your-api-key")
character = client.characters.create(
    agent_id="hero_arthur",
    name="King Arthur",
    personality_traits="Noble, brave, just"
)
            </div>

            <h3>JavaScript/TypeScript SDK</h3>
            <div class="code-block">
npm install novel-engine-js

import { NovelEngineClient } from 'novel-engine-js';

const client = new NovelEngineClient({ apiKey: 'your-api-key' });

const character = await client.characters.create({
  agentId: 'hero_arthur',
  name: 'King Arthur',
  personalityTraits: 'Noble, brave, just'
});
            </div>
        </div>

        <footer style="margin-top: 60px; padding-top: 20px; border-top: 1px solid #e9ecef; text-align: center; color: #6c757d;">
            <p>© 2024 Novel Engine. All rights reserved. | <a href="https://novel-engine.app">Website</a> | <a href="https://docs.novel-engine.app">Documentation</a> | <a href="mailto:support@novel-engine.app">Support</a></p>
        </footer>
    </body>
    </html>
    """

__all__ = ['DocumentationGenerator', 'setup_enhanced_docs']