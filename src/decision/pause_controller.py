"""
Interaction Pause Controller

Manages the pause/resume mechanism for user interaction during story generation.
Uses asyncio.Event for non-blocking wait with timeout support.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from .models import (
    DecisionPoint,
    NegotiationResult,
    PauseState,
    PendingDecision,
    UserDecision,
)

logger = logging.getLogger(__name__)


class InteractionPauseController:
    """
    Controls the pause/resume flow for user decision points.

    When a decision point is detected, the controller:
    1. Pauses the turn loop
    2. Waits for user input (with timeout)
    3. Optionally negotiates the input
    4. Resumes with the final decision

    Thread-safe for use with asyncio-based orchestration.
    """

    def __init__(
        self,
        default_timeout: int = 120,
        on_decision_point: Optional[Callable[[DecisionPoint], None]] = None,
        on_resolution: Optional[Callable[[PendingDecision], None]] = None,
    ):
        """
        Initialize the pause controller.

        Args:
            default_timeout: Default timeout in seconds for user response
            on_decision_point: Callback when a decision point is created
            on_resolution: Callback when a decision is resolved
        """
        self._default_timeout = default_timeout
        self._on_decision_point = on_decision_point
        self._on_resolution = on_resolution

        # Internal state
        self._resume_event = asyncio.Event()
        self._pending: Optional[PendingDecision] = None
        self._state: PauseState = PauseState.RUNNING
        self._lock = asyncio.Lock()

    @property
    def state(self) -> PauseState:
        """Get current pause state."""
        return self._state

    @property
    def is_paused(self) -> bool:
        """Check if currently paused waiting for input."""
        return self._state in (PauseState.AWAITING_INPUT, PauseState.NEGOTIATING)

    @property
    def current_decision_point(self) -> Optional[DecisionPoint]:
        """Get the current pending decision point, if any."""
        return self._pending.decision_point if self._pending else None

    async def pause_for_decision(
        self,
        decision_point: DecisionPoint,
    ) -> UserDecision:
        """
        Pause and wait for user input on a decision point.

        Args:
            decision_point: The decision point requiring user input

        Returns:
            UserDecision with user's response or default if timeout
        """
        async with self._lock:
            if self._state != PauseState.RUNNING:
                logger.warning("Cannot pause: already in state %s", self._state)
                return UserDecision(
                    decision_id=decision_point.decision_id,
                    input_type="option",
                    use_default=True,
                )

            # Create pending decision
            self._pending = PendingDecision(
                decision_point=decision_point,
                state=PauseState.AWAITING_INPUT,
            )
            self._state = PauseState.AWAITING_INPUT
            self._resume_event.clear()

            logger.info(
                "Paused for decision point: %s (timeout: %ds)",
                decision_point.decision_id,
                decision_point.timeout_seconds,
            )

            # Notify callback
            if self._on_decision_point:
                try:
                    self._on_decision_point(decision_point)
                except Exception as e:
                    logger.error("Error in decision point callback: %s", e)

        # Wait for user response (outside lock to allow submit_response)
        try:
            timeout = decision_point.timeout_seconds or self._default_timeout
            await asyncio.wait_for(
                self._resume_event.wait(),
                timeout=timeout,
            )

            # User responded in time
            async with self._lock:
                if self._pending and self._pending.user_response:
                    response = self._pending.user_response
                    logger.info(
                        "Decision point %s resolved by user input",
                        decision_point.decision_id,
                    )
                else:
                    # Shouldn't happen, but handle gracefully
                    response = UserDecision(
                        decision_id=decision_point.decision_id,
                        input_type="option",
                        use_default=True,
                    )

        except asyncio.TimeoutError:
            # Timeout - use default option
            logger.info(
                "Decision point %s timed out after %ds",
                decision_point.decision_id,
                timeout,
            )
            async with self._lock:
                response = UserDecision(
                    decision_id=decision_point.decision_id,
                    input_type="option",
                    selected_option_id=decision_point.default_option_id,
                    use_default=True,
                )
                if self._pending:
                    self._pending.user_response = response
                    self._pending.decision_point.is_resolved = True
                    self._pending.decision_point.resolution = "timeout"

        # Finalize
        async with self._lock:
            if self._pending:
                self._pending.resolved_at = datetime.now(timezone.utc)
                self._pending.state = PauseState.RESUMING

                # Notify callback
                if self._on_resolution:
                    try:
                        self._on_resolution(self._pending)
                    except Exception as e:
                        logger.error("Error in resolution callback: %s", e)

            self._state = PauseState.RUNNING
            pending = self._pending
            self._pending = None

        return response

    async def submit_response(
        self,
        decision_id: str,
        input_type: str,
        selected_option_id: Optional[int] = None,
        free_text: Optional[str] = None,
    ) -> bool:
        """
        Submit user response to a pending decision point.

        Args:
            decision_id: ID of the decision point
            input_type: "option" or "freetext"
            selected_option_id: Selected option ID (for option input)
            free_text: User's free text input (for freetext input)

        Returns:
            True if response was accepted, False otherwise
        """
        async with self._lock:
            if not self._pending:
                logger.warning("No pending decision to respond to")
                return False

            if self._pending.decision_point.decision_id != decision_id:
                logger.warning(
                    "Decision ID mismatch: expected %s, got %s",
                    self._pending.decision_point.decision_id,
                    decision_id,
                )
                return False

            if self._state not in (PauseState.AWAITING_INPUT, PauseState.NEGOTIATING):
                logger.warning("Cannot submit response in state: %s", self._state)
                return False

            # Create user decision
            self._pending.user_response = UserDecision(
                decision_id=decision_id,
                input_type=input_type,
                selected_option_id=selected_option_id,
                free_text=free_text,
                use_default=False,
            )
            self._pending.decision_point.is_resolved = True
            self._pending.decision_point.resolution = "user_input"

            logger.info(
                "User response submitted for decision %s: %s",
                decision_id,
                input_type,
            )

        # Signal resume
        self._resume_event.set()
        return True

    async def skip_decision(self, decision_id: str) -> bool:
        """
        Skip the current decision point, using default option.

        Args:
            decision_id: ID of the decision point to skip

        Returns:
            True if skip was accepted, False otherwise
        """
        async with self._lock:
            if not self._pending:
                return False

            if self._pending.decision_point.decision_id != decision_id:
                return False

            # Use default
            self._pending.user_response = UserDecision(
                decision_id=decision_id,
                input_type="option",
                selected_option_id=self._pending.decision_point.default_option_id,
                use_default=True,
            )
            self._pending.decision_point.is_resolved = True
            self._pending.decision_point.resolution = "skipped"

            logger.info("Decision point %s skipped", decision_id)

        self._resume_event.set()
        return True

    async def start_negotiation(
        self,
        decision_id: str,
        negotiation_result: NegotiationResult,
    ) -> bool:
        """
        Start negotiation phase for a free text input.

        Args:
            decision_id: ID of the decision point
            negotiation_result: Result of LLM feasibility evaluation

        Returns:
            True if negotiation started, False otherwise
        """
        async with self._lock:
            if not self._pending:
                return False

            if self._pending.decision_point.decision_id != decision_id:
                return False

            if self._state != PauseState.AWAITING_INPUT:
                return False

            self._pending.negotiation_result = negotiation_result
            self._pending.state = PauseState.NEGOTIATING
            self._state = PauseState.NEGOTIATING

            logger.info(
                "Started negotiation for decision %s: %s",
                decision_id,
                negotiation_result.feasibility.value,
            )

        return True

    async def confirm_negotiation(
        self,
        decision_id: str,
        accepted: bool,
        insist_original: bool = False,
    ) -> bool:
        """
        Confirm or reject negotiation result.

        Args:
            decision_id: ID of the decision point
            accepted: Whether user accepts the adjusted action
            insist_original: Whether user insists on original input

        Returns:
            True if confirmation processed, False otherwise
        """
        async with self._lock:
            if not self._pending:
                return False

            if self._pending.decision_point.decision_id != decision_id:
                return False

            if self._state != PauseState.NEGOTIATING:
                return False

            if self._pending.negotiation_result:
                self._pending.negotiation_result.user_confirmed = accepted
                self._pending.negotiation_result.user_insisted = insist_original

                # Set final action
                if accepted and self._pending.negotiation_result.adjusted_action:
                    self._pending.final_action = self._pending.negotiation_result.adjusted_action
                elif self._pending.user_response and self._pending.user_response.free_text:
                    self._pending.final_action = self._pending.user_response.free_text

            self._pending.decision_point.is_resolved = True
            self._pending.decision_point.resolution = "user_input"

            logger.info(
                "Negotiation confirmed for decision %s: accepted=%s, insist=%s",
                decision_id,
                accepted,
                insist_original,
            )

        self._resume_event.set()
        return True

    def get_status(self) -> dict:
        """Get current status of the pause controller."""
        return {
            "state": self._state.value,
            "is_paused": self.is_paused,
            "pending_decision": (
                self._pending.decision_point.to_dict()
                if self._pending
                else None
            ),
            "negotiation": (
                self._pending.negotiation_result.to_dict()
                if self._pending and self._pending.negotiation_result
                else None
            ),
        }

    async def reset(self):
        """Reset the controller to initial state."""
        async with self._lock:
            if self._pending:
                logger.warning(
                    "Resetting with pending decision: %s",
                    self._pending.decision_point.decision_id,
                )
            self._pending = None
            self._state = PauseState.RUNNING
            self._resume_event.clear()
