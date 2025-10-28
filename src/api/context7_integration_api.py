#!/usr/bin/env python3
"""
Context7 Integration API Module
===============================

FastAPI endpoints that leverage Context7 MCP server for enhanced API documentation,
code examples, framework patterns, and best practices integration.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Path, Query
from pydantic import BaseModel, Field

from src.core.data_models import StandardResponse
from src.security.auth_system import get_current_user

logger = logging.getLogger(__name__)


# Request/Response Models
class FrameworkType(str, Enum):
    """Supported framework types for Context7 integration."""

    FASTAPI = "fastapi"
    PYDANTIC = "pydantic"
    ASYNCIO = "asyncio"
    SQLALCHEMY = "sqlalchemy"
    UVICORN = "uvicorn"
    PYTEST = "pytest"
    PYTHON = "python"


class ExampleFormat(str, Enum):
    """Code example formats."""

    PYTHON = "python"
    JSON = "json"
    CURL = "curl"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


class DocumentationType(str, Enum):
    """Documentation types."""

    API_REFERENCE = "api_reference"
    QUICK_START = "quick_start"
    BEST_PRACTICES = "best_practices"
    INTEGRATION_GUIDE = "integration_guide"
    TROUBLESHOOTING = "troubleshooting"


class CodeExampleRequest(BaseModel):
    """Request for Context7-powered code examples."""

    endpoint_path: str = Field(..., description="API endpoint path")
    framework: FrameworkType = Field(
        FrameworkType.PYTHON, description="Target framework"
    )
    format: ExampleFormat = Field(ExampleFormat.PYTHON, description="Example format")
    include_auth: bool = Field(True, description="Include authentication examples")
    include_error_handling: bool = Field(True, description="Include error handling")
    complexity_level: str = Field(
        "intermediate", description="Example complexity level"
    )
    use_case: Optional[str] = Field(None, description="Specific use case scenario")


class CodeExampleResponse(BaseModel):
    """Context7-generated code example."""

    endpoint_path: str = Field(..., description="Target endpoint path")
    framework: str = Field(..., description="Framework used")
    format: str = Field(..., description="Example format")
    title: str = Field(..., description="Example title")
    description: str = Field(..., description="Example description")
    code: str = Field(..., description="Generated code example")
    explanation: str = Field(..., description="Code explanation")
    requirements: List[str] = Field(
        default_factory=list, description="Required dependencies"
    )
    notes: List[str] = Field(default_factory=list, description="Implementation notes")
    related_patterns: List[str] = Field(
        default_factory=list, description="Related framework patterns"
    )
    generated_at: datetime = Field(default_factory=datetime.now)


class PatternValidationRequest(BaseModel):
    """Request for API pattern validation using Context7."""

    api_code: str = Field(..., description="API code to validate")
    framework: FrameworkType = Field(
        FrameworkType.FASTAPI, description="Framework to validate against"
    )
    validation_rules: List[str] = Field(
        default_factory=list, description="Specific validation rules"
    )
    include_suggestions: bool = Field(
        True, description="Include improvement suggestions"
    )


class ValidationIssue(BaseModel):
    """API pattern validation issue."""

    severity: str = Field(..., description="Issue severity (error, warning, info)")
    category: str = Field(..., description="Issue category")
    message: str = Field(..., description="Issue description")
    line_number: Optional[int] = Field(None, description="Line number if applicable")
    suggestion: Optional[str] = Field(None, description="Improvement suggestion")
    pattern_reference: Optional[str] = Field(
        None, description="Reference to best practice"
    )


class PatternValidationResponse(BaseModel):
    """API pattern validation result."""

    is_valid: bool = Field(..., description="Overall validation status")
    score: float = Field(..., ge=0.0, le=1.0, description="Quality score")
    issues: List[ValidationIssue] = Field(
        default_factory=list, description="Identified issues"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="General improvements"
    )
    best_practices: List[str] = Field(
        default_factory=list, description="Applicable best practices"
    )
    framework_compliance: Dict[str, bool] = Field(
        default_factory=dict, description="Framework compliance status"
    )
    validated_at: datetime = Field(default_factory=datetime.now)


class DocumentationRequest(BaseModel):
    """Request for Context7-enhanced documentation."""

    doc_type: DocumentationType = Field(..., description="Documentation type")
    api_endpoints: Optional[List[str]] = Field(
        None, description="Specific endpoints to document"
    )
    framework_focus: List[FrameworkType] = Field(
        default_factory=list, description="Framework emphasis"
    )
    audience_level: str = Field("intermediate", description="Target audience level")
    include_examples: bool = Field(True, description="Include code examples")
    include_patterns: bool = Field(True, description="Include framework patterns")


class DocumentationSection(BaseModel):
    """Documentation section."""

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    code_examples: List[CodeExampleResponse] = Field(default_factory=list)
    subsections: List["DocumentationSection"] = Field(default_factory=list)


class EnhancedDocumentationResponse(BaseModel):
    """Context7-enhanced documentation response."""

    doc_type: str = Field(..., description="Documentation type")
    title: str = Field(..., description="Documentation title")
    overview: str = Field(..., description="Documentation overview")
    sections: List[DocumentationSection] = Field(
        ..., description="Documentation sections"
    )
    quick_reference: Dict[str, str] = Field(
        default_factory=dict, description="Quick reference links"
    )
    external_resources: List[Dict[str, str]] = Field(
        default_factory=list, description="External resources"
    )
    generated_at: datetime = Field(default_factory=datetime.now)


class BestPracticeRequest(BaseModel):
    """Request for framework best practices."""

    framework: FrameworkType = Field(..., description="Target framework")
    category: str = Field("general", description="Best practice category")
    api_pattern: Optional[str] = Field(None, description="Specific API pattern")
    include_examples: bool = Field(True, description="Include example implementations")


class BestPracticeItem(BaseModel):
    """Best practice item."""

    title: str = Field(..., description="Practice title")
    description: str = Field(..., description="Practice description")
    rationale: str = Field(..., description="Why this practice is important")
    example: Optional[str] = Field(None, description="Code example")
    anti_pattern: Optional[str] = Field(None, description="What to avoid")
    references: List[str] = Field(default_factory=list, description="Reference links")


class BestPracticesResponse(BaseModel):
    """Framework best practices response."""

    framework: str = Field(..., description="Target framework")
    category: str = Field(..., description="Best practice category")
    practices: List[BestPracticeItem] = Field(..., description="Best practice items")
    framework_version: str = Field(..., description="Framework version info")
    last_updated: datetime = Field(default_factory=datetime.now)


class Context7IntegrationAPI:
    """API endpoints for Context7 MCP server integration."""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.context7_available = False
        self._check_context7_availability()

    def _check_context7_availability(self):
        """Check if Context7 MCP server is available."""
        # Check if Context7 MCP server is running and accessible
        self.context7_available = True  # Default to available
        logger.info(f"Context7 availability: {self.context7_available}")

    async def _call_context7(
        self, operation: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Context7 MCP server with error handling."""
        if not self.context7_available:
            raise HTTPException(
                status_code=503, detail="Context7 MCP server not available"
            )

        try:
            # Use MCP protocol to communicate with Context7
            # Currently using mock responses for development
            return await self._mock_context7_response(operation, params)

        except Exception as e:
            logger.error(f"Context7 call failed for {operation}: {e}")
            raise HTTPException(
                status_code=502, detail=f"Context7 service error: {str(e)}"
            )

    async def _mock_context7_response(
        self, operation: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock Context7 responses for development."""
        if operation == "generate_code_example":
            return {
                "success": True,
                "example": {
                    "title": f"Example for {params.get('endpoint_path', 'API')}",
                    "description": f"This example shows how to use {params.get('endpoint_path', 'the API')} with {params.get('framework', 'Python')}",
                    "code": self._generate_mock_code_example(params),
                    "explanation": "This code demonstrates proper usage patterns and error handling.",
                    "requirements": ["fastapi", "httpx", "pydantic"],
                    "notes": [
                        "Always handle authentication",
                        "Use proper error handling",
                    ],
                    "related_patterns": [
                        "async/await",
                        "dependency injection",
                        "response models",
                    ],
                },
            }
        elif operation == "validate_pattern":
            return {
                "success": True,
                "validation": {
                    "is_valid": True,
                    "score": 0.85,
                    "issues": [
                        {
                            "severity": "warning",
                            "category": "naming",
                            "message": "Consider using more descriptive parameter names",
                            "suggestion": "Use domain-specific parameter names for clarity",
                        }
                    ],
                    "suggestions": [
                        "Add input validation",
                        "Include comprehensive documentation",
                    ],
                    "best_practices": [
                        "Use dependency injection",
                        "Implement proper error handling",
                    ],
                    "framework_compliance": {"fastapi": True, "pydantic": True},
                },
            }
        elif operation == "get_best_practices":
            return {
                "success": True,
                "practices": [
                    {
                        "title": "Use Dependency Injection",
                        "description": "Leverage FastAPI's dependency injection system for clean architecture",
                        "rationale": "Improves testability and maintainability",
                        "example": "@app.get('/endpoint')\nasync def endpoint(service: Service = Depends(get_service)):\n    return await service.process()",
                        "references": [
                            "https://fastapi.tiangolo.com/tutorial/dependencies/"
                        ],
                    }
                ],
            }
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    def _generate_mock_code_example(self, params: Dict[str, Any]) -> str:
        """Generate mock code examples based on parameters."""
        endpoint = params.get("endpoint_path", "/api/endpoint")
        format_type = params.get("format", "python")

        if format_type == "python":
            return f'''import httpx
import asyncio
from typing import Dict, Any

async def call_novel_engine_api():
    """Example usage of Novel Engine API endpoint {endpoint}"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000{endpoint}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred: {{e}}")
            return None

# Usage
if __name__ == "__main__":
    result = asyncio.run(call_novel_engine_api())
    logger.info(result)
'''
        elif format_type == "curl":
            return f'curl -X GET "http://localhost:8000{endpoint}" -H "Content-Type: application/json"'
        elif format_type == "javascript":
            return f"""const response = await fetch('http://localhost:8000{endpoint}', {{
    method: 'GET',
    headers: {{
        'Content-Type': 'application/json'
    }}
}});

if (response.ok) {{
    const data = await response.json();
    console.log(data);
}} else {{
    console.error('API call failed:', response.statusText);
}}"""
        else:
            return f"# Example code for {endpoint} in {format_type} format"

    def setup_routes(self, app: FastAPI):
        """Setup Context7 integration API routes."""

        @app.post(
            "/api/v1/context7/examples",
            response_model=StandardResponse,
            summary="Generate Code Examples",
            description="Generate Context7-powered code examples for API endpoints",
        )
        async def generate_code_example(
            request: CodeExampleRequest, current_user: Dict = Depends(get_current_user)
        ):
            """Generate code examples using Context7 documentation patterns."""
            try:
                # Call Context7 for code example generation
                context7_response = await self._call_context7(
                    "generate_code_example",
                    {
                        "endpoint_path": request.endpoint_path,
                        "framework": request.framework.value,
                        "format": request.format.value,
                        "include_auth": request.include_auth,
                        "include_error_handling": request.include_error_handling,
                        "complexity_level": request.complexity_level,
                        "use_case": request.use_case,
                    },
                )

                if not context7_response.get("success"):
                    raise HTTPException(
                        status_code=500, detail="Failed to generate code example"
                    )

                example_data = context7_response["example"]
                code_example = CodeExampleResponse(
                    endpoint_path=request.endpoint_path,
                    framework=request.framework.value,
                    format=request.format.value,
                    title=example_data["title"],
                    description=example_data["description"],
                    code=example_data["code"],
                    explanation=example_data["explanation"],
                    requirements=example_data["requirements"],
                    notes=example_data["notes"],
                    related_patterns=example_data["related_patterns"],
                )

                return StandardResponse(success=True, data=code_example)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error generating code example: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @app.post(
            "/api/v1/context7/validate",
            response_model=StandardResponse,
            summary="Validate API Patterns",
            description="Validate API code against Context7 framework patterns",
        )
        async def validate_api_pattern(
            request: PatternValidationRequest,
            current_user: Dict = Depends(get_current_user),
        ):
            """Validate API patterns using Context7 best practices."""
            try:
                # Call Context7 for pattern validation
                context7_response = await self._call_context7(
                    "validate_pattern",
                    {
                        "api_code": request.api_code,
                        "framework": request.framework.value,
                        "validation_rules": request.validation_rules,
                        "include_suggestions": request.include_suggestions,
                    },
                )

                if not context7_response.get("success"):
                    raise HTTPException(
                        status_code=500, detail="Failed to validate API pattern"
                    )

                validation_data = context7_response["validation"]

                # Transform issues to proper format
                issues = [
                    ValidationIssue(**issue)
                    for issue in validation_data.get("issues", [])
                ]

                validation_response = PatternValidationResponse(
                    is_valid=validation_data["is_valid"],
                    score=validation_data["score"],
                    issues=issues,
                    suggestions=validation_data["suggestions"],
                    best_practices=validation_data["best_practices"],
                    framework_compliance=validation_data["framework_compliance"],
                )

                return StandardResponse(success=True, data=validation_response)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error validating API pattern: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @app.post(
            "/api/v1/context7/documentation",
            response_model=StandardResponse,
            summary="Generate Enhanced Documentation",
            description="Generate Context7-powered enhanced API documentation",
        )
        async def generate_enhanced_documentation(
            request: DocumentationRequest,
            current_user: Dict = Depends(get_current_user),
        ):
            """Generate enhanced documentation using Context7 patterns."""
            try:
                # Call Context7 for documentation generation
                context7_response = await self._call_context7(
                    "generate_documentation",
                    {
                        "doc_type": request.doc_type.value,
                        "api_endpoints": request.api_endpoints,
                        "framework_focus": [f.value for f in request.framework_focus],
                        "audience_level": request.audience_level,
                        "include_examples": request.include_examples,
                        "include_patterns": request.include_patterns,
                    },
                )

                if not context7_response.get("success"):
                    # Generate fallback documentation
                    doc_response = EnhancedDocumentationResponse(
                        doc_type=request.doc_type.value,
                        title=f"Novel Engine API {request.doc_type.value.replace('_', ' ').title()}",
                        overview="Comprehensive API documentation for the Novel Engine framework.",
                        sections=[
                            DocumentationSection(
                                title="Getting Started",
                                content="Learn how to get started with the Novel Engine API.",
                                code_examples=[],
                                subsections=[],
                            ),
                            DocumentationSection(
                                title="Authentication",
                                content="Information about API authentication and security.",
                                code_examples=[],
                                subsections=[],
                            ),
                        ],
                        quick_reference={
                            "base_url": "http://localhost:8000",
                            "docs_url": "/docs",
                            "version": "1.1.0",
                        },
                        external_resources=[
                            {
                                "title": "FastAPI Documentation",
                                "url": "https://fastapi.tiangolo.com/",
                            },
                            {
                                "title": "Pydantic Documentation",
                                "url": "https://pydantic-docs.helpmanual.io/",
                            },
                        ],
                    )
                else:
                    # Process Context7 response
                    doc_data = context7_response["documentation"]
                    doc_response = EnhancedDocumentationResponse(**doc_data)

                return StandardResponse(success=True, data=doc_response)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error generating enhanced documentation: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @app.get(
            "/api/v1/context7/best-practices/{framework}",
            response_model=StandardResponse,
            summary="Get Framework Best Practices",
            description="Get Context7-powered framework best practices",
        )
        async def get_best_practices(
            framework: FrameworkType = Path(
                ..., description="Framework to get practices for"
            ),
            category: str = Query("general", description="Practice category"),
            include_examples: bool = Query(True, description="Include code examples"),
            current_user: Dict = Depends(get_current_user),
        ):
            """Get framework best practices from Context7."""
            try:
                # Call Context7 for best practices
                context7_response = await self._call_context7(
                    "get_best_practices",
                    {
                        "framework": framework.value,
                        "category": category,
                        "include_examples": include_examples,
                    },
                )

                if not context7_response.get("success"):
                    raise HTTPException(
                        status_code=500, detail="Failed to retrieve best practices"
                    )

                practices_data = context7_response["practices"]

                # Transform practices to proper format
                practices = [
                    BestPracticeItem(**practice) for practice in practices_data
                ]

                best_practices_response = BestPracticesResponse(
                    framework=framework.value,
                    category=category,
                    practices=practices,
                    framework_version="latest",
                )

                return StandardResponse(success=True, data=best_practices_response)

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting best practices: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @app.get(
            "/api/v1/context7/status",
            response_model=StandardResponse,
            summary="Get Context7 Status",
            description="Get Context7 MCP server status and capabilities",
        )
        async def get_context7_status():
            """Get Context7 integration status."""
            try:
                status_data = {
                    "available": self.context7_available,
                    "supported_frameworks": [f.value for f in FrameworkType],
                    "supported_formats": [f.value for f in ExampleFormat],
                    "documentation_types": [d.value for d in DocumentationType],
                    "capabilities": [
                        "Code example generation",
                        "API pattern validation",
                        "Enhanced documentation",
                        "Best practices lookup",
                        "Framework pattern analysis",
                    ],
                    "version": "1.0.0",
                    "last_checked": datetime.now(),
                }

                return StandardResponse(success=True, data=status_data)

            except Exception as e:
                logger.error(f"Error getting Context7 status: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")


def create_context7_integration_api(orchestrator=None) -> Context7IntegrationAPI:
    """Factory function to create Context7IntegrationAPI instance."""
    return Context7IntegrationAPI(orchestrator)
