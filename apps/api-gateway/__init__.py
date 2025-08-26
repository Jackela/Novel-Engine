"""
API Gateway Service
==================

Main API orchestration and routing service for the Novel Engine.
Provides unified API entry point, request routing, authentication,
and cross-service communication coordination.

Responsibilities:
- API request routing and orchestration
- Authentication and authorization
- Rate limiting and request validation
- Service discovery and load balancing
- API versioning and backward compatibility

Architecture: Central API gateway with service mesh capabilities
"""

__version__ = "1.0.0"
__service_name__ = "api-gateway"
__description__ = "API Gateway and Orchestration Service"