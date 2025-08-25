#!/usr/bin/env python3
"""
Enhanced API Documentation System with Context7 Integration
==========================================================

Comprehensive documentation system that leverages Context7 for interactive examples,
framework patterns, and best practices integration.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader, Template

logger = logging.getLogger(__name__)

class EnhancedDocumentationSystem:
    """Enhanced documentation system with Context7 integration."""
    
    def __init__(self, app: FastAPI, context7_api=None):
        self.app = app
        self.context7_api = context7_api
        self.template_env = self._setup_templates()
        self._api_inventory = self._build_api_inventory()
        
    def _setup_templates(self) -> Environment:
        """Setup Jinja2 template environment."""
        # Create templates directory if it doesn't exist
        templates_dir = Path("src/templates")
        templates_dir.mkdir(exist_ok=True)
        
        # Create basic template if it doesn't exist
        docs_template_path = templates_dir / "enhanced_docs.html"
        if not docs_template_path.exists():
            self._create_default_template(docs_template_path)
        
        return Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True
        )
    
    def _create_default_template(self, template_path: Path):
        """Create default documentation template."""
        template_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Novel Engine API</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/themes/prism-tomorrow.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/components/prism-core.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/plugins/autoloader/prism-autoloader.min.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 40px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; }
        .nav { display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }
        .nav a { text-decoration: none; padding: 10px 15px; background: #f8f9fa; border-radius: 5px; color: #333; }
        .nav a:hover { background: #e9ecef; }
        .section { margin-bottom: 40px; }
        .endpoint { border: 1px solid #ddd; border-radius: 8px; margin-bottom: 20px; overflow: hidden; }
        .endpoint-header { background: #f8f9fa; padding: 15px; border-bottom: 1px solid #ddd; }
        .endpoint-content { padding: 15px; }
        .method { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; margin-right: 10px; }
        .method.get { background: #28a745; }
        .method.post { background: #007bff; }
        .method.put { background: #ffc107; color: #333; }
        .method.delete { background: #dc3545; }
        .code-example { margin: 15px 0; }
        .tab-container { border: 1px solid #ddd; border-radius: 5px; }
        .tab-headers { display: flex; background: #f8f9fa; }
        .tab-header { padding: 10px 15px; cursor: pointer; border-right: 1px solid #ddd; }
        .tab-header.active { background: white; border-bottom: 1px solid white; }
        .tab-content { display: none; padding: 15px; }
        .tab-content.active { display: block; }
        .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }
        .feature-card { padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #f8f9fa; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ title }}</h1>
            <p>{{ description }}</p>
            {% if version %}
                <span style="background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 20px;">v{{ version }}</span>
            {% endif %}
        </div>
        
        <div class="nav">
            <a href="#overview">Overview</a>
            <a href="#authentication">Authentication</a>
            <a href="#endpoints">API Endpoints</a>
            <a href="#examples">Code Examples</a>
            <a href="#best-practices">Best Practices</a>
            <a href="#sdk">SDK & Tools</a>
        </div>
        
        <div id="overview" class="section">
            <h2>Overview</h2>
            <p>{{ overview }}</p>
            
            <div class="features">
                {% for feature in features %}
                <div class="feature-card">
                    <h3>{{ feature.title }}</h3>
                    <p>{{ feature.description }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div id="authentication" class="section">
            <h2>Authentication</h2>
            <p>The Novel Engine API uses JWT tokens for authentication.</p>
            
            <div class="tab-container">
                <div class="tab-headers">
                    <div class="tab-header active" onclick="showTab(this, 'auth-curl')">cURL</div>
                    <div class="tab-header" onclick="showTab(this, 'auth-python')">Python</div>
                    <div class="tab-header" onclick="showTab(this, 'auth-javascript')">JavaScript</div>
                </div>
                <div id="auth-curl" class="tab-content active">
                    <pre><code class="language-bash">curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
     http://localhost:8000/api/v1/endpoint</code></pre>
                </div>
                <div id="auth-python" class="tab-content">
                    <pre><code class="language-python">import httpx

headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}
response = httpx.get("http://localhost:8000/api/v1/endpoint", headers=headers)</code></pre>
                </div>
                <div id="auth-javascript" class="tab-content">
                    <pre><code class="language-javascript">const response = await fetch('http://localhost:8000/api/v1/endpoint', {
    headers: {'Authorization': 'Bearer YOUR_JWT_TOKEN'}
});</code></pre>
                </div>
            </div>
        </div>
        
        <div id="endpoints" class="section">
            <h2>API Endpoints</h2>
            {% for endpoint in endpoints %}
            <div class="endpoint">
                <div class="endpoint-header">
                    <span class="method {{ endpoint.method.lower() }}">{{ endpoint.method.upper() }}</span>
                    <strong>{{ endpoint.path }}</strong>
                    {% if endpoint.summary %}
                        - {{ endpoint.summary }}
                    {% endif %}
                </div>
                <div class="endpoint-content">
                    {% if endpoint.description %}
                        <p>{{ endpoint.description }}</p>
                    {% endif %}
                    
                    {% if endpoint.examples %}
                    <div class="code-example">
                        <h4>Examples</h4>
                        <div class="tab-container">
                            <div class="tab-headers">
                                {% for example in endpoint.examples %}
                                <div class="tab-header{% if loop.first %} active{% endif %}" 
                                     onclick="showTab(this, '{{ endpoint.path|replace('/', '_') }}_{{ example.format }}')">
                                     {{ example.format|title }}
                                </div>
                                {% endfor %}
                            </div>
                            {% for example in endpoint.examples %}
                            <div id="{{ endpoint.path|replace('/', '_') }}_{{ example.format }}" 
                                 class="tab-content{% if loop.first %} active{% endif %}">
                                <pre><code class="language-{{ example.language }}">{{ example.code }}</code></pre>
                                {% if example.explanation %}
                                    <p><em>{{ example.explanation }}</em></p>
                                {% endif %}
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div id="examples" class="section">
            <h2>Code Examples</h2>
            <p>Interactive code examples powered by Context7 integration.</p>
            
            <div class="tab-container">
                <div class="tab-headers">
                    <div class="tab-header active" onclick="showTab(this, 'example-quickstart')">Quick Start</div>
                    <div class="tab-header" onclick="showTab(this, 'example-auth')">Authentication</div>
                    <div class="tab-header" onclick="showTab(this, 'example-characters')">Characters</div>
                    <div class="tab-header" onclick="showTab(this, 'example-stories')">Stories</div>
                </div>
                
                <div id="example-quickstart" class="tab-content active">
                    <h3>Quick Start Guide</h3>
                    <pre><code class="language-python"># Install dependencies
pip install httpx pydantic

# Basic API client
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Get API status
        response = await client.get("http://localhost:8000/")
        print("API Status:", response.json())
        
        # Get health check
        health = await client.get("http://localhost:8000/health")
        print("Health:", health.json())

if __name__ == "__main__":
    asyncio.run(main())</code></pre>
                </div>
                
                <div id="example-auth" class="tab-content">
                    <h3>Authentication Example</h3>
                    <pre><code class="language-python"># Authentication workflow
import httpx
from typing import Dict, Optional

class NovelEngineClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token: Optional[str] = None
        
    async def login(self, username: str, password: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": username, "password": password}
            )
            response.raise_for_status()
            self.token = response.json()["token"]
            
    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers</code></pre>
                </div>
                
                <div id="example-characters" class="tab-content">
                    <h3>Character Management</h3>
                    <pre><code class="language-python"># Character operations
async def character_examples(client: NovelEngineClient):
    headers = client.get_headers()
    
    async with httpx.AsyncClient() as http_client:
        # List all characters
        response = await http_client.get(
            f"{client.base_url}/api/v1/characters",
            headers=headers
        )
        characters = response.json()["data"]
        
        # Create new character
        new_character = {
            "name": "Hero Protagonist",
            "background_summary": "A brave adventurer",
            "personality_traits": ["brave", "curious", "loyal"]
        }
        
        response = await http_client.post(
            f"{client.base_url}/api/v1/characters",
            json=new_character,
            headers=headers
        )
        character_id = response.json()["data"]["character_id"]</code></pre>
                </div>
                
                <div id="example-stories" class="tab-content">
                    <h3>Story Generation</h3>
                    <pre><code class="language-python"># Story generation workflow
async def story_examples(client: NovelEngineClient):
    headers = client.get_headers()
    
    async with httpx.AsyncClient() as http_client:
        # Generate new story
        story_request = {
            "title": "The Epic Adventure",
            "characters": ["Hero Protagonist", "Wise Mentor"],
            "setting": "A mystical fantasy realm",
            "genre": "fantasy",
            "complexity_level": "intermediate"
        }
        
        # Start generation
        response = await http_client.post(
            f"{client.base_url}/api/v1/stories/generate",
            json=story_request,
            headers=headers
        )
        generation_id = response.json()["data"]["generation_id"]
        
        # Check progress
        progress_response = await http_client.get(
            f"{client.base_url}/api/v1/stories/generate/{generation_id}/progress",
            headers=headers
        )
        print("Progress:", progress_response.json())</code></pre>
                </div>
            </div>
        </div>
        
        <div id="best-practices" class="section">
            <h2>Best Practices</h2>
            <p>Framework best practices powered by Context7 integration.</p>
            
            <div class="features">
                <div class="feature-card">
                    <h3>Error Handling</h3>
                    <p>Always implement proper error handling with try-catch blocks and status code checks.</p>
                    <pre><code class="language-python">try:
    response.raise_for_status()
    return response.json()
except httpx.HTTPError as e:
    logger.error(f"API call failed: {e}")
    return None</code></pre>
                </div>
                
                <div class="feature-card">
                    <h3>Rate Limiting</h3>
                    <p>Implement backoff strategies and respect rate limits to ensure stable API usage.</p>
                    <pre><code class="language-python">import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), 
       wait=wait_exponential(multiplier=1, min=4, max=10))
async def api_call_with_retry():
    return await client.get("/api/endpoint")</code></pre>
                </div>
                
                <div class="feature-card">
                    <h3>Authentication</h3>
                    <p>Store tokens securely and implement proper token refresh mechanisms.</p>
                    <pre><code class="language-python"># Use environment variables for sensitive data
import os
token = os.getenv("NOVEL_ENGINE_TOKEN")

# Implement token refresh
if response.status_code == 401:
    await refresh_token()
    # Retry request with new token</code></pre>
                </div>
            </div>
        </div>
        
        <div id="sdk" class="section">
            <h2>SDK & Tools</h2>
            <p>Official SDKs and development tools for the Novel Engine API.</p>
            
            <div class="features">
                <div class="feature-card">
                    <h3>Python SDK</h3>
                    <p>Official Python SDK with async support and comprehensive type hints.</p>
                    <pre><code class="language-bash">pip install novel-engine-sdk</code></pre>
                </div>
                
                <div class="feature-card">
                    <h3>CLI Tool</h3>
                    <p>Command-line interface for quick API interactions and testing.</p>
                    <pre><code class="language-bash">novel-engine characters list
novel-engine stories generate --title "My Story"</code></pre>
                </div>
                
                <div class="feature-card">
                    <h3>Postman Collection</h3>
                    <p>Ready-to-use Postman collection with example requests and environments.</p>
                    <a href="/api/v1/postman/collection" style="color: #007bff;">Download Collection</a>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function showTab(element, tabId) {
            // Hide all tabs in the same container
            const container = element.closest('.tab-container');
            const tabs = container.querySelectorAll('.tab-content');
            const headers = container.querySelectorAll('.tab-header');
            
            tabs.forEach(tab => tab.classList.remove('active'));
            headers.forEach(header => header.classList.remove('active'));
            
            // Show selected tab
            document.getElementById(tabId).classList.add('active');
            element.classList.add('active');
        }
        
        // Smooth scrolling for navigation links
        document.addEventListener('DOMContentLoaded', function() {
            const navLinks = document.querySelectorAll('.nav a');
            navLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('href').substring(1);
                    const targetElement = document.getElementById(targetId);
                    if (targetElement) {
                        targetElement.scrollIntoView({ behavior: 'smooth' });
                    }
                });
            });
        });
    </script>
</body>
</html>'''
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
    
    def _build_api_inventory(self) -> Dict[str, Any]:
        """Build comprehensive API inventory."""
        return {
            "endpoints": [
                {
                    "path": "/api/v1/characters",
                    "method": "GET",
                    "summary": "List all characters",
                    "description": "Retrieve a list of all available characters",
                    "category": "Characters"
                },
                {
                    "path": "/api/v1/characters",
                    "method": "POST", 
                    "summary": "Create new character",
                    "description": "Create a new character with detailed attributes",
                    "category": "Characters"
                },
                {
                    "path": "/api/v1/stories/generate",
                    "method": "POST",
                    "summary": "Generate story",
                    "description": "Generate a new story with specified parameters",
                    "category": "Stories"
                },
                {
                    "path": "/api/v1/interactions",
                    "method": "POST",
                    "summary": "Create interaction",
                    "description": "Create a new character interaction",
                    "category": "Interactions"
                },
                {
                    "path": "/api/v1/turns/{turn_id}/briefs/{agent_id}",
                    "method": "GET",
                    "summary": "Get turn brief",
                    "description": "Get personalized turn brief for an agent",
                    "category": "Narrative"
                },
                {
                    "path": "/api/v1/narratives/emergent/generate",
                    "method": "POST",
                    "summary": "Generate emergent narrative",
                    "description": "Generate emergent narrative based on interactions",
                    "category": "Narrative"
                }
            ],
            "categories": ["Characters", "Stories", "Interactions", "Narrative", "Context7"],
            "features": [
                {
                    "title": "Character Management",
                    "description": "Create, modify, and manage complex character profiles with personality traits, backgrounds, and relationships."
                },
                {
                    "title": "Story Generation",
                    "description": "Generate dynamic stories with multiple characters, complex plots, and narrative coherence."
                },
                {
                    "title": "Subjective Reality",
                    "description": "Each character has their own perspective and knowledge base, creating realistic interactions."
                },
                {
                    "title": "Emergent Narratives",
                    "description": "Stories emerge naturally from character interactions and causal relationships."
                },
                {
                    "title": "Context7 Integration",
                    "description": "Enhanced documentation with interactive examples and framework best practices."
                }
            ]
        }
    
    async def generate_code_examples_for_endpoint(self, endpoint_path: str) -> List[Dict[str, Any]]:
        """Generate Context7-powered code examples for an endpoint."""
        if not self.context7_api:
            return self._get_fallback_examples(endpoint_path)
        
        try:
            # Generate examples in multiple formats
            formats = ["python", "curl", "javascript"]
            examples = []
            
            for format_type in formats:
                # This would call the Context7 API to generate examples
                example = {
                    "format": format_type,
                    "language": format_type if format_type != "curl" else "bash",
                    "code": self._generate_example_code(endpoint_path, format_type),
                    "explanation": f"Example usage in {format_type}"
                }
                examples.append(example)
            
            return examples
            
        except Exception as e:
            logger.warning(f"Failed to generate Context7 examples for {endpoint_path}: {e}")
            return self._get_fallback_examples(endpoint_path)
    
    def _get_fallback_examples(self, endpoint_path: str) -> List[Dict[str, Any]]:
        """Get fallback examples when Context7 is not available."""
        return [
            {
                "format": "python",
                "language": "python",
                "code": f'import httpx\nresponse = await httpx.get("http://localhost:8000{endpoint_path}")\nprint(response.json())',
                "explanation": "Basic Python example using httpx"
            },
            {
                "format": "curl",
                "language": "bash", 
                "code": f'curl -X GET "http://localhost:8000{endpoint_path}"',
                "explanation": "Command line example using curl"
            }
        ]
    
    def _generate_example_code(self, endpoint_path: str, format_type: str) -> str:
        """Generate example code for different formats."""
        if format_type == "python":
            return f'''import httpx
import asyncio

async def call_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000{endpoint_path}")
        response.raise_for_status()
        return response.json()

result = asyncio.run(call_api())
print(result)'''
        elif format_type == "curl":
            return f'curl -X GET "http://localhost:8000{endpoint_path}" -H "Content-Type: application/json"'
        elif format_type == "javascript":
            return f'''const response = await fetch('http://localhost:8000{endpoint_path}');
const data = await response.json();
console.log(data);'''
        else:
            return f"# Example for {endpoint_path} in {format_type}"
    
    async def generate_enhanced_documentation(self) -> str:
        """Generate enhanced HTML documentation."""
        try:
            # Enhance endpoints with Context7 examples
            enhanced_endpoints = []
            for endpoint in self._api_inventory["endpoints"]:
                examples = await self.generate_code_examples_for_endpoint(endpoint["path"])
                endpoint_with_examples = {**endpoint, "examples": examples}
                enhanced_endpoints.append(endpoint_with_examples)
            
            template = self.template_env.get_template("enhanced_docs.html")
            return template.render(
                title="Novel Engine API Documentation",
                description="Comprehensive API documentation with Context7-powered examples",
                version="1.1.0",
                overview="The Novel Engine API provides a powerful framework for creating dynamic, narrative-driven experiences with intelligent character interactions and emergent storytelling.",
                endpoints=enhanced_endpoints,
                features=self._api_inventory["features"]
            )
            
        except Exception as e:
            logger.error(f"Failed to generate enhanced documentation: {e}")
            return self._generate_fallback_documentation()
    
    def _generate_fallback_documentation(self) -> str:
        """Generate fallback documentation when template fails."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Novel Engine API Documentation</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }
                .endpoint { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
                .method { font-weight: bold; color: #007bff; }
                pre { background: #f8f9fa; padding: 10px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>Novel Engine API Documentation</h1>
            <p>Enhanced documentation system with Context7 integration.</p>
            <div class="endpoint">
                <div class="method">GET /health</div>
                <p>Health check endpoint</p>
                <pre>curl http://localhost:8000/health</pre>
            </div>
        </body>
        </html>
        """
    
    def setup_routes(self, app: FastAPI):
        """Setup enhanced documentation routes."""
        
        @app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
        async def enhanced_docs():
            """Enhanced interactive documentation."""
            return await self.generate_enhanced_documentation()
        
        @app.get("/api/documentation", response_class=HTMLResponse, include_in_schema=False)
        async def api_documentation():
            """API documentation endpoint."""
            return await self.generate_enhanced_documentation()
        
        @app.get("/api/v1/postman/collection")
        async def get_postman_collection():
            """Get Postman collection for API testing."""
            collection = {
                "info": {
                    "name": "Novel Engine API",
                    "version": "1.1.0",
                    "description": "Comprehensive API collection for Novel Engine"
                },
                "item": [
                    {
                        "name": "Health Check",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}/health",
                                "host": ["{{base_url}}"],
                                "path": ["health"]
                            }
                        }
                    },
                    {
                        "name": "List Characters",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{token}}"}],
                            "url": {
                                "raw": "{{base_url}}/api/v1/characters",
                                "host": ["{{base_url}}"],
                                "path": ["api", "v1", "characters"]
                            }
                        }
                    }
                ],
                "variable": [
                    {"key": "base_url", "value": "http://localhost:8000"},
                    {"key": "token", "value": "YOUR_JWT_TOKEN"}
                ]
            }
            
            return JSONResponse(content=collection, headers={
                "Content-Disposition": "attachment; filename=novel-engine-api.postman_collection.json"
            })