"""Unit tests for DiplomaticPact entity and DiplomacyMatrix pact integration.

Tests cover PactType enum, DiplomaticPact entity, and pact management in DiplomacyMatrix.
"""

from datetime import datetime, timedelta

import pytest

from src.contexts.world.domain.aggregates import DiplomacyMatrix
from src.contexts.world.domain.entities import (
    DiplomaticPact,
    PactType,
)
from src.contexts.world.domain.value_objects import DiplomaticStatus

pytestmark = pytest.mark.unit


class TestPactType:
    """Tests for PactType enum."""

    def test_pact_type_values(self) -> None:
        """Test that all expected pact types exist."""
        assert PactType.TRADE_AGREEMENT.value == "trade_agreement"
        assert PactType.NON_AGGRESSION.value == "non_aggression"
        assert PactType.ALLIANCE.value == "alliance"
        assert PactType.WAR.value == "war"
        assert PactType.CEASEFIRE.value == "ceasefire"

    def test_is_hostile(self) -> None:
        """Test hostile pact type identification."""
        assert PactType.WAR.is_hostile() is True
        assert PactType.ALLIANCE.is_hostile() is False
        assert PactType.TRADE_AGREEMENT.is_hostile() is False

    def test_is_friendly(self) -> None:
        """Test friendly pact type identification."""
        assert PactType.ALLIANCE.is_friendly() is True
        assert PactType.DEFENSIVE_PACT.is_friendly() is True
        assert PactType.TRADE_AGREEMENT.is_friendly() is True
        assert PactType.WAR.is_friendly() is False

    def test_is_economic(self) -> None:
        """Test economic pact type identification."""
        assert PactType.TRADE_AGREEMENT.is_economic() is True
        assert PactType.ALLIANCE.is_economic() is True
        assert PactType.WAR.is_economic() is False

    def test_is_military(self) -> None:
        """Test military pact type identification."""
        assert PactType.ALLIANCE.is_military() is True
        assert PactType.WAR.is_military() is True
        assert PactType.DEFENSIVE_PACT.is_military() is True
        assert PactType.TRADE_AGREEMENT.is_military() is False


class TestDiplomaticPact:
    """Tests for DiplomaticPact entity."""

    def test_create_pact(self) -> None:
        """Test basic pact creation."""
        pact = DiplomaticPact(
            pact_type=PactType.TRADE_AGREEMENT,
            faction_a_id="faction-1",
            faction_b_id="faction-2",
        )
        assert pact.pact_type == PactType.TRADE_AGREEMENT
        assert pact.faction_a_id == "faction-1"
        assert pact.faction_b_id == "faction-2"
        assert pact.is_active() is True
        assert pact.is_broken is False

    def test_is_active_with_expiration(self) -> None:
        """Test is_active with expiration date."""
        # Active pact (expires in future)
        future_date = datetime.now() + timedelta(days=30)
        active_pact = DiplomaticPact(
            pact_type=PactType.TRADE_AGREEMENT,
            faction_a_id="f1",
            faction_b_id="f2",
            expires_date=future_date,
        )
        assert active_pact.is_active() is True

        # Expired pact - signed in past, expired recently
        past_signed = datetime.now() - timedelta(days=60)
        past_expires = datetime.now() - timedelta(days=1)
        expired_pact = DiplomaticPact(
            pact_type=PactType.TRADE_AGREEMENT,
            faction_a_id="f1",
            faction_b_id="f2",
            signed_date=past_signed,
            expires_date=past_expires,
        )
        assert expired_pact.is_active() is False

    def test_is_active_when_broken(self) -> None:
        """Test is_active returns False for broken pacts."""
        pact = DiplomaticPact(
            pact_type=PactType.ALLIANCE,
            faction_a_id="f1",
            faction_b_id="f2",
            is_broken=True,
            broken_date=datetime.now(),
            broken_by="f1",
        )
        assert pact.is_active() is False

    def test_involves_faction(self) -> None:
        """Test involves_faction check."""
        pact = DiplomaticPact(
            pact_type=PactType.ALLIANCE,
            faction_a_id="faction-1",
            faction_b_id="faction-2",
        )
        assert pact.involves_faction("faction-1") is True
        assert pact.involves_faction("faction-2") is True
        assert pact.involves_faction("faction-3") is False

    def test_get_other_faction(self) -> None:
        """Test get_other_faction method."""
        pact = DiplomaticPact(
            pact_type=PactType.ALLIANCE,
            faction_a_id="faction-1",
            faction_b_id="faction-2",
        )
        assert pact.get_other_faction("faction-1") == "faction-2"
        assert pact.get_other_faction("faction-2") == "faction-1"
        assert pact.get_other_faction("faction-3") is None

    def test_break_pact(self) -> None:
        """Test breaking a pact."""
        pact = DiplomaticPact(
            pact_type=PactType.ALLIANCE,
            faction_a_id="f1",
            faction_b_id="f2",
        )

        pact.break_pact("f1")

        assert pact.is_broken is True
        assert pact.broken_by == "f1"
        assert pact.broken_date is not None
        assert pact.is_active() is False

    def test_break_pact_by_non_party_raises_error(self) -> None:
        """Test that non-party cannot break pact."""
        pact = DiplomaticPact(
            pact_type=PactType.ALLIANCE,
            faction_a_id="f1",
            faction_b_id="f2",
        )

        with pytest.raises(ValueError, match="is not party to this pact"):
            pact.break_pact("f3")

    def test_renew_pact(self) -> None:
        """Test renewing a pact."""
        pact = DiplomaticPact(
            pact_type=PactType.CEASEFIRE,
            faction_a_id="f1",
            faction_b_id="f2",
            expires_date=datetime.now() + timedelta(days=1),
        )

        new_expires = datetime.now() + timedelta(days=30)
        pact.renew(new_expires)

        assert pact.expires_date == new_expires

    def test_renew_broken_pact_raises_error(self) -> None:
        """Test that broken pact cannot be renewed."""
        pact = DiplomaticPact(
            pact_type=PactType.ALLIANCE,
            faction_a_id="f1",
            faction_b_id="f2",
            is_broken=True,
            broken_date=datetime.now(),
            broken_by="f1",
        )

        with pytest.raises(ValueError, match="Cannot renew a broken pact"):
            pact.renew(datetime.now() + timedelta(days=30))

    def test_is_incompatible_with(self) -> None:
        """Test pact incompatibility checking."""
        war_pact = DiplomaticPact(
            pact_type=PactType.WAR, faction_a_id="f1", faction_b_id="f2"
        )
        trade_pact = DiplomaticPact(
            pact_type=PactType.TRADE_AGREEMENT, faction_a_id="f1", faction_b_id="f2"
        )

        assert war_pact.is_incompatible_with(PactType.TRADE_AGREEMENT) is True
        assert trade_pact.is_incompatible_with(PactType.WAR) is True
        assert war_pact.is_incompatible_with(PactType.ALLIANCE) is True

    def test_validation_faction_with_self_raises_error(self) -> None:
        """Test that pact with self raises validation error."""
        with pytest.raises(ValueError, match="cannot make a pact with itself"):
            DiplomaticPact(
                pact_type=PactType.ALLIANCE,
                faction_a_id="f1",
                faction_b_id="f1",
            )

    def test_validation_expires_before_signed_raises_error(self) -> None:
        """Test that expiration before signed raises error."""
        with pytest.raises(
            ValueError, match="Expiration date cannot be before signed date"
        ):
            DiplomaticPact(
                pact_type=PactType.CEASEFIRE,
                faction_a_id="f1",
                faction_b_id="f2",
                signed_date=datetime.now(),
                expires_date=datetime.now() - timedelta(days=1),
            )


class TestDiplomaticPactFactoryMethods:
    """Tests for DiplomaticPact factory methods."""

    def test_create_alliance(self) -> None:
        """Test alliance factory method."""
        alliance = DiplomaticPact.create_alliance(
            faction_a_id="kingdom-1",
            faction_b_id="kingdom-2",
            terms={"mutual_defense": True},
        )

        assert alliance.pact_type == PactType.ALLIANCE
        assert alliance.faction_a_id == "kingdom-1"
        assert alliance.faction_b_id == "kingdom-2"
        assert alliance.terms == {"mutual_defense": True}
        assert alliance.expires_date is None  # Permanent by default

    def test_create_alliance_with_duration(self) -> None:
        """Test alliance with duration."""
        alliance = DiplomaticPact.create_alliance(
            faction_a_id="k1",
            faction_b_id="k2",
            duration_days=365,
        )

        assert alliance.expires_date is not None
        assert alliance.expires_date > datetime.now()

    def test_create_trade_agreement(self) -> None:
        """Test trade agreement factory method."""
        trade = DiplomaticPact.create_trade_agreement(
            faction_a_id="merchant-1",
            faction_b_id="merchant-2",
            terms={"tariff_reduction": 0.1},
        )

        assert trade.pact_type == PactType.TRADE_AGREEMENT

    def test_create_war_declaration(self) -> None:
        """Test war declaration factory method."""
        war = DiplomaticPact.create_war_declaration(
            faction_a_id="kingdom-1",
            faction_b_id="kingdom-2",
            casus_belli="Territorial dispute",
        )

        assert war.pact_type == PactType.WAR
        assert war.terms["casus_belli"] == "Territorial dispute"
        assert war.expires_date is None  # Wars don't expire

    def test_create_ceasefire(self) -> None:
        """Test ceasefire factory method."""
        ceasefire = DiplomaticPact.create_ceasefire(
            faction_a_id="f1",
            faction_b_id="f2",
            duration_days=30,
        )

        assert ceasefire.pact_type == PactType.CEASEFIRE
        assert ceasefire.expires_date is not None


class TestDiplomacyMatrixPacts:
    """Tests for pact management in DiplomacyMatrix."""

    def test_add_pact(self) -> None:
        """Test adding a pact to the matrix."""
        matrix = DiplomacyMatrix(world_id="world-1")
        pact = DiplomaticPact.create_trade_agreement("f1", "f2")

        result = matrix.add_pact(pact)

        assert result.is_ok
        assert len(matrix.active_pacts) == 1
        assert "f1" in matrix.faction_ids
        assert "f2" in matrix.faction_ids

    def test_get_pacts_between(self) -> None:
        """Test getting pacts between two factions."""
        matrix = DiplomacyMatrix(world_id="world-1")
        pact1 = DiplomaticPact.create_trade_agreement("f1", "f2")
        pact2 = DiplomaticPact.create_alliance("f1", "f3")

        matrix.add_pact(pact1)
        matrix.add_pact(pact2)

        pacts = matrix.get_pacts_between("f1", "f2")
        assert len(pacts) == 1
        assert pacts[0].pact_type == PactType.TRADE_AGREEMENT

    def test_get_active_pacts_between(self) -> None:
        """Test getting only active pacts."""
        matrix = DiplomacyMatrix(world_id="world-1")

        # Active pact
        active = DiplomaticPact.create_trade_agreement("f1", "f2")
        matrix.add_pact(active)

        # Broken pact
        broken = DiplomaticPact.create_alliance("f1", "f2")
        broken.break_pact("f1")
        matrix.active_pacts.append(broken)  # Add directly for test

        active_pacts = matrix.get_active_pacts_between("f1", "f2")
        assert len(active_pacts) == 1
        assert active_pacts[0].pact_type == PactType.TRADE_AGREEMENT

    def test_add_pact_war_blocks_trade(self) -> None:
        """Test that war prevents trade agreement."""
        matrix = DiplomacyMatrix(world_id="world-1")
        matrix.set_status("f1", "f2", DiplomaticStatus.AT_WAR)

        trade = DiplomaticPact.create_trade_agreement("f1", "f2")
        result = matrix.add_pact(trade)

        assert result.is_error
        assert "war" in str(result.error).lower()

    def test_remove_pact(self) -> None:
        """Test removing a pact."""
        matrix = DiplomacyMatrix(world_id="world-1")
        pact = DiplomaticPact.create_trade_agreement("f1", "f2")
        matrix.add_pact(pact)

        result = matrix.remove_pact(pact.id)

        assert result is True
        assert len(matrix.active_pacts) == 0

    def test_remove_pact_not_found(self) -> None:
        """Test removing non-existent pact."""
        matrix = DiplomacyMatrix(world_id="world-1")

        result = matrix.remove_pact("nonexistent")

        assert result is False

    def test_get_pacts_for_faction(self) -> None:
        """Test getting all pacts for a faction."""
        matrix = DiplomacyMatrix(world_id="world-1")
        pact1 = DiplomaticPact.create_trade_agreement("f1", "f2")
        pact2 = DiplomaticPact.create_alliance("f1", "f3")
        pact3 = DiplomaticPact.create_trade_agreement("f2", "f3")

        matrix.add_pact(pact1)
        matrix.add_pact(pact2)
        matrix.add_pact(pact3)

        f1_pacts = matrix.get_pacts_for_faction("f1")
        assert len(f1_pacts) == 2

    def test_cleanup_expired_pacts(self) -> None:
        """Test cleaning up expired pacts."""
        matrix = DiplomacyMatrix(world_id="world-1")

        # Active pact
        active = DiplomaticPact(
            pact_type=PactType.TRADE_AGREEMENT,
            faction_a_id="f1",
            faction_b_id="f2",
            expires_date=datetime.now() + timedelta(days=30),
        )
        matrix.add_pact(active)

        # Expired pact (add directly to bypass validation)
        expired = DiplomaticPact(
            pact_type=PactType.CEASEFIRE,
            faction_a_id="f1",
            faction_b_id="f3",
            signed_date=datetime.now() - timedelta(days=60),
            expires_date=datetime.now() - timedelta(days=30),
        )
        matrix.active_pacts.append(expired)

        removed = matrix.cleanup_expired_pacts()

        assert removed == 1
        assert len(matrix.active_pacts) == 1
