"""Narrative Infrastructure Layer.

This module contains infrastructure adapters for the Narrative bounded context.
These adapters implement the ports defined in the application layer.

Why this structure:
    Infrastructure adapters handle the technical details of persistence,
    messaging, and external service integration. They implement the ports
    (interfaces) defined by the application layer, keeping the domain
    isolated from infrastructure concerns.
"""
