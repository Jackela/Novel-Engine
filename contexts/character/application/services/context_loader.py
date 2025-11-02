#!/usr/bin/env python3
"""
Character Context Loader Service

This service implements the User-Generated Content Framework context loading
capability, providing robust file parsing and structured data consolidation
for character context files (memory, objectives, profile, stats).

Following DDD principles and backend reliability patterns for production use.
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import yaml

from ...domain.value_objects.context_models import (
    CharacterContext,
    CombatStats,
    EmotionalDrive,
    FormativeEvent,
    LoadedFileInfo,
    MemoryContext,
    MemoryType,
    Objective,
    ObjectivesContext,
    ObjectiveStatus,
    ObjectiveTier,
    ProfileContext,
    PsychologicalProfile,
    RelationshipEntry,
    RelationshipMemory,
    RelationshipType,
    StatsContext,
    TrustLevel,
)

logger = logging.getLogger(__name__)


class ContextLoaderError(Exception):
    """Base exception for context loading errors."""

    pass


class FileParsingError(ContextLoaderError):
    """Exception raised when file parsing fails."""

    pass


class ValidationError(ContextLoaderError):
    """Exception raised when data validation fails."""

    pass


class SecurityError(ContextLoaderError):
    """Exception raised when security violations are detected."""

    pass


class ServiceUnavailableError(ContextLoaderError):
    """Exception raised when service is temporarily unavailable."""

    pass


class ContextLoaderService:
    """
    Service for loading and parsing character context files.

    This service provides robust file loading, parsing, and validation
    capabilities for the Character Context Engineering Framework. It handles
    multiple file formats, graceful error recovery, and comprehensive validation.

    Backend Reliability Principles:
    - Fail-safe file operations with comprehensive error handling
    - Input validation and sanitization for security
    - Structured logging for operational monitoring
    - Graceful degradation when files are missing or corrupted
    - Data integrity validation across loaded contexts
    """

    def __init__(
        self,
        base_characters_path: str = "characters",
        max_file_size: int = 10 * 1024 * 1024,
        enable_caching: bool = True,
        cache_ttl_minutes: int = 30,
        max_concurrent_loads: int = 5,
    ):
        """
        Initialize the context loader service.

        Args:
            base_characters_path: Base directory for character files
            max_file_size: Maximum allowed file size in bytes (default: 10MB)
            enable_caching: Whether to enable context caching
            cache_ttl_minutes: Cache time-to-live in minutes
            max_concurrent_loads: Maximum concurrent load operations
        """
        self.base_path = Path(base_characters_path)
        self.max_file_size = max_file_size
        self.logger = logger.getChild(self.__class__.__name__)

        # Security and reliability configuration
        self.max_concurrent_loads = max_concurrent_loads
        self._load_semaphore = asyncio.Semaphore(max_concurrent_loads)
        self._active_loads = set()

        # File naming conventions for context files
        self.file_patterns = {
            "memory": "_memory.md",
            "objectives": "_objectives.md",
            "profile": "_profile.md",
            "stats": "_stats.yaml",
        }

        # Security whitelist for file extensions
        self.allowed_extensions = {".md", ".yaml", ".yml"}

        # Caching system
        self.enable_caching = enable_caching
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self._cache = {}
        self._cache_timestamps = {}

        # Initialize monitoring counters
        self._load_stats = {
            "total_attempts": 0,
            "successful_loads": 0,
            "partial_loads": 0,
            "failed_loads": 0,
            "security_violations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Circuit breaker for resilience
        self._circuit_breaker = {
            "failure_count": 0,
            "failure_threshold": 10,
            "recovery_timeout": timedelta(minutes=5),
            "last_failure_time": None,
            "state": "CLOSED",  # CLOSED, OPEN, HALF_OPEN
        }

        self.logger.info(
            f"ContextLoaderService initialized: base_path={self.base_path}, "
            f"max_file_size={max_file_size/1024/1024:.1f}MB, "
            f"caching={enable_caching}, concurrent_limit={max_concurrent_loads}"
        )

    async def load_character_context(
        self, character_identifier: str
    ) -> CharacterContext:
        """
        Load complete character context from files.

        This is the primary service method that orchestrates loading all
        context files for a character and consolidates them into a single
        structured representation. Enhanced with caching, concurrency control,
        and circuit breaker pattern for production reliability.

        Args:
            character_identifier: Character identifier (name or ID)

        Returns:
            CharacterContext: Consolidated context data

        Raises:
            ContextLoaderError: If critical loading errors occur
            ValueError: If character_identifier is invalid
            ServiceUnavailableError: If service is circuit-broken
            SecurityError: If security violations are detected
        """
        self._load_stats["total_attempts"] += 1
        start_time = datetime.now(UTC)

        # Check circuit breaker
        await self._check_circuit_breaker()

        self.logger.info(f"Loading character context for: {character_identifier}")

        # Acquire load semaphore to control concurrency
        async with self._load_semaphore:
            try:
                # Track active load
                load_id = f"{character_identifier}_{start_time.timestamp()}"
                self._active_loads.add(load_id)

                try:
                    # Validate and sanitize input
                    sanitized_id = await self._validate_character_identifier(
                        character_identifier
                    )

                    # Check cache first
                    if self.enable_caching:
                        cached_result = await self._get_from_cache(sanitized_id)
                        if cached_result:
                            self._load_stats["cache_hits"] += 1
                            self.logger.debug(f"Cache hit for {character_identifier}")
                            return cached_result
                        else:
                            self._load_stats["cache_misses"] += 1

                    # Security validation
                    await self._security_check(sanitized_id)

                    # Locate character directory
                    character_dir = await self._find_character_directory(sanitized_id)

                    # Load all context files with timeout
                    context_data = await asyncio.wait_for(
                        self._load_all_context_files(character_dir, sanitized_id),
                        timeout=30.0,  # 30 second timeout
                    )

                    # Validate and create consolidated context
                    character_context = await self._create_character_context(
                        sanitized_id, context_data, character_dir
                    )

                    # Enhanced data integrity validation
                    await self._validate_context_integrity(character_context)

                    # Cache result if successful
                    if self.enable_caching and character_context.load_success:
                        await self._store_in_cache(sanitized_id, character_context)

                    # Update statistics
                    if character_context.load_success:
                        self._load_stats["successful_loads"] += 1
                        await self._record_success()
                    elif character_context.partial_load:
                        self._load_stats["partial_loads"] += 1
                        await self._record_partial_failure()
                    else:
                        self._load_stats["failed_loads"] += 1
                        await self._record_failure()

                    load_duration = (datetime.now(UTC) - start_time).total_seconds()
                    self.logger.info(
                        f"Context loading completed for {character_identifier} "
                        f"in {load_duration:.2f}s - Success: {character_context.load_success}, "
                        f"Partial: {character_context.partial_load}"
                    )

                    return character_context

                finally:
                    self._active_loads.discard(load_id)

            except asyncio.TimeoutError:
                await self._record_failure()
                self.logger.error(f"Context loading timeout for {character_identifier}")
                raise ContextLoaderError(
                    "Context loading timeout - operation took too long"
                )

            except SecurityError as e:
                self._load_stats["security_violations"] += 1
                self.logger.error(f"Security violation for {character_identifier}: {e}")
                raise

            except Exception as e:
                await self._record_failure()
                self.logger.error(
                    f"Failed to load context for {character_identifier}: {e}"
                )
                raise ContextLoaderError(f"Context loading failed: {str(e)}") from e

    async def _validate_character_identifier(self, identifier: str) -> str:
        """
        Validate and sanitize character identifier.

        Args:
            identifier: Raw character identifier

        Returns:
            str: Sanitized identifier

        Raises:
            ValueError: If identifier is invalid
        """
        if not identifier or not isinstance(identifier, str):
            raise ValueError("Character identifier must be a non-empty string")

        # Sanitize for filesystem safety
        sanitized = re.sub(r"[^\w\-_\s]", "", identifier.strip())
        if not sanitized:
            raise ValueError(
                f"Character identifier contains no valid characters: {identifier}"
            )

        # Convert to filesystem-safe format (lowercase with underscores)
        sanitized = re.sub(r"\s+", "_", sanitized.lower())

        if len(sanitized) > 100:
            raise ValueError(
                f"Character identifier too long (max 100 chars): {identifier}"
            )

        self.logger.debug(f"Sanitized identifier: {identifier} -> {sanitized}")
        return sanitized

    async def _find_character_directory(self, character_id: str) -> Path:
        """
        Locate character directory in filesystem.

        Args:
            character_id: Sanitized character identifier

        Returns:
            Path: Path to character directory

        Raises:
            ContextLoaderError: If directory not found
        """
        character_dir = self.base_path / character_id

        if not character_dir.exists():
            self.logger.warning(f"Character directory not found: {character_dir}")
            raise ContextLoaderError(
                f"Character directory not found for: {character_id}"
            )

        if not character_dir.is_dir():
            raise ContextLoaderError(
                f"Character path is not a directory: {character_dir}"
            )

        self.logger.debug(f"Found character directory: {character_dir}")
        return character_dir

    async def _load_all_context_files(
        self, character_dir: Path, character_id: str
    ) -> Dict[str, Any]:
        """
        Load all context files for a character.

        Args:
            character_dir: Path to character directory
            character_id: Character identifier

        Returns:
            Dict containing loaded context data and file info
        """
        context_data = {"loaded_files": [], "contexts": {}}

        # Load each context file type
        for context_type, file_suffix in self.file_patterns.items():
            try:
                file_path = character_dir / f"{character_id}{file_suffix}"

                if file_path.exists():
                    self.logger.debug(f"Loading {context_type} file: {file_path}")

                    # Load and parse file based on type
                    if context_type == "stats":
                        parsed_data, file_info = await self._load_yaml_file(file_path)
                    else:
                        parsed_data, file_info = await self._load_markdown_file(
                            file_path, context_type
                        )

                    context_data["contexts"][context_type] = parsed_data
                    context_data["loaded_files"].append(file_info)

                else:
                    self.logger.info(f"Optional file not found: {file_path}")
                    # Create file info for missing file
                    context_data["loaded_files"].append(
                        LoadedFileInfo(
                            file_name=f"{character_id}{file_suffix}",
                            file_path=str(file_path),
                            loaded_successfully=False,
                            error_message="File not found",
                        )
                    )

            except Exception as e:
                self.logger.error(f"Error loading {context_type} file: {e}")
                context_data["loaded_files"].append(
                    LoadedFileInfo(
                        file_name=f"{character_id}{file_suffix}",
                        file_path=str(character_dir / f"{character_id}{file_suffix}"),
                        loaded_successfully=False,
                        error_message=str(e),
                    )
                )

        return context_data

    async def _load_yaml_file(
        self, file_path: Path
    ) -> Tuple[Optional[StatsContext], LoadedFileInfo]:
        """
        Load and parse YAML stats file.

        Args:
            file_path: Path to YAML file

        Returns:
            Tuple of parsed StatsContext and LoadedFileInfo
        """
        file_info = LoadedFileInfo(
            file_name=file_path.name,
            file_path=str(file_path),
            loaded_successfully=False,
        )

        try:
            # Security check: file size
            file_size = file_path.stat().st_size
            file_info.file_size_bytes = file_size

            if file_size > self.max_file_size:
                raise FileParsingError(
                    f"File too large: {file_size} bytes (max: {self.max_file_size})"
                )

            # Load YAML content
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                content = await f.read()

            if not content.strip():
                raise FileParsingError("YAML file is empty")

            # Parse YAML
            yaml_data = yaml.safe_load(content)
            if not yaml_data:
                raise FileParsingError("YAML file contains no data")

            # Convert to StatsContext model
            stats_context = await self._parse_stats_data(yaml_data)

            file_info.loaded_successfully = True
            self.logger.debug(f"Successfully loaded YAML file: {file_path}")

            return stats_context, file_info

        except Exception as e:
            error_msg = f"YAML parsing error: {str(e)}"
            file_info.error_message = error_msg
            self.logger.error(f"Failed to load YAML file {file_path}: {error_msg}")
            return None, file_info

    async def _load_markdown_file(
        self, file_path: Path, context_type: str
    ) -> Tuple[Optional[Any], LoadedFileInfo]:
        """
        Load and parse Markdown context file.

        Args:
            file_path: Path to Markdown file
            context_type: Type of context (memory, objectives, profile)

        Returns:
            Tuple of parsed context model and LoadedFileInfo
        """
        file_info = LoadedFileInfo(
            file_name=file_path.name,
            file_path=str(file_path),
            loaded_successfully=False,
        )

        try:
            # Security check: file size
            file_size = file_path.stat().st_size
            file_info.file_size_bytes = file_size

            if file_size > self.max_file_size:
                raise FileParsingError(
                    f"File too large: {file_size} bytes (max: {self.max_file_size})"
                )

            # Load Markdown content
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                content = await f.read()

            if not content.strip():
                raise FileParsingError("Markdown file is empty")

            # Parse based on context type
            if context_type == "memory":
                parsed_context = await self._parse_memory_markdown(content)
            elif context_type == "objectives":
                parsed_context = await self._parse_objectives_markdown(content)
            elif context_type == "profile":
                parsed_context = await self._parse_profile_markdown(content)
            else:
                raise FileParsingError(f"Unknown context type: {context_type}")

            file_info.loaded_successfully = True
            self.logger.debug(f"Successfully loaded {context_type} file: {file_path}")

            return parsed_context, file_info

        except Exception as e:
            error_msg = f"Markdown parsing error: {str(e)}"
            file_info.error_message = error_msg
            self.logger.error(
                f"Failed to load {context_type} file {file_path}: {error_msg}"
            )
            return None, file_info

    async def _parse_stats_data(self, yaml_data: Dict[str, Any]) -> StatsContext:
        """
        Parse YAML data into StatsContext model.

        Args:
            yaml_data: Raw YAML data dictionary

        Returns:
            StatsContext: Validated stats model
        """
        try:
            # Extract character info
            character_info = yaml_data.get("character", {})

            # Extract combat stats
            combat_data = yaml_data.get("combat_stats", {})
            combat_stats = CombatStats(primary_stats=combat_data)

            # Extract psychological profile
            psych_data = yaml_data.get("psychological_profile", {})
            psychological_profile = PsychologicalProfile(traits=psych_data)

            # Extract relationships
            relationships = {}
            relationship_data = yaml_data.get("relationships", {})
            for rel_type, rel_list in relationship_data.items():
                if isinstance(rel_list, list):
                    relationships[rel_type] = []
                    for rel in rel_list:
                        if isinstance(rel, dict):
                            relationships[rel_type].append(
                                RelationshipEntry(
                                    name=rel.get("name", ""),
                                    trust_level=rel.get("trust_level", 50),
                                    relationship_type=rel.get(
                                        "relationship_type", "unknown"
                                    ),
                                )
                            )
                        elif isinstance(rel, str):
                            relationships[rel_type].append(
                                RelationshipEntry(
                                    name=rel, trust_level=50, relationship_type=rel_type
                                )
                            )

            # Create StatsContext model
            stats_context = StatsContext(
                name=character_info.get("name", "Unknown"),
                age=character_info.get("age", 0),
                origin=character_info.get("origin", "Unknown"),
                faction=character_info.get("faction", "Independent"),
                rank=character_info.get("rank"),
                specialization=character_info.get("specialization", "General"),
                combat_stats=combat_stats,
                psychological_profile=psychological_profile,
                equipment=yaml_data.get("equipment", {}),
                relationships=relationships,
                locations=yaml_data.get("locations", {}),
                objectives=yaml_data.get("objectives", {}),
                additional_data={
                    k: v
                    for k, v in yaml_data.items()
                    if k
                    not in [
                        "character",
                        "combat_stats",
                        "psychological_profile",
                        "equipment",
                        "relationships",
                        "locations",
                        "objectives",
                    ]
                },
            )

            return stats_context

        except Exception as e:
            raise FileParsingError(f"Stats data parsing error: {str(e)}")

    async def _parse_memory_markdown(self, content: str) -> MemoryContext:
        """
        Parse memory markdown content into MemoryContext model.

        This is a simplified parser focusing on extracting key structural
        information. A full implementation would use more sophisticated
        markdown parsing and natural language processing.

        Args:
            content: Markdown content string

        Returns:
            MemoryContext: Parsed memory context
        """
        try:
            # Simplified parsing - extract character mentions and relationships
            formative_events = []
            relationships = []
            behavioral_triggers = []

            # Extract character names mentioned in relationships
            relationship_pattern = (
                r"\*\*([^*]+)\*\*[^*]*trust.*?(\d+).*?relationship.*?[:\-]?\s*([^*\n]+)"
            )
            for match in re.finditer(relationship_pattern, content, re.IGNORECASE):
                char_name = match.group(1).strip()
                try:
                    trust_score = int(match.group(2))
                    rel_type = match.group(3).strip()

                    relationships.append(
                        RelationshipMemory(
                            character_name=char_name,
                            relationship_type=RelationshipType.PROFESSIONAL_NETWORK,  # Default type
                            memory_foundation="Documented in memory context",
                            trust_level=TrustLevel(score=trust_score),
                            emotional_dynamics=rel_type,
                            shared_experiences=[],
                            conflict_points=[],
                        )
                    )
                except (ValueError, IndexError):
                    continue

            # Extract age-based events for formative experiences
            age_pattern = r"[Aa]ge\s*(\d+)[^.]*[:\-]?\s*([^.]+\.)"
            for match in re.finditer(age_pattern, content):
                try:
                    age = int(match.group(1))
                    description = match.group(2).strip()

                    if (
                        age <= 120 and len(description) > 10
                    ):  # Reasonable age and description
                        formative_events.append(
                            FormativeEvent(
                                age=age,
                                event_name=f"Event at age {age}",
                                description=description,
                                memory_type=MemoryType.FOUNDATIONAL_LEARNING,
                                emotional_impact="Documented in memory context",
                                decision_influence="Influences current behavior patterns",
                                trigger_phrases=[],
                            )
                        )
                except (ValueError, IndexError):
                    continue

            return MemoryContext(
                formative_events=formative_events,
                relationships=relationships,
                behavioral_triggers=behavioral_triggers,
            )

        except Exception as e:
            raise FileParsingError(f"Memory markdown parsing error: {str(e)}")

    async def _parse_objectives_markdown(self, content: str) -> ObjectivesContext:
        """
        Parse objectives markdown content into ObjectivesContext model.

        Args:
            content: Markdown content string

        Returns:
            ObjectivesContext: Parsed objectives context
        """
        try:
            core_objectives = []
            strategic_objectives = []
            tactical_objectives = []

            # Extract objectives by tier (simplified pattern matching)
            tier_patterns = {
                "Core Life": (ObjectiveTier.CORE_LIFE, core_objectives),
                "Strategic": (ObjectiveTier.STRATEGIC, strategic_objectives),
                "Tactical": (ObjectiveTier.TACTICAL, tactical_objectives),
            }

            for tier_name, (tier_enum, objective_list) in tier_patterns.items():
                # Pattern to match objective sections
                pattern = rf"{tier_name}[^#]*?(\*\*[^*]+\*\*[^#]*?)(?=\*\*|\#|$)"

                for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                    obj_text = match.group(1)

                    # Extract objective name from bold text
                    name_match = re.search(r"\*\*([^*]+)\*\*", obj_text)
                    if name_match:
                        name = name_match.group(1).strip()
                        description = obj_text.replace(name_match.group(0), "").strip()

                        objective_list.append(
                            Objective(
                                name=name,
                                description=description[
                                    :500
                                ],  # Limit description length
                                tier=tier_enum,
                                status=ObjectiveStatus.ACTIVE,
                                priority=5,  # Default priority
                                success_metrics=[],
                                timeline="Ongoing",
                            )
                        )

            return ObjectivesContext(
                core_objectives=core_objectives,
                strategic_objectives=strategic_objectives,
                tactical_objectives=tactical_objectives,
            )

        except Exception as e:
            raise FileParsingError(f"Objectives markdown parsing error: {str(e)}")

    async def _parse_profile_markdown(self, content: str) -> ProfileContext:
        """
        Parse profile markdown content into ProfileContext model.

        Args:
            content: Markdown content string

        Returns:
            ProfileContext: Parsed profile context
        """
        try:
            # Extract basic identity information
            name_match = re.search(r"\*\*Name\*\*:\s*([^\n]+)", content, re.IGNORECASE)
            age_match = re.search(r"\*\*Age\*\*:\s*(\d+)", content, re.IGNORECASE)
            gender_match = re.search(
                r"\*\*Gender\*\*:\s*([^\n]+)", content, re.IGNORECASE
            )
            race_match = re.search(r"\*\*Race\*\*:\s*([^\n]+)", content, re.IGNORECASE)
            class_match = re.search(
                r"\*\*Class\*\*:\s*([^\n]+)", content, re.IGNORECASE
            )

            # Extract profile sections
            physical_pattern = r"Physical Description[^#]*?([^#]+?)(?=\#|$)"
            physical_match = re.search(
                physical_pattern, content, re.IGNORECASE | re.DOTALL
            )

            background_pattern = r"Background[^#]*?([^#]+?)(?=\#|$)"
            background_match = re.search(
                background_pattern, content, re.IGNORECASE | re.DOTALL
            )

            # Extract emotional drives (simplified)
            emotional_drives = []
            drive_pattern = r"\*\*(\d+\..*?)\*\*[^*]*?([^*]+)"
            for match in re.finditer(drive_pattern, content):
                drive_name = match.group(1).strip()
                drive_desc = match.group(2).strip()[:200]  # Limit length

                if "drive" in drive_name.lower() or "emotional" in drive_name.lower():
                    emotional_drives.append(
                        EmotionalDrive(
                            name=drive_name,
                            dominance_level="Core",
                            foundation=drive_desc,
                            positive_expression="Positive manifestation documented",
                            negative_expression="Negative manifestation documented",
                            trigger_events=[],
                            soothing_behaviors=[],
                        )
                    )

            return ProfileContext(
                name=name_match.group(1).strip() if name_match else "Unknown",
                age=int(age_match.group(1)) if age_match else 0,
                gender=gender_match.group(1).strip() if gender_match else "Unknown",
                race=race_match.group(1).strip() if race_match else "Unknown",
                character_class=(
                    class_match.group(1).strip() if class_match else "Unknown"
                ),
                physical_description=(
                    physical_match.group(1).strip()
                    if physical_match
                    else "Not provided"
                ),
                background_summary=(
                    background_match.group(1).strip()
                    if background_match
                    else "Not provided"
                ),
                emotional_drives=emotional_drives,
                emotional_responses=[],
                personality_traits=[],
                core_skills=[],
                specializations=[],
                equipment=[],
                resources=[],
            )

        except Exception as e:
            raise FileParsingError(f"Profile markdown parsing error: {str(e)}")

    async def _create_character_context(
        self, character_id: str, context_data: Dict[str, Any], character_dir: Path
    ) -> CharacterContext:
        """
        Create consolidated CharacterContext from loaded data.

        Args:
            character_id: Character identifier
            context_data: Loaded context data
            character_dir: Character directory path

        Returns:
            CharacterContext: Consolidated context model
        """
        try:
            contexts = context_data["contexts"]
            loaded_files = context_data["loaded_files"]

            # Determine character name from available contexts
            character_name = character_id
            if contexts.get("profile") and hasattr(contexts["profile"], "name"):
                character_name = contexts["profile"].name
            elif contexts.get("stats") and hasattr(contexts["stats"], "name"):
                character_name = contexts["stats"].name

            # Create consolidated context
            character_context = CharacterContext(
                character_id=character_id,
                character_name=character_name,
                memory_context=contexts.get("memory"),
                objectives_context=contexts.get("objectives"),
                profile_context=contexts.get("profile"),
                stats_context=contexts.get("stats"),
                loaded_files=loaded_files,
            )

            self.logger.info(
                f"Created character context for {character_name}: "
                f"Success={character_context.load_success}, "
                f"Partial={character_context.partial_load}, "
                f"Files loaded: {len([f for f in loaded_files if f.loaded_successfully])}/{len(loaded_files)}"
            )

            return character_context

        except Exception as e:
            raise ContextLoaderError(f"Failed to create character context: {str(e)}")

    # ==================== Enhanced Error Handling & Security ====================

    async def _check_circuit_breaker(self):
        """Check circuit breaker state and potentially raise ServiceUnavailableError."""
        now = datetime.now(UTC)

        if self._circuit_breaker["state"] == "OPEN":
            time_since_failure = now - self._circuit_breaker["last_failure_time"]

            if time_since_failure > self._circuit_breaker["recovery_timeout"]:
                self._circuit_breaker["state"] = "HALF_OPEN"
                self.logger.info("Circuit breaker moved to HALF_OPEN state")
            else:
                remaining_time = (
                    self._circuit_breaker["recovery_timeout"] - time_since_failure
                )
                raise ServiceUnavailableError(
                    f"Service temporarily unavailable. Recovery in {remaining_time.total_seconds():.0f}s"
                )

    async def _record_success(self):
        """Record successful operation for circuit breaker."""
        if self._circuit_breaker["state"] == "HALF_OPEN":
            self._circuit_breaker["state"] = "CLOSED"
            self._circuit_breaker["failure_count"] = 0
            self.logger.info("Circuit breaker closed after successful recovery")

    async def _record_failure(self):
        """Record failed operation for circuit breaker."""
        self._circuit_breaker["failure_count"] += 1
        self._circuit_breaker["last_failure_time"] = datetime.now(UTC)

        if (
            self._circuit_breaker["failure_count"]
            >= self._circuit_breaker["failure_threshold"]
        ):
            self._circuit_breaker["state"] = "OPEN"
            self.logger.warning(
                f"Circuit breaker opened after {self._circuit_breaker['failure_count']} failures"
            )

    async def _record_partial_failure(self):
        """Record partial failure (less severe than full failure)."""
        # Only count as half a failure for circuit breaker
        self._circuit_breaker["failure_count"] += 0.5
        self._circuit_breaker["last_failure_time"] = datetime.now(UTC)

    async def _security_check(self, character_id: str):
        """
        Perform security checks on character identifier and path.

        Args:
            character_id: Sanitized character identifier

        Raises:
            SecurityError: If security violations detected
        """
        # Check for path traversal attempts
        if ".." in character_id or "/" in character_id or "\\" in character_id:
            raise SecurityError(
                f"Path traversal detected in character ID: {character_id}"
            )

        # Check character ID length and characters
        if len(character_id) > 100:
            raise SecurityError(f"Character ID too long: {len(character_id)} chars")

        # Ensure character ID contains only safe characters
        safe_pattern = re.compile(r"^[a-z0-9_-]+$")
        if not safe_pattern.match(character_id):
            raise SecurityError(f"Invalid characters in character ID: {character_id}")

        # Check if path would resolve outside base directory
        try:
            resolved_path = (self.base_path / character_id).resolve()
            base_resolved = self.base_path.resolve()

            if not str(resolved_path).startswith(str(base_resolved)):
                raise SecurityError("Path resolution outside base directory detected")

        except Exception as e:
            raise SecurityError(f"Path validation error: {str(e)}")

    async def _validate_context_integrity(self, character_context: CharacterContext):
        """
        Perform comprehensive data integrity validation.

        Args:
            character_context: Loaded character context

        Raises:
            ValidationError: If critical integrity issues found
        """
        warnings = []

        # Name consistency validation
        names = []
        if character_context.profile_context:
            names.append(character_context.profile_context.name)
        if character_context.stats_context:
            names.append(character_context.stats_context.name)

        unique_names = set(names)
        if len(unique_names) > 1:
            warnings.append(f"Name inconsistency: {unique_names}")

        # Age consistency validation
        ages = []
        if character_context.profile_context:
            ages.append(character_context.profile_context.age)
        if character_context.stats_context:
            ages.append(character_context.stats_context.age)

        unique_ages = set(ages)
        if len(unique_ages) > 1:
            warnings.append(f"Age inconsistency: {unique_ages}")

        # Memory-profile consistency
        if character_context.memory_context and character_context.profile_context:
            {
                rel.character_name
                for rel in character_context.memory_context.relationships
            }
            # This could be expanded to check profile mentions

        # Update context with warnings
        if warnings:
            character_context.validation_warnings.extend(warnings)
            if len(warnings) > 5:  # Too many warnings indicate serious problems
                character_context.context_integrity = False
                raise ValidationError(f"Critical data integrity issues: {warnings[:3]}")

    # ==================== Caching System ====================

    async def _get_from_cache(self, character_id: str) -> Optional[CharacterContext]:
        """Get character context from cache if available and fresh."""
        if character_id not in self._cache:
            return None

        cache_time = self._cache_timestamps.get(character_id)
        if not cache_time or (datetime.now(UTC) - cache_time) > self.cache_ttl:
            # Cache expired
            self._cache.pop(character_id, None)
            self._cache_timestamps.pop(character_id, None)
            return None

        return self._cache[character_id]

    async def _store_in_cache(
        self, character_id: str, character_context: CharacterContext
    ):
        """Store character context in cache."""
        # Create a copy to avoid reference issues
        cache_entry = CharacterContext.model_validate(character_context.model_dump())
        self._cache[character_id] = cache_entry
        self._cache_timestamps[character_id] = datetime.now(UTC)

        # Basic cache size management
        if len(self._cache) > 100:  # Max 100 entries
            oldest_id = min(
                self._cache_timestamps.keys(), key=lambda k: self._cache_timestamps[k]
            )
            self._cache.pop(oldest_id, None)
            self._cache_timestamps.pop(oldest_id, None)

    async def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        self._cache_timestamps.clear()
        self.logger.info("Context cache cleared")

    async def _generate_cache_key(
        self, character_id: str, files_info: List[LoadedFileInfo]
    ) -> str:
        """Generate cache key based on character ID and file modification times."""
        file_hashes = []
        for file_info in files_info:
            if file_info.loaded_successfully:
                # Use file path and timestamp for cache key
                file_hashes.append(f"{file_info.file_path}:{file_info.load_timestamp}")

        combined = f"{character_id}:{'|'.join(file_hashes)}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    # ==================== Service Monitoring & Utilities ====================

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics for monitoring."""
        return {
            "load_statistics": self._load_stats.copy(),
            "base_path": str(self.base_path),
            "max_file_size_mb": self.max_file_size / (1024 * 1024),
            "supported_file_types": list(self.file_patterns.keys()),
            "caching": {
                "enabled": self.enable_caching,
                "cache_size": len(self._cache),
                "cache_ttl_minutes": self.cache_ttl.total_seconds() / 60,
                "hit_rate": (
                    self._load_stats["cache_hits"]
                    / max(
                        1,
                        self._load_stats["cache_hits"]
                        + self._load_stats["cache_misses"],
                    )
                ),
            },
            "concurrency": {
                "max_concurrent_loads": self.max_concurrent_loads,
                "active_loads": len(self._active_loads),
                "active_load_ids": list(self._active_loads),
            },
            "circuit_breaker": {
                "state": self._circuit_breaker["state"],
                "failure_count": self._circuit_breaker["failure_count"],
                "threshold": self._circuit_breaker["failure_threshold"],
            },
            "service_status": self._get_service_health_status(),
        }

    def _get_service_health_status(self) -> str:
        """Determine overall service health status."""
        if self._circuit_breaker["state"] == "OPEN":
            return "degraded"
        elif self._circuit_breaker["state"] == "HALF_OPEN":
            return "recovering"
        elif self._load_stats["security_violations"] > 10:
            return "security_alert"
        elif len(self._active_loads) >= self.max_concurrent_loads:
            return "high_load"
        else:
            return "healthy"

    async def validate_character_directory_structure(
        self, character_id: str
    ) -> Dict[str, Any]:
        """
        Validate character directory structure without loading files.

        Args:
            character_id: Character identifier to validate

        Returns:
            Dict containing validation results
        """
        try:
            sanitized_id = await self._validate_character_identifier(character_id)
            character_dir = self.base_path / sanitized_id

            validation_result = {
                "character_id": sanitized_id,
                "directory_exists": character_dir.exists(),
                "directory_path": str(character_dir),
                "expected_files": {},
                "validation_success": False,
            }

            if not character_dir.exists():
                validation_result["error"] = "Character directory does not exist"
                return validation_result

            # Check each expected file
            for context_type, file_suffix in self.file_patterns.items():
                file_path = character_dir / f"{sanitized_id}{file_suffix}"
                validation_result["expected_files"][context_type] = {
                    "file_name": f"{sanitized_id}{file_suffix}",
                    "exists": file_path.exists(),
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size if file_path.exists() else 0,
                }

            # Determine overall validation success
            files_found = sum(
                1
                for file_info in validation_result["expected_files"].values()
                if file_info["exists"]
            )
            validation_result["files_found"] = files_found
            validation_result["total_expected"] = len(self.file_patterns)
            validation_result["validation_success"] = (
                files_found > 0
            )  # At least one file must exist

            return validation_result

        except Exception as e:
            return {
                "character_id": character_id,
                "validation_success": False,
                "error": str(e),
            }
