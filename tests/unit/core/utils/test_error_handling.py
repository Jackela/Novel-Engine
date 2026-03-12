#!/usr/bin/env python3
"""
Unit tests for error_handling module.

Tests the handle_standard_errors decorator for both sync and async functions,
covering normal execution, exception handling, and various configuration options.
"""

import asyncio

import pytest

from src.core.data_models import ErrorInfo, StandardResponse

pytestmark = pytest.mark.unit
from src.core.utils.error_handling import handle_standard_errors


class TestHandleStandardErrors:
    """Test suite for handle_standard_errors decorator."""

    # ==========================================================================
    # Synchronous Function Tests
    # ==========================================================================

    def test_sync_function_success(self) -> None:
        """Test decorator with successful sync function."""
        @handle_standard_errors("test_operation")
        def success_func() -> StandardResponse:
            return StandardResponse(success=True, data={"result": "ok"})

        result = success_func()
        assert isinstance(result, StandardResponse)
        assert result.success is True
        assert result.data == {"result": "ok"}

    def test_sync_function_with_exception(self) -> None:
        """Test decorator handles sync function exception."""
        @handle_standard_errors("test_operation", "TEST_ERROR", recoverable=False)
        def failing_func() -> StandardResponse:
            raise ValueError("Something went wrong")

        result = failing_func()
        assert isinstance(result, StandardResponse)
        assert result.success is False
        assert isinstance(result.error, ErrorInfo)
        assert result.error.code == "TEST_ERROR"
        assert "test_operation failed" in result.error.message
        assert "Something went wrong" in result.error.message
        assert result.error.recoverable is False

    def test_sync_function_default_error_code(self) -> None:
        """Test decorator generates default error code from operation name."""
        @handle_standard_errors("my operation")
        def failing_func() -> StandardResponse:
            raise RuntimeError("Error occurred")

        result = failing_func()
        assert result.error is not None
        assert result.error.code == "MY_OPERATION_FAILED"

    def test_sync_function_preserves_function_metadata(self) -> None:
        """Test decorator preserves original function metadata."""
        @handle_standard_errors("test_operation")
        def my_function() -> StandardResponse:
            """My docstring."""
            return StandardResponse(success=True)

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    @pytest.mark.parametrize("log_level", ["error", "warning", "info", "debug"])
    def test_sync_function_different_log_levels(self, log_level: str) -> None:
        """Test decorator with different log levels."""
        @handle_standard_errors("test_operation", log_level=log_level)
        def failing_func() -> StandardResponse:
            raise Exception("Test error")

        # Should not raise, just verify it works with different log levels
        result = failing_func()
        assert result.success is False

    # ==========================================================================
    # Asynchronous Function Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_async_function_success(self) -> None:
        """Test decorator with successful async function."""
        @handle_standard_errors("test_operation")
        async def async_success() -> StandardResponse:
            await asyncio.sleep(0)  # Simulate async work
            return StandardResponse(success=True, data={"async_result": "ok"})

        result = await async_success()
        assert isinstance(result, StandardResponse)
        assert result.success is True
        assert result.data == {"async_result": "ok"}

    @pytest.mark.asyncio
    async def test_async_function_with_exception(self) -> None:
        """Test decorator handles async function exception."""
        @handle_standard_errors("async_operation", "ASYNC_ERROR", recoverable=True)
        async def async_failing() -> StandardResponse:
            await asyncio.sleep(0)
            raise RuntimeError("Async error occurred")

        result = await async_failing()
        assert isinstance(result, StandardResponse)
        assert result.success is False
        assert isinstance(result.error, ErrorInfo)
        assert result.error.code == "ASYNC_ERROR"
        assert "async_operation failed" in result.error.message
        assert "Async error occurred" in result.error.message
        assert result.error.recoverable is True

    @pytest.mark.asyncio
    async def test_async_function_default_error_code(self) -> None:
        """Test decorator generates default error code for async function."""
        @handle_standard_errors("async task")
        async def async_failing() -> StandardResponse:
            raise Exception("Error")

        result = await async_failing()
        assert result.error is not None
        assert result.error.code == "ASYNC_TASK_FAILED"

    # ==========================================================================
    # Function Arguments Tests
    # ==========================================================================

    def test_sync_function_with_args_and_kwargs(self) -> None:
        """Test decorator preserves function arguments."""
        @handle_standard_errors("test_operation")
        def func_with_args(a: int, b: str, c: int = 10) -> StandardResponse:
            return StandardResponse(success=True, data={"a": a, "b": b, "c": c})

        result = func_with_args(1, "test", c=20)
        assert result.success is True
        assert result.data == {"a": 1, "b": "test", "c": 20}

    @pytest.mark.asyncio
    async def test_async_function_with_args_and_kwargs(self) -> None:
        """Test decorator preserves async function arguments."""
        @handle_standard_errors("test_operation")
        async def async_func_with_args(x: int, y: str, z: bool = False) -> StandardResponse:
            return StandardResponse(success=True, data={"x": x, "y": y, "z": z})

        result = await async_func_with_args(42, "hello", z=True)
        assert result.success is True
        assert result.data == {"x": 42, "y": "hello", "z": True}

    # ==========================================================================
    # Exception Type Tests
    # ==========================================================================

    @pytest.mark.parametrize("exception_type,message", [
        (ValueError, "Invalid value provided"),
        (TypeError, "Wrong type"),
        (KeyError, "Missing key"),
        (RuntimeError, "Runtime problem"),
        (ZeroDivisionError, "Division by zero"),
        (AttributeError, "Attribute missing"),
    ])
    def test_sync_various_exception_types(self, exception_type: type, message: str) -> None:
        """Test decorator handles various exception types."""
        @handle_standard_errors("test_operation")
        def failing_func() -> StandardResponse:
            raise exception_type(message)

        result = failing_func()
        assert result.success is False
        assert result.error is not None
        assert message in result.error.message

    @pytest.mark.asyncio
    @pytest.mark.parametrize("exception_type,message", [
        (ValueError, "Invalid async value"),
        (RuntimeError, "Async runtime error"),
        (ConnectionError, "Connection failed"),
    ])
    async def test_async_various_exception_types(self, exception_type: type, message: str) -> None:
        """Test decorator handles various async exception types."""
        @handle_standard_errors("async_operation")
        async def async_failing() -> StandardResponse:
            raise exception_type(message)

        result = await async_failing()
        assert result.success is False
        assert result.error is not None
        assert message in result.error.message

    # ==========================================================================
    # Edge Case Tests
    # ==========================================================================

    def test_empty_operation_name(self) -> None:
        """Test decorator with empty operation name."""
        @handle_standard_errors("")
        def func() -> StandardResponse:
            raise Exception("Error")

        result = func()
        assert result.error is not None
        assert " failed" in result.error.message

    def test_operation_name_with_spaces(self) -> None:
        """Test decorator converts spaces to underscores in error code."""
        @handle_standard_errors("my test operation")
        def func() -> StandardResponse:
            raise Exception("Error")

        result = func()
        assert result.error is not None
        assert result.error.code == "MY_TEST_OPERATION_FAILED"

    def test_nested_exception(self) -> None:
        """Test decorator handles nested exception messages."""
        @handle_standard_errors("nested_operation")
        def func() -> StandardResponse:
            try:
                raise ValueError("Inner error")
            except ValueError:
                raise RuntimeError("Outer error")

        result = func()
        assert result.success is False
        assert "Outer error" in result.error.message

    @pytest.mark.asyncio
    async def test_async_empty_operation_name(self) -> None:
        """Test decorator with empty operation name for async function."""
        @handle_standard_errors("")
        async def async_func() -> StandardResponse:
            raise Exception("Error")

        result = await async_func()
        assert result.error is not None
        assert " failed" in result.error.message
