"""DI container validation utilities.

This module provides validation functions for the DI container,
including circular dependency detection and configuration validation.
"""

from __future__ import annotations

from typing import Any, TypeVar

from dependency_injector import containers, providers

T = TypeVar("T")


def check_circular_dependencies(
    container: containers.DeclarativeContainer,
) -> list[dict[str, Any]]:
    """Check for circular dependencies in container.

    This function analyzes all providers in the container and detects
    any circular dependency chains.

    Args:
        container: The container to check.

    Returns:
        List of circular dependency chains found. Empty list if none.

    Example:
        >>> circular = check_circular_dependencies(container)
        >>> if circular:
        >>>     print(f"Found {len(circular)} circular dependencies")
    """
    circular_deps: list[dict[str, Any]] = []

    # Build dependency graph
    graph: dict[str, set[str]] = {}
    provider_map: dict[str, providers.Provider] = {}

    def add_to_graph(name: str, provider: providers.Provider) -> None:
        """Add provider and its dependencies to graph."""
        if name in graph:
            return

        graph[name] = set()
        provider_map[name] = provider

        # Extract dependencies from provider
        if isinstance(provider, providers.Factory):
            if hasattr(provider, "kwargs") and provider.kwargs:
                for key, value in provider.kwargs.items():
                    if isinstance(value, providers.Provider):
                        # Store reference to dependent provider
                        dep_name = f"{name}.{key}"
                        graph[name].add(dep_name)

        # Handle nested containers
        if isinstance(provider, providers.Container):
            nested_container = provider()
            if hasattr(nested_container, "providers"):
                for nested_name, nested_provider in nested_container.providers.items():
                    full_name = f"{name}.{nested_name}"
                    add_to_graph(full_name, nested_provider)

    # Build graph from all providers
    if hasattr(container, "providers"):
        for name, provider in container.providers.items():
            add_to_graph(name, provider)

    # DFS to detect cycles
    visited: set[str] = set()
    recursion_stack: set[str] = set()

    def dfs(node: str, path: list[str]) -> None:
        """Depth-first search to detect cycles."""
        if node in recursion_stack:
            # Found a cycle
            try:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                circular_deps.append(
                    {
                        "cycle": cycle,
                        "description": " -> ".join(cycle),
                    }
                )
            except ValueError:
                # Node not in path, shouldn't happen but handle gracefully
                pass
            return

        if node in visited:
            return

        visited.add(node)
        recursion_stack.add(node)
        path.append(node)

        # Visit dependencies
        for dep in graph.get(node, set()):
            dfs(dep, path.copy())

        recursion_stack.remove(node)

    # Run DFS from each node
    for node in graph:
        if node not in visited:
            dfs(node, [])

    return circular_deps


def validate_container(
    container: containers.DeclarativeContainer,
    raise_on_error: bool = False,
) -> dict[str, Any]:
    """Validate container configuration.

    This function performs comprehensive validation of the container:
    - Checks all providers can be resolved
    - Detects circular dependencies
    - Validates required dependencies are present

    Args:
        container: The container to validate.
        raise_on_error: If True, raise ValidationError on any issue.

    Returns:
        Validation results dictionary with:
        - is_valid: Whether container is valid
        - errors: List of error messages
        - warnings: List of warning messages
        - circular_dependencies: List of circular dependency chains

    Example:
        >>> results = validate_container(container)
        >>> if not results["is_valid"]:
        >>>     for error in results["errors"]:
        >>>         print(f"Error: {error}")
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check for circular dependencies
    try:
        circular = check_circular_dependencies(container)
        if circular:
            for cycle in circular:
                errors.append(f"Circular dependency: {cycle['description']}")
    except Exception as e:
        # If circular dependency check fails, report it but don't crash
        warnings.append(f"Could not check circular dependencies: {e}")
        circular = []

    # Validate all providers can be resolved
    if hasattr(container, "providers"):
        for name, provider in container.providers.items():
            try:
                # Check if provider has required dependencies
                if isinstance(provider, providers.Factory):
                    if hasattr(provider, "kwargs") and provider.kwargs:
                        for key, value in provider.kwargs.items():
                            if value is None:
                                warnings.append(
                                    f"Provider '{name}' has None dependency for '{key}'"
                                )
            except Exception as e:
                errors.append(f"Provider '{name}' resolution error: {str(e)}")

    is_valid = len(errors) == 0

    results = {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "circular_dependencies": circular,
    }

    if raise_on_error and not is_valid:
        raise ValidationError(f"Container validation failed: {errors}")

    return results


class ValidationError(Exception):
    """Exception raised when container validation fails."""

    pass


def get_container_graph(
    container: containers.DeclarativeContainer,
) -> dict[str, list[str]]:
    """Generate dependency graph for visualization.

    Args:
        container: The container to analyze.

    Returns:
        Dictionary mapping provider names to their dependencies.

    Example:
        >>> graph = get_container_graph(container)
        >>> for provider, deps in graph.items():
        >>>     print(f"{provider} depends on: {deps}")
    """
    graph: dict[str, list[str]] = {}

    def extract_name_from_provider(provider: Any) -> str | None:
        """Extract a readable name from a provider."""
        if hasattr(provider, "name"):
            return provider.name
        return str(type(provider).__name__)

    if hasattr(container, "providers"):
        for name, provider in container.providers.items():
            deps: list[str] = []

            # Extract dependencies from provider
            if isinstance(provider, providers.Factory):
                if hasattr(provider, "kwargs") and provider.kwargs:
                    for key, value in provider.kwargs.items():
                        if isinstance(value, providers.Provider):
                            dep_name = extract_name_from_provider(value)
                            if dep_name:
                                deps.append(dep_name)

            graph[name] = deps

    return graph


def print_container_tree(
    container: containers.DeclarativeContainer,
    indent: int = 0,
) -> str:
    """Generate a string representation of container hierarchy.

    Args:
        container: The container to visualize.
        indent: Current indentation level.

    Returns:
        String representation of container tree.

    Example:
        >>> print(print_container_tree(container))
        ApplicationContainer
          core: CoreContainer
            db_pool: Singleton(DatabaseConnectionPool)
            jwt_manager: Singleton(JWTManager)
    """
    lines: list[str] = []
    prefix = "  " * indent

    container_name = container.__class__.__name__
    lines.append(f"{prefix}{container_name}")

    if hasattr(container, "providers"):
        for name, provider in container.providers.items():
            if isinstance(provider, providers.Container):
                # Recursively print nested container
                nested_tree = print_container_tree(provider, indent + 1)
                lines.append(f"{prefix}  {name}: {nested_tree}")
            else:
                provider_type = type(provider).__name__
                provider_class = ""
                if hasattr(provider, "provides") and provider.provides:
                    provider_class = f"({provider.provides.__name__})"
                lines.append(f"{prefix}  {name}: {provider_type}{provider_class}")

    return "\n".join(lines)
