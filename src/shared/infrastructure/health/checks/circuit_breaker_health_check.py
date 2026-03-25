"""Health check for circuit breakers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.shared.infrastructure.circuit_breaker import CircuitBreakerRegistry


@dataclass
class HealthStatus:
    """Health status result."""

    status: str
    message: str
    details: dict[str, Any] | None = None


class CircuitBreakerHealthCheck:
    """Check circuit breaker states."""

    async def check(self) -> dict[str, Any]:
        """Check circuit breaker states."""
        try:
            states = CircuitBreakerRegistry.get_all_states()

            if not states:
                return {
                    "status": "healthy",
                    "message": "No circuit breakers registered",
                    "circuits": {},
                }

            open_circuits = [
                name for name, state in states.items() if state.get("state") == "open"
            ]

            half_open_circuits = [
                name
                for name, state in states.items()
                if state.get("state") == "half_open"
            ]

            if open_circuits:
                return {
                    "status": "degraded",
                    "message": f"Open circuits: {', '.join(open_circuits)}",
                    "circuits": states,
                    "open_circuits": open_circuits,
                    "half_open_circuits": half_open_circuits,
                }

            if half_open_circuits:
                return {
                    "status": "healthy",
                    "message": f"All circuits closed, {len(half_open_circuits)} in half-open state",
                    "circuits": states,
                    "half_open_circuits": half_open_circuits,
                }

            return {
                "status": "healthy",
                "message": "All circuits closed",
                "circuits": states,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Circuit breaker health check failed: {str(e)}",
            }
