"""Narrative Application Layer.

This module contains the application services and ports for the Narrative
bounded context. It orchestrates domain operations and defines the interfaces
that infrastructure adapters must implement.

Why this structure:
    The application layer sits between the domain and infrastructure layers
    in hexagonal architecture. It contains use cases (services) and ports
    (interfaces) that allow the domain to remain isolated from external
    concerns.
"""
