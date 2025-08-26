"""
Platform Validation Package
===========================

Comprehensive validation and health checking for Novel Engine platform services.
End-to-end validation for M2: Platform Foundation milestone completion.
"""

from .e2e_platform_validator import PlatformValidator, ValidationResult, ComponentStatus

__version__ = "1.0.0"
__platform_service__ = "validation"
__description__ = "Platform Foundation Validation and Health Checking"

__all__ = [
    "PlatformValidator", 
    "ValidationResult", 
    "ComponentStatus"
]