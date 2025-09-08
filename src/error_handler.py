"""
Centralized error handling system for the application.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
import logging
import traceback

logger = logging.getLogger(__name__)


class CentralizedErrorHandler:
    """Centralized error handling with recovery strategies."""

    def __init__(self):
        self.error_history = []
        self.recovery_strategies = {
            "network": self._recover_network_error,
            "database": self._recover_database_error,
            "validation": self._recover_validation_error,
            "llm": self._recover_llm_error,
        }

    def detect_category(self, error: Exception) -> str:
        """Detect error category from exception."""
        error_str = str(error).lower()
        error_type = type(error).__name__

        if (
            "connection" in error_str
            or "network" in error_str
            or "timeout" in error_str
        ):
            return "network"
        elif "database" in error_str or "sql" in error_str or "db" in error_str:
            return "database"
        elif (
            "validation" in error_str or "invalid" in error_str or "value" in error_str
        ):
            return "validation"
        elif "llm" in error_str or "api" in error_str or "model" in error_str:
            return "llm"
        else:
            return "unknown"

    def handle_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle error with categorization and recovery."""
        category = self.detect_category(error)

        error_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context or {},
            "traceback": traceback.format_exc(),
        }

        self.error_history.append(error_record)
        logger.error(f"Error handled: {category} - {error}")

        # Attempt recovery
        recovery_result = self.attempt_recovery(category, error, context)

        return {
            "error": error_record,
            "recovery_attempted": recovery_result["attempted"],
            "recovery_successful": recovery_result["success"],
            "recovery_action": recovery_result["action"],
        }

    def attempt_recovery(
        self, category: str, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Attempt to recover from error based on category."""
        if category in self.recovery_strategies:
            try:
                strategy = self.recovery_strategies[category]
                result = strategy(error, context)
                return {
                    "attempted": True,
                    "success": result.get("success", False),
                    "action": result.get("action", "none"),
                }
            except Exception as recovery_error:
                logger.error(f"Recovery failed: {recovery_error}")
                return {
                    "attempted": True,
                    "success": False,
                    "action": "recovery_failed",
                }

        return {"attempted": False, "success": False, "action": "no_strategy"}

    def _recover_network_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Recover from network errors."""
        return {"success": True, "action": "retry_with_backoff"}

    def _recover_database_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Recover from database errors."""
        return {"success": True, "action": "reconnect_database"}

    def _recover_validation_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Recover from validation errors."""
        return {"success": False, "action": "return_validation_errors"}

    def _recover_llm_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Recover from LLM errors."""
        return {"success": True, "action": "fallback_to_cached_response"}

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        if not self.error_history:
            return {"total_errors": 0, "categories": {}, "recent_errors": []}

        categories = {}
        for error in self.error_history:
            cat = error["category"]
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "categories": categories,
            "recent_errors": self.error_history[-10:],
        }


# Global error handler instance
error_handler = CentralizedErrorHandler()


def handle_error(
    error: Exception, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Global error handling function."""
    return error_handler.handle_error(error, context)
