#!/usr/bin/env python3
"""
Campaign Logging Component

Extracted from DirectorAgent for better separation of concerns.
Handles campaign log initialization, event logging, and narrative tracking.
"""

import logging
import os
from datetime import datetime
from typing import Optional

from config_loader import get_campaign_log_filename

logger = logging.getLogger(__name__)


class CampaignLogger:
    """
    Manages campaign event logging and narrative tracking.

    Responsibilities:
    - Campaign log file initialization and management
    - Event logging with proper formatting
    - Log backup and rotation
    - Narrative context preservation
    """

    def __init__(self, campaign_log_path: Optional[str] = None):
        """
        Initialize the campaign logger.

        Args:
            campaign_log_path: Optional path to campaign log file
        """
        self.campaign_log_path = campaign_log_path or get_campaign_log_filename()
        self.events_logged = 0

        self._initialize_campaign_log()

    def _initialize_campaign_log(self) -> None:
        """Initialize or continue existing campaign log."""
        try:
            if os.path.exists(self.campaign_log_path):
                logger.info(
                    f"Continuing existing campaign log: {self.campaign_log_path}"
                )
                self._backup_existing_log()
            else:
                logger.info(f"Creating new campaign log: {self.campaign_log_path}")
                self._create_new_campaign_log()
        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # File system errors during log initialization
            logger.error(
                f"File system error initializing campaign log: {e}",
                extra={"error_type": type(e).__name__},
            )
            raise
        except (ValueError, RuntimeError) as e:
            # Configuration or log creation errors
            logger.error(
                f"Failed to initialize campaign log: {e}",
                extra={"error_type": type(e).__name__},
            )
            raise

    def _create_new_campaign_log(self) -> None:
        """Create a new campaign log file with header."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.campaign_log_path), exist_ok=True)

            with open(self.campaign_log_path, "w") as f:
                f.write("# Campaign Log\n")
                f.write(
                    f"**Campaign Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                f.write("**Simulation Mode:** Multi-Agent Interactive Narrative\n\n")
                f.write("---\n\n")
                f.write("## Campaign Events\n\n")

            logger.info(f"Created new campaign log: {self.campaign_log_path}")

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # File system errors creating campaign log
            logger.error(
                f"File system error creating campaign log: {e}",
                extra={"error_type": type(e).__name__},
            )
            # Fallback to a default filename in current directory
        except (ValueError, TypeError) as e:
            # String formatting or datetime errors
            logger.error(
                f"Data formatting error creating campaign log: {e}",
                extra={"error_type": type(e).__name__},
            )
            # Fallback to a default filename in current directory
            fallback_path = (
                f"campaign_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            )
            logger.info(f"Using fallback campaign log: {fallback_path}")
            self.campaign_log_path = fallback_path

            with open(self.campaign_log_path, "w") as f:
                f.write("# Campaign Log (Fallback)\n")
                f.write(
                    f"**Campaign Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                )

    def _backup_existing_log(self) -> None:
        """Create backup of existing log file."""
        if os.path.exists(self.campaign_log_path):
            backup_path = f"{self.campaign_log_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                import shutil

                shutil.copy2(self.campaign_log_path, backup_path)
                logger.info(f"Backed up existing log to: {backup_path}")
            except (FileNotFoundError, PermissionError, IOError, OSError) as e:
                # File system errors during backup
                logger.warning(
                    f"File system error backing up log: {e}",
                    extra={"error_type": type(e).__name__},
                )
            except (ImportError, AttributeError) as e:
                # Shutil import or copy errors
                logger.warning(
                    f"Backup operation error: {e}",
                    extra={"error_type": type(e).__name__},
                )

    def log_event(self, event_description: str) -> None:
        """
        Log an event to the campaign log.

        Args:
            event_description: Description of the event to log
        """
        if not event_description or not event_description.strip():
            logger.warning("Attempted to log empty event")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(self.campaign_log_path, "a") as f:
                f.write(f"**[{timestamp}]** {event_description.strip()}\n\n")

            self.events_logged += 1
            logger.debug(f"Logged event: {event_description[:50]}...")

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # File system errors during event logging
            logger.error(
                f"File system error logging event: {e}",
                extra={"error_type": type(e).__name__},
            )
            # Try to log to a fallback file
            self._log_to_fallback(event_description, timestamp)
        except (ValueError, TypeError, AttributeError) as e:
            # String formatting or data errors
            logger.error(
                f"Data error logging event: {e}", extra={"error_type": type(e).__name__}
            )
            # Try to log to a fallback file
            self._log_to_fallback(event_description, timestamp)

    def _log_to_fallback(self, event_description: str, timestamp: str) -> None:
        """Log to fallback file if main log fails."""
        fallback_path = f"fallback_campaign_log_{datetime.now().strftime('%Y%m%d')}.md"
        try:
            with open(fallback_path, "a") as f:
                f.write(f"**[{timestamp}]** {event_description.strip()}\n\n")
            logger.info(f"Logged to fallback file: {fallback_path}")
        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # File system errors in fallback logging
            logger.error(
                f"File system error in fallback logging: {e}",
                extra={"error_type": type(e).__name__},
            )
        except (ValueError, TypeError) as e:
            # Data formatting errors in fallback
            logger.error(
                f"Data error in fallback logging: {e}",
                extra={"error_type": type(e).__name__},
            )

    def log_simulation_start(
        self, agent_count: int, simulation_config: dict = None
    ) -> None:
        """Log simulation start event with configuration."""
        config_info = ""
        if simulation_config:
            config_info = f" with configuration: {simulation_config}"

        self.log_event(
            f"🎬 **SIMULATION STARTED** - {agent_count} agents registered{config_info}"
        )

    def log_turn_start(self, turn_number: int, active_agents: int) -> None:
        """Log turn start event."""
        self.log_event(f"🎯 **TURN {turn_number}** - {active_agents} agents active")

    def log_turn_end(self, turn_number: int, actions_processed: int) -> None:
        """Log turn end event."""
        self.log_event(
            f"✅ **TURN {turn_number} COMPLETE** - {actions_processed} actions processed"
        )

    def log_agent_action(
        self, agent_name: str, agent_id: str, action_type: str, reasoning: str = None
    ) -> None:
        """Log agent action with formatting."""
        action_description = (
            f"🎭 **{agent_name}** ({agent_id}) decided to **{action_type}**"
        )
        if reasoning:
            action_description += f": _{reasoning}_"
        self.log_event(action_description)

    def log_agent_waiting(self, agent_name: str, agent_id: str) -> None:
        """Log agent waiting/observing."""
        self.log_event(f"⏸️ **{agent_name}** ({agent_id}) is waiting and observing")

    def log_narrative_event(self, event_type: str, description: str) -> None:
        """Log narrative event with special formatting."""
        self.log_event(f"📖 **NARRATIVE EVENT - {event_type.upper()}**: {description}")

    def log_world_state_change(self, change_description: str) -> None:
        """Log world state changes."""
        self.log_event(f"🌍 **WORLD STATE**: {change_description}")

    def log_error(self, error_description: str, context: str = None) -> None:
        """Log error events."""
        error_msg = f"❌ **ERROR**: {error_description}"
        if context:
            error_msg += f" (Context: {context})"
        self.log_event(error_msg)

    def log_simulation_end(self, total_turns: int, total_events: int) -> None:
        """Log simulation end summary."""
        self.log_event(
            f"🏁 **SIMULATION ENDED** - {total_turns} turns completed, {total_events} events logged"
        )

    def get_log_stats(self) -> dict:
        """Get logging statistics."""
        log_size = 0
        if os.path.exists(self.campaign_log_path):
            log_size = os.path.getsize(self.campaign_log_path)

        return {
            "log_path": self.campaign_log_path,
            "events_logged": self.events_logged,
            "log_size_bytes": log_size,
            "log_exists": os.path.exists(self.campaign_log_path),
        }

    def rotate_log(self, max_size_mb: float = 10.0) -> bool:
        """
        Rotate log file if it exceeds size limit.

        Args:
            max_size_mb: Maximum log size in MB before rotation

        Returns:
            True if rotation occurred, False otherwise
        """
        if not os.path.exists(self.campaign_log_path):
            return False

        log_size_mb = os.path.getsize(self.campaign_log_path) / (1024 * 1024)

        if log_size_mb > max_size_mb:
            try:
                # Archive current log
                archive_path = f"{self.campaign_log_path}.archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.campaign_log_path, archive_path)

                # Create new log
                self._create_new_campaign_log()
                self.log_event(
                    f"📋 Log rotated. Previous log archived to: {archive_path}"
                )

                logger.info(f"Log rotated: {archive_path}")
                return True

            except (FileNotFoundError, PermissionError, IOError, OSError) as e:
                # File system errors during log rotation
                logger.error(
                    f"File system error rotating log: {e}",
                    extra={"error_type": type(e).__name__},
                )
                return False
            except (ValueError, RuntimeError) as e:
                # Rotation operation or initialization errors
                logger.error(
                    f"Log rotation error: {e}", extra={"error_type": type(e).__name__}
                )
                return False

        return False
