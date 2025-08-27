#!/usr/bin/env python3
"""
Cost Tracking Service for AI Gateway

Provides comprehensive cost monitoring, budget enforcement, and usage analytics
for LLM operations across different providers, models, and consumers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple
import asyncio
from uuid import UUID, uuid4

from ...domain.value_objects.common import ProviderId, ModelId, TokenBudget
from ...domain.services.llm_provider import LLMRequest, LLMResponse


@dataclass(frozen=True)
class CostEntry:
    """
    Immutable record of a cost-incurring operation.
    
    Tracks the cost details for individual LLM operations
    including provider, model, token usage, and calculated costs.
    """
    entry_id: UUID
    timestamp: datetime
    provider_id: ProviderId
    model_id: ModelId
    request_id: UUID
    operation_type: str
    
    input_tokens: int
    output_tokens: int
    total_tokens: int
    
    input_cost: Decimal
    output_cost: Decimal
    total_cost: Decimal
    
    budget_id: Optional[str] = None
    client_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate cost entry data integrity."""
        if self.input_tokens < 0:
            raise ValueError("input_tokens cannot be negative")
        if self.output_tokens < 0:
            raise ValueError("output_tokens cannot be negative")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input_tokens + output_tokens")
        
        if self.input_cost < 0:
            raise ValueError("input_cost cannot be negative")
        if self.output_cost < 0:
            raise ValueError("output_cost cannot be negative")
        if abs(self.total_cost - (self.input_cost + self.output_cost)) > Decimal('0.0001'):
            raise ValueError("total_cost must equal input_cost + output_cost")
    
    @classmethod
    def from_request_response(
        cls,
        request: LLMRequest,
        response: LLMResponse,
        budget_id: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> 'CostEntry':
        """
        Create cost entry from request/response pair.
        
        Args:
            request: Original LLM request
            response: LLM response with usage statistics
            budget_id: Associated budget identifier
            client_id: Client identifier for attribution
            
        Returns:
            Cost entry with calculated costs
        """
        # Extract token usage from response
        usage_stats = response.usage_stats or {}
        input_tokens = usage_stats.get('input_tokens', 0)
        output_tokens = usage_stats.get('output_tokens', 0)
        total_tokens = usage_stats.get('total_tokens', input_tokens + output_tokens)
        
        # Calculate costs using model pricing
        model_id = request.model_id
        input_cost = Decimal('0')
        output_cost = Decimal('0')
        
        if model_id.cost_per_input_token:
            input_cost = Decimal(str(input_tokens)) * model_id.cost_per_input_token
        
        if model_id.cost_per_output_token:
            output_cost = Decimal(str(output_tokens)) * model_id.cost_per_output_token
        
        # Round to reasonable precision (4 decimal places)
        input_cost = input_cost.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        output_cost = output_cost.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        total_cost = input_cost + output_cost
        
        return cls(
            entry_id=uuid4(),
            timestamp=datetime.now(),
            provider_id=model_id.provider_id,
            model_id=model_id,
            request_id=request.request_id,
            operation_type=request.request_type.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            budget_id=budget_id,
            client_id=client_id,
            metadata=request.metadata.copy() if request.metadata else {}
        )


@dataclass
class UsageSummary:
    """
    Aggregated usage statistics for analysis and reporting.
    """
    period_start: datetime
    period_end: datetime
    
    total_requests: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    
    total_cost: Decimal = field(default_factory=lambda: Decimal('0'))
    input_cost: Decimal = field(default_factory=lambda: Decimal('0'))
    output_cost: Decimal = field(default_factory=lambda: Decimal('0'))
    
    provider_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    model_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    avg_cost_per_request: Optional[Decimal] = None
    avg_tokens_per_request: Optional[float] = None
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.total_requests > 0:
            self.avg_cost_per_request = (self.total_cost / self.total_requests).quantize(
                Decimal('0.0001'), rounding=ROUND_HALF_UP
            )
            self.avg_tokens_per_request = self.total_tokens / self.total_requests


@dataclass
class BudgetStatus:
    """
    Current status of a token budget including consumption and projections.
    """
    budget: TokenBudget
    current_consumption: Decimal
    projected_consumption: Decimal
    remaining_budget: Decimal
    utilization_percentage: float
    is_exceeded: bool
    is_at_risk: bool  # >80% utilization
    
    recent_entries: List[CostEntry] = field(default_factory=list)
    
    @classmethod
    def from_budget_and_entries(
        cls,
        budget: TokenBudget,
        entries: List[CostEntry],
        projection_factor: float = 1.2
    ) -> 'BudgetStatus':
        """
        Create budget status from budget and cost entries.
        
        Args:
            budget: Token budget to analyze
            entries: Recent cost entries for the budget
            projection_factor: Factor for projecting future usage
            
        Returns:
            Current budget status with analysis
        """
        current_cost = sum(entry.total_cost for entry in entries)
        projected_cost = current_cost * Decimal(str(projection_factor))
        
        cost_limit = budget.cost_limit or Decimal('0')
        remaining_budget = max(Decimal('0'), cost_limit - current_cost)
        
        utilization = float(current_cost / cost_limit * 100) if cost_limit > 0 else 0.0
        is_exceeded = current_cost > cost_limit if cost_limit > 0 else False
        is_at_risk = utilization > 80.0
        
        return cls(
            budget=budget,
            current_consumption=current_cost.quantize(Decimal('0.0001')),
            projected_consumption=projected_cost.quantize(Decimal('0.0001')),
            remaining_budget=remaining_budget.quantize(Decimal('0.0001')),
            utilization_percentage=round(utilization, 2),
            is_exceeded=is_exceeded,
            is_at_risk=is_at_risk,
            recent_entries=entries[-10:]  # Keep only recent entries
        )


class ICostTracker(ABC):
    """
    Abstract interface for AI Gateway cost tracking service.
    
    Provides cost monitoring, budget enforcement, and usage analytics
    for LLM operations across providers and consumers.
    """
    
    @abstractmethod
    async def record_cost_async(self, entry: CostEntry) -> None:
        """
        Record cost entry for tracking and analysis.
        
        Args:
            entry: Cost entry to record
        """
        pass
    
    @abstractmethod
    async def check_budget_async(
        self, 
        budget: TokenBudget, 
        estimated_cost: Decimal
    ) -> Tuple[bool, BudgetStatus]:
        """
        Check if operation is within budget limits.
        
        Args:
            budget: Budget to check against
            estimated_cost: Estimated cost of operation
            
        Returns:
            Tuple of (is_allowed, budget_status)
        """
        pass
    
    @abstractmethod
    async def get_usage_summary_async(
        self,
        start_time: datetime,
        end_time: datetime,
        provider_id: Optional[ProviderId] = None,
        client_id: Optional[str] = None
    ) -> UsageSummary:
        """
        Get aggregated usage summary for time period.
        
        Args:
            start_time: Start of analysis period
            end_time: End of analysis period  
            provider_id: Optional provider filter
            client_id: Optional client filter
            
        Returns:
            Usage summary with aggregated metrics
        """
        pass
    
    @abstractmethod
    async def get_budget_status_async(self, budget_id: str) -> Optional[BudgetStatus]:
        """
        Get current status of specific budget.
        
        Args:
            budget_id: Budget identifier
            
        Returns:
            Budget status if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_cost_projection_async(
        self,
        budget_id: str,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """
        Get cost projection for budget based on historical usage.
        
        Args:
            budget_id: Budget identifier
            days_ahead: Days to project into future
            
        Returns:
            Dictionary with projection data and confidence metrics
        """
        pass


class DefaultCostTracker(ICostTracker):
    """
    Default in-memory implementation of cost tracking service.
    
    Provides comprehensive cost tracking with budget enforcement,
    usage analytics, and projection capabilities.
    """
    
    def __init__(self, retention_days: int = 90):
        """
        Initialize cost tracker.
        
        Args:
            retention_days: Days to retain cost entries
        """
        self._retention_days = retention_days
        self._cost_entries: List[CostEntry] = []
        self._budget_entries: Dict[str, List[CostEntry]] = {}
        self._lock = asyncio.Lock()
    
    async def record_cost_async(self, entry: CostEntry) -> None:
        """Record cost entry with automatic cleanup."""
        async with self._lock:
            self._cost_entries.append(entry)
            
            # Record in budget-specific tracking
            if entry.budget_id:
                if entry.budget_id not in self._budget_entries:
                    self._budget_entries[entry.budget_id] = []
                self._budget_entries[entry.budget_id].append(entry)
            
            # Periodic cleanup of old entries
            if len(self._cost_entries) % 100 == 0:
                await self._cleanup_old_entries()
    
    async def check_budget_async(
        self, 
        budget: TokenBudget, 
        estimated_cost: Decimal
    ) -> Tuple[bool, BudgetStatus]:
        """Check budget with comprehensive status analysis."""
        async with self._lock:
            # Get recent entries for this budget
            budget_entries = self._budget_entries.get(budget.budget_id, [])
            
            # Filter to recent entries (last 30 days)
            cutoff_time = datetime.now() - timedelta(days=30)
            recent_entries = [
                entry for entry in budget_entries 
                if entry.timestamp > cutoff_time
            ]
            
            # Calculate current status
            status = BudgetStatus.from_budget_and_entries(budget, recent_entries)
            
            # Check if estimated cost would exceed budget
            cost_limit = budget.cost_limit or Decimal('0')
            would_exceed = (status.current_consumption + estimated_cost) > cost_limit
            
            is_allowed = not would_exceed if cost_limit > 0 else True
            
            return is_allowed, status
    
    async def get_usage_summary_async(
        self,
        start_time: datetime,
        end_time: datetime,
        provider_id: Optional[ProviderId] = None,
        client_id: Optional[str] = None
    ) -> UsageSummary:
        """Generate comprehensive usage summary."""
        async with self._lock:
            # Filter entries by time range and optional filters
            filtered_entries = [
                entry for entry in self._cost_entries
                if start_time <= entry.timestamp <= end_time
            ]
            
            if provider_id:
                filtered_entries = [
                    entry for entry in filtered_entries
                    if entry.provider_id.provider_name == provider_id.provider_name
                ]
            
            if client_id:
                filtered_entries = [
                    entry for entry in filtered_entries
                    if entry.client_id == client_id
                ]
            
            # Calculate aggregations
            total_requests = len(filtered_entries)
            total_tokens = sum(entry.total_tokens for entry in filtered_entries)
            input_tokens = sum(entry.input_tokens for entry in filtered_entries)
            output_tokens = sum(entry.output_tokens for entry in filtered_entries)
            
            total_cost = sum(entry.total_cost for entry in filtered_entries)
            input_cost = sum(entry.input_cost for entry in filtered_entries)
            output_cost = sum(entry.output_cost for entry in filtered_entries)
            
            # Provider breakdown
            provider_breakdown = {}
            for entry in filtered_entries:
                provider_name = entry.provider_id.provider_name
                if provider_name not in provider_breakdown:
                    provider_breakdown[provider_name] = {
                        'requests': 0,
                        'tokens': 0,
                        'cost': Decimal('0')
                    }
                
                provider_breakdown[provider_name]['requests'] += 1
                provider_breakdown[provider_name]['tokens'] += entry.total_tokens
                provider_breakdown[provider_name]['cost'] += entry.total_cost
            
            # Model breakdown
            model_breakdown = {}
            for entry in filtered_entries:
                model_name = entry.model_id.model_name
                if model_name not in model_breakdown:
                    model_breakdown[model_name] = {
                        'requests': 0,
                        'tokens': 0,
                        'cost': Decimal('0')
                    }
                
                model_breakdown[model_name]['requests'] += 1
                model_breakdown[model_name]['tokens'] += entry.total_tokens
                model_breakdown[model_name]['cost'] += entry.total_cost
            
            return UsageSummary(
                period_start=start_time,
                period_end=end_time,
                total_requests=total_requests,
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost=total_cost,
                input_cost=input_cost,
                output_cost=output_cost,
                provider_breakdown=provider_breakdown,
                model_breakdown=model_breakdown
            )
    
    async def get_budget_status_async(self, budget_id: str) -> Optional[BudgetStatus]:
        """Get current budget status with analysis."""
        async with self._lock:
            if budget_id not in self._budget_entries:
                return None
            
            entries = self._budget_entries[budget_id]
            if not entries:
                return None
            
            # Get the most recent budget from entries (assuming consistent budget)
            latest_entry = max(entries, key=lambda e: e.timestamp)
            
            # Create a TokenBudget for analysis (simplified)
            # In a real implementation, this would be stored separately
            budget = TokenBudget(
                budget_id=budget_id,
                allocated_tokens=100000,  # Would be retrieved from storage
                cost_limit=Decimal('100.00')  # Would be retrieved from storage
            )
            
            return BudgetStatus.from_budget_and_entries(budget, entries)
    
    async def get_cost_projection_async(
        self,
        budget_id: str,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """Generate cost projection based on historical usage."""
        async with self._lock:
            entries = self._budget_entries.get(budget_id, [])
            if not entries:
                return {
                    'projection': Decimal('0'),
                    'confidence': 'low',
                    'daily_average': Decimal('0'),
                    'trend': 'unknown'
                }
            
            # Calculate daily usage for last 30 days
            cutoff_time = datetime.now() - timedelta(days=30)
            recent_entries = [
                entry for entry in entries
                if entry.timestamp > cutoff_time
            ]
            
            if not recent_entries:
                return {
                    'projection': Decimal('0'),
                    'confidence': 'low',
                    'daily_average': Decimal('0'),
                    'trend': 'unknown'
                }
            
            # Calculate daily averages
            total_cost = sum(entry.total_cost for entry in recent_entries)
            days_with_data = len(set(entry.timestamp.date() for entry in recent_entries))
            daily_average = total_cost / max(1, days_with_data)
            
            # Simple linear projection
            projected_cost = daily_average * days_ahead
            
            # Determine confidence based on data consistency
            confidence = 'high' if days_with_data > 20 else 'medium' if days_with_data > 10 else 'low'
            
            # Simple trend analysis (compare first half vs second half)
            mid_point = len(recent_entries) // 2
            if mid_point > 0:
                first_half_avg = sum(entry.total_cost for entry in recent_entries[:mid_point]) / mid_point
                second_half_avg = sum(entry.total_cost for entry in recent_entries[mid_point:]) / (len(recent_entries) - mid_point)
                
                if second_half_avg > first_half_avg * 1.1:
                    trend = 'increasing'
                elif second_half_avg < first_half_avg * 0.9:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            else:
                trend = 'unknown'
            
            return {
                'projection': projected_cost.quantize(Decimal('0.0001')),
                'confidence': confidence,
                'daily_average': daily_average.quantize(Decimal('0.0001')),
                'trend': trend,
                'data_points': len(recent_entries),
                'period_days': days_with_data
            }
    
    async def _cleanup_old_entries(self) -> None:
        """Remove entries older than retention period."""
        cutoff_time = datetime.now() - timedelta(days=self._retention_days)
        
        # Clean main entries list
        self._cost_entries = [
            entry for entry in self._cost_entries
            if entry.timestamp > cutoff_time
        ]
        
        # Clean budget-specific entries
        for budget_id in list(self._budget_entries.keys()):
            self._budget_entries[budget_id] = [
                entry for entry in self._budget_entries[budget_id]
                if entry.timestamp > cutoff_time
            ]
            
            # Remove empty budget entries
            if not self._budget_entries[budget_id]:
                del self._budget_entries[budget_id]