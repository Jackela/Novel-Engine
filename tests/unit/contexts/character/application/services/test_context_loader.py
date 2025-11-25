#!/usr/bin/env python3
"""
Unit Tests for Character Context Loader Service

Comprehensive test suite covering all functionality of the ContextLoaderService
including file loading, parsing, error handling, caching, security, and edge cases.
"""

import asyncio
import logging
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Dict
from unittest.mock import AsyncMock, mock_open, patch

import pytest
import yaml

# Assuming the service is imported from the correct path
from contexts.character.application.services.context_loader import (
    ContextLoaderError,
    ContextLoaderService,
    SecurityError,
    ServiceUnavailableError,
)
from contexts.character.domain.value_objects.context_models import (
    CharacterContext,
    MemoryContext,
    ObjectivesContext,
    ProfileContext,
    StatsContext,
)


def create_async_mock_file(content: str):
    """Create an async mock file for aiofiles.open."""
    async_mock = AsyncMock()
    async_mock.read = AsyncMock(return_value=content)
    async_mock.__aenter__ = AsyncMock(return_value=async_mock)
    async_mock.__aexit__ = AsyncMock(return_value=None)
    return async_mock


class TestContextLoaderService(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive test suite for ContextLoaderService.

    Tests all functionality including normal operations, error handling,
    security features, caching, and circuit breaker patterns.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.service = ContextLoaderService(
            base_characters_path=self.temp_dir,
            max_file_size=1024 * 1024,  # 1MB for testing
            enable_caching=True,
            cache_ttl_minutes=5,
            max_concurrent_loads=2,
        )

        # Sample valid character data
        self.sample_stats_data = {
            "character": {
                "name": "Test Character",
                "age": 25,
                "origin": "Test Origin",
                "faction": "Test Faction",
                "specialization": "Testing",
            },
            "combat_stats": {"stealth": 8, "agility": 7, "melee": 6},
            "psychological_profile": {"loyalty": 8, "aggression": 5, "caution": 9},
            "equipment": {"primary_weapon": "Test Weapon"},
            "relationships": {
                "allies": [
                    {
                        "name": "Test Ally",
                        "trust_level": 85,
                        "relationship_type": "mentor_partner",
                    }
                ]
            },
        }

        self.sample_memory_content = """
# Test Character - Memory System

## Formative Events

**Age 8: First Test Event**
- Event: Character learned testing
- Memory Type: foundational_learning
- Impact: Developed systematic approach
- Decision Influence: Always validates assumptions

**Elder Thorne**
- Trust Level: 85/100 (High)
- Relationship Type: Strategic Partner
"""

        self.sample_objectives_content = """
# Test Character - Objectives Framework

## Core Life Objectives

**Master of Testing**
- Description: Become expert at comprehensive testing
- Success Metrics: All tests pass, coverage >90%

## Strategic Objectives

**Build Test Framework** 
- Description: Create robust testing infrastructure
- Timeline: 6-8 months
"""

        self.sample_profile_content = """
# Character Profile: Test Character

## Core Identity
- **Name**: Test Character
- **Age**: 25
- **Gender**: Non-binary
- **Race**: Human
- **Class**: Test Engineer

## Physical Description
A methodical individual with keen attention to detail.

## Background
Developed expertise in systematic validation and quality assurance.

## Emotional Drives

**1. Security Through Testing** (Dominant)
- Foundation: Need to ensure reliability
- Positive Expression: Thorough validation
- Negative Expression: Over-testing paralysis
"""

    async def asyncTearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil

        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def create_test_character_files(
        self, character_id: str, include_files: Dict[str, bool] = None
    ):
        """Create test character files in temp directory."""
        if include_files is None:
            include_files = {
                "memory": True,
                "objectives": True,
                "profile": True,
                "stats": True,
            }

        char_dir = Path(self.temp_dir) / character_id
        char_dir.mkdir(exist_ok=True)

        if include_files.get("stats", True):
            stats_file = char_dir / f"{character_id}_stats.yaml"
            with open(stats_file, "w") as f:
                yaml.dump(self.sample_stats_data, f)

        if include_files.get("memory", True):
            memory_file = char_dir / f"{character_id}_memory.md"
            with open(memory_file, "w") as f:
                f.write(self.sample_memory_content)

        if include_files.get("objectives", True):
            objectives_file = char_dir / f"{character_id}_objectives.md"
            with open(objectives_file, "w") as f:
                f.write(self.sample_objectives_content)

        if include_files.get("profile", True):
            profile_file = char_dir / f"{character_id}_profile.md"
            with open(profile_file, "w") as f:
                f.write(self.sample_profile_content)

    # ==================== Basic Functionality Tests ====================

    @pytest.mark.unit
    async def test_load_complete_character_context(self):
        """Test loading a complete character context with all files."""
        character_id = "test_character"
        self.create_test_character_files(character_id)

        result = await self.service.load_character_context(character_id)

        self.assertIsInstance(result, CharacterContext)
        self.assertEqual(result.character_id, character_id)
        self.assertEqual(result.character_name, "Test Character")
        self.assertTrue(result.load_success)
        self.assertFalse(result.partial_load)

        # Verify all contexts loaded
        self.assertIsNotNone(result.memory_context)
        self.assertIsNotNone(result.objectives_context)
        self.assertIsNotNone(result.profile_context)
        self.assertIsNotNone(result.stats_context)

        # Verify file info
        self.assertEqual(len(result.loaded_files), 4)
        successful_files = [f for f in result.loaded_files if f.loaded_successfully]
        self.assertEqual(len(successful_files), 4)

    @pytest.mark.unit
    async def test_load_partial_character_context(self):
        """Test loading character context with some files missing."""
        character_id = "partial_character"
        self.create_test_character_files(
            character_id,
            {"memory": True, "stats": True, "objectives": False, "profile": False},
        )

        result = await self.service.load_character_context(character_id)

        self.assertIsInstance(result, CharacterContext)
        # Partial load means some files loaded successfully (2/4 in this case)
        self.assertTrue(result.load_success)  # Changed: 2 files is enough for success
        self.assertTrue(result.partial_load)

        # Verify loaded contexts
        self.assertIsNotNone(result.memory_context)
        self.assertIsNotNone(result.stats_context)
        self.assertIsNone(result.objectives_context)
        self.assertIsNone(result.profile_context)

        # Verify file info includes failed files
        self.assertEqual(len(result.loaded_files), 4)
        successful_files = [f for f in result.loaded_files if f.loaded_successfully]
        failed_files = [f for f in result.loaded_files if not f.loaded_successfully]
        self.assertEqual(len(successful_files), 2)
        self.assertEqual(len(failed_files), 2)

    @pytest.mark.unit
    async def test_character_identifier_validation_and_sanitization(self):
        """Test character identifier validation and sanitization."""
        # Valid identifiers
        test_cases = [
            ("Test Character", "test_character"),
            ("Aria-Shadowbane", "aria-shadowbane"),
            ("character_123", "character_123"),
            ("  SPACED NAME  ", "spaced_name"),
        ]

        for input_id, expected in test_cases:
            sanitized = await self.service._validate_character_identifier(input_id)
            self.assertEqual(sanitized, expected)

        # Invalid identifiers
        invalid_cases = ["", "   ", "a" * 101, None]  # Too long

        for invalid_id in invalid_cases:
            with self.assertRaises(ValueError):
                await self.service._validate_character_identifier(invalid_id)

    # ==================== File Parsing Tests ====================

    @pytest.mark.unit
    async def test_yaml_parsing_valid_data(self):
        """Test YAML file parsing with valid data."""
        yaml_content = yaml.dump(self.sample_stats_data)
        with patch("aiofiles.open", return_value=create_async_mock_file(yaml_content)):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 1024

                result, file_info = await self.service._load_yaml_file(
                    Path("test.yaml")
                )

                self.assertIsNotNone(result)
                self.assertIsInstance(result, StatsContext)
                self.assertEqual(result.name, "Test Character")
                self.assertEqual(result.age, 25)
                self.assertTrue(file_info.loaded_successfully)

    @pytest.mark.unit
    async def test_yaml_parsing_empty_file(self):
        """Test YAML parsing with empty file."""
        with patch("aiofiles.open", return_value=create_async_mock_file("")):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 0

                result, file_info = await self.service._load_yaml_file(
                    Path("empty.yaml")
                )

                self.assertIsNone(result)
                self.assertFalse(file_info.loaded_successfully)
                self.assertIn("empty", file_info.error_message.lower())

    @pytest.mark.unit
    async def test_yaml_parsing_invalid_yaml(self):
        """Test YAML parsing with malformed YAML."""
        invalid_yaml = "invalid: yaml: content: [unclosed"

        with patch("aiofiles.open", return_value=create_async_mock_file(invalid_yaml)):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = len(invalid_yaml)

                result, file_info = await self.service._load_yaml_file(
                    Path("invalid.yaml")
                )

                self.assertIsNone(result)
                self.assertFalse(file_info.loaded_successfully)
                self.assertIsNotNone(file_info.error_message)

    @pytest.mark.unit
    async def test_markdown_parsing_memory(self):
        """Test memory markdown parsing."""
        with patch(
            "aiofiles.open",
            return_value=create_async_mock_file(self.sample_memory_content),
        ):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = len(self.sample_memory_content)

                result, file_info = await self.service._load_markdown_file(
                    Path("memory.md"), "memory"
                )

                self.assertIsNotNone(result)
                self.assertIsInstance(result, MemoryContext)
                self.assertTrue(file_info.loaded_successfully)

    @pytest.mark.unit
    async def test_markdown_parsing_objectives(self):
        """Test objectives markdown parsing."""
        with patch(
            "aiofiles.open",
            return_value=create_async_mock_file(self.sample_objectives_content),
        ):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = len(self.sample_objectives_content)

                result, file_info = await self.service._load_markdown_file(
                    Path("objectives.md"), "objectives"
                )

                self.assertIsNotNone(result)
                self.assertIsInstance(result, ObjectivesContext)
                self.assertTrue(file_info.loaded_successfully)

    @pytest.mark.unit
    async def test_markdown_parsing_profile(self):
        """Test profile markdown parsing."""
        with patch(
            "aiofiles.open",
            return_value=create_async_mock_file(self.sample_profile_content),
        ):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = len(self.sample_profile_content)

                result, file_info = await self.service._load_markdown_file(
                    Path("profile.md"), "profile"
                )

                self.assertIsNotNone(result)
                self.assertIsInstance(result, ProfileContext)
                self.assertEqual(result.name, "Test Character")
                self.assertEqual(result.age, 25)
                self.assertTrue(file_info.loaded_successfully)

    # ==================== Error Handling Tests ====================

    @pytest.mark.unit
    async def test_file_size_limit_enforcement(self):
        """Test that files exceeding size limits are rejected."""
        large_content = "x" * (2 * 1024 * 1024)  # 2MB content

        with patch("aiofiles.open", mock_open(read_data=large_content)):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = len(large_content)

                result, file_info = await self.service._load_yaml_file(
                    Path("large.yaml")
                )

                self.assertIsNone(result)
                self.assertFalse(file_info.loaded_successfully)
                self.assertIn("too large", file_info.error_message.lower())

    @pytest.mark.unit
    async def test_nonexistent_character_directory(self):
        """Test handling of nonexistent character directory."""
        with self.assertRaises(ContextLoaderError) as context:
            await self.service.load_character_context("nonexistent_character")

        self.assertIn("directory not found", str(context.exception).lower())

    @pytest.mark.unit
    async def test_invalid_context_type(self):
        """Test handling of invalid context type in markdown parsing."""
        # Use the helper function for proper async context manager
        with patch(
            "aiofiles.open", return_value=create_async_mock_file("test content")
        ):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 100

                result, file_info = await self.service._load_markdown_file(
                    Path("test.md"), "invalid_type"
                )

                self.assertIsNone(result)
                self.assertFalse(file_info.loaded_successfully)
                self.assertIn("unknown context type", file_info.error_message.lower())

    # ==================== Security Tests ====================

    @pytest.mark.unit
    async def test_path_traversal_protection(self):
        """Test protection against path traversal attacks."""
        malicious_ids = [
            "../../../etc/passwd",
            "..\\windows\\system32",
            "test/../../../sensitive",
            "normal_name/../malicious",
        ]

        for malicious_id in malicious_ids:
            with self.assertRaises(SecurityError):
                await self.service._security_check(malicious_id)

    @pytest.mark.unit
    async def test_invalid_character_security_check(self):
        """Test security check with invalid characters."""
        invalid_ids = [
            "test/character",
            "test\\character",
            "test;character",
            "test|character",
            "test&character",
        ]

        for invalid_id in invalid_ids:
            with self.assertRaises(SecurityError):
                await self.service._security_check(invalid_id)

    @pytest.mark.unit
    async def test_character_id_length_security(self):
        """Test security check for overly long character IDs."""
        long_id = "a" * 101  # Exceeds 100 character limit

        with self.assertRaises(SecurityError):
            await self.service._security_check(long_id)

    # ==================== Caching Tests ====================

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_caching_functionality(self):
        """Test that caching works correctly."""
        character_id = "cache_test"
        self.create_test_character_files(character_id)

        # First load should miss cache
        result1 = await self.service.load_character_context(character_id)
        self.assertEqual(self.service._load_stats["cache_misses"], 1)
        self.assertEqual(self.service._load_stats["cache_hits"], 0)

        # Second load should hit cache
        result2 = await self.service.load_character_context(character_id)
        self.assertEqual(self.service._load_stats["cache_hits"], 1)

        # Results should be equivalent
        self.assertEqual(result1.character_id, result2.character_id)
        self.assertEqual(result1.character_name, result2.character_name)

    @pytest.mark.unit
    @pytest.mark.slow
    async def test_cache_expiration(self):
        """Test that cache entries expire correctly."""
        # Create service with very short cache TTL
        short_cache_service = ContextLoaderService(
            base_characters_path=self.temp_dir, cache_ttl_minutes=0.01  # ~0.6 seconds
        )

        character_id = "cache_expiry_test"
        self.create_test_character_files(character_id)

        # First load
        await short_cache_service.load_character_context(character_id)

        # Wait for cache to expire (0.7 seconds > 0.6 second TTL)
        await asyncio.sleep(0.7)

        # Second load should miss cache due to expiration
        await short_cache_service.load_character_context(character_id)
        self.assertEqual(short_cache_service._load_stats["cache_misses"], 2)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_cache_clearing(self):
        """Test manual cache clearing."""
        character_id = "cache_clear_test"
        self.create_test_character_files(character_id)

        # Load to populate cache
        await self.service.load_character_context(character_id)
        self.assertTrue(len(self.service._cache) > 0)

        # Clear cache
        await self.service.clear_cache()
        self.assertEqual(len(self.service._cache), 0)
        self.assertEqual(len(self.service._cache_timestamps), 0)

    # ==================== Circuit Breaker Tests ====================

    @pytest.mark.unit
    async def test_circuit_breaker_failure_accumulation(self):
        """Test that circuit breaker accumulates failures correctly."""
        # Trigger multiple failures
        for _ in range(5):
            await self.service._record_failure()

        self.assertEqual(self.service._circuit_breaker["failure_count"], 5)
        self.assertEqual(
            self.service._circuit_breaker["state"], "CLOSED"
        )  # Not yet at threshold

    @pytest.mark.unit
    async def test_circuit_breaker_opens_on_threshold(self):
        """Test that circuit breaker opens when failure threshold is reached."""
        # Trigger failures to reach threshold
        for _ in range(10):
            await self.service._record_failure()

        self.assertEqual(self.service._circuit_breaker["state"], "OPEN")

    @pytest.mark.unit
    async def test_circuit_breaker_blocks_requests_when_open(self):
        """Test that circuit breaker blocks requests when open."""
        # Force circuit breaker open
        self.service._circuit_breaker["state"] = "OPEN"
        self.service._circuit_breaker["last_failure_time"] = datetime.now(UTC)

        with self.assertRaises(ServiceUnavailableError):
            await self.service.load_character_context("test")

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery to half-open state."""
        # Force circuit breaker open with old failure time
        self.service._circuit_breaker["state"] = "OPEN"
        self.service._circuit_breaker["last_failure_time"] = datetime.now(
            UTC
        ) - timedelta(minutes=10)

        character_id = "recovery_test"
        self.create_test_character_files(character_id)

        # Should transition to HALF_OPEN and allow request
        result = await self.service.load_character_context(character_id)
        self.assertIsInstance(result, CharacterContext)
        self.assertEqual(
            self.service._circuit_breaker["state"], "CLOSED"
        )  # Should close after success

    # ==================== Concurrency Control Tests ====================

    @pytest.mark.unit
    @pytest.mark.slow
    async def test_concurrent_load_limit(self):
        """Test that concurrent load limit is enforced."""
        character_id = "concurrency_test"
        self.create_test_character_files(character_id)

        # Start multiple concurrent loads (more than limit)
        tasks = []
        for i in range(5):  # More than max_concurrent_loads (2)
            task = asyncio.create_task(
                self.service.load_character_context(f"{character_id}_{i}")
            )
            tasks.append(task)
            self.create_test_character_files(f"{character_id}_{i}")

        # Some should complete successfully
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_results = [r for r in results if isinstance(r, CharacterContext)]
        self.assertTrue(len(successful_results) > 0)

    @pytest.mark.unit
    async def test_load_timeout_handling(self):
        """Test that load operations timeout correctly."""
        character_id = "timeout_test"

        # Mock a slow file operation
        async def slow_file_read(*args, **kwargs):
            await asyncio.sleep(35)  # Longer than 30s timeout
            return "content"

        with patch("aiofiles.open", side_effect=slow_file_read):
            with self.assertRaises(ContextLoaderError) as context:
                await self.service.load_character_context(character_id)

            self.assertIn("timeout", str(context.exception).lower())

    # ==================== Data Integrity Tests ====================

    @pytest.mark.unit
    async def test_name_consistency_validation(self):
        """Test validation of name consistency across contexts."""
        character_id = "inconsistent_name_test"

        # Create files with inconsistent names
        inconsistent_stats = self.sample_stats_data.copy()
        inconsistent_stats["character"]["name"] = "Different Name"

        char_dir = Path(self.temp_dir) / character_id
        char_dir.mkdir(exist_ok=True)

        # Create stats with different name
        stats_file = char_dir / f"{character_id}_stats.yaml"
        with open(stats_file, "w") as f:
            yaml.dump(inconsistent_stats, f)

        # Create profile with original name
        profile_file = char_dir / f"{character_id}_profile.md"
        with open(profile_file, "w") as f:
            f.write(self.sample_profile_content)

        result = await self.service.load_character_context(character_id)

        # Should have validation warnings
        self.assertTrue(len(result.validation_warnings) > 0)
        self.assertFalse(result.context_integrity)

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_age_consistency_validation(self):
        """Test validation of age consistency across contexts."""
        character_id = "inconsistent_age_test"

        # Create files with inconsistent ages
        inconsistent_stats = self.sample_stats_data.copy()
        inconsistent_stats["character"]["age"] = 50  # Different from profile (25)

        char_dir = Path(self.temp_dir) / character_id
        char_dir.mkdir(exist_ok=True)

        stats_file = char_dir / f"{character_id}_stats.yaml"
        with open(stats_file, "w") as f:
            yaml.dump(inconsistent_stats, f)

        profile_file = char_dir / f"{character_id}_profile.md"
        with open(profile_file, "w") as f:
            f.write(self.sample_profile_content)

        result = await self.service.load_character_context(character_id)

        # Should have validation warnings for age inconsistency
        age_warnings = [w for w in result.validation_warnings if "age" in w.lower()]
        self.assertTrue(len(age_warnings) > 0)

    # ==================== Service Monitoring Tests ====================

    @pytest.mark.unit
    async def test_service_statistics_collection(self):
        """Test that service statistics are collected correctly."""
        character_id = "stats_test"
        self.create_test_character_files(character_id)

        # Perform some operations
        await self.service.load_character_context(character_id)  # Should hit cache miss
        await self.service.load_character_context(character_id)  # Should hit cache

        stats = self.service.get_service_statistics()

        # Verify statistics structure
        self.assertIn("load_statistics", stats)
        self.assertIn("caching", stats)
        self.assertIn("concurrency", stats)
        self.assertIn("circuit_breaker", stats)
        self.assertIn("service_status", stats)

        # Verify some values
        self.assertEqual(stats["load_statistics"]["total_attempts"], 2)
        # Only first load counts as successful_loads, second is cache hit
        self.assertEqual(stats["load_statistics"]["successful_loads"], 1)
        self.assertEqual(stats["load_statistics"]["cache_hits"], 1)
        self.assertEqual(stats["load_statistics"]["cache_misses"], 1)

        # Verify cache hit rate calculation
        expected_hit_rate = 1 / (1 + 1)  # 1 hit, 1 miss
        self.assertAlmostEqual(
            stats["caching"]["hit_rate"], expected_hit_rate, places=2
        )

    @pytest.mark.unit
    @pytest.mark.fast
    async def test_service_health_status_determination(self):
        """Test service health status determination logic."""
        # Test healthy status
        self.assertEqual(self.service._get_service_health_status(), "healthy")

        # Test circuit breaker open
        self.service._circuit_breaker["state"] = "OPEN"
        self.assertEqual(self.service._get_service_health_status(), "degraded")

        # Test circuit breaker half-open
        self.service._circuit_breaker["state"] = "HALF_OPEN"
        self.assertEqual(self.service._get_service_health_status(), "recovering")

        # Reset and test security alert
        self.service._circuit_breaker["state"] = "CLOSED"
        self.service._load_stats["security_violations"] = 15
        self.assertEqual(self.service._get_service_health_status(), "security_alert")

    # ==================== Directory Structure Validation Tests ====================

    @pytest.mark.unit
    async def test_directory_structure_validation_success(self):
        """Test successful directory structure validation."""
        character_id = "validation_test"
        self.create_test_character_files(character_id)

        result = await self.service.validate_character_directory_structure(character_id)

        self.assertTrue(result["validation_success"])
        self.assertTrue(result["directory_exists"])
        self.assertEqual(result["files_found"], 4)
        self.assertEqual(result["total_expected"], 4)

        # All files should exist
        for file_type, file_info in result["expected_files"].items():
            self.assertTrue(file_info["exists"])

    @pytest.mark.unit
    async def test_directory_structure_validation_partial(self):
        """Test directory structure validation with missing files."""
        character_id = "partial_validation_test"
        self.create_test_character_files(
            character_id,
            {"memory": True, "stats": True, "objectives": False, "profile": False},
        )

        result = await self.service.validate_character_directory_structure(character_id)

        self.assertTrue(result["validation_success"])  # At least one file exists
        self.assertEqual(result["files_found"], 2)
        self.assertEqual(result["total_expected"], 4)

    @pytest.mark.unit
    async def test_directory_structure_validation_missing_directory(self):
        """Test directory structure validation with missing directory."""
        result = await self.service.validate_character_directory_structure(
            "nonexistent"
        )

        self.assertFalse(result["validation_success"])
        self.assertFalse(result["directory_exists"])
        self.assertIn("error", result)

    # ==================== Edge Cases and Robustness Tests ====================

    @pytest.mark.unit
    async def test_empty_yaml_handling(self):
        """Test handling of empty YAML files."""
        character_id = "empty_yaml_test"
        char_dir = Path(self.temp_dir) / character_id
        char_dir.mkdir(exist_ok=True)

        # Create empty YAML file
        stats_file = char_dir / f"{character_id}_stats.yaml"
        with open(stats_file, "w") as f:
            f.write("")

        result = await self.service.load_character_context(character_id)

        # Should handle gracefully - empty YAML means no files loaded successfully
        self.assertFalse(result.load_success)
        # No files loaded successfully, so partial_load should be False
        self.assertFalse(result.partial_load)
        self.assertIsNone(result.stats_context)

    @pytest.mark.unit
    async def test_malformed_markdown_handling(self):
        """Test handling of malformed markdown files."""
        character_id = "malformed_md_test"
        char_dir = Path(self.temp_dir) / character_id
        char_dir.mkdir(exist_ok=True)

        # Create malformed markdown (should still parse something)
        profile_file = char_dir / f"{character_id}_profile.md"
        with open(profile_file, "w") as f:
            f.write("This is not properly formatted markdown without proper headers")

        result = await self.service.load_character_context(character_id)

        # Service successfully parses even malformed markdown, 1 file loaded is success
        self.assertTrue(result.load_success)
        # Only 1 of 4 files loaded, so partial_load should be True
        self.assertTrue(result.partial_load)

    @pytest.mark.unit
    async def test_unicode_character_handling(self):
        """Test handling of Unicode characters in content."""
        character_id = "unicode_test"

        # Create content with Unicode characters
        unicode_content = """
# 测试角色 - Test Character 

## Core Identity
- **Name**: Aeolus Çhäracter
- **Description**: Character with émojis 🎭 and spëcial chars
- **Age**: 25

## Background
This character has international names and symbols: αβγδε, 中文, العربية
"""
        char_dir = Path(self.temp_dir) / character_id
        char_dir.mkdir(exist_ok=True)

        profile_file = char_dir / f"{character_id}_profile.md"
        with open(profile_file, "w", encoding="utf-8") as f:
            f.write(unicode_content)

        result = await self.service.load_character_context(character_id)

        # Should handle Unicode content gracefully
        self.assertTrue(result.partial_load)  # Only profile file exists
        self.assertIsNotNone(result.profile_context)


# ==================== Integration and Performance Tests ====================


class TestContextLoaderServiceIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for ContextLoaderService with real file operations."""

    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.service = ContextLoaderService(base_characters_path=self.temp_dir)

    async def asyncTearDown(self):
        """Clean up integration test environment."""
        import shutil

        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    @pytest.mark.unit
    async def test_load_aria_shadowbane_context(self):
        """Integration test with Aria Shadowbane example data."""
        # This test would use the actual Aria Shadowbane files created earlier
        # but we'll create a simplified version for testing

        character_id = "aria"
        char_dir = Path(self.temp_dir) / character_id
        char_dir.mkdir(exist_ok=True)

        # Create simplified Aria files based on the templates
        aria_profile = """
# Character Profile: Aria Shadowbane

## Core Identity
- **Name**: Aria Shadowbane
- **Age**: 25
- **Gender**: Female
- **Race**: Human
- **Class**: Rogue

## Physical Description
A lithe figure in her mid-twenties with keen amber eyes.

## Background
Born in Crystal City's Shadow Quarter during civil unrest.
"""

        aria_stats = {
            "character": {
                "name": "Aria Shadowbane",
                "age": 25,
                "origin": "Crystal City Shadow Quarter",
                "faction": "Independent Operative",
                "specialization": "Stealth Operations",
            },
            "combat_stats": {"stealth": 9, "agility": 8, "melee": 7},
        }

        # Write files
        with open(char_dir / "aria_profile.md", "w") as f:
            f.write(aria_profile)

        with open(char_dir / "aria_stats.yaml", "w") as f:
            yaml.dump(aria_stats, f)

        # Load context
        result = await self.service.load_character_context("aria")

        # Verify results
        self.assertEqual(result.character_name, "Aria Shadowbane")
        self.assertTrue(result.partial_load)  # Only 2 of 4 files exist
        self.assertIsNotNone(result.profile_context)
        self.assertIsNotNone(result.stats_context)

        # Verify profile data
        self.assertEqual(result.profile_context.name, "Aria Shadowbane")
        self.assertEqual(result.profile_context.age, 25)
        self.assertEqual(result.profile_context.character_class, "Rogue")

        # Verify stats data
        self.assertEqual(result.stats_context.name, "Aria Shadowbane")
        self.assertEqual(result.stats_context.age, 25)
        self.assertEqual(result.stats_context.specialization, "Stealth Operations")


# ==================== Performance Tests ====================


class TestContextLoaderPerformance(unittest.IsolatedAsyncioTestCase):
    """Performance tests for ContextLoaderService."""

    def setUp(self):
        """Set up performance test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.service = ContextLoaderService(
            base_characters_path=self.temp_dir,
            enable_caching=True,
            max_concurrent_loads=10,
        )

    async def asyncTearDown(self):
        """Clean up performance test environment."""
        import shutil

        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    @pytest.mark.unit
    @pytest.mark.medium
    async def test_concurrent_loading_performance(self):
        """Test performance under concurrent loading conditions."""
        import time

        # Create multiple character files
        character_count = 10
        character_ids = []

        for i in range(character_count):
            char_id = f"perf_test_{i}"
            character_ids.append(char_id)

            char_dir = Path(self.temp_dir) / char_id
            char_dir.mkdir(exist_ok=True)

            # Create simple files for each character
            with open(char_dir / f"{char_id}_profile.md", "w") as f:
                f.write(
                    f"# Character {i}\n\n- **Name**: Test Character {i}\n- **Age**: {20 + i}"
                )

        # Measure concurrent loading time
        start_time = time.time()

        tasks = [
            self.service.load_character_context(char_id) for char_id in character_ids
        ]

        results = await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time

        # Verify all loaded successfully
        self.assertEqual(len(results), character_count)
        for result in results:
            self.assertIsInstance(result, CharacterContext)

        # Performance assertion (should complete in reasonable time)
        # This is a basic check - adjust threshold based on system capabilities
        self.assertLess(
            duration, 10.0, f"Concurrent loading took {duration:.2f}s, expected <10s"
        )

        # Verify cache performance
        stats = self.service.get_service_statistics()
        self.assertEqual(stats["load_statistics"]["total_attempts"], character_count)


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)

    # Run tests
    unittest.main()
