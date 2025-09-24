"""
AI Services Platform Component
=============================

Platform service for LLM integration, AI orchestration, and machine learning
capabilities shared across all application services.

Platform Responsibilities:
- LLM provider integration and orchestration
- AI model management and deployment
- Prompt engineering and template management
- AI request routing and load balancing
- AI performance monitoring and optimization

Architecture: Platform service providing AI capabilities to all applications
Usage: Consumed by story-engine, character-service, and other AI-dependent services
"""

__version__ = "1.0.0"
__platform_service__ = "ai-services"
__description__ = "AI and LLM Integration Platform Service"
