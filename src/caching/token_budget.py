"""Token budget management primitives used by integration tests."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List


class OperationType(str, Enum):
    CHAT_COMPLETION = "chat_completion"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image_generation"


class BudgetPeriod(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"

    @property
    def seconds(self) -> int:
        if self is BudgetPeriod.HOURLY:
            return 3600
        if self is BudgetPeriod.DAILY:
            return 86400
        return 30 * 86400


@dataclass
class BudgetLimit:
    period: BudgetPeriod
    max_tokens: int | None = None
    max_cost: float | None = None
    max_operations: int | None = None


@dataclass
class TokenBudgetConfig:
    enable_persistence: bool = True
    persistence_file: Path | None = None
    enable_cache_integration: bool = True
    enable_debug_logging: bool = False


@dataclass
class _UsageRecord:
    operation_id: str
    operation_type: OperationType
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_cost: float
    duration_ms: int
    success: bool
    character_id: str | None
    created_ts: float = field(default_factory=time.time)
    context: str | None = None


_MODEL_PRICING = {
    "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.0020},
    "gpt-4o-mini": {"prompt": 0.0007, "completion": 0.0007},
}
_FALLBACK_PRICING = {"prompt": 0.002, "completion": 0.0025}


class TokenBudgetManager:
    def __init__(self, config: TokenBudgetConfig | None = None):
        self.config = config or TokenBudgetConfig()
        self._limits: List[BudgetLimit] = []
        self._usage: List[_UsageRecord] = []
        self._load_usage()

    # Limit management ---------------------------------------------------
    def add_budget_limit(self, limit: BudgetLimit) -> None:
        self._limits.append(limit)

    # Cost estimation ----------------------------------------------------
    def estimate_operation_cost(
        self,
        operation_type: OperationType,
        prompt_text: str,
        model_name: str,
        completion_tokens_estimate: int,
    ) -> Dict[str, float | bool | str]:
        prompt_tokens = max(1, math.ceil(len(prompt_text) / 4))
        completion_tokens = max(0, completion_tokens_estimate)
        total_tokens = prompt_tokens + completion_tokens
        cost = _compute_cost(model_name, prompt_tokens, completion_tokens)
        within_budget = self._check_limits(total_tokens, cost)
        return {
            "operation_type": operation_type.value,
            "model_name": model_name,
            "estimated_prompt_tokens": prompt_tokens,
            "estimated_completion_tokens": completion_tokens,
            "estimated_total_tokens": total_tokens,
            "estimated_total_cost": cost,
            "budget_check": within_budget,
        }

    def check_budget_approval(
        self,
        operation_type: OperationType,
        estimated_tokens: int,
        estimated_cost: float,
        priority: str = "normal",
    ) -> Dict[str, str | bool]:
        within_budget = self._check_limits(estimated_tokens, estimated_cost)
        if within_budget:
            return {"approved": True, "reason": "Within configured limits."}
        reason = "Estimated usage exceeds configured budget"
        if priority == "low":
            reason += " (auto-denied for low priority)."
        return {"approved": False, "reason": reason}

    def record_operation(
        self,
        operation_id: str,
        operation_type: OperationType,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: int,
        success: bool,
        character_id: str | None = None,
        operation_context: str | None = None,
    ) -> bool:
        total_tokens = prompt_tokens + completion_tokens
        total_cost = _compute_cost(model_name, prompt_tokens, completion_tokens)
        if not self._check_limits(total_tokens, total_cost):
            return False
        record = _UsageRecord(
            operation_id=operation_id,
            operation_type=operation_type,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_cost=total_cost,
            duration_ms=duration_ms,
            success=success,
            character_id=character_id,
            context=operation_context,
        )
        self._usage.append(record)
        return True

    # Reporting ----------------------------------------------------------
    def get_usage_report(self, period: BudgetPeriod) -> Dict[str, object]:
        cutoff = time.time() - period.seconds
        window = [rec for rec in self._usage if rec.created_ts >= cutoff]
        total_tokens = sum(rec.prompt_tokens + rec.completion_tokens for rec in window)
        total_cost = sum(rec.total_cost for rec in window)
        summary = {
            "total_operations": len(window),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
        }
        by_operation = {}
        for rec in window:
            by_operation.setdefault(rec.operation_type.value, 0)
            by_operation[rec.operation_type.value] += 1
        limits = [
            {
                "period": limit.period.value,
                "max_tokens": limit.max_tokens,
                "max_cost": limit.max_cost,
                "max_operations": limit.max_operations,
            }
            for limit in self._limits
        ]
        return {
            "period": period.value,
            "summary_metrics": summary,
            "operations": by_operation,
            "limits": limits,
        }

    def optimize_costs(self) -> Dict[str, List[str]]:
        if not self._usage:
            return {"recommendations": ["Enable caching to accumulate savings."]}
        pricey_models = sorted(
            {rec.model_name for rec in self._usage},
            key=lambda name: _MODEL_PRICING.get(name, _FALLBACK_PRICING)["prompt"],
            reverse=True,
        )
        recs = [
            f"Review usage of {model} for potential downgrade."
            for model in pricey_models[:2]
        ]
        recs.append("Track semantic cache hit-rate to unlock more savings.")
        return {"recommendations": recs}

    # Persistence --------------------------------------------------------
    def save_usage_data(self) -> None:
        if not self.config.enable_persistence or not self.config.persistence_file:
            return
        payload = [
            {
                "operation_id": rec.operation_id,
                "operation_type": rec.operation_type.value,
                "model_name": rec.model_name,
                "prompt_tokens": rec.prompt_tokens,
                "completion_tokens": rec.completion_tokens,
                "total_cost": rec.total_cost,
                "duration_ms": rec.duration_ms,
                "success": rec.success,
                "character_id": rec.character_id,
                "created_ts": rec.created_ts,
                "context": rec.context,
            }
            for rec in self._usage
        ]
        path = self.config.persistence_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Internal helpers ---------------------------------------------------
    def _check_limits(self, tokens: int, cost: float) -> bool:
        if not self._limits:
            return True
        for limit in self._limits:
            if limit.max_tokens is not None and tokens > limit.max_tokens:
                return False
            if limit.max_cost is not None and cost > limit.max_cost:
                return False
            if limit.max_operations is not None:
                ops = self._operations_in_period(limit.period)
                if ops >= limit.max_operations:
                    return False
        return True

    def _operations_in_period(self, period: BudgetPeriod) -> int:
        cutoff = time.time() - period.seconds
        return sum(1 for rec in self._usage if rec.created_ts >= cutoff)

    def _load_usage(self) -> None:
        path = self.config.persistence_file
        if not self.config.enable_persistence or not path or not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        for item in payload:
            rec = _UsageRecord(
                operation_id=item["operation_id"],
                operation_type=OperationType(item["operation_type"]),
                model_name=item["model_name"],
                prompt_tokens=item["prompt_tokens"],
                completion_tokens=item["completion_tokens"],
                total_cost=item["total_cost"],
                duration_ms=item.get("duration_ms", 0),
                success=item.get("success", True),
                character_id=item.get("character_id"),
                created_ts=item.get("created_ts", time.time()),
                context=item.get("context"),
            )
            self._usage.append(rec)


def _compute_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = _MODEL_PRICING.get(model_name.lower(), _FALLBACK_PRICING)
    prompt_cost = pricing["prompt"] * (prompt_tokens / 1000)
    completion_cost = pricing["completion"] * (completion_tokens / 1000)
    return round(prompt_cost + completion_cost, 6)
