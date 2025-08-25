#!/usr/bin/env python3
"""
CentralizedErrorHandler Test Suite
==================================

Comprehensive unit tests for the centralized error handling system.
Tests error classification, recovery strategies, and monitoring.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.error_handler import (
    CentralizedErrorHandler, ErrorContext, ErrorRecord, ErrorSeverity,
    ErrorCategory, RecoveryStrategy, get_error_handler, handle_error
)


class TestErrorContext:
    """Test ErrorContext functionality."""
    
    def test_error_context_creation(self):
        """Test ErrorContext creation."""
        context = ErrorContext(
            component="test_component",
            operation="test_operation",
            user_id="test_user",
            session_id="test_session"
        )
        
        assert context.component == "test_component"
        assert context.operation == "test_operation"
        assert context.user_id == "test_user"
        assert context.session_id == "test_session"
        assert isinstance(context.timestamp, datetime)


class TestCentralizedErrorHandler:
    """Test CentralizedErrorHandler functionality."""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing."""
        return CentralizedErrorHandler()
    
    @pytest.fixture
    def error_context(self):
        """Create test error context."""
        return ErrorContext(
            component="test_component",
            operation="test_operation",
            metadata={"test_key": "test_value"}
        )
    
    def test_error_handler_initialization(self, error_handler):
        """Test error handler initialization."""
        assert len(error_handler.error_records) == 0
        assert len(error_handler.error_history) == 0
        assert len(error_handler.recovery_handlers) > 0
        assert ErrorSeverity.CRITICAL in error_handler.alert_thresholds
    
    @pytest.mark.asyncio
    async def test_error_handling_basic(self, error_handler, error_context):
        """Test basic error handling."""
        test_error = ValueError("Test error message")
        
        error_record = await error_handler.handle_error(
            error=test_error,
            context=error_context,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION
        )
        
        assert isinstance(error_record, ErrorRecord)
        assert error_record.error_type == "ValueError"
        assert error_record.message == "Test error message"
        assert error_record.severity == ErrorSeverity.MEDIUM
        assert error_record.category == ErrorCategory.VALIDATION
        assert error_record.occurrence_count == 1
    
    def test_error_severity_detection(self, error_handler, error_context):
        """Test automatic error severity detection."""
        # Critical errors
        critical_error = SystemExit("System exit")
        severity = error_handler._detect_error_severity(critical_error, error_context)
        assert severity == ErrorSeverity.CRITICAL
        
        # High severity errors  
        system_error = SystemError("System failure")
        severity = error_handler._detect_error_severity(system_error, error_context)
        assert severity == ErrorSeverity.HIGH
        
        # Medium severity errors
        value_error = ValueError("Invalid value")
        severity = error_handler._detect_error_severity(value_error, error_context)
        assert severity == ErrorSeverity.MEDIUM
    
    def test_error_category_detection(self, error_handler, error_context):
        """Test automatic error category detection."""
        # System errors
        system_error = SystemError("System failure")
        category = error_handler._detect_error_category(system_error, error_context)
        assert category == ErrorCategory.SYSTEM
        
        # Network errors
        network_error = ConnectionError("Connection failed")
        category = error_handler._detect_error_category(network_error, error_context)
        assert category == ErrorCategory.NETWORK
        
        # Validation errors
        validation_error = ValueError("Invalid input")
        category = error_handler._detect_error_category(validation_error, error_context)
        assert category == ErrorCategory.VALIDATION
    
    def test_recovery_strategy_selection(self, error_handler):
        """Test recovery strategy selection logic."""
        context = ErrorContext("test_component", "test_operation")
        
        # Critical errors should require user intervention
        strategy = error_handler._select_recovery_strategy(
            Exception(), ErrorSeverity.CRITICAL, ErrorCategory.SYSTEM
        )
        assert strategy == RecoveryStrategy.USER_INTERVENTION
        
        # Network errors should use retry
        strategy = error_handler._select_recovery_strategy(
            Exception(), ErrorSeverity.MEDIUM, ErrorCategory.NETWORK
        )
        assert strategy == RecoveryStrategy.RETRY
        
        # External service errors should use circuit breaker
        strategy = error_handler._select_recovery_strategy(
            Exception(), ErrorSeverity.MEDIUM, ErrorCategory.EXTERNAL_SERVICE
        )
        assert strategy == RecoveryStrategy.CIRCUIT_BREAKER
    
    @pytest.mark.asyncio
    async def test_error_recovery_retry(self, error_handler, error_context):
        """Test retry recovery mechanism."""
        test_error = ConnectionError("Network timeout")
        
        error_record = await error_handler.handle_error(test_error, error_context)
        
        assert error_record.recovery_attempted == True
        assert error_record.recovery_strategy == RecoveryStrategy.RETRY
    
    @pytest.mark.asyncio
    async def test_error_deduplication(self, error_handler, error_context):
        """Test error deduplication."""
        test_error = ValueError("Duplicate error")
        
        # Handle same error twice
        error_record1 = await error_handler.handle_error(test_error, error_context)
        error_record2 = await error_handler.handle_error(test_error, error_context)
        
        # Should be same error record with increased count
        assert error_record1.error_id == error_record2.error_id
        assert error_record2.occurrence_count == 2
    
    def test_error_statistics(self, error_handler):
        """Test error statistics reporting."""
        stats = error_handler.get_error_statistics()
        
        assert "total_errors" in stats
        assert "performance_metrics" in stats
        assert "severity_distribution" in stats
        assert "category_distribution" in stats
        assert "recovery_statistics" in stats
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self, error_handler, error_context):
        """Test circuit breaker functionality."""
        # Simulate multiple failures to trigger circuit breaker
        for i in range(6):  # Threshold is 5
            await error_handler._handle_circuit_breaker_recovery(
                ErrorRecord(
                    error_id=f"test_{i}",
                    error_type="TestError",
                    message="Test",
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.EXTERNAL_SERVICE,
                    context=error_context,
                    stack_trace="",
                    recovery_strategy=RecoveryStrategy.CIRCUIT_BREAKER
                )
            )
        
        # Check circuit breaker state
        cb = error_handler.circuit_breakers.get("test_component")
        assert cb is not None
        assert cb["state"] == "open"
        assert cb["failure_count"] >= 5


class TestGlobalErrorHandler:
    """Test global error handler functionality."""
    
    @pytest.mark.asyncio
    async def test_global_error_handler(self):
        """Test global error handler function."""
        test_error = RuntimeError("Global test error")
        
        error_record = await handle_error(
            error=test_error,
            component="global_test",
            operation="test_global_handling",
            metadata={"global": True}
        )
        
        assert error_record.error_type == "RuntimeError"
        assert error_record.context.component == "global_test"
        assert error_record.context.operation == "test_global_handling"
        assert error_record.context.metadata["global"] == True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
