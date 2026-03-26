"""Health check for circuit breakers using the unified HealthStatus model."""

from __future__ import annotations

from src.shared.infrastructure.circuit_breaker import CircuitBreakerRegistry
from src.shared.infrastructure.health.health_checker import HealthStatus


class CircuitBreakerHealthCheck:
    """Check circuit breaker states."""

    async def check(self) -> HealthStatus:
        """Check circuit breaker states and return standardized HealthStatus.

        Returns:
            HealthStatus with status, message, and circuit breaker details.
        """
        try:
            states = CircuitBreakerRegistry.get_all_states()

            if not states:
                return HealthStatus(
                    status="healthy",
                    message="No circuit breakers registered",
                    details={"circuits": {}},
                )

            open_circuits = [
                name for name, state in states.items() if state.get("state") == "open"
            ]

            half_open_circuits = [
                name
                for name, state in states.items()
                if state.get("state") == "half_open"
            ]

            if open_circuits:
                return HealthStatus(
                    status="degraded",
                    message=f"Open circuits: {', '.join(open_circuits)}",
                    details={
                        "circuits": states,
                        "open_circuits": open_circuits,
                        "half_open_circuits": half_open_circuits,
                    },
                )

            if half_open_circuits:
                return HealthStatus(
                    status="healthy",
                    message=f"All circuits closed, {len(half_open_circuits)} in half-open state",
                    details={
                        "circuits": states,
                        "half_open_circuits": half_open_circuits,
                    },
                )

            return HealthStatus(
                status="healthy",
                message="All circuits closed",
                details={"circuits": states},
            )

        except Exception as e:
            return HealthStatus(
                status="unhealthy",
                message=f"Circuit breaker health check failed: {str(e)}",
                error=str(e),
                details={"error_type": type(e).__name__},
            )
