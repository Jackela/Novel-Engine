"""Unit tests for resource value objects and entities.

Tests cover ResourceType, ResourceYield, FactionResources, and Resource entity.
"""

import pytest


pytestmark = pytest.mark.unit

from src.contexts.world.domain.entities import Resource
from src.contexts.world.domain.value_objects import (
    FactionResources,
    ResourceType,
    ResourceYield,
)


@pytest.mark.unit
class TestResourceType:
    """Tests for ResourceType enum."""

    def test_resource_type_values(self) -> None:
        """Test that all expected resource types exist."""
        assert ResourceType.GOLD.value == "gold"
        assert ResourceType.FOOD.value == "food"
        assert ResourceType.MANA.value == "mana"
        assert ResourceType.IRON.value == "iron"
        assert ResourceType.WOOD.value == "wood"
        assert ResourceType.POPULATION.value == "population"
        assert ResourceType.KNOWLEDGE.value == "knowledge"
        assert ResourceType.MILITARY.value == "military"
        assert ResourceType.TRADE_GOODS.value == "trade_goods"
        assert ResourceType.CULTURAL_INFLUENCE.value == "cultural_influence"

    def test_is_strategic(self) -> None:
        """Test strategic resource identification."""
        assert ResourceType.MILITARY.is_strategic() is True
        assert ResourceType.KNOWLEDGE.is_strategic() is True
        assert ResourceType.MANA.is_strategic() is True
        assert ResourceType.GOLD.is_strategic() is False
        assert ResourceType.FOOD.is_strategic() is False

    def test_is_consumable(self) -> None:
        """Test consumable resource identification."""
        assert ResourceType.FOOD.is_consumable() is True
        assert ResourceType.MANA.is_consumable() is True
        assert ResourceType.MILITARY.is_consumable() is True
        assert ResourceType.GOLD.is_consumable() is False
        assert ResourceType.IRON.is_consumable() is False

    def test_is_tradeable(self) -> None:
        """Test tradeable resource identification."""
        assert ResourceType.GOLD.is_tradeable() is True
        assert ResourceType.FOOD.is_tradeable() is True
        assert ResourceType.IRON.is_tradeable() is True
        assert ResourceType.POPULATION.is_tradeable() is False
        assert ResourceType.KNOWLEDGE.is_tradeable() is False


@pytest.mark.unit
class TestResourceYield:
    """Tests for ResourceYield value object."""

    def test_create_resource_yield(self) -> None:
        """Test basic ResourceYield creation."""
        yield_obj = ResourceYield(
            resource_type=ResourceType.GOLD,
            base_amount=100,
            modifier=1.5,
        )
        assert yield_obj.resource_type == ResourceType.GOLD
        assert yield_obj.base_amount == 100
        assert yield_obj.modifier == 1.5
        assert yield_obj.current_stock == 0

    def test_calculate_yield(self) -> None:
        """Test yield calculation with modifier."""
        yield_obj = ResourceYield(
            resource_type=ResourceType.FOOD,
            base_amount=50,
            modifier=1.2,
        )
        assert yield_obj.calculate_yield() == 60

    def test_calculate_yield_default_modifier(self) -> None:
        """Test yield calculation with default modifier."""
        yield_obj = ResourceYield(
            resource_type=ResourceType.IRON,
            base_amount=100,
        )
        assert yield_obj.calculate_yield() == 100

    def test_invalid_base_amount(self) -> None:
        """Test that negative base amount raises error."""
        with pytest.raises(ValueError, match="Base amount cannot be negative"):
            ResourceYield(
                resource_type=ResourceType.GOLD,
                base_amount=-10,
            )

    def test_invalid_modifier(self) -> None:
        """Test that negative modifier raises error."""
        with pytest.raises(ValueError, match="Modifier cannot be negative"):
            ResourceYield(
                resource_type=ResourceType.GOLD,
                base_amount=100,
                modifier=-0.5,
            )

    def test_with_modifier(self) -> None:
        """Test creating new yield with updated modifier."""
        original = ResourceYield(
            resource_type=ResourceType.GOLD,
            base_amount=100,
            modifier=1.0,
        )
        updated = original.with_modifier(2.0)
        assert updated.modifier == 2.0
        assert original.modifier == 1.0  # Original unchanged (frozen)

    def test_add_to_stock(self) -> None:
        """Test adding to stock creates new instance."""
        original = ResourceYield(
            resource_type=ResourceType.GOLD,
            base_amount=100,
            current_stock=50,
        )
        updated = original.add_to_stock(25)
        assert updated.current_stock == 75
        assert original.current_stock == 50  # Original unchanged

    def test_collect_yield(self) -> None:
        """Test collecting yield adds to stock."""
        yield_obj = ResourceYield(
            resource_type=ResourceType.FOOD,
            base_amount=50,
            modifier=1.0,
            current_stock=100,
        )
        updated = yield_obj.collect_yield()
        assert updated.current_stock == 150

    def test_consume(self) -> None:
        """Test consuming from stock."""
        original = ResourceYield(
            resource_type=ResourceType.GOLD,
            base_amount=100,
            current_stock=200,
        )
        updated = original.consume(50)
        assert updated.current_stock == 150

    def test_consume_insufficient(self) -> None:
        """Test consuming more than available raises error."""
        yield_obj = ResourceYield(
            resource_type=ResourceType.GOLD,
            base_amount=100,
            current_stock=50,
        )
        with pytest.raises(ValueError, match="Cannot consume 100, only 50 available"):
            yield_obj.consume(100)


@pytest.mark.unit
class TestFactionResources:
    """Tests for FactionResources value object."""

    def test_create_faction_resources(self) -> None:
        """Test basic FactionResources creation."""
        resources = FactionResources(faction_id="faction-123")
        assert resources.faction_id == "faction-123"
        assert resources.resources == {}

    def test_create_with_initial_resources(self) -> None:
        """Test creating with initial resources."""
        resources = FactionResources(
            faction_id="faction-123",
            resources={ResourceType.GOLD: 1000, ResourceType.FOOD: 500},
        )
        assert resources.get_amount(ResourceType.GOLD) == 1000
        assert resources.get_amount(ResourceType.FOOD) == 500
        assert resources.get_amount(ResourceType.IRON) == 0

    def test_add_resources(self) -> None:
        """Test adding resources creates new instance."""
        original = FactionResources(faction_id="faction-123")
        updated = original.add(ResourceType.GOLD, 500)
        assert updated.get_amount(ResourceType.GOLD) == 500
        assert original.get_amount(ResourceType.GOLD) == 0

    def test_add_negative_raises_error(self) -> None:
        """Test adding negative amount raises error."""
        resources = FactionResources(faction_id="faction-123")
        with pytest.raises(ValueError, match="Cannot add negative amount"):
            resources.add(ResourceType.GOLD, -100)

    def test_spend_resources(self) -> None:
        """Test spending resources."""
        resources = FactionResources(
            faction_id="faction-123",
            resources={ResourceType.GOLD: 1000},
        )
        updated = resources.spend(ResourceType.GOLD, 300)
        assert updated.get_amount(ResourceType.GOLD) == 700

    def test_spend_insufficient_raises_error(self) -> None:
        """Test spending more than available raises error."""
        resources = FactionResources(
            faction_id="faction-123",
            resources={ResourceType.GOLD: 100},
        )
        with pytest.raises(ValueError, match="Insufficient gold"):
            resources.spend(ResourceType.GOLD, 200)

    def test_spend_negative_raises_error(self) -> None:
        """Test spending negative amount raises error."""
        resources = FactionResources(
            faction_id="faction-123",
            resources={ResourceType.GOLD: 1000},
        )
        with pytest.raises(ValueError, match="Cannot spend negative amount"):
            resources.spend(ResourceType.GOLD, -100)

    def test_can_afford(self) -> None:
        """Test can_afford check."""
        resources = FactionResources(
            faction_id="faction-123",
            resources={ResourceType.GOLD: 500},
        )
        assert resources.can_afford(ResourceType.GOLD, 300) is True
        assert resources.can_afford(ResourceType.GOLD, 500) is True
        assert resources.can_afford(ResourceType.GOLD, 600) is False
        assert resources.can_afford(ResourceType.FOOD, 100) is False

    def test_can_afford_all(self) -> None:
        """Test can_afford_all check with multiple resources."""
        resources = FactionResources(
            faction_id="faction-123",
            resources={ResourceType.GOLD: 1000, ResourceType.FOOD: 500},
        )
        assert resources.can_afford_all({
            ResourceType.GOLD: 500,
            ResourceType.FOOD: 200,
        }) is True
        assert resources.can_afford_all({
            ResourceType.GOLD: 1500,
            ResourceType.FOOD: 200,
        }) is False
        assert resources.can_afford_all({
            ResourceType.GOLD: 500,
            ResourceType.FOOD: 600,
        }) is False

    def test_total_value(self) -> None:
        """Test total value calculation."""
        resources = FactionResources(
            faction_id="faction-123",
            resources={
                ResourceType.GOLD: 1000,
                ResourceType.FOOD: 10000,  # 0.01 conversion = 100
                ResourceType.IRON: 200,  # 0.5 conversion = 100
            },
        )
        # 1000 + 100 + 100 = 1200
        assert resources.total_value() == 1200

    def test_merge_resources(self) -> None:
        """Test merging resources from another object."""
        original = FactionResources(
            faction_id="faction-123",
            resources={ResourceType.GOLD: 500, ResourceType.FOOD: 100},
        )
        addition = FactionResources(
            faction_id="faction-123",
            resources={ResourceType.GOLD: 300, ResourceType.IRON: 50},
        )
        merged = original.merge(addition)
        assert merged.get_amount(ResourceType.GOLD) == 800
        assert merged.get_amount(ResourceType.FOOD) == 100
        assert merged.get_amount(ResourceType.IRON) == 50

    def test_merge_different_factions_raises_error(self) -> None:
        """Test merging resources from different faction raises error."""
        resources1 = FactionResources(faction_id="faction-123")
        resources2 = FactionResources(faction_id="faction-456")
        with pytest.raises(ValueError, match="Cannot merge resources from different factions"):
            resources1.merge(resources2)

    def test_to_dict_and_from_dict(self) -> None:
        """Test serialization and deserialization."""
        original = FactionResources(
            faction_id="faction-123",
            resources={ResourceType.GOLD: 1000, ResourceType.FOOD: 500},
        )
        data = original.to_dict()
        assert data == {"gold": 1000, "food": 500}

        restored = FactionResources.from_dict("faction-123", data)
        assert restored.get_amount(ResourceType.GOLD) == 1000
        assert restored.get_amount(ResourceType.FOOD) == 500


@pytest.mark.unit
class TestResourceEntity:
    """Tests for Resource entity."""

    def test_create_resource(self) -> None:
        """Test basic Resource creation."""
        resource = Resource(
            resource_type=ResourceType.GOLD,
            amount=1000,
            max_capacity=5000,
        )
        assert resource.resource_type == ResourceType.GOLD
        assert resource.amount == 1000
        assert resource.max_capacity == 5000

    def test_add_to_resource(self) -> None:
        """Test adding to resource amount."""
        resource = Resource(
            resource_type=ResourceType.GOLD,
            amount=1000,
            max_capacity=5000,
        )
        resource.add(500)
        assert resource.amount == 1500

    def test_add_exceeds_capacity_raises_error(self) -> None:
        """Test adding beyond capacity raises error."""
        resource = Resource(
            resource_type=ResourceType.GOLD,
            amount=4500,
            max_capacity=5000,
        )
        with pytest.raises(ValueError, match="would exceed max capacity"):
            resource.add(1000)

    def test_add_negative_raises_error(self) -> None:
        """Test adding negative raises error."""
        resource = Resource(
            resource_type=ResourceType.GOLD,
            amount=1000,
        )
        with pytest.raises(ValueError, match="Cannot add negative quantity"):
            resource.add(-100)

    def test_consume_from_resource(self) -> None:
        """Test consuming from resource."""
        resource = Resource(
            resource_type=ResourceType.FOOD,
            amount=500,
        )
        resource.consume(200)
        assert resource.amount == 300

    def test_consume_insufficient_raises_error(self) -> None:
        """Test consuming more than available raises error."""
        resource = Resource(
            resource_type=ResourceType.FOOD,
            amount=100,
        )
        with pytest.raises(ValueError, match="Cannot consume 200: only 100 available"):
            resource.consume(200)

    def test_can_add(self) -> None:
        """Test can_add check."""
        resource = Resource(
            resource_type=ResourceType.GOLD,
            amount=4000,
            max_capacity=5000,
        )
        assert resource.can_add(500) is True
        assert resource.can_add(1000) is True  # 4000 + 1000 = 5000 = max
        assert resource.can_add(1001) is False  # 4000 + 1001 = 5001 > max
        assert resource.can_add(-100) is False

    def test_can_consume(self) -> None:
        """Test can_consume check."""
        resource = Resource(
            resource_type=ResourceType.GOLD,
            amount=500,
        )
        assert resource.can_consume(300) is True
        assert resource.can_consume(500) is True
        assert resource.can_consume(600) is False
        assert resource.can_consume(-100) is False

    def test_available_capacity(self) -> None:
        """Test available capacity calculation."""
        limited = Resource(
            resource_type=ResourceType.GOLD,
            amount=3000,
            max_capacity=5000,
        )
        assert limited.available_capacity() == 2000

        unlimited = Resource(
            resource_type=ResourceType.GOLD,
            amount=3000,
            max_capacity=None,
        )
        assert unlimited.available_capacity() is None

    def test_is_full(self) -> None:
        """Test is_full check."""
        full = Resource(
            resource_type=ResourceType.GOLD,
            amount=5000,
            max_capacity=5000,
        )
        assert full.is_full() is True

        not_full = Resource(
            resource_type=ResourceType.GOLD,
            amount=4000,
            max_capacity=5000,
        )
        assert not_full.is_full() is False

        unlimited = Resource(
            resource_type=ResourceType.GOLD,
            amount=10000,
            max_capacity=None,
        )
        assert unlimited.is_full() is False

    def test_is_empty(self) -> None:
        """Test is_empty check."""
        empty = Resource(resource_type=ResourceType.GOLD, amount=0)
        assert empty.is_empty() is True

        not_empty = Resource(resource_type=ResourceType.GOLD, amount=100)
        assert not_empty.is_empty() is False

    def test_transfer_to(self) -> None:
        """Test transferring resources between stockpiles."""
        source = Resource(
            resource_type=ResourceType.GOLD,
            amount=1000,
        )
        target = Resource(
            resource_type=ResourceType.GOLD,
            amount=500,
            max_capacity=2000,
        )
        source.transfer_to(target, 300)
        assert source.amount == 700
        assert target.amount == 800

    def test_transfer_wrong_type_raises_error(self) -> None:
        """Test transferring to wrong type raises error."""
        gold = Resource(resource_type=ResourceType.GOLD, amount=1000)
        food = Resource(resource_type=ResourceType.FOOD, amount=100)
        with pytest.raises(ValueError, match="Cannot transfer gold to food"):
            gold.transfer_to(food, 100)

    def test_factory_methods(self) -> None:
        """Test factory methods for creating resources."""
        gold_vault = Resource.create_gold_vault(
            initial_amount=5000,
            max_capacity=10000,
            owner_faction_id="faction-123",
        )
        assert gold_vault.resource_type == ResourceType.GOLD
        assert gold_vault.amount == 5000
        assert gold_vault.max_capacity == 10000
        assert gold_vault.owner_faction_id == "faction-123"

        food_storage = Resource.create_food_storage(
            initial_amount=1000,
            owner_faction_id="faction-123",
        )
        assert food_storage.resource_type == ResourceType.FOOD
        assert food_storage.amount == 1000

        military = Resource.create_military_force(
            initial_amount=500,
            owner_faction_id="faction-123",
        )
        assert military.resource_type == ResourceType.MILITARY
        assert military.max_capacity is None  # Military typically unlimited
