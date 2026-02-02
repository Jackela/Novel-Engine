"""
Campaign Logging Service
========================

Comprehensive logging system for campaign events, turns, and system activities.
Provides structured logging, audit trails, and log analysis capabilities.
"""

import asyncio
import gzip
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO


class LogLevel(Enum):
    """Log levels for campaign events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventCategory(Enum):
    """Categories of campaign events."""

    SYSTEM = "system"
    AGENT = "agent"
    TURN = "turn"
    NARRATIVE = "narrative"
    USER = "user"
    PERFORMANCE = "performance"
    ERROR = "error"


@dataclass
class LogEntry:
    """Represents a single log entry."""

    entry_id: str
    timestamp: datetime
    level: LogLevel
    category: EventCategory
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    agent_id: Optional[str] = None
    turn_number: Optional[int] = None
    session_id: Optional[str] = None


class CampaignLoggingService:
    """
    Comprehensive campaign logging service.

    Features:
    - Structured logging with metadata
    - Multiple output formats (JSON, text, compressed)
    - Log rotation and archival
    - Real-time log analysis
    - Search and filtering capabilities
    """

    def __init__(
        self,
        log_dir: str = "logs",
        session_id: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.log_dir = Path(log_dir)
        self.session_id = (
            session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        # Storage
        self._log_entries: List[LogEntry] = []
        self._log_files: Dict[str, TextIO] = {}
        self._log_lock = asyncio.Lock()

        # Configuration
        self._max_memory_entries = 1000
        self._log_rotation_size = 10 * 1024 * 1024  # 10MB
        self._compression_enabled = True
        self._real_time_analysis = True

        # Statistics
        self._log_statistics = {
            "total_entries": 0,
            "entries_by_level": {level.value: 0 for level in LogLevel},
            "entries_by_category": {category.value: 0 for category in EventCategory},
            "errors_last_hour": 0,
            "session_start": datetime.now(),
        }

        # Analysis
        self._error_patterns = {}
        self._performance_metrics = {}

    async def initialize(self) -> bool:
        """Initialize logging service."""
        try:
            # Create log directory
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Initialize log files
            await self._initialize_log_files()

            # Log service start
            await self.log_event(
                {
                    "level": "info",
                    "category": "system",
                    "message": f"Campaign logging service initialized for session {self.session_id}",
                    "metadata": {
                        "log_dir": str(self.log_dir),
                        "compression_enabled": self._compression_enabled,
                    },
                }
            )

            self.logger.info(
                f"Campaign logging service initialized for session {self.session_id}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Campaign logging service initialization failed: {e}")
            return False

    async def log_event(self, event: Dict[str, Any]) -> None:
        """
        Log a single event with comprehensive metadata.

        Args:
            event: Event data dictionary
        """
        try:
            async with self._log_lock:
                # Create log entry
                entry = await self._create_log_entry(event)

                # Store in memory
                self._log_entries.append(entry)

                # Write to file
                await self._write_to_file(entry)

                # Update statistics
                self._update_statistics(entry)

                # Real-time analysis
                if self._real_time_analysis:
                    await self._analyze_entry(entry)

                # Manage memory
                await self._manage_memory()

        except Exception as e:
            self.logger.error(f"Failed to log event: {e}")
            # Don't raise - logging should never break the main system

    async def log_turn_summary(self, summary: Dict[str, Any]) -> None:
        """
        Log comprehensive turn summary.

        Args:
            summary: Turn summary data
        """
        try:
            turn_number = summary.get("turn_number", 0)

            # Create detailed turn log entry
            await self.log_event(
                {
                    "level": "info",
                    "category": "turn",
                    "message": f"Turn {turn_number} completed",
                    "metadata": {
                        "turn_number": turn_number,
                        "success": summary.get("success", False),
                        "duration": summary.get("metrics", {}).get("total_duration", 0),
                        "agent_count": summary.get("metrics", {}).get(
                            "total_agents", 0
                        ),
                        "successful_decisions": summary.get("metrics", {}).get(
                            "successful_decisions", 0
                        ),
                        "world_state_changes": len(
                            summary.get("world_state_changes", {})
                        ),
                        "narrative_events": len(summary.get("narrative_events", [])),
                        "conflicts_resolved": summary.get("metrics", {}).get(
                            "conflicts_resolved", 0
                        ),
                    },
                    "turn_number": turn_number,
                }
            )

            # Log individual agent decisions if available
            for agent_id, result in summary.get("agent_results", {}).items():
                await self.log_event(
                    {
                        "level": "debug",
                        "category": "agent",
                        "message": f"Agent {agent_id} decision result",
                        "metadata": {
                            "agent_id": agent_id,
                            "success": result.get("success", False),
                            "action_type": result.get("action_type"),
                            "response_time": result.get("response_time", 0),
                        },
                        "agent_id": agent_id,
                        "turn_number": turn_number,
                    }
                )

            # Log errors if turn failed
            if not summary.get("success", True) and summary.get("error"):
                await self.log_event(
                    {
                        "level": "error",
                        "category": "turn",
                        "message": f'Turn {turn_number} failed: {summary["error"]}',
                        "metadata": {
                            "turn_number": turn_number,
                            "error_details": summary.get("error"),
                            "partial_results": summary.get("agent_results", {}),
                        },
                        "turn_number": turn_number,
                    }
                )

        except Exception as e:
            self.logger.error(f"Failed to log turn summary: {e}")

    async def get_log_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent log history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of log entries as dictionaries
        """
        try:
            recent_entries = self._log_entries[-limit:] if self._log_entries else []

            return [
                {
                    "id": entry.entry_id,
                    "timestamp": entry.timestamp.isoformat(),
                    "level": entry.level.value,
                    "category": entry.category.value,
                    "message": entry.message,
                    "metadata": entry.metadata,
                    "agent_id": entry.agent_id,
                    "turn_number": entry.turn_number,
                    "session_id": entry.session_id,
                }
                for entry in recent_entries
            ]

        except Exception as e:
            self.logger.error(f"Failed to get log history: {e}")
            return []

    async def search_logs(
        self,
        query: Optional[str] = None,
        level: Optional[str] = None,
        category: Optional[str] = None,
        agent_id: Optional[str] = None,
        turn_number: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search logs with various filters."""
        try:
            matching_entries = []

            for entry in self._log_entries:
                # Apply filters
                if level and entry.level.value != level:
                    continue
                if category and entry.category.value != category:
                    continue
                if agent_id and entry.agent_id != agent_id:
                    continue
                if turn_number and entry.turn_number != turn_number:
                    continue
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue
                if query and query.lower() not in entry.message.lower():
                    continue

                matching_entries.append(
                    {
                        "id": entry.entry_id,
                        "timestamp": entry.timestamp.isoformat(),
                        "level": entry.level.value,
                        "category": entry.category.value,
                        "message": entry.message,
                        "metadata": entry.metadata,
                        "agent_id": entry.agent_id,
                        "turn_number": entry.turn_number,
                    }
                )

                if len(matching_entries) >= limit:
                    break

            return matching_entries

        except Exception as e:
            self.logger.error(f"Log search failed: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics and analytics."""
        try:
            current_time = datetime.now()
            session_duration = (
                current_time - self._log_statistics["session_start"]
            ).total_seconds()

            # Calculate error rate in last hour
            one_hour_ago = current_time - timedelta(hours=1)
            recent_errors = sum(
                1
                for entry in self._log_entries
                if entry.timestamp > one_hour_ago
                and entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]
            )

            # Calculate performance metrics
            recent_entries = self._log_entries[-100:] if self._log_entries else []
            avg_entries_per_minute = len(recent_entries) / max(1, session_duration / 60)

            return {
                "session_id": self.session_id,
                "session_duration": session_duration,
                "total_entries": self._log_statistics["total_entries"],
                "entries_by_level": self._log_statistics["entries_by_level"].copy(),
                "entries_by_category": self._log_statistics[
                    "entries_by_category"
                ].copy(),
                "recent_errors": recent_errors,
                "error_rate_last_hour": recent_errors,
                "avg_entries_per_minute": avg_entries_per_minute,
                "memory_entries": len(self._log_entries),
                "active_log_files": len(self._log_files),
                "top_error_patterns": self._get_top_error_patterns(),
                "performance_summary": self._get_performance_summary(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}

    async def _create_log_entry(self, event: Dict[str, Any]) -> LogEntry:
        """Create structured log entry from event data."""
        entry_id = self._generate_entry_id()

        # Parse level
        level_str = event.get("level", "info")
        level = (
            LogLevel(level_str)
            if level_str in [log_level.value for log_level in LogLevel]
            else LogLevel.INFO
        )

        # Parse category
        category_str = event.get("category", "system")
        category = (
            EventCategory(category_str)
            if category_str in [c.value for c in EventCategory]
            else EventCategory.SYSTEM
        )

        return LogEntry(
            entry_id=entry_id,
            timestamp=datetime.now(),
            level=level,
            category=category,
            message=event.get("message", ""),
            metadata=event.get("metadata", {}),
            agent_id=event.get("agent_id"),
            turn_number=event.get("turn_number"),
            session_id=self.session_id,
        )

    async def _write_to_file(self, entry: LogEntry) -> None:
        """Write log entry to appropriate file."""
        try:
            # Determine file name based on category and date
            date_str = entry.timestamp.strftime("%Y%m%d")
            filename = f"{self.session_id}_{entry.category.value}_{date_str}.jsonl"
            file_path = self.log_dir / filename

            # Create JSON line format
            log_line = {
                "id": entry.entry_id,
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "category": entry.category.value,
                "message": entry.message,
                "metadata": entry.metadata,
                "agent_id": entry.agent_id,
                "turn_number": entry.turn_number,
                "session_id": entry.session_id,
            }

            # Write to file
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_line, ensure_ascii=False) + "\n")

            # Check for rotation
            await self._check_log_rotation(file_path)

        except Exception as e:
            self.logger.error(f"Failed to write log entry to file: {e}")

    def _update_statistics(self, entry: LogEntry) -> None:
        """Update logging statistics."""
        self._log_statistics["total_entries"] += 1
        self._log_statistics["entries_by_level"][entry.level.value] += 1
        self._log_statistics["entries_by_category"][entry.category.value] += 1

        # Update error count for last hour
        if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            current_time = datetime.now()
            one_hour_ago = current_time - timedelta(hours=1)

            # Count recent errors
            recent_error_count = sum(
                1
                for e in self._log_entries[-100:]
                if e.timestamp > one_hour_ago
                and e.level in [LogLevel.ERROR, LogLevel.CRITICAL]
            )
            self._log_statistics["errors_last_hour"] = recent_error_count

    async def _analyze_entry(self, entry: LogEntry) -> None:
        """Perform real-time analysis of log entry."""
        try:
            # Error pattern analysis
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                error_signature = self._generate_error_signature(entry)
                if error_signature not in self._error_patterns:
                    self._error_patterns[error_signature] = {
                        "count": 0,
                        "first_seen": entry.timestamp,
                        "last_seen": entry.timestamp,
                        "message_sample": entry.message[:100],
                    }

                self._error_patterns[error_signature]["count"] += 1
                self._error_patterns[error_signature]["last_seen"] = entry.timestamp

            # Performance metric tracking
            if entry.category == EventCategory.PERFORMANCE:
                metric_name = entry.metadata.get("metric_name", "unknown")
                metric_value = entry.metadata.get("metric_value", 0)

                if metric_name not in self._performance_metrics:
                    self._performance_metrics[metric_name] = []

                self._performance_metrics[metric_name].append(
                    {"timestamp": entry.timestamp, "value": metric_value}
                )

                # Keep only recent metrics
                cutoff = entry.timestamp - timedelta(hours=1)
                self._performance_metrics[metric_name] = [
                    m
                    for m in self._performance_metrics[metric_name]
                    if m["timestamp"] > cutoff
                ]

        except Exception as e:
            self.logger.debug(f"Log analysis failed: {e}")

    async def _manage_memory(self) -> None:
        """Manage in-memory log entries."""
        if len(self._log_entries) > self._max_memory_entries:
            # Archive older entries to compressed files
            entries_to_archive = self._log_entries[: -self._max_memory_entries // 2]
            await self._archive_entries(entries_to_archive)

            # Keep recent entries in memory
            self._log_entries = self._log_entries[-self._max_memory_entries // 2 :]

    async def _archive_entries(self, entries: List[LogEntry]) -> None:
        """Archive entries to compressed file."""
        if not entries:
            return

        try:
            # Group entries by date
            entries_by_date = {}
            for entry in entries:
                date_key = entry.timestamp.strftime("%Y%m%d")
                if date_key not in entries_by_date:
                    entries_by_date[date_key] = []
                entries_by_date[date_key].append(entry)

            # Write to compressed archive files
            for date_key, date_entries in entries_by_date.items():
                archive_file = (
                    self.log_dir / f"{self.session_id}_archive_{date_key}.jsonl.gz"
                )

                with gzip.open(archive_file, "at", encoding="utf-8") as f:
                    for entry in date_entries:
                        log_line = {
                            "id": entry.entry_id,
                            "timestamp": entry.timestamp.isoformat(),
                            "level": entry.level.value,
                            "category": entry.category.value,
                            "message": entry.message,
                            "metadata": entry.metadata,
                            "agent_id": entry.agent_id,
                            "turn_number": entry.turn_number,
                            "session_id": entry.session_id,
                        }
                        f.write(json.dumps(log_line, ensure_ascii=False) + "\n")

                self.logger.debug(
                    f"Archived {len(date_entries)} entries to {archive_file}"
                )

        except Exception as e:
            self.logger.error(f"Failed to archive log entries: {e}")

    async def _check_log_rotation(self, file_path: Path) -> None:
        """Check if log file needs rotation."""
        try:
            if (
                file_path.exists()
                and file_path.stat().st_size > self._log_rotation_size
            ):
                # Rotate the file
                timestamp = datetime.now().strftime("%H%M%S")
                rotated_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                rotated_path = file_path.parent / rotated_name

                file_path.rename(rotated_path)

                # Compress rotated file if enabled
                if self._compression_enabled:
                    compressed_path = rotated_path.with_suffix(
                        rotated_path.suffix + ".gz"
                    )
                    with open(rotated_path, "rb") as f_in:
                        with gzip.open(compressed_path, "wb") as f_out:
                            f_out.writelines(f_in)
                    rotated_path.unlink()

                self.logger.debug(f"Rotated log file: {file_path} -> {rotated_name}")

        except Exception as e:
            self.logger.error(f"Log rotation failed: {e}")

    async def _initialize_log_files(self) -> None:
        """Initialize log file handles."""
        # Create session metadata file
        metadata_file = self.log_dir / f"{self.session_id}_metadata.json"
        metadata = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "log_version": "1.0",
            "compression_enabled": self._compression_enabled,
        }

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    def _generate_entry_id(self) -> str:
        """Generate unique entry ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"log_{timestamp}"

    def _generate_error_signature(self, entry: LogEntry) -> str:
        """Generate signature for error pattern matching."""
        # Create signature based on error message and metadata
        signature_data = f"{entry.message[:50]}_{entry.category.value}"
        if entry.agent_id:
            signature_data += f"_{entry.agent_id}"

        return hashlib.md5(signature_data.encode(), usedforsecurity=False).hexdigest()[:12]  # nosec B324

    def _get_top_error_patterns(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top error patterns by frequency."""
        sorted_patterns = sorted(
            self._error_patterns.items(), key=lambda x: x[1]["count"], reverse=True
        )

        return [
            {
                "signature": signature,
                "count": data["count"],
                "first_seen": data["first_seen"].isoformat(),
                "last_seen": data["last_seen"].isoformat(),
                "sample_message": data["message_sample"],
            }
            for signature, data in sorted_patterns[:limit]
        ]

    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        summary = {}

        for metric_name, measurements in self._performance_metrics.items():
            if measurements:
                values = [m["value"] for m in measurements]
                summary[metric_name] = {
                    "count": len(values),
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "recent_value": values[-1] if values else 0,
                }

        return summary

    async def export_logs(
        self,
        export_path: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: str = "json",
    ) -> bool:
        """Export logs to file."""
        try:
            entries_to_export = []

            for entry in self._log_entries:
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue
                entries_to_export.append(entry)

            export_data = {
                "export_metadata": {
                    "session_id": self.session_id,
                    "export_time": datetime.now().isoformat(),
                    "entry_count": len(entries_to_export),
                    "format": format,
                },
                "entries": [
                    {
                        "id": entry.entry_id,
                        "timestamp": entry.timestamp.isoformat(),
                        "level": entry.level.value,
                        "category": entry.category.value,
                        "message": entry.message,
                        "metadata": entry.metadata,
                        "agent_id": entry.agent_id,
                        "turn_number": entry.turn_number,
                        "session_id": entry.session_id,
                    }
                    for entry in entries_to_export
                ],
            }

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(
                f"Exported {len(entries_to_export)} log entries to {export_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Log export failed: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup logging service."""
        try:
            # Final log entry
            await self.log_event(
                {
                    "level": "info",
                    "category": "system",
                    "message": f"Campaign logging service shutting down for session {self.session_id}",
                    "metadata": {
                        "total_entries": self._log_statistics["total_entries"],
                        "session_duration": (
                            datetime.now() - self._log_statistics["session_start"]
                        ).total_seconds(),
                    },
                }
            )

            # Archive remaining entries
            if self._log_entries:
                await self._archive_entries(self._log_entries)

            # Close file handles
            for file_handle in self._log_files.values():
                try:
                    file_handle.close()
                except Exception:
                    logging.getLogger(__name__).debug(
                        "Suppressed exception", exc_info=True
                    )
            self._log_entries.clear()
            self._log_files.clear()

            self.logger.info(
                f"Campaign logging service cleanup completed for session {self.session_id}"
            )

        except Exception as e:
            self.logger.error(f"Campaign logging cleanup error: {e}")
