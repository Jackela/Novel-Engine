#!/usr/bin/env python3
"""
Equipment analytics and performance calculations.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from src.core.data_models import EquipmentCondition

from .models import DynamicEquipment

logger = logging.getLogger(__name__)


class EquipmentAnalyzer:
    """Analyzes equipment performance and predicts failures."""

    def calculate_wear_factor(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any], duration: int
    ) -> float:
        """Calculate enhanced wear factor for equipment usage"""
        base_wear = 0.001  # Base wear per use

        # Blessed intensity factor
        intensity = usage_context.get("intensity", 1.0)
        base_wear *= intensity

        # Blessed duration factor
        duration_factor = min(2.0, duration / 3600.0)  # Hours
        base_wear *= duration_factor

        # Blessed condition factor
        condition_multipliers = {
            EquipmentCondition.EXCELLENT: 0.5,
            EquipmentCondition.GOOD: 1.0,
            EquipmentCondition.FAIR: 1.5,
            EquipmentCondition.POOR: 2.0,
            EquipmentCondition.DAMAGED: 3.0,
        }
        condition_mult = condition_multipliers.get(
            equipment.base_equipment.condition, 1.0
        )
        base_wear *= condition_mult

        # Blessed maintenance factor
        days_since_maintenance = 7  # Default
        if equipment.maintenance_history:
            last_maintenance = equipment.maintenance_history[-1].performed_at
            days_since_maintenance = (datetime.now() - last_maintenance).days

        maintenance_factor = min(2.0, 1.0 + days_since_maintenance / 30.0)
        base_wear *= maintenance_factor

        return min(0.1, base_wear)  # Cap at 10% per use

    def update_performance_from_wear(self, equipment: DynamicEquipment):
        """Update enhanced performance metrics based on wear accumulation"""
        wear_impact = equipment.wear_accumulation

        # Blessed performance degradation
        for metric in equipment.performance_metrics:
            if metric == "reliability":
                equipment.performance_metrics[metric] = max(
                    0.1, 1.0 - wear_impact * 0.5
                )
            elif metric == "effectiveness":
                equipment.performance_metrics[metric] = max(
                    0.3, 1.0 - wear_impact * 0.3
                )
            elif metric == "efficiency":
                equipment.performance_metrics[metric] = max(
                    0.2, 1.0 - wear_impact * 0.4
                )
            elif metric == "responsiveness":
                equipment.performance_metrics[metric] = max(
                    0.1, 1.0 - wear_impact * 0.6
                )

    def evaluate_system_core_response(
        self, equipment: DynamicEquipment, usage_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate enhanced system core response to usage"""
        current_mood = equipment.system_core_mood

        # Blessed mood factors
        enhanced_usage = usage_context.get("enhanced_usage", False)
        respectful_usage = usage_context.get("respectful", True)
        maintenance_overdue = equipment.wear_accumulation > 0.8

        mood_transitions = {
            "content": {
                "pleased": enhanced_usage and respectful_usage,
                "agitated": maintenance_overdue or not respectful_usage,
                "content": True,  # Default
            },
            "pleased": {"content": not enhanced_usage, "pleased": True},  # Maintain
            "agitated": {
                "content": enhanced_usage
                and respectful_usage
                and not maintenance_overdue,
                "angry": maintenance_overdue and not respectful_usage,
                "agitated": True,  # Default
            },
        }

        transitions = mood_transitions.get(current_mood, {"content": True})
        new_mood = current_mood

        for mood, condition in transitions.items():
            if condition and mood != current_mood:
                new_mood = mood
                break

        responses = {
            "pleased": "The system core hums with satisfaction",
            "content": "The system core remains cooperative",
            "agitated": "The system core shows signs of displeasure",
            "angry": "The system core rebels against poor treatment",
        }

        return {
            "mood": new_mood,
            "response": responses.get(new_mood, "system core status unknown"),
        }

    def predict_equipment_failure(self, equipment: DynamicEquipment) -> Dict[str, Any]:
        """Predict enhanced equipment failure probability and timeline"""
        # Blessed failure risk calculation
        base_risk = equipment.wear_accumulation * 0.5

        # Blessed condition factor
        condition_risks = {
            EquipmentCondition.EXCELLENT: 0.0,
            EquipmentCondition.GOOD: 0.1,
            EquipmentCondition.FAIR: 0.3,
            EquipmentCondition.POOR: 0.6,
            EquipmentCondition.DAMAGED: 0.9,
            EquipmentCondition.BROKEN: 1.0,
        }
        condition_risk = condition_risks.get(equipment.base_equipment.condition, 0.5)

        # Blessed usage intensity factor
        usage_intensity = equipment.usage_statistics.get("total_uses", 0) / max(
            1, len(equipment.maintenance_history)
        )
        intensity_risk = min(0.3, usage_intensity * 0.01)

        # Blessed maintenance factor
        days_since_maintenance = 30  # Default
        if equipment.maintenance_history:
            last_maintenance = equipment.maintenance_history[-1].performed_at
            days_since_maintenance = (datetime.now() - last_maintenance).days

        maintenance_risk = min(0.4, days_since_maintenance / 100.0)

        # Blessed system core factor
        spirit_risks = {"pleased": -0.1, "content": 0.0, "agitated": 0.1, "angry": 0.3}
        spirit_risk = spirit_risks.get(equipment.system_core_mood, 0.0)

        total_risk = min(
            1.0,
            base_risk
            + condition_risk
            + intensity_risk
            + maintenance_risk
            + spirit_risk,
        )

        # Blessed timeframe calculation
        if total_risk < 0.2:
            timeframe_days = 365  # Low risk
        elif total_risk < 0.5:
            timeframe_days = 90  # Medium risk
        elif total_risk < 0.8:
            timeframe_days = 30  # High risk
        else:
            timeframe_days = 7  # Critical risk

        return {
            "risk_score": total_risk,
            "timeframe_days": timeframe_days,
            "risk_level": (
                "Critical"
                if total_risk > 0.8
                else (
                    "High"
                    if total_risk > 0.5
                    else "Medium" if total_risk > 0.2 else "Low"
                )
            ),
        }
