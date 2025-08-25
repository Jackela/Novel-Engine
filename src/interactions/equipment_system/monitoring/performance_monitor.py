"""
Performance Monitor
==================

Equipment performance monitoring, failure prediction, and analytics system.
Tracks equipment health, predicts failures, and provides optimization recommendations.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ..core.types import DynamicEquipment, EquipmentSystemConfig

# Import enhanced core systems
try:
    from src.core.data_models import EquipmentCondition
except ImportError:
    # Fallback for testing
    class EquipmentCondition:
        EXCELLENT = "excellent"
        GOOD = "good"
        FAIR = "fair"
        POOR = "poor"
        DAMAGED = "damaged"
        BROKEN = "broken"

__all__ = ['PerformanceMonitor']


class PerformanceMonitor:
    """
    Equipment Performance Monitoring and Prediction System
    
    Responsibilities:
    - Monitor equipment performance metrics and health
    - Predict equipment failures and maintenance needs
    - Generate performance analytics and reports
    - Provide optimization recommendations
    """
    
    def __init__(self, config: EquipmentSystemConfig,
                 logger: Optional[logging.Logger] = None):
        """Initialize performance monitor."""
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        self.logger.info("Performance monitor initialized")
    
    def predict_equipment_failure(self, equipment: DynamicEquipment) -> Dict[str, Any]:
        """Predict equipment failure probability and timeline."""
        try:
            # Base risk from wear accumulation
            base_risk = equipment.wear_accumulation * 0.5
            
            # Condition factor
            condition_risks = {
                "excellent": 0.0, "good": 0.1, "fair": 0.3,
                "poor": 0.6, "damaged": 0.9, "broken": 1.0
            }
            condition = getattr(equipment.base_equipment, 'condition', 'good')
            if hasattr(condition, 'value'):
                condition = condition.value
            condition_risk = condition_risks.get(condition, 0.5)
            
            # Usage intensity factor
            total_uses = equipment.usage_statistics.get("total_uses", 0)
            maintenance_count = len(equipment.maintenance_history)
            usage_intensity = total_uses / max(1, maintenance_count)
            intensity_risk = min(0.3, usage_intensity * 0.01)
            
            # Maintenance factor
            days_since_maintenance = 30  # Default
            if equipment.maintenance_history:
                last_maintenance = equipment.maintenance_history[-1].performed_at
                days_since_maintenance = (datetime.now() - last_maintenance).days
            maintenance_risk = min(0.4, days_since_maintenance / 100.0)
            
            # Machine spirit factor
            spirit_risks = {
                "pleased": -0.1, "content": 0.0, "agitated": 0.1, "angry": 0.3
            }
            spirit_risk = spirit_risks.get(equipment.machine_spirit_mood, 0.0)
            
            total_risk = min(1.0, base_risk + condition_risk + intensity_risk + maintenance_risk + spirit_risk)
            
            # Calculate timeframe
            if total_risk < 0.2:
                timeframe_days = 365
            elif total_risk < 0.5:
                timeframe_days = 90
            elif total_risk < 0.8:
                timeframe_days = 30
            else:
                timeframe_days = 7
            
            risk_level = ("Critical" if total_risk > 0.8 else
                         "High" if total_risk > 0.5 else
                         "Medium" if total_risk > 0.2 else "Low")
            
            return {
                "risk_score": total_risk,
                "timeframe_days": timeframe_days,
                "risk_level": risk_level,
                "contributing_factors": {
                    "wear": base_risk,
                    "condition": condition_risk,
                    "usage_intensity": intensity_risk,
                    "maintenance_delay": maintenance_risk,
                    "machine_spirit": spirit_risk
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting equipment failure: {e}")
            return {"risk_score": 0.5, "risk_level": "Unknown", "error": str(e)}
    
    def get_performance_metrics(self, equipment: DynamicEquipment) -> Dict[str, Any]:
        """Get comprehensive performance metrics for equipment."""
        try:
            # Base metrics
            metrics = equipment.performance_metrics.copy()
            
            # Calculate derived metrics
            total_uses = equipment.usage_statistics.get("total_uses", 0)
            successful_uses = equipment.usage_statistics.get("successful_uses", 0)
            
            success_rate = successful_uses / max(1, total_uses)
            metrics["success_rate"] = success_rate
            
            # Availability metric (based on status and maintenance time)
            availability = 1.0
            if equipment.maintenance_history:
                total_maintenance_time = sum(
                    maintenance.duration_minutes 
                    for maintenance in equipment.maintenance_history
                )
                total_operation_time = equipment.usage_statistics.get("total_duration", 3600)  # Default 1 hour
                availability = total_operation_time / max(1, total_operation_time + total_maintenance_time)
            
            metrics["availability"] = availability
            
            # Overall health score
            health_factors = [
                1.0 - equipment.wear_accumulation,  # Wear factor
                metrics.get("reliability", 1.0),    # Reliability
                availability,                       # Availability
                success_rate                        # Success rate
            ]
            
            # Machine spirit bonus/penalty
            spirit_modifiers = {
                "pleased": 0.1, "content": 0.0, "agitated": -0.05, "angry": -0.15
            }
            spirit_bonus = spirit_modifiers.get(equipment.machine_spirit_mood, 0.0)
            
            health_score = (sum(health_factors) / len(health_factors)) + spirit_bonus
            metrics["overall_health"] = max(0.0, min(1.0, health_score))
            
            return {
                "equipment_id": equipment.equipment_id,
                "metrics": metrics,
                "wear_accumulation": equipment.wear_accumulation,
                "machine_spirit_mood": equipment.machine_spirit_mood,
                "condition": getattr(equipment.base_equipment, 'condition', 'unknown'),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {"equipment_id": equipment.equipment_id, "error": str(e)}
    
    def get_optimization_recommendations(self, equipment: DynamicEquipment) -> List[Dict[str, Any]]:
        """Generate optimization recommendations for equipment."""
        recommendations = []
        
        try:
            # High wear recommendation
            if equipment.wear_accumulation > 0.7:
                recommendations.append({
                    "type": "maintenance",
                    "priority": "high",
                    "title": "High Wear Detected",
                    "description": f"Equipment wear at {equipment.wear_accumulation:.1%} - schedule maintenance",
                    "estimated_benefit": "Restore 20-40% performance"
                })
            
            # Machine spirit mood recommendation
            if equipment.machine_spirit_mood in ["agitated", "angry"]:
                recommendations.append({
                    "type": "machine_spirit",
                    "priority": "medium",
                    "title": "Machine Spirit Displeasure",
                    "description": f"Machine spirit is {equipment.machine_spirit_mood} - perform appeasement ritual",
                    "estimated_benefit": "Improve reliability and reduce failures"
                })
            
            # Performance degradation recommendation
            avg_performance = sum(equipment.performance_metrics.values()) / max(1, len(equipment.performance_metrics))
            if avg_performance < 0.7:
                recommendations.append({
                    "type": "performance",
                    "priority": "medium",
                    "title": "Performance Degradation",
                    "description": f"Average performance at {avg_performance:.1%} - consider upgrade or overhaul",
                    "estimated_benefit": "Restore performance to optimal levels"
                })
            
            # Modification recommendation
            if len(equipment.modifications) == 0 and equipment.wear_accumulation < 0.3:
                recommendations.append({
                    "type": "enhancement",
                    "priority": "low", 
                    "title": "Enhancement Opportunity",
                    "description": "Equipment in good condition - suitable for modifications",
                    "estimated_benefit": "Improve specific performance aspects"
                })
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
        
        return recommendations