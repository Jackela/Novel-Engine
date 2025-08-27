#!/usr/bin/env python3
"""
Application Services Package for Interaction Domain

This package contains high-level application services that orchestrate
business operations across the Interaction bounded context.

Key Services:
- InteractionApplicationService: Main orchestration service for negotiation workflows
"""

from .interaction_application_service import InteractionApplicationService

__all__ = [
    'InteractionApplicationService'
]

__version__ = "1.0.0"
