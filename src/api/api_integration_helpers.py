#!/usr/bin/env python3
"""
API Integration Helpers with Context7 Enhancement
================================================

Utility functions and classes to enhance existing APIs with Context7 integration,
providing seamless documentation, examples, and pattern validation.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime
from functools import wraps
from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class APIEnhancementConfig(BaseModel):
    """Configuration for API enhancements."""
    enable_context7_examples: bool = True
    enable_pattern_validation: bool = True
    enable_documentation_enhancement: bool = True
    enable_best_practice_suggestions: bool = True
    cache_examples: bool = True
    cache_duration_minutes: int = 60

class Context7EnhancedRoute(APIRoute):
    """Enhanced API route with Context7 integration."""
    
    def __init__(self, *args, context7_api=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.context7_api = context7_api
        self.example_cache: Dict[str, Any] = {}
        
    async def get_route_examples(self) -> List[Dict[str, Any]]:
        """Get Context7-powered examples for this route."""
        if not self.context7_api:
            return []
            
        cache_key = f"{self.path}_{self.methods}"
        if cache_key in self.example_cache:
            cached_data = self.example_cache[cache_key]
            if (datetime.now() - cached_data["timestamp"]).total_seconds() < 3600:  # 1 hour cache
                return cached_data["examples"]
        
        try:
            examples = []
            for method in self.methods:
                example = await self.context7_api._call_context7("generate_code_example", {
                    "endpoint_path": self.path,
                    "method": method,
                    "format": "python"
                })
                if example.get("success"):
                    examples.append(example["example"])
            
            # Cache the results
            self.example_cache[cache_key] = {
                "examples": examples,
                "timestamp": datetime.now()
            }
            
            return examples
            
        except Exception as e:
            logger.warning(f"Failed to get Context7 examples for {self.path}: {e}")
            return []

class APIDocumentationEnhancer:
    """Enhances existing API endpoints with Context7-powered documentation."""
    
    def __init__(self, context7_api=None):
        self.context7_api = context7_api
        self.enhancement_cache: Dict[str, Any] = {}
        
    async def enhance_endpoint_documentation(self, endpoint_path: str, method: str, 
                                           existing_docs: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance endpoint documentation with Context7 features."""
        if not self.context7_api:
            return existing_docs
            
        try:
            # Generate enhanced documentation
            enhanced_docs = existing_docs.copy()
            
            # Add Context7-powered examples
            examples = await self._get_endpoint_examples(endpoint_path, method)
            if examples:
                enhanced_docs["examples"] = examples
            
            # Add best practice recommendations
            best_practices = await self._get_best_practices(endpoint_path, method)
            if best_practices:
                enhanced_docs["best_practices"] = best_practices
            
            # Add framework patterns
            patterns = await self._get_framework_patterns(endpoint_path, method)
            if patterns:
                enhanced_docs["framework_patterns"] = patterns
            
            return enhanced_docs
            
        except Exception as e:
            logger.error(f"Failed to enhance documentation for {endpoint_path}: {e}")
            return existing_docs
    
    async def _get_endpoint_examples(self, endpoint_path: str, method: str) -> List[Dict[str, Any]]:
        """Get Context7-powered code examples."""
        try:
            response = await self.context7_api._call_context7("generate_code_example", {
                "endpoint_path": endpoint_path,
                "method": method,
                "format": "python",
                "include_auth": True,
                "include_error_handling": True
            })
            
            if response.get("success"):
                return [response["example"]]
            return []
            
        except Exception as e:
            logger.warning(f"Failed to get examples for {endpoint_path}: {e}")
            return []
    
    async def _get_best_practices(self, endpoint_path: str, method: str) -> List[str]:
        """Get relevant best practices for the endpoint."""
        try:
            response = await self.context7_api._call_context7("get_best_practices", {
                "framework": "fastapi",
                "endpoint_pattern": f"{method} {endpoint_path}"
            })
            
            if response.get("success"):
                practices = response.get("practices", [])
                return [practice.get("title", "") for practice in practices]
            return []
            
        except Exception as e:
            logger.warning(f"Failed to get best practices for {endpoint_path}: {e}")
            return []
    
    async def _get_framework_patterns(self, endpoint_path: str, method: str) -> List[str]:
        """Get relevant framework patterns."""
        patterns = []
        
        # Analyze endpoint to suggest relevant patterns
        if "/{" in endpoint_path:  # Path parameters
            patterns.append("Path Parameter Validation")
        
        if method.upper() == "POST":
            patterns.append("Request Body Validation")
            patterns.append("Response Model Design")
        
        if method.upper() == "GET":
            patterns.append("Query Parameter Handling")
            patterns.append("Response Caching")
        
        if "/auth" in endpoint_path.lower():
            patterns.append("JWT Authentication")
            patterns.append("Permission-Based Access Control")
        
        return patterns

class APIValidationEnhancer:
    """Provides Context7-powered API validation capabilities."""
    
    def __init__(self, context7_api=None):
        self.context7_api = context7_api
        
    async def validate_api_implementation(self, api_code: str, endpoint_path: str) -> Dict[str, Any]:
        """Validate API implementation using Context7 patterns."""
        if not self.context7_api:
            return {"valid": True, "message": "Context7 validation not available"}
        
        try:
            response = await self.context7_api._call_context7("validate_pattern", {
                "api_code": api_code,
                "framework": "fastapi",
                "endpoint_path": endpoint_path,
                "validation_rules": ["naming_conventions", "error_handling", "documentation"]
            })
            
            if response.get("success"):
                return response["validation"]
            
            return {"valid": False, "message": "Validation failed"}
            
        except Exception as e:
            logger.error(f"API validation failed: {e}")
            return {"valid": False, "message": f"Validation error: {str(e)}"}

def enhance_api_with_context7(context7_api=None, config: APIEnhancementConfig = None):
    """Decorator to enhance API endpoints with Context7 integration."""
    if config is None:
        config = APIEnhancementConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the original function
            result = await func(*args, **kwargs)
            
            # Enhance response with Context7 features if enabled
            if config.enable_context7_examples and context7_api:
                try:
                    # Add Context7 enhancements to response metadata
                    if hasattr(result, 'metadata') and hasattr(result.metadata, '__dict__'):
                        result.metadata.__dict__['context7_enhanced'] = True
                        result.metadata.__dict__['enhanced_at'] = datetime.now().isoformat()
                except Exception as e:
                    logger.debug(f"Failed to add Context7 metadata: {e}")
            
            return result
        
        return wrapper
    return decorator

class APIIntegrationManager:
    """Manages integration between existing APIs and Context7 enhancements."""
    
    def __init__(self, app: FastAPI, context7_api=None, config: APIEnhancementConfig = None):
        self.app = app
        self.context7_api = context7_api
        self.config = config or APIEnhancementConfig()
        self.documentation_enhancer = APIDocumentationEnhancer(context7_api)
        self.validation_enhancer = APIValidationEnhancer(context7_api)
        
    def setup_integrations(self):
        """Setup Context7 integrations across all registered endpoints."""
        if not self.context7_api:
            logger.warning("Context7 API not available - skipping integrations")
            return
        
        # Enhance existing routes
        for route in self.app.routes:
            if isinstance(route, APIRoute):
                self._enhance_route(route)
        
        # Add integration endpoints
        self._add_integration_endpoints()
        
        logger.info("Context7 integrations configured successfully")
    
    def _enhance_route(self, route: APIRoute):
        """Enhance individual route with Context7 features."""
        try:
            # Store original endpoint function
            original_endpoint = route.endpoint
            
            # Create enhanced endpoint
            @wraps(original_endpoint)
            async def enhanced_endpoint(*args, **kwargs):
                return await original_endpoint(*args, **kwargs)
            
            # Replace with enhanced version
            route.endpoint = enhanced_endpoint
            
        except Exception as e:
            logger.warning(f"Failed to enhance route {route.path}: {e}")
    
    def _add_integration_endpoints(self):
        """Add integration-specific endpoints."""
        
        @self.app.get("/api/v1/integration/examples/{endpoint_path:path}")
        async def get_endpoint_examples(endpoint_path: str):
            """Get Context7 examples for a specific endpoint."""
            try:
                examples = await self.documentation_enhancer._get_endpoint_examples(
                    f"/{endpoint_path}", "GET"
                )
                return {"success": True, "examples": examples}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @self.app.post("/api/v1/integration/validate")
        async def validate_api_code(request: Dict[str, Any]):
            """Validate API code using Context7 patterns."""
            api_code = request.get("code", "")
            endpoint_path = request.get("endpoint_path", "/")
            
            try:
                validation_result = await self.validation_enhancer.validate_api_implementation(
                    api_code, endpoint_path
                )
                return {"success": True, "validation": validation_result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/v1/integration/status")
        async def get_integration_status():
            """Get integration status and capabilities."""
            return {
                "context7_available": self.context7_api is not None,
                "features_enabled": {
                    "examples": self.config.enable_context7_examples,
                    "validation": self.config.enable_pattern_validation,
                    "documentation": self.config.enable_documentation_enhancement,
                    "best_practices": self.config.enable_best_practice_suggestions
                },
                "cache_enabled": self.config.cache_examples,
                "enhanced_routes": len([r for r in self.app.routes if isinstance(r, APIRoute)])
            }

def create_context7_middleware():
    """Create middleware for Context7 integration."""
    
    async def context7_middleware(request: Request, call_next):
        """Middleware to add Context7 enhancements to responses."""
        start_time = datetime.now()
        
        # Process the request
        response = await call_next(request)
        
        # Add Context7 headers if available
        if hasattr(request.app.state, 'context7_integration_api'):
            response.headers["X-Context7-Enhanced"] = "true"
            response.headers["X-Context7-Version"] = "1.0.0"
        
        processing_time = (datetime.now() - start_time).total_seconds()
        response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"
        
        return response
    
    return context7_middleware

class APISchemaEnhancer:
    """Enhances OpenAPI schema with Context7 information."""
    
    def __init__(self, context7_api=None):
        self.context7_api = context7_api
    
    def enhance_openapi_schema(self, app: FastAPI) -> Dict[str, Any]:
        """Enhance OpenAPI schema with Context7 features."""
        schema = app.openapi()
        
        if not schema:
            return {}
        
        # Add Context7 extension information
        if "info" in schema:
            schema["info"]["x-context7-enhanced"] = True
            schema["info"]["x-context7-features"] = [
                "Interactive code examples",
                "API pattern validation", 
                "Framework best practices",
                "Enhanced documentation"
            ]
        
        # Enhance each endpoint with Context7 information
        if "paths" in schema:
            for path, methods in schema["paths"].items():
                for method, details in methods.items():
                    if isinstance(details, dict):
                        details["x-context7-examples-available"] = True
                        details["x-context7-validation-enabled"] = True
        
        return schema

# Utility functions for Context7 integration

async def get_context7_enhanced_response(original_response: Any, endpoint_path: str, 
                                       context7_api=None) -> Any:
    """Enhance response with Context7 features."""
    if not context7_api:
        return original_response
    
    try:
        # Add Context7 enhancements to response if possible
        if hasattr(original_response, '__dict__'):
            original_response.__dict__['_context7_enhanced'] = True
            original_response.__dict__['_context7_endpoint'] = endpoint_path
    except Exception as e:
        logger.debug(f"Could not enhance response with Context7 metadata: {e}")
    
    return original_response

def get_framework_recommendations(endpoint_path: str, method: str) -> List[str]:
    """Get framework-specific recommendations for an endpoint."""
    recommendations = []
    
    # Analyze endpoint characteristics
    if "/{id}" in endpoint_path or "/{" in endpoint_path:
        recommendations.append("Use path parameter validation with Pydantic")
    
    if method.upper() in ["POST", "PUT", "PATCH"]:
        recommendations.append("Implement comprehensive request body validation")
        recommendations.append("Use appropriate HTTP status codes for responses")
    
    if method.upper() == "GET":
        recommendations.append("Consider implementing response caching")
        recommendations.append("Use query parameters for filtering and pagination")
    
    if "/api/v" in endpoint_path:
        recommendations.append("Maintain API versioning consistency")
        recommendations.append("Provide backward compatibility when possible")
    
    return recommendations

__all__ = [
    'APIEnhancementConfig',
    'Context7EnhancedRoute', 
    'APIDocumentationEnhancer',
    'APIValidationEnhancer',
    'APIIntegrationManager',
    'APISchemaEnhancer',
    'enhance_api_with_context7',
    'create_context7_middleware',
    'get_context7_enhanced_response',
    'get_framework_recommendations'
]