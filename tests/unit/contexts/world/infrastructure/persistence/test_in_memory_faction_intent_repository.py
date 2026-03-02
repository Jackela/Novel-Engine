#!/usr/bin/env python3
"""Unit tests for InMemoryFactionIntentRepository.

Tests thread safety, constraint enforcement, and core repository operations.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest

from src.contexts.world.domain.entities.faction_intent import (
    ActionType,
    FactionIntent,
    IntentStatus,
)
from src.contexts.world.infrastructure.persistence.in_memory_faction_intent_repository import (
    InMemoryFactionIntentRepository,
)

pytestmark = pytest.mark.unit


class TestInMemoryFactionIntentRepositoryThreadSafety:
    """Tests for thread safety of repository operations."""

    @pytest.mark.unit
    def test_concurrent_saves_are_thread_safe(self):
        """Test that concurrent saves don't cause race conditions."""
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-concurrent"
        num_threads = 20
        intents_per_thread = 5

        def save_intents(thread_id: int) -> None:
            for i in range(intents_per_thread):
                intent = FactionIntent(
                    faction_id=faction_id,
                    action_type=ActionType.STABILIZE,
                    rationale=f"Thread {thread_id} intent {i}",
                    priority=1,
                )
                repo.save(intent)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(save_intents, i) for i in range(num_threads)]
            for future in futures:
                future.result()

        # Verify all intents were saved
        all_intents = repo.find_by_faction(faction_id)
        assert len(all_intents) == num_threads * intents_per_thread

    @pytest.mark.unit
    def test_concurrent_read_write_operations(self):
        """Test concurrent reads and writes don't cause issues."""
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-rw"
        num_operations = 50

        # Pre-populate some intents
        for i in range(10):
            intent = FactionIntent(
                faction_id=faction_id,
                action_type=ActionType.STABILIZE,
                rationale=f"Initial intent {i}",
                priority=1,
            )
            repo.save(intent)

        errors = []

        def read_operations() -> None:
            try:
                for _ in range(num_operations):
                    repo.find_by_faction(faction_id)
                    repo.count_active(faction_id)
            except Exception as e:
                errors.append(e)

        def write_operations() -> None:
            try:
                for i in range(num_operations):
                    intent = FactionIntent(
                        faction_id=faction_id,
                        action_type=ActionType.EXPAND,
                        rationale=f"Write intent {i}",
                        priority=2,
                    )
                    repo.save(intent)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=read_operations),
            threading.Thread(target=read_operations),
            threading.Thread(target=write_operations),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestInMemoryFactionIntentRepositoryConstraints:
    """Tests for max active intents constraint enforcement."""

    @pytest.mark.unit
    def test_max_10_active_intents_enforced(self):
        """Test that saving more than 10 active intents triggers auto-rejection."""
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-max"

        # Save 15 PROPOSED intents
        for i in range(15):
            intent = FactionIntent(
                faction_id=faction_id,
                action_type=ActionType.STABILIZE,
                rationale=f"Intent {i}",
                priority=1,
            )
            repo.save(intent)

        # Count active (PROPOSED) intents - should be max 10
        active_count = repo.count_active(faction_id)
        assert active_count <= repo.MAX_ACTIVE_INTENTS

        # The oldest intents should have been rejected
        all_intents = repo.find_by_faction(faction_id)
        rejected_count = sum(1 for i in all_intents if i.status == IntentStatus.REJECTED)
        assert rejected_count >= 5  # At least 5 should be rejected

    @pytest.mark.unit
    def test_selected_intents_not_counted_as_active(self):
        """Test that SELECTED intents don't count toward max active limit."""
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-selected"

        # Save and select 5 intents
        for i in range(5):
            intent = FactionIntent(
                faction_id=faction_id,
                action_type=ActionType.STABILIZE,
                rationale=f"Intent {i}",
                priority=1,
            )
            repo.save(intent)
            repo.mark_selected(intent.id)

        # Now save 10 more PROPOSED intents
        for i in range(10):
            intent = FactionIntent(
                faction_id=faction_id,
                action_type=ActionType.EXPAND,
                rationale=f"Later intent {i}",
                priority=2,
            )
            repo.save(intent)

        # Active count should only count PROPOSED, not SELECTED
        active_count = repo.count_active(faction_id)
        assert active_count <= repo.MAX_ACTIVE_INTENTS


class TestInMemoryFactionIntentRepositoryOperations:
    """Tests for core repository operations."""

    @pytest.mark.unit
    def test_expire_old_intents(self):
        """Test that old intents are expired correctly."""
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-expire"

        # Create an old intent (8 days ago)
        old_intent = FactionIntent(
            faction_id=faction_id,
            action_type=ActionType.STABILIZE,
            rationale="Old intent",
            priority=1,
            created_at=datetime.now() - timedelta(days=8),
        )
        repo.save(old_intent)

        # Create a new intent
        new_intent = FactionIntent(
            faction_id=faction_id,
            action_type=ActionType.EXPAND,
            rationale="New intent",
            priority=2,
            created_at=datetime.now(),
        )
        repo.save(new_intent)

        # Expire intents older than 7 days
        expired_count = repo.expire_old_intents(faction_id, max_age_days=7)

        assert expired_count == 1

        # Verify old intent is rejected
        old = repo.find_by_id(old_intent.id)
        assert old.status == IntentStatus.REJECTED

        # Verify new intent is still proposed
        new = repo.find_by_id(new_intent.id)
        assert new.status == IntentStatus.PROPOSED

    @pytest.mark.unit
    def test_find_by_action_type(self):
        """Test filtering intents by action type."""
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-action-type"

        # Create intents with different action types
        for action_type in [ActionType.EXPAND, ActionType.ATTACK, ActionType.TRADE]:
            for i in range(3):
                intent = FactionIntent(
                    faction_id=faction_id,
                    action_type=action_type,
                    rationale=f"{action_type.value} intent {i}",
                    priority=1,
                )
                repo.save(intent)

        # Find only ATTACK intents
        attack_intents = repo.find_by_action_type(faction_id, ActionType.ATTACK)
        assert len(attack_intents) == 3
        for intent in attack_intents:
            assert intent.action_type == ActionType.ATTACK

        # Find only TRADE intents
        trade_intents = repo.find_by_action_type(faction_id, ActionType.TRADE)
        assert len(trade_intents) == 3
        for intent in trade_intents:
            assert intent.action_type == ActionType.TRADE

    @pytest.mark.unit
    def test_mark_executed(self):
        """Test marking an intent as executed."""
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-executed"

        intent = FactionIntent(
            faction_id=faction_id,
            action_type=ActionType.STABILIZE,
            rationale="Test intent",
            priority=1,
        )
        repo.save(intent)

        # First select it
        repo.mark_selected(intent.id)

        # Then execute it
        success = repo.mark_executed(intent.id)
        assert success is True

        executed = repo.find_by_id(intent.id)
        assert executed.status == IntentStatus.EXECUTED
        assert executed.is_terminal is True

    @pytest.mark.unit
    def test_mark_rejected(self):
        """Test marking an intent as rejected."""
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-rejected"

        intent = FactionIntent(
            faction_id=faction_id,
            action_type=ActionType.STABILIZE,
            rationale="Test intent",
            priority=1,
        )
        repo.save(intent)

        success = repo.mark_rejected(intent.id)
        assert success is True

        rejected = repo.find_by_id(intent.id)
        assert rejected.status == IntentStatus.REJECTED
        assert rejected.is_terminal is True

    @pytest.mark.unit
    def test_mark_rejected_already_terminal_is_idempotent(self):
        """Test that rejecting an already rejected intent is idempotent.

        Note: The implementation treats same-status transitions as no-ops,
        so calling reject() on an already rejected intent succeeds (no-op).
        """
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-rejected-fail"

        intent = FactionIntent(
            faction_id=faction_id,
            action_type=ActionType.STABILIZE,
            rationale="Test intent",
            priority=1,
        )
        repo.save(intent)

        # Reject once
        success1 = repo.mark_rejected(intent.id)
        assert success1 is True

        # Reject again - returns True because it's idempotent (same status)
        success2 = repo.mark_rejected(intent.id)
        assert success2 is True

        # Verify status remains REJECTED
        rejected = repo.find_by_id(intent.id)
        assert rejected.status == IntentStatus.REJECTED

    @pytest.mark.unit
    def test_mark_executed_after_rejected_fails(self):
        """Test that executing a rejected intent fails."""
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-executed-after-rejected"

        intent = FactionIntent(
            faction_id=faction_id,
            action_type=ActionType.STABILIZE,
            rationale="Test intent",
            priority=1,
        )
        repo.save(intent)

        # Reject it first
        repo.mark_rejected(intent.id)

        # Try to execute - should fail because REJECTED is terminal
        success = repo.mark_executed(intent.id)
        assert success is False

    @pytest.mark.unit
    def test_find_by_faction_paginated(self):
        """Test paginated retrieval of faction intents."""
        repo = InMemoryFactionIntentRepository()
        faction_id = "test-faction-paginated"

        # Create 25 intents
        for i in range(25):
            intent = FactionIntent(
                faction_id=faction_id,
                action_type=ActionType.STABILIZE,
                rationale=f"Intent {i}",
                priority=(i % 3) + 1,
            )
            repo.save(intent)

        # Get first page
        page1, total, has_more = repo.find_by_faction_paginated(
            faction_id, limit=10, offset=0
        )
        assert len(page1) == 10
        assert total == 25
        assert has_more is True

        # Get second page
        page2, total, has_more = repo.find_by_faction_paginated(
            faction_id, limit=10, offset=10
        )
        assert len(page2) == 10
        assert total == 25
        assert has_more is True

        # Get last page
        page3, total, has_more = repo.find_by_faction_paginated(
            faction_id, limit=10, offset=20
        )
        assert len(page3) == 5
        assert total == 25
        assert has_more is False
