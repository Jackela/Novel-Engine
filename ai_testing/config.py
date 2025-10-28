"""
AI Testing Framework Configuration
Handles environment-specific settings for local, Docker, and cloud deployments
"""

import os
from enum import Enum
from typing import Dict


class Environment(Enum):
    """Deployment environment types"""
    LOCAL = "local"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    CLOUD = "cloud"

class ServiceConfig:
    """Service configuration management"""
    
    @staticmethod
    def detect_environment() -> Environment:
        """Detect current deployment environment"""
        # Check for Docker environment
        if os.path.exists("/.dockerenv"):
            return Environment.DOCKER
        
        # Check for Kubernetes
        if os.environ.get("KUBERNETES_SERVICE_HOST"):
            return Environment.KUBERNETES
        
        # Check for cloud environments
        if os.environ.get("CLOUD_PROVIDER"):
            return Environment.CLOUD
        
        # Default to local
        return Environment.LOCAL
    
    @staticmethod
    def get_service_urls() -> Dict[str, str]:
        """Get service URLs based on environment"""
        env = ServiceConfig.detect_environment()
        
        if env == Environment.LOCAL:
            # Local development URLs
            return {
                "orchestrator": "http://localhost:8000",
                "browser-automation": "http://localhost:8001",
                "api-testing": "http://localhost:8002",
                "ai-quality": "http://localhost:8003",
                "results-aggregation": "http://localhost:8004",
                "notification": "http://localhost:8005"
            }
        elif env == Environment.DOCKER:
            # Docker service names
            return {
                "orchestrator": "http://orchestrator:8000",
                "browser-automation": "http://browser-automation:8001",
                "api-testing": "http://api-testing:8002",
                "ai-quality": "http://ai-quality:8003",
                "results-aggregation": "http://results-aggregation:8004",
                "notification": "http://notification:8005"
            }
        else:
            # Kubernetes or cloud - use service discovery
            base_domain = os.environ.get("SERVICE_DOMAIN", "ai-testing.local")
            return {
                "orchestrator": f"http://orchestrator.{base_domain}:8000",
                "browser-automation": f"http://browser-automation.{base_domain}:8001",
                "api-testing": f"http://api-testing.{base_domain}:8002",
                "ai-quality": f"http://ai-quality.{base_domain}:8003",
                "results-aggregation": f"http://results-aggregation.{base_domain}:8004",
                "notification": f"http://notification.{base_domain}:8005"
            }
    
    @staticmethod
    def get_service_url(service_name: str) -> str:
        """Get URL for a specific service"""
        urls = ServiceConfig.get_service_urls()
        # Handle both hyphenated and underscored names
        normalized_name = service_name.replace("_", "-")
        return urls.get(normalized_name, "http://localhost:8000")
    
    @staticmethod
    def get_base_url() -> str:
        """Get base URL for the orchestrator"""
        env = ServiceConfig.detect_environment()
        if env == Environment.LOCAL:
            return "http://localhost"
        elif env == Environment.DOCKER:
            return "http://orchestrator"
        else:
            return os.environ.get("BASE_URL", "http://localhost")
    
    @staticmethod
    def get_service_ports() -> Dict[str, int]:
        """Get service port mappings"""
        return {
            "orchestrator": 8000,
            "browser-automation": 8001,
            "api-testing": 8002,
            "ai-quality": 8003,
            "results-aggregation": 8004,
            "notification": 8005
        }

# Convenience functions
def get_environment() -> Environment:
    """Get current environment"""
    return ServiceConfig.detect_environment()

def get_service_url(service: str) -> str:
    """Get URL for a service"""
    return ServiceConfig.get_service_url(service)

def get_all_service_urls() -> Dict[str, str]:
    """Get all service URLs"""
    return ServiceConfig.get_service_urls()

def is_local_environment() -> bool:
    """Check if running in local environment"""
    return ServiceConfig.detect_environment() == Environment.LOCAL

def is_docker_environment() -> bool:
    """Check if running in Docker environment"""
    return ServiceConfig.detect_environment() == Environment.DOCKER