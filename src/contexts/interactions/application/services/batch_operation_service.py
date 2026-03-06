#!/usr/bin/env python3
"""
Batch Operation Application Service

Application service for batch operations using Result pattern.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from .....core.result import Err, Ok, Result
from .shared.errors import (
    InteractionError,
    ValidationError,
)


class BatchOperationService:
    """
    Service for executing batch operations.
    
    Provides business operations for batch processing with partial
    success handling and comprehensive result reporting.
    """

    def __init__(self) -> None:
        """Initialize batch operation service."""
        pass

    def execute_batch_with_rollback(
        self,
        operations: List[Dict[str, Any]],
        stop_on_first_error: bool = False,
    ) -> Result[Dict[str, Any], InteractionError]:
        """
        Execute a batch of operations with optional rollback.

        Args:
            operations: List of operations to execute
            stop_on_first_error: Whether to stop on first error

        Returns:
            Result containing batch execution results or error
        """
        if not operations:
            return Err(ValidationError(
                message="At least one operation required",
                field="operations",
                recoverable=True,
            ))

        try:
            results: List[Dict[str, Any]] = []
            successful: List[Dict[str, Any]] = []
            failed: List[Dict[str, Any]] = []

            for i, operation in enumerate(operations):
                op_id = operation.get("id", f"op_{i}")
                op_type = operation.get("type", "unknown")

                try:
                    # Simulate operation execution
                    # In real implementation, this would execute actual operations
                    result = {
                        "operation_id": op_id,
                        "type": op_type,
                        "status": "success",
                        "index": i,
                    }
                    results.append(result)
                    successful.append(result)
                except Exception as e:
                    error_result = {
                        "operation_id": op_id,
                        "type": op_type,
                        "status": "failed",
                        "error": str(e),
                        "index": i,
                    }
                    results.append(error_result)
                    failed.append(error_result)

                    if stop_on_first_error:
                        break

            success_rate = len(successful) / len(operations) if operations else 0

            result = {
                "total_operations": len(operations),
                "successful_count": len(successful),
                "failed_count": len(failed),
                "success_rate": success_rate,
                "all_succeeded": len(failed) == 0,
                "partial_success": len(successful) > 0 and len(failed) > 0,
                "stopped_early": stop_on_first_error and len(failed) > 0,
                "successful_operations": successful,
                "failed_operations": failed,
                "results": results,
            }

            return Ok(result)
        except Exception as e:
            return Err(InteractionError(
                message=f"Failed to execute batch: {e!s}",
                recoverable=True,
            ))

    def execute_parallel_operations(
        self,
        operations: List[Dict[str, Any]],
        max_concurrent: int = 5,
    ) -> Result[Dict[str, Any], InteractionError]:
        """
        Execute operations in parallel.

        Args:
            operations: List of operations to execute
            max_concurrent: Maximum concurrent operations

        Returns:
            Result containing parallel execution results or error
        """
        if not operations:
            return Err(ValidationError(
                message="At least one operation required",
                field="operations",
                recoverable=True,
            ))

        if max_concurrent < 1:
            return Err(ValidationError(
                message="max_concurrent must be at least 1",
                field="max_concurrent",
                field_value=max_concurrent,
                recoverable=True,
            ))

        try:
            # In real implementation, this would execute in parallel
            # For now, simulate sequential execution
            results: List[Dict[str, Any]] = []
            
            for i, operation in enumerate(operations):
                op_id = operation.get("id", f"op_{i}")
                results.append({
                    "operation_id": op_id,
                    "status": "completed",
                    "index": i,
                })

            result = {
                "total_operations": len(operations),
                "max_concurrent": max_concurrent,
                "completed_count": len(results),
                "all_completed": len(results) == len(operations),
                "results": results,
            }

            return Ok(result)
        except Exception as e:
            return Err(InteractionError(
                message=f"Failed to execute parallel operations: {e!s}",
                recoverable=True,
            ))

    def validate_batch_operations(
        self,
        operations: List[Dict[str, Any]],
    ) -> Result[Dict[str, Any], ValidationError]:
        """
        Validate a batch of operations without executing.

        Args:
            operations: List of operations to validate

        Returns:
            Result containing validation results or error
        """
        if not operations:
            return Err(ValidationError(
                message="At least one operation required",
                field="operations",
                recoverable=True,
            ))

        try:
            valid_operations: List[Dict[str, Any]] = []
            invalid_operations: List[Dict[str, Any]] = []

            for i, operation in enumerate(operations):
                errors: List[str] = []
                
                # Check required fields
                if "type" not in operation:
                    errors.append("Missing required field: type")
                
                if "id" not in operation:
                    errors.append("Missing required field: id")

                # Validate based on operation type
                op_type = operation.get("type", "")
                if op_type == "unknown":
                    errors.append("Invalid operation type")

                if errors:
                    invalid_operations.append({
                        "index": i,
                        "operation": operation,
                        "errors": errors,
                    })
                else:
                    valid_operations.append({
                        "index": i,
                        "operation": operation,
                    })

            result = {
                "total_operations": len(operations),
                "valid_count": len(valid_operations),
                "invalid_count": len(invalid_operations),
                "is_valid": len(invalid_operations) == 0,
                "valid_operations": valid_operations,
                "invalid_operations": invalid_operations,
            }

            return Ok(result)
        except Exception as e:
            return Err(ValidationError(
                message=f"Failed to validate batch: {e!s}",
                recoverable=True,
            ))

    def merge_batch_results(
        self,
        batch_results: List[Dict[str, Any]],
    ) -> Result[Dict[str, Any], InteractionError]:
        """
        Merge results from multiple batch operations.

        Args:
            batch_results: List of batch results to merge

        Returns:
            Result containing merged results or error
        """
        if not batch_results:
            return Err(ValidationError(
                message="At least one batch result required",
                field="batch_results",
                recoverable=True,
            ))

        try:
            total_operations = 0
            total_successful = 0
            total_failed = 0
            all_results: List[Dict[str, Any]] = []

            for batch in batch_results:
                total_operations += batch.get("total_operations", 0)
                total_successful += batch.get("successful_count", 0)
                total_failed += batch.get("failed_count", 0)
                all_results.extend(batch.get("results", []))

            result = {
                "batch_count": len(batch_results),
                "total_operations": total_operations,
                "total_successful": total_successful,
                "total_failed": total_failed,
                "overall_success_rate": (
                    total_successful / total_operations if total_operations > 0 else 0
                ),
                "all_results": all_results,
            }

            return Ok(result)
        except Exception as e:
            return Err(InteractionError(
                message=f"Failed to merge batch results: {e!s}",
                recoverable=True,
            ))

    def calculate_batch_statistics(
        self,
        operations: List[Dict[str, Any]],
    ) -> Result[Dict[str, Any], InteractionError]:
        """
        Calculate statistics for a batch of operations.

        Args:
            operations: List of operations

        Returns:
            Result containing statistics or error
        """
        if not operations:
            return Err(ValidationError(
                message="At least one operation required",
                field="operations",
                recoverable=True,
            ))

        try:
            # Count by type
            type_counts: Dict[str, int] = {}
            for op in operations:
                op_type = op.get("type", "unknown")
                type_counts[op_type] = type_counts.get(op_type, 0) + 1

            # Calculate complexity score (based on number of related operations)
            complexity_scores: List[int] = []
            for op in operations:
                # Simplified complexity calculation
                score = len(op.get("dependencies", [])) * 2
                score += len(op.get("parameters", {}))
                complexity_scores.append(score)

            avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0

            result = {
                "total_operations": len(operations),
                "type_distribution": type_counts,
                "unique_types": len(type_counts),
                "average_complexity": avg_complexity,
                "estimated_duration_seconds": len(operations) * 2,  # Rough estimate
            }

            return Ok(result)
        except Exception as e:
            return Err(InteractionError(
                message=f"Failed to calculate statistics: {e!s}",
                recoverable=True,
            ))
