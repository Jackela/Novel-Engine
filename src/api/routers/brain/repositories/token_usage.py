"""
Token Usage Repository

In-memory repository for token usage analytics.
Stores usage events for cost tracking and visualization.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog

logger = structlog.get_logger(__name__)


class InMemoryTokenUsageRepository:
    """
    In-memory repository for token usage analytics.

    Stores usage events for cost tracking and visualization.
    """

    def __init__(self) -> None:
        self._usages: list[dict] = []

    async def add_usage(self, usage: dict) -> None:
        """Add a usage event."""
        self._usages.append(usage)

    async def get_usages(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        provider: str | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """Get usage events with optional filters."""
        filtered = self._usages

        if start_time:
            filtered = [
                u
                for u in filtered
                if datetime.fromisoformat(u["timestamp"]) >= start_time
            ]
        if end_time:
            filtered = [
                u
                for u in filtered
                if datetime.fromisoformat(u["timestamp"]) <= end_time
            ]
        if provider:
            filtered = [u for u in filtered if u["provider"] == provider]

        return filtered[-limit:]

    async def get_summary(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict:
        """Get aggregated usage summary."""
        usages = await self.get_usages(start_time, end_time)

        if not usages:
            return {
                "total_tokens": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost": 0.0,
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_latency_ms": 0.0,
                "period_start": start_time.isoformat() if start_time else None,
                "period_end": end_time.isoformat() if end_time else None,
            }

        total_tokens = sum(u["total_tokens"] for u in usages)
        total_input = sum(u["input_tokens"] for u in usages)
        total_output = sum(u["output_tokens"] for u in usages)
        total_cost = sum(float(u.get("total_cost", 0)) for u in usages)
        total_latency = sum(u.get("latency_ms", 0) for u in usages)
        successful = sum(1 for u in usages if u.get("success", True))

        return {
            "total_tokens": total_tokens,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost": round(total_cost, 6),
            "total_requests": len(usages),
            "successful_requests": successful,
            "failed_requests": len(usages) - successful,
            "avg_latency_ms": round(total_latency / len(usages), 2) if usages else 0.0,
            "period_start": min(u["timestamp"] for u in usages),
            "period_end": max(u["timestamp"] for u in usages),
        }

    async def get_daily_stats(
        self,
        days: int = 30,
    ) -> list[dict]:
        """Get daily aggregated stats for the last N days."""
        now = datetime.now(UTC)
        daily_stats: dict[str, dict] = {}

        for i in range(days):
            date = (now - timedelta(days=days - i - 1)).date()
            date_str = date.isoformat()
            daily_stats[date_str] = {
                "date": date_str,
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_requests": 0,
                "providers": {},
            }

        for usage in self._usages:
            timestamp = datetime.fromisoformat(usage["timestamp"])
            date_str = timestamp.date().isoformat()

            if date_str in daily_stats:
                daily_stats[date_str]["total_tokens"] += usage["total_tokens"]
                daily_stats[date_str]["total_cost"] += float(usage.get("total_cost", 0))
                daily_stats[date_str]["total_requests"] += 1

                provider = usage["provider"]
                if provider not in daily_stats[date_str]["providers"]:
                    daily_stats[date_str]["providers"][provider] = {
                        "tokens": 0,
                        "cost": 0.0,
                        "requests": 0,
                    }
                daily_stats[date_str]["providers"][provider]["tokens"] += usage[
                    "total_tokens"
                ]
                daily_stats[date_str]["providers"][provider]["cost"] += float(
                    usage.get("total_cost", 0)
                )
                daily_stats[date_str]["providers"][provider]["requests"] += 1

        return list(daily_stats.values())

    async def get_model_breakdown(self) -> list[dict]:
        """Get cost breakdown by model."""
        model_stats: dict[str, dict] = {}

        for usage in self._usages:
            model = usage.get(
                "model_identifier", f"{usage['provider']}:{usage['model_name']}"
            )
            if model not in model_stats:
                model_stats[model] = {
                    "provider": usage["provider"],
                    "model_name": usage["model_name"],
                    "model_identifier": model,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "total_requests": 0,
                }
            model_stats[model]["total_tokens"] += usage["total_tokens"]
            model_stats[model]["total_cost"] += float(usage.get("total_cost", 0))
            model_stats[model]["total_requests"] += 1

        # Sort by cost descending
        return sorted(model_stats.values(), key=lambda x: x["total_cost"], reverse=True)


def seed_mock_data(repository: InMemoryTokenUsageRepository) -> None:
    """Seed mock usage data for BRAIN-035A testing."""
    now = datetime.now(UTC)
    providers = ["openai", "anthropic", "gemini"]

    models = {
        "openai": ["gpt-4o", "gpt-4o-mini"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        "gemini": ["gemini-2.0-flash", "gemini-2.5-pro"],
    }

    pricing = {
        "openai": {"gpt-4o": (5.0, 15.0), "gpt-4o-mini": (0.15, 0.6)},
        "anthropic": {
            "claude-3-5-sonnet-20241022": (3.0, 15.0),
            "claude-3-5-haiku-20241022": (0.8, 4.0),
        },
        "gemini": {"gemini-2.0-flash": (0.075, 0.3), "gemini-2.5-pro": (1.25, 10.0)},
    }

    # Generate 30 days of mock data
    for day in range(30):
        date = now - timedelta(days=30 - day)

        # 5-20 requests per day
        num_requests = 5 + (day * 7) % 16

        for i in range(num_requests):
            provider = providers[day % 3]
            model_list = models[provider]
            model = model_list[(day + i) % len(model_list)]

            input_tokens = 500 + (i * 200) % 2000
            output_tokens = 200 + (i * 100) % 1000
            total_tokens = input_tokens + output_tokens

            cost_input, cost_output = pricing[provider][model]
            input_cost = input_tokens * cost_input / 1_000_000
            output_cost = output_tokens * cost_output / 1_000_000
            total_cost = input_cost + output_cost

            timestamp = date + timedelta(hours=i % 24, minutes=(i * 7) % 60)

            repository._usages.append(
                {
                    "id": f"mock-{day}-{i}",
                    "timestamp": timestamp.isoformat(),
                    "provider": provider,
                    "model_name": model,
                    "model_identifier": f"{provider}:{model}",
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "input_cost": str(
                        Decimal(str(input_cost)).quantize(Decimal("0.000001"))
                    ),
                    "output_cost": str(
                        Decimal(str(output_cost)).quantize(Decimal("0.000001"))
                    ),
                    "total_cost": str(
                        Decimal(str(total_cost)).quantize(Decimal("0.000001"))
                    ),
                    "latency_ms": 500 + (i * 50) % 2000,
                    "success": True,
                    "workspace_id": None,
                    "user_id": None,
                }
            )


__all__ = ["InMemoryTokenUsageRepository", "seed_mock_data"]
