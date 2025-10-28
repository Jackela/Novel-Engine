#!/usr/bin/env python3
"""
Unit Tests for Core Exception Hierarchy

Test-Driven Development approach for custom exception system that provides
better error context and debugging capabilities.
"""

import pytest
from typing import Dict, Any


class TestCustomExceptions:
    """Test custom exception hierarchy."""
    
    def test_novel_engine_base_exception(self):
        """Test base exception with metadata."""
        from src.core.exceptions import NovelEngineException
        
        exc = NovelEngineException(
            "Test error",
            error_code="TEST_001",
            context={"component": "test"}
        )
        
        assert str(exc) == "Test error"
        assert exc.error_code == "TEST_001"
        assert exc.context["component"] == "test"
        assert exc.recoverable is True  # Default
    
    def test_validation_exception(self):
        """Test validation exception with field errors."""
        from src.core.exceptions import ValidationException
        
        exc = ValidationException(
            message="Validation failed",
            field="agent_id",
            value="invalid_id",
            constraint="must be non-empty"
        )
        
        assert exc.field == "agent_id"
        assert exc.value == "invalid_id"
        assert exc.constraint == "must be non-empty"
        assert "agent_id" in str(exc)
    
    def test_resource_not_found_exception(self):
        """Test resource not found exception."""
        from src.core.exceptions import ResourceNotFoundException
        
        exc = ResourceNotFoundException(
            resource_type="Character",
            resource_id="char_123"
        )
        
        assert "Character" in str(exc)
        assert "char_123" in str(exc)
        assert exc.resource_type == "Character"
        assert exc.resource_id == "char_123"
        assert exc.recoverable is False
    
    def test_state_inconsistency_exception(self):
        """Test state inconsistency exception."""
        from src.core.exceptions import StateInconsistencyException
        
        exc = StateInconsistencyException(
            component="MemoryManager",
            expected_state="initialized",
            actual_state="uninitialized",
            action="store_memory"
        )
        
        assert exc.component == "MemoryManager"
        assert exc.expected_state == "initialized"
        assert exc.actual_state == "uninitialized"
        assert exc.action == "store_memory"
        assert "MemoryManager" in str(exc)
    
    def test_llm_exception(self):
        """Test LLM integration exception."""
        from src.core.exceptions import LLMException
        
        exc = LLMException(
            message="Token limit exceeded",
            provider="gemini",
            retry_count=3
        )
        
        assert exc.provider == "gemini"
        assert exc.retry_count == 3
        assert "Token limit exceeded" in str(exc)
    
    def test_memory_exception(self):
        """Test memory system exception."""
        from src.core.exceptions import MemoryException
        
        exc = MemoryException(
            message="Memory storage failed",
            memory_type="episodic",
            agent_id="agent_001"
        )
        
        assert exc.memory_type == "episodic"
        assert exc.agent_id == "agent_001"
        assert "Memory storage failed" in str(exc)
    
    def test_exception_inheritance(self):
        """Test exception hierarchy inheritance."""
        from src.core.exceptions import (
            NovelEngineException,
            ValidationException,
            ResourceNotFoundException,
            StateInconsistencyException,
            LLMException,
            MemoryException
        )
        
        # All exceptions should inherit from NovelEngineException
        assert issubclass(ValidationException, NovelEngineException)
        assert issubclass(ResourceNotFoundException, NovelEngineException)
        assert issubclass(StateInconsistencyException, NovelEngineException)
        assert issubclass(LLMException, NovelEngineException)
        assert issubclass(MemoryException, NovelEngineException)
    
    def test_exception_with_cause(self):
        """Test exception chaining with cause."""
        from src.core.exceptions import LLMException
        
        original_error = ValueError("Invalid token count")
        
        try:
            raise LLMException(
                message="LLM call failed",
                provider="gemini"
            ) from original_error
        except LLMException as e:
            assert e.__cause__ is original_error
            assert isinstance(e.__cause__, ValueError)
    
    def test_exception_recoverable_flag(self):
        """Test recoverable flag on exceptions."""
        from src.core.exceptions import (
            ValidationException,
            ResourceNotFoundException,
            StateInconsistencyException
        )
        
        # Validation errors are recoverable
        val_exc = ValidationException("test", field="test")
        assert val_exc.recoverable is True
        
        # Resource not found is not recoverable
        not_found_exc = ResourceNotFoundException("Character", "id_123")
        assert not_found_exc.recoverable is False
        
        # State inconsistency is not recoverable
        state_exc = StateInconsistencyException(
            component="test", 
            expected_state="init",
            actual_state="uninit"
        )
        assert state_exc.recoverable is False
    
    def test_exception_context_data(self):
        """Test exception context preservation."""
        from src.core.exceptions import NovelEngineException
        
        context = {
            "user_id": "user_123",
            "operation": "character_creation",
            "timestamp": "2025-01-27T10:00:00Z"
        }
        
        exc = NovelEngineException(
            "Operation failed",
            error_code="OP_FAIL",
            context=context
        )
        
        assert exc.context["user_id"] == "user_123"
        assert exc.context["operation"] == "character_creation"
        assert len(exc.context) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
