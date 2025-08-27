#!/usr/bin/env python3
"""
Comprehensive Unit Tests for NarrativeContext Value Objects

Test suite covering narrative context creation, validation, business logic,
enums, properties, score calculations, temporal logic, and relationship methods
in the Narrative Context domain layer.
"""

import pytest
from unittest.mock import patch
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Set, List, Dict, Any

from contexts.narratives.domain.value_objects.narrative_context import (
    NarrativeContext, ContextScope, ContextType
)


class TestContextScopeEnum:
    """Test suite for ContextScope enum."""
    
    def test_all_scope_levels_exist(self):
        """Test that all expected scope levels are defined."""
        expected_scopes = {'GLOBAL', 'ARC', 'CHAPTER', 'SCENE', 'MOMENT'}
        actual_scopes = {item.name for item in ContextScope}
        assert actual_scopes == expected_scopes
    
    def test_scope_string_values(self):
        """Test that scope enum values have correct string representations."""
        assert ContextScope.GLOBAL.value == "global"
        assert ContextScope.ARC.value == "arc"
        assert ContextScope.CHAPTER.value == "chapter"
        assert ContextScope.SCENE.value == "scene"
        assert ContextScope.MOMENT.value == "moment"
    
    def test_scope_logical_ordering(self):
        """Test that scope levels represent logical hierarchy."""
        scope_hierarchy = {
            ContextScope.GLOBAL: 5,
            ContextScope.ARC: 4,
            ContextScope.CHAPTER: 3,
            ContextScope.SCENE: 2,
            ContextScope.MOMENT: 1
        }
        
        assert scope_hierarchy[ContextScope.GLOBAL] > scope_hierarchy[ContextScope.ARC]
        assert scope_hierarchy[ContextScope.ARC] > scope_hierarchy[ContextScope.CHAPTER]
        assert scope_hierarchy[ContextScope.CHAPTER] > scope_hierarchy[ContextScope.SCENE]
        assert scope_hierarchy[ContextScope.SCENE] > scope_hierarchy[ContextScope.MOMENT]
    
    def test_scope_uniqueness(self):
        """Test that all scope values are unique."""
        values = [item.value for item in ContextScope]
        assert len(values) == len(set(values))
    
    def test_scope_membership(self):
        """Test scope membership operations."""
        assert ContextScope.GLOBAL in ContextScope
        assert "global" == ContextScope.GLOBAL.value
        assert ContextScope.GLOBAL == ContextScope("global")


class TestContextTypeEnum:
    """Test suite for ContextType enum."""
    
    def test_all_context_types_exist(self):
        """Test that all expected context types are defined."""
        expected_types = {
            'SETTING', 'CULTURAL', 'HISTORICAL', 'SOCIAL', 'POLITICAL', 'ECONOMIC',
            'TECHNOLOGICAL', 'MAGICAL', 'EMOTIONAL', 'THEMATIC', 'INTERPERSONAL', 'ENVIRONMENTAL'
        }
        actual_types = {item.name for item in ContextType}
        assert actual_types == expected_types
    
    def test_context_type_string_values(self):
        """Test that context type enum values have correct string representations."""
        assert ContextType.SETTING.value == "setting"
        assert ContextType.CULTURAL.value == "cultural"
        assert ContextType.HISTORICAL.value == "historical"
        assert ContextType.SOCIAL.value == "social"
        assert ContextType.POLITICAL.value == "political"
        assert ContextType.ECONOMIC.value == "economic"
        assert ContextType.TECHNOLOGICAL.value == "technological"
        assert ContextType.MAGICAL.value == "magical"
        assert ContextType.EMOTIONAL.value == "emotional"
        assert ContextType.THEMATIC.value == "thematic"
        assert ContextType.INTERPERSONAL.value == "interpersonal"
        assert ContextType.ENVIRONMENTAL.value == "environmental"
    
    def test_context_type_uniqueness(self):
        """Test that all context type values are unique."""
        values = [item.value for item in ContextType]
        assert len(values) == len(set(values))
    
    def test_context_type_membership(self):
        """Test context type membership operations."""
        assert ContextType.SETTING in ContextType
        assert "setting" == ContextType.SETTING.value
        assert ContextType.SETTING == ContextType("setting")


class TestNarrativeContextCreation:
    """Test suite for NarrativeContext creation and initialization."""
    
    def test_create_minimal_narrative_context(self):
        """Test creating narrative context with minimal required fields."""
        context = NarrativeContext(
            context_id="minimal-context-1",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="Castle Throne Room",
            description="The formal throne room where important court business is conducted"
        )
        
        assert context.context_id == "minimal-context-1"
        assert context.context_type == ContextType.SETTING
        assert context.scope == ContextScope.SCENE
        assert context.name == "Castle Throne Room"
        assert context.description == "The formal throne room where important court business is conducted"
    
    def test_create_comprehensive_narrative_context(self):
        """Test creating narrative context with all fields specified."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        char_id3 = uuid4()
        creation_time = datetime.now(timezone.utc)
        
        context = NarrativeContext(
            context_id="comprehensive-context",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Civil War Era",
            description="A time of political upheaval and division within the kingdom",
            applies_from_sequence=10,
            applies_to_sequence=75,
            is_persistent=False,
            locations={"capital_city", "northern_provinces", "border_towns"},
            affected_regions={"north", "central", "eastern_march"},
            geographical_scope="kingdom_wide",
            affected_characters={char_id1, char_id2, char_id3},
            character_knowledge_required={char_id1, char_id2},
            character_reactions={
                char_id1: "suspicious_and_cautious",
                char_id2: "opportunistic",
                char_id3: "fearful"
            },
            key_facts=[
                "King's authority is weakened",
                "Noble houses are taking sides",
                "Trade routes are disrupted"
            ],
            implicit_knowledge=[
                "Everyone knows war is coming",
                "Loyalty is questioned everywhere"
            ],
            hidden_information=[
                "The queen is secretly funding rebels",
                "Foreign powers are involved"
            ],
            narrative_constraints=[
                "Characters cannot travel freely",
                "Communication is monitored",
                "Resources are scarce"
            ],
            behavioral_influences=[
                "Increased paranoia among characters",
                "Stronger group loyalties",
                "Reduced trust in institutions"
            ],
            plot_implications=[
                "Forces characters to choose sides",
                "Creates opportunities for betrayal",
                "Sets up major confrontations"
            ],
            mood_influences={
                "tension": Decimal('8.0'),
                "fear": Decimal('6.5'),
                "uncertainty": Decimal('9.0')
            },
            tension_modifiers={
                "political": Decimal('7.5'),
                "social": Decimal('5.0'),
                "military": Decimal('8.5')
            },
            pacing_effects={
                "urgency": Decimal('6.0'),
                "deliberation": Decimal('-3.0'),
                "action_frequency": Decimal('4.0')
            },
            prerequisite_contexts={"peaceful_kingdom", "economic_prosperity"},
            conflicting_contexts={"time_of_peace", "royal_wedding_celebration"},
            reinforcing_contexts={"economic_hardship", "foreign_threat"},
            narrative_importance=Decimal('9.0'),
            visibility_level=Decimal('8.5'),
            complexity_level=Decimal('7.5'),
            evolution_rate=Decimal('0.6'),
            stability=Decimal('0.3'),
            tags={"major_arc", "political", "conflict"},
            source_material="Historical research on civil wars",
            research_notes="Based on War of the Roses and similar conflicts",
            creation_timestamp=creation_time,
            metadata={
                "inspiration": "Real historical events",
                "complexity_rating": "high",
                "audience_impact": "significant"
            }
        )
        
        assert context.context_id == "comprehensive-context"
        assert context.context_type == ContextType.POLITICAL
        assert context.scope == ContextScope.ARC
        assert context.applies_from_sequence == 10
        assert context.applies_to_sequence == 75
        assert context.is_persistent is False
        assert context.locations == {"capital_city", "northern_provinces", "border_towns"}
        assert context.affected_regions == {"north", "central", "eastern_march"}
        assert context.geographical_scope == "kingdom_wide"
        assert context.affected_characters == {char_id1, char_id2, char_id3}
        assert context.character_knowledge_required == {char_id1, char_id2}
        assert context.character_reactions[char_id1] == "suspicious_and_cautious"
        assert len(context.key_facts) == 3
        assert len(context.implicit_knowledge) == 2
        assert len(context.hidden_information) == 2
        assert len(context.narrative_constraints) == 3
        assert len(context.behavioral_influences) == 3
        assert len(context.plot_implications) == 3
        assert context.mood_influences["tension"] == Decimal('8.0')
        assert context.tension_modifiers["political"] == Decimal('7.5')
        assert context.pacing_effects["urgency"] == Decimal('6.0')
        assert context.prerequisite_contexts == {"peaceful_kingdom", "economic_prosperity"}
        assert context.conflicting_contexts == {"time_of_peace", "royal_wedding_celebration"}
        assert context.reinforcing_contexts == {"economic_hardship", "foreign_threat"}
        assert context.narrative_importance == Decimal('9.0')
        assert context.visibility_level == Decimal('8.5')
        assert context.complexity_level == Decimal('7.5')
        assert context.evolution_rate == Decimal('0.6')
        assert context.stability == Decimal('0.3')
        assert context.tags == {"major_arc", "political", "conflict"}
        assert context.source_material == "Historical research on civil wars"
        assert context.research_notes == "Based on War of the Roses and similar conflicts"
        assert context.creation_timestamp == creation_time
        assert context.metadata["inspiration"] == "Real historical events"
    
    def test_default_values_initialization(self):
        """Test that default values are properly initialized."""
        context = NarrativeContext(
            context_id="default-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.GLOBAL,
            name="Default Culture",
            description="Testing default value initialization"
        )
        
        # Test default collections are empty
        assert context.locations == set()
        assert context.affected_regions == set()
        assert context.affected_characters == set()
        assert context.character_knowledge_required == set()
        assert context.character_reactions == {}
        assert context.key_facts == []
        assert context.implicit_knowledge == []
        assert context.hidden_information == []
        assert context.narrative_constraints == []
        assert context.behavioral_influences == []
        assert context.plot_implications == []
        assert context.mood_influences == {}
        assert context.tension_modifiers == {}
        assert context.pacing_effects == {}
        assert context.prerequisite_contexts == set()
        assert context.conflicting_contexts == set()
        assert context.reinforcing_contexts == set()
        assert context.tags == set()
        assert context.metadata == {}
        
        # Test default values
        assert context.applies_from_sequence is None
        assert context.applies_to_sequence is None
        assert context.is_persistent is True
        assert context.geographical_scope is None
        assert context.narrative_importance == Decimal('5.0')
        assert context.visibility_level == Decimal('5.0')
        assert context.complexity_level == Decimal('5.0')
        assert context.evolution_rate == Decimal('0.0')
        assert context.stability == Decimal('1.0')
        assert context.source_material is None
        assert context.research_notes == ""
        
        # Test that creation timestamp was set
        assert context.creation_timestamp is not None
        assert isinstance(context.creation_timestamp, datetime)
    
    def test_frozen_dataclass_immutability(self):
        """Test that NarrativeContext is immutable (frozen dataclass)."""
        context = NarrativeContext(
            context_id="immutable-test",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.CHAPTER,
            name="Immutable Test",
            description="Testing immutability"
        )
        
        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            context.name = "Modified Name"
        
        with pytest.raises(AttributeError):
            context.scope = ContextScope.GLOBAL
        
        with pytest.raises(AttributeError):
            context.narrative_importance = Decimal('8.0')


class TestNarrativeContextValidation:
    """Test suite for NarrativeContext validation logic."""
    
    def test_empty_context_id_validation(self):
        """Test validation fails with empty context ID."""
        with pytest.raises(ValueError, match="Context ID cannot be empty"):
            NarrativeContext(
                context_id="",
                context_type=ContextType.SETTING,
                scope=ContextScope.SCENE,
                name="Valid Name",
                description="Valid description"
            )
    
    def test_whitespace_only_context_id_validation(self):
        """Test validation fails with whitespace-only context ID."""
        with pytest.raises(ValueError, match="Context ID cannot be empty"):
            NarrativeContext(
                context_id="   ",
                context_type=ContextType.SETTING,
                scope=ContextScope.SCENE,
                name="Valid Name",
                description="Valid description"
            )
    
    def test_empty_name_validation(self):
        """Test validation fails with empty name."""
        with pytest.raises(ValueError, match="Context name cannot be empty"):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.HISTORICAL,
                scope=ContextScope.ARC,
                name="",
                description="Valid description"
            )
    
    def test_whitespace_only_name_validation(self):
        """Test validation fails with whitespace-only name."""
        with pytest.raises(ValueError, match="Context name cannot be empty"):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.HISTORICAL,
                scope=ContextScope.ARC,
                name="   ",
                description="Valid description"
            )
    
    def test_empty_description_validation(self):
        """Test validation fails with empty description."""
        with pytest.raises(ValueError, match="Context description cannot be empty"):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.SOCIAL,
                scope=ContextScope.GLOBAL,
                name="Valid Name",
                description=""
            )
    
    def test_whitespace_only_description_validation(self):
        """Test validation fails with whitespace-only description."""
        with pytest.raises(ValueError, match="Context description cannot be empty"):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.SOCIAL,
                scope=ContextScope.GLOBAL,
                name="Valid Name",
                description="   \t\n  "
            )
    
    def test_invalid_sequence_range_validation(self):
        """Test validation fails when from sequence is after to sequence."""
        with pytest.raises(ValueError, match="From sequence must be before or equal to to sequence"):
            NarrativeContext(
                context_id="invalid-range-test",
                context_type=ContextType.THEMATIC,
                scope=ContextScope.ARC,
                name="Invalid Range",
                description="Testing invalid sequence range",
                applies_from_sequence=50,
                applies_to_sequence=25
            )
    
    def test_valid_sequence_range_equal_values(self):
        """Test that equal from and to sequence values are valid."""
        context = NarrativeContext(
            context_id="equal-sequence-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.SCENE,
            name="Equal Sequence",
            description="Testing equal sequence values",
            applies_from_sequence=30,
            applies_to_sequence=30
        )
        
        assert context.applies_from_sequence == 30
        assert context.applies_to_sequence == 30
    
    def test_valid_sequence_range_proper_order(self):
        """Test that proper sequence order is valid."""
        context = NarrativeContext(
            context_id="valid-range-test",
            context_type=ContextType.ENVIRONMENTAL,
            scope=ContextScope.CHAPTER,
            name="Valid Range",
            description="Testing valid sequence range",
            applies_from_sequence=10,
            applies_to_sequence=20
        )
        
        assert context.applies_from_sequence == 10
        assert context.applies_to_sequence == 20
    
    def test_narrative_importance_below_minimum_validation(self):
        """Test validation fails with narrative importance below 1."""
        with pytest.raises(ValueError, match="narrative_importance must be between 1 and 10"):
            NarrativeContext(
                context_id="low-importance-test",
                context_type=ContextType.MAGICAL,
                scope=ContextScope.ARC,
                name="Low Importance",
                description="Testing low importance",
                narrative_importance=Decimal('0.5')
            )
    
    def test_narrative_importance_above_maximum_validation(self):
        """Test validation fails with narrative importance above 10."""
        with pytest.raises(ValueError, match="narrative_importance must be between 1 and 10"):
            NarrativeContext(
                context_id="high-importance-test",
                context_type=ContextType.MAGICAL,
                scope=ContextScope.ARC,
                name="High Importance",
                description="Testing high importance",
                narrative_importance=Decimal('11.0')
            )
    
    def test_visibility_level_boundary_validation(self):
        """Test visibility level boundary validation."""
        with pytest.raises(ValueError, match="visibility_level must be between 1 and 10"):
            NarrativeContext(
                context_id="low-visibility-test",
                context_type=ContextType.TECHNOLOGICAL,
                scope=ContextScope.GLOBAL,
                name="Low Visibility",
                description="Testing low visibility",
                visibility_level=Decimal('0.9')
            )
        
        with pytest.raises(ValueError, match="visibility_level must be between 1 and 10"):
            NarrativeContext(
                context_id="high-visibility-test",
                context_type=ContextType.TECHNOLOGICAL,
                scope=ContextScope.GLOBAL,
                name="High Visibility",
                description="Testing high visibility",
                visibility_level=Decimal('10.1')
            )
    
    def test_complexity_level_boundary_validation(self):
        """Test complexity level boundary validation."""
        with pytest.raises(ValueError, match="complexity_level must be between 1 and 10"):
            NarrativeContext(
                context_id="low-complexity-test",
                context_type=ContextType.ECONOMIC,
                scope=ContextScope.ARC,
                name="Low Complexity",
                description="Testing low complexity",
                complexity_level=Decimal('0.5')
            )
        
        with pytest.raises(ValueError, match="complexity_level must be between 1 and 10"):
            NarrativeContext(
                context_id="high-complexity-test",
                context_type=ContextType.ECONOMIC,
                scope=ContextScope.ARC,
                name="High Complexity",
                description="Testing high complexity",
                complexity_level=Decimal('15.0')
            )
    
    def test_valid_decimal_boundary_values(self):
        """Test that boundary decimal values are valid."""
        context = NarrativeContext(
            context_id="boundary-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.GLOBAL,
            name="Boundary Test",
            description="Testing boundary values",
            narrative_importance=Decimal('1.0'),
            visibility_level=Decimal('10.0'),
            complexity_level=Decimal('5.5')
        )
        
        assert context.narrative_importance == Decimal('1.0')
        assert context.visibility_level == Decimal('10.0')
        assert context.complexity_level == Decimal('5.5')
    
    def test_evolution_rate_below_minimum_validation(self):
        """Test validation fails with evolution rate below 0."""
        with pytest.raises(ValueError, match="evolution_rate must be between 0 and 1"):
            NarrativeContext(
                context_id="low-evolution-test",
                context_type=ContextType.CULTURAL,
                scope=ContextScope.ARC,
                name="Low Evolution",
                description="Testing low evolution rate",
                evolution_rate=Decimal('-0.1')
            )
    
    def test_evolution_rate_above_maximum_validation(self):
        """Test validation fails with evolution rate above 1."""
        with pytest.raises(ValueError, match="evolution_rate must be between 0 and 1"):
            NarrativeContext(
                context_id="high-evolution-test",
                context_type=ContextType.CULTURAL,
                scope=ContextScope.ARC,
                name="High Evolution",
                description="Testing high evolution rate",
                evolution_rate=Decimal('1.1')
            )
    
    def test_stability_boundary_validation(self):
        """Test stability boundary validation."""
        with pytest.raises(ValueError, match="stability must be between 0 and 1"):
            NarrativeContext(
                context_id="low-stability-test",
                context_type=ContextType.SOCIAL,
                scope=ContextScope.CHAPTER,
                name="Low Stability",
                description="Testing low stability",
                stability=Decimal('-0.2')
            )
        
        with pytest.raises(ValueError, match="stability must be between 0 and 1"):
            NarrativeContext(
                context_id="high-stability-test",
                context_type=ContextType.SOCIAL,
                scope=ContextScope.CHAPTER,
                name="High Stability",
                description="Testing high stability",
                stability=Decimal('1.5')
            )
    
    def test_valid_rate_boundary_values(self):
        """Test that boundary rate values (0 and 1) are valid."""
        context = NarrativeContext(
            context_id="boundary-rates-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Boundary Rates",
            description="Testing rate boundaries",
            evolution_rate=Decimal('0.0'),
            stability=Decimal('1.0')
        )
        
        assert context.evolution_rate == Decimal('0.0')
        assert context.stability == Decimal('1.0')
    
    def test_influence_values_below_minimum_validation(self):
        """Test validation fails with influence values below -10."""
        with pytest.raises(ValueError, match="Influence values must be between -10 and 10"):
            NarrativeContext(
                context_id="low-mood-influence-test",
                context_type=ContextType.EMOTIONAL,
                scope=ContextScope.SCENE,
                name="Low Mood Influence",
                description="Testing low mood influence",
                mood_influences={"fear": Decimal('-11.0')}
            )
    
    def test_influence_values_above_maximum_validation(self):
        """Test validation fails with influence values above 10."""
        with pytest.raises(ValueError, match="Influence values must be between -10 and 10"):
            NarrativeContext(
                context_id="high-tension-modifier-test",
                context_type=ContextType.INTERPERSONAL,
                scope=ContextScope.SCENE,
                name="High Tension Modifier",
                description="Testing high tension modifier",
                tension_modifiers={"conflict": Decimal('15.0')}
            )
    
    def test_pacing_effects_boundary_validation(self):
        """Test pacing effects boundary validation."""
        with pytest.raises(ValueError, match="Influence values must be between -10 and 10"):
            NarrativeContext(
                context_id="invalid-pacing-test",
                context_type=ContextType.THEMATIC,
                scope=ContextScope.ARC,
                name="Invalid Pacing",
                description="Testing invalid pacing effects",
                pacing_effects={"urgency": Decimal('-12.0')}
            )
    
    def test_valid_influence_boundary_values(self):
        """Test that boundary influence values (-10 and 10) are valid."""
        context = NarrativeContext(
            context_id="boundary-influences-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.GLOBAL,
            name="Boundary Influences",
            description="Testing influence boundaries",
            mood_influences={"wonder": Decimal('10.0'), "fear": Decimal('-10.0')},
            tension_modifiers={"magical": Decimal('5.0')},
            pacing_effects={"acceleration": Decimal('-8.5')}
        )
        
        assert context.mood_influences["wonder"] == Decimal('10.0')
        assert context.mood_influences["fear"] == Decimal('-10.0')
        assert context.tension_modifiers["magical"] == Decimal('5.0')
        assert context.pacing_effects["acceleration"] == Decimal('-8.5')
    
    def test_string_length_validations(self):
        """Test string length constraint validations."""
        # Context ID too long
        with pytest.raises(ValueError, match="Context ID too long \\(max 100 characters\\)"):
            NarrativeContext(
                context_id="x" * 101,
                context_type=ContextType.SETTING,
                scope=ContextScope.SCENE,
                name="Valid Name",
                description="Valid description"
            )
        
        # Name too long
        with pytest.raises(ValueError, match="Context name too long \\(max 200 characters\\)"):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.SETTING,
                scope=ContextScope.SCENE,
                name="x" * 201,
                description="Valid description"
            )
        
        # Description too long
        with pytest.raises(ValueError, match="Context description too long \\(max 2000 characters\\)"):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.SETTING,
                scope=ContextScope.SCENE,
                name="Valid Name",
                description="x" * 2001
            )
    
    def test_valid_string_length_boundaries(self):
        """Test that maximum string length boundaries are valid."""
        context = NarrativeContext(
            context_id="x" * 100,
            context_type=ContextType.ENVIRONMENTAL,
            scope=ContextScope.GLOBAL,
            name="x" * 200,
            description="x" * 2000
        )
        
        assert len(context.context_id) == 100
        assert len(context.name) == 200
        assert len(context.description) == 2000


class TestNarrativeContextProperties:
    """Test suite for NarrativeContext property methods."""
    
    def test_has_sequence_range_with_from_sequence(self):
        """Test has_sequence_range returns True when from sequence is set."""
        context = NarrativeContext(
            context_id="from-seq-test",
            context_type=ContextType.THEMATIC,
            scope=ContextScope.ARC,
            name="From Sequence Test",
            description="Testing from sequence",
            applies_from_sequence=10
        )
        
        assert context.has_sequence_range is True
    
    def test_has_sequence_range_with_to_sequence(self):
        """Test has_sequence_range returns True when to sequence is set."""
        context = NarrativeContext(
            context_id="to-seq-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.CHAPTER,
            name="To Sequence Test",
            description="Testing to sequence",
            applies_to_sequence=50
        )
        
        assert context.has_sequence_range is True
    
    def test_has_sequence_range_with_both_sequences(self):
        """Test has_sequence_range returns True when both sequences are set."""
        context = NarrativeContext(
            context_id="both-seq-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.ARC,
            name="Both Sequences Test",
            description="Testing both sequences",
            applies_from_sequence=15,
            applies_to_sequence=45
        )
        
        assert context.has_sequence_range is True
    
    def test_has_sequence_range_false(self):
        """Test has_sequence_range returns False when no sequences are set."""
        context = NarrativeContext(
            context_id="no-seq-test",
            context_type=ContextType.SETTING,
            scope=ContextScope.GLOBAL,
            name="No Sequence Test",
            description="Testing no sequences"
        )
        
        assert context.has_sequence_range is False
    
    def test_is_temporal_context_true(self):
        """Test is_temporal_context returns True when not persistent and has sequence range."""
        context = NarrativeContext(
            context_id="temporal-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.CHAPTER,
            name="Temporal Context",
            description="Testing temporal context",
            is_persistent=False,
            applies_from_sequence=20,
            applies_to_sequence=30
        )
        
        assert context.is_temporal_context is True
    
    def test_is_temporal_context_false_persistent(self):
        """Test is_temporal_context returns False when persistent even with sequence range."""
        context = NarrativeContext(
            context_id="persistent-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Persistent Context",
            description="Testing persistent context",
            is_persistent=True,
            applies_from_sequence=5,
            applies_to_sequence=100
        )
        
        assert context.is_temporal_context is False
    
    def test_is_temporal_context_false_no_range(self):
        """Test is_temporal_context returns False when no sequence range."""
        context = NarrativeContext(
            context_id="no-range-test",
            context_type=ContextType.SOCIAL,
            scope=ContextScope.ARC,
            name="No Range Context",
            description="Testing no range context",
            is_persistent=False
        )
        
        assert context.is_temporal_context is False
    
    def test_affects_characters_true(self):
        """Test affects_characters returns True when characters are affected."""
        char_id = uuid4()
        
        context = NarrativeContext(
            context_id="char-affects-test",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.SCENE,
            name="Character Affects Test",
            description="Testing character affects",
            affected_characters={char_id}
        )
        
        assert context.affects_characters is True
    
    def test_affects_characters_false(self):
        """Test affects_characters returns False when no characters are affected."""
        context = NarrativeContext(
            context_id="no-char-affects-test",
            context_type=ContextType.ENVIRONMENTAL,
            scope=ContextScope.GLOBAL,
            name="No Character Affects Test",
            description="Testing no character affects"
        )
        
        assert context.affects_characters is False
    
    def test_has_hidden_information_true(self):
        """Test has_hidden_information returns True when hidden information exists."""
        context = NarrativeContext(
            context_id="hidden-info-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.ARC,
            name="Hidden Info Test",
            description="Testing hidden information",
            hidden_information=["Secret magical ward protects the castle", "Ancient curse affects the land"]
        )
        
        assert context.has_hidden_information is True
    
    def test_has_hidden_information_false(self):
        """Test has_hidden_information returns False when no hidden information exists."""
        context = NarrativeContext(
            context_id="no-hidden-info-test",
            context_type=ContextType.TECHNOLOGICAL,
            scope=ContextScope.CHAPTER,
            name="No Hidden Info Test",
            description="Testing no hidden information"
        )
        
        assert context.has_hidden_information is False
    
    def test_has_narrative_constraints_true(self):
        """Test has_narrative_constraints returns True when constraints exist."""
        context = NarrativeContext(
            context_id="constraints-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Constraints Test",
            description="Testing narrative constraints",
            narrative_constraints=["No magic can be used", "Characters must remain in city"]
        )
        
        assert context.has_narrative_constraints is True
    
    def test_has_narrative_constraints_false(self):
        """Test has_narrative_constraints returns False when no constraints exist."""
        context = NarrativeContext(
            context_id="no-constraints-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.SCENE,
            name="No Constraints Test",
            description="Testing no constraints"
        )
        
        assert context.has_narrative_constraints is False
    
    def test_influences_mood_true(self):
        """Test influences_mood returns True when mood influences exist."""
        context = NarrativeContext(
            context_id="mood-influence-test",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.SCENE,
            name="Mood Influence Test",
            description="Testing mood influence",
            mood_influences={"melancholy": Decimal('6.0'), "hope": Decimal('-3.0')}
        )
        
        assert context.influences_mood is True
    
    def test_influences_mood_false(self):
        """Test influences_mood returns False when no mood influences exist."""
        context = NarrativeContext(
            context_id="no-mood-influence-test",
            context_type=ContextType.ECONOMIC,
            scope=ContextScope.GLOBAL,
            name="No Mood Influence Test",
            description="Testing no mood influence"
        )
        
        assert context.influences_mood is False
    
    def test_influences_pacing_true(self):
        """Test influences_pacing returns True when pacing effects exist."""
        context = NarrativeContext(
            context_id="pacing-influence-test",
            context_type=ContextType.THEMATIC,
            scope=ContextScope.ARC,
            name="Pacing Influence Test",
            description="Testing pacing influence",
            pacing_effects={"urgency": Decimal('4.5'), "contemplation": Decimal('2.0')}
        )
        
        assert context.influences_pacing is True
    
    def test_influences_pacing_false(self):
        """Test influences_pacing returns False when no pacing effects exist."""
        context = NarrativeContext(
            context_id="no-pacing-influence-test",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="No Pacing Influence Test",
            description="Testing no pacing influence"
        )
        
        assert context.influences_pacing is False
    
    def test_has_prerequisites_true(self):
        """Test has_prerequisites returns True when prerequisite contexts exist."""
        context = NarrativeContext(
            context_id="prerequisites-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.ARC,
            name="Prerequisites Test",
            description="Testing prerequisites",
            prerequisite_contexts={"ancient_prophecy", "hero_training"}
        )
        
        assert context.has_prerequisites is True
    
    def test_has_prerequisites_false(self):
        """Test has_prerequisites returns False when no prerequisite contexts exist."""
        context = NarrativeContext(
            context_id="no-prerequisites-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.SCENE,
            name="No Prerequisites Test",
            description="Testing no prerequisites"
        )
        
        assert context.has_prerequisites is False
    
    def test_has_conflicts_true(self):
        """Test has_conflicts returns True when conflicting contexts exist."""
        context = NarrativeContext(
            context_id="conflicts-test",
            context_type=ContextType.SOCIAL,
            scope=ContextScope.CHAPTER,
            name="Conflicts Test",
            description="Testing conflicts",
            conflicting_contexts={"peaceful_times", "celebration_mood"}
        )
        
        assert context.has_conflicts is True
    
    def test_has_conflicts_false(self):
        """Test has_conflicts returns False when no conflicting contexts exist."""
        context = NarrativeContext(
            context_id="no-conflicts-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.MOMENT,
            name="No Conflicts Test",
            description="Testing no conflicts"
        )
        
        assert context.has_conflicts is False


class TestOverallInfluenceStrength:
    """Test suite for overall influence strength calculation."""
    
    def test_influence_strength_base_calculation(self):
        """Test influence strength with base values only."""
        context = NarrativeContext(
            context_id="base-strength-test",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="Base Strength Test",
            description="Testing base influence strength",
            narrative_importance=Decimal('6.0'),
            visibility_level=Decimal('8.0')
        )
        
        # Expected: (6.0 * 8.0) / 10.0 + 0 = 4.8
        assert context.overall_influence_strength == Decimal('4.8')
    
    def test_influence_strength_with_influences(self):
        """Test influence strength with various influences."""
        context = NarrativeContext(
            context_id="influences-strength-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Influences Strength Test",
            description="Testing influence strength with influences",
            narrative_importance=Decimal('8.0'),
            visibility_level=Decimal('7.0'),
            mood_influences={"tension": Decimal('5.0'), "fear": Decimal('3.0')},
            tension_modifiers={"political": Decimal('6.0')},
            pacing_effects={"urgency": Decimal('4.0'), "deliberation": Decimal('-2.0')},
            behavioral_influences=["increased_caution", "group_solidarity"],
            narrative_constraints=["limited_travel", "monitored_communication", "resource_scarcity"]
        )
        
        # Base: (8.0 * 7.0) / 10.0 = 5.6
        # Influences: 2 mood + 1 tension + 2 pacing + 2 behavioral + 3 constraints = 10 total
        # Bonus: min(3, 10 * 0.2) = min(3, 2.0) = 2.0
        # Total: min(10, 5.6 + 2.0) = min(10, 7.6) = 7.6
        assert context.overall_influence_strength == Decimal('7.6')
    
    def test_influence_strength_capped_at_ten(self):
        """Test that influence strength is capped at 10."""
        context = NarrativeContext(
            context_id="max-strength-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.GLOBAL,
            name="Maximum Strength Test",
            description="Testing maximum influence strength",
            narrative_importance=Decimal('10.0'),
            visibility_level=Decimal('10.0'),
            mood_influences={f"mood_{i}": Decimal('5.0') for i in range(10)},
            tension_modifiers={f"tension_{i}": Decimal('3.0') for i in range(10)},
            pacing_effects={f"pacing_{i}": Decimal('2.0') for i in range(10)},
            behavioral_influences=[f"behavior_{i}" for i in range(20)],
            narrative_constraints=[f"constraint_{i}" for i in range(20)]
        )
        
        # Base: (10.0 * 10.0) / 10.0 = 10.0
        # Influences: 10 + 10 + 10 + 20 + 20 = 70 total
        # Bonus: min(3, 70 * 0.2) = min(3, 14.0) = 3.0
        # Total: min(10, 10.0 + 3.0) = 10.0 (capped)
        assert context.overall_influence_strength == Decimal('10.0')
    
    def test_influence_strength_bonus_capped(self):
        """Test that influence bonus is capped at 3."""
        context = NarrativeContext(
            context_id="bonus-cap-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.ARC,
            name="Bonus Cap Test",
            description="Testing bonus cap",
            narrative_importance=Decimal('5.0'),
            visibility_level=Decimal('4.0'),
            behavioral_influences=[f"influence_{i}" for i in range(20)]
        )
        
        # Base: (5.0 * 4.0) / 10.0 = 2.0
        # Influences: 20 total
        # Bonus: min(3, 20 * 0.2) = min(3, 4.0) = 3.0 (capped)
        # Total: min(10, 2.0 + 3.0) = 5.0
        assert context.overall_influence_strength == Decimal('5.0')


class TestContextualComplexityScore:
    """Test suite for contextual complexity score calculation."""
    
    def test_complexity_score_base_only(self):
        """Test complexity score with only base complexity level."""
        context = NarrativeContext(
            context_id="base-complexity-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Base Complexity Test",
            description="Testing base complexity",
            complexity_level=Decimal('6.0')
        )
        
        # Expected: 6.0 + 0 + 0 = 6.0
        assert context.contextual_complexity_score == Decimal('6.0')
    
    def test_complexity_score_with_relationships(self):
        """Test complexity score with context relationships."""
        context = NarrativeContext(
            context_id="relationships-complexity-test",
            context_type=ContextType.SOCIAL,
            scope=ContextScope.ARC,
            name="Relationships Complexity Test",
            description="Testing relationship complexity",
            complexity_level=Decimal('4.0'),
            prerequisite_contexts={"context1", "context2"},
            conflicting_contexts={"context3"},
            reinforcing_contexts={"context4", "context5", "context6"}
        )
        
        # Base: 4.0
        # Relationships: (2 + 1 + 3) * 0.3 = 6 * 0.3 = 1.8
        # Information: 0
        # Total: 4.0 + 1.8 + 0 = 5.8
        assert context.contextual_complexity_score == Decimal('5.8')
    
    def test_complexity_score_with_information_layers(self):
        """Test complexity score with information layer complexity."""
        context = NarrativeContext(
            context_id="information-complexity-test",
            context_type=ContextType.THEMATIC,
            scope=ContextScope.CHAPTER,
            name="Information Complexity Test",
            description="Testing information complexity",
            complexity_level=Decimal('5.0'),
            key_facts=["fact1", "fact2", "fact3", "fact4"],
            implicit_knowledge=["implicit1", "implicit2"],
            hidden_information=["hidden1", "hidden2", "hidden3"]
        )
        
        # Base: 5.0
        # Relationships: 0
        # Information: (4 + 2 + 3) * 0.1 = 9 * 0.1 = 0.9
        # Total: 5.0 + 0 + 0.9 = 5.9
        assert context.contextual_complexity_score == Decimal('5.9')
    
    def test_complexity_score_comprehensive(self):
        """Test complexity score with all components."""
        context = NarrativeContext(
            context_id="comprehensive-complexity-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.GLOBAL,
            name="Comprehensive Complexity Test",
            description="Testing comprehensive complexity",
            complexity_level=Decimal('7.0'),
            prerequisite_contexts={"prereq1", "prereq2"},
            conflicting_contexts={"conflict1", "conflict2", "conflict3"},
            reinforcing_contexts={"reinforce1"},
            key_facts=["fact1", "fact2", "fact3"],
            implicit_knowledge=["implicit1", "implicit2", "implicit3", "implicit4"],
            hidden_information=["hidden1", "hidden2"]
        )
        
        # Base: 7.0
        # Relationships: (2 + 3 + 1) * 0.3 = 6 * 0.3 = 1.8
        # Information: (3 + 4 + 2) * 0.1 = 9 * 0.1 = 0.9
        # Total: 7.0 + 1.8 + 0.9 = 9.7
        assert context.contextual_complexity_score == Decimal('9.7')
    
    def test_complexity_score_capped_at_ten(self):
        """Test that complexity score is capped at 10."""
        context = NarrativeContext(
            context_id="max-complexity-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.ARC,
            name="Maximum Complexity Test",
            description="Testing maximum complexity",
            complexity_level=Decimal('9.0'),
            prerequisite_contexts={f"prereq_{i}" for i in range(10)},
            conflicting_contexts={f"conflict_{i}" for i in range(10)},
            reinforcing_contexts={f"reinforce_{i}" for i in range(10)},
            key_facts=[f"fact_{i}" for i in range(20)],
            implicit_knowledge=[f"implicit_{i}" for i in range(20)],
            hidden_information=[f"hidden_{i}" for i in range(20)]
        )
        
        # Base: 9.0
        # Relationships: (10 + 10 + 10) * 0.3 = 30 * 0.3 = 9.0
        # Information: (20 + 20 + 20) * 0.1 = 60 * 0.1 = 6.0
        # Total: min(10, 9.0 + 9.0 + 6.0) = min(10, 24.0) = 10.0
        assert context.contextual_complexity_score == Decimal('10.0')


class TestNarrativeContextInstanceMethods:
    """Test suite for NarrativeContext instance methods."""
    
    def test_applies_at_sequence_persistent_no_range(self):
        """Test applies_at_sequence for persistent context with no range."""
        context = NarrativeContext(
            context_id="persistent-no-range-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.GLOBAL,
            name="Persistent No Range",
            description="Testing persistent context without range",
            is_persistent=True
        )
        
        # Should apply at any sequence for persistent contexts without range
        assert context.applies_at_sequence(1) is True
        assert context.applies_at_sequence(50) is True
        assert context.applies_at_sequence(100) is True
    
    def test_applies_at_sequence_non_persistent_no_range(self):
        """Test applies_at_sequence for non-persistent context with no range."""
        context = NarrativeContext(
            context_id="non-persistent-no-range-test",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.SCENE,
            name="Non-Persistent No Range",
            description="Testing non-persistent context without range",
            is_persistent=False
        )
        
        # Should not apply at any sequence for non-persistent contexts without range
        assert context.applies_at_sequence(1) is False
        assert context.applies_at_sequence(25) is False
        assert context.applies_at_sequence(100) is False
    
    def test_applies_at_sequence_with_range(self):
        """Test applies_at_sequence with defined sequence range."""
        context = NarrativeContext(
            context_id="range-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Range Test",
            description="Testing sequence range",
            applies_from_sequence=20,
            applies_to_sequence=40
        )
        
        # Should not apply before range
        assert context.applies_at_sequence(10) is False
        assert context.applies_at_sequence(19) is False
        
        # Should apply within range
        assert context.applies_at_sequence(20) is True
        assert context.applies_at_sequence(30) is True
        assert context.applies_at_sequence(40) is True
        
        # Should not apply after range
        assert context.applies_at_sequence(41) is False
        assert context.applies_at_sequence(50) is False
    
    def test_applies_at_sequence_from_only(self):
        """Test applies_at_sequence with only from sequence defined."""
        context = NarrativeContext(
            context_id="from-only-test",
            context_type=ContextType.TECHNOLOGICAL,
            scope=ContextScope.ARC,
            name="From Only Test",
            description="Testing from sequence only",
            applies_from_sequence=30
        )
        
        # Should not apply before from sequence
        assert context.applies_at_sequence(20) is False
        assert context.applies_at_sequence(29) is False
        
        # Should apply from sequence onwards
        assert context.applies_at_sequence(30) is True
        assert context.applies_at_sequence(50) is True
        assert context.applies_at_sequence(100) is True
    
    def test_applies_at_sequence_to_only(self):
        """Test applies_at_sequence with only to sequence defined."""
        context = NarrativeContext(
            context_id="to-only-test",
            context_type=ContextType.ENVIRONMENTAL,
            scope=ContextScope.CHAPTER,
            name="To Only Test",
            description="Testing to sequence only",
            applies_to_sequence=50
        )
        
        # Should apply up to and including to sequence
        assert context.applies_at_sequence(1) is True
        assert context.applies_at_sequence(25) is True
        assert context.applies_at_sequence(50) is True
        
        # Should not apply after to sequence
        assert context.applies_at_sequence(51) is False
        assert context.applies_at_sequence(75) is False
    
    def test_affects_character_true(self):
        """Test affects_character returns True for affected character."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        char_id3 = uuid4()
        
        context = NarrativeContext(
            context_id="char-affects-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.SCENE,
            name="Character Affects Test",
            description="Testing character affects",
            affected_characters={char_id1, char_id2}
        )
        
        assert context.affects_character(char_id1) is True
        assert context.affects_character(char_id2) is True
        assert context.affects_character(char_id3) is False
    
    def test_character_knows_context_true(self):
        """Test character_knows_context returns True for required character."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        char_id3 = uuid4()
        
        context = NarrativeContext(
            context_id="char-knowledge-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.ARC,
            name="Character Knowledge Test",
            description="Testing character knowledge",
            character_knowledge_required={char_id1, char_id2}
        )
        
        assert context.character_knows_context(char_id1) is True
        assert context.character_knows_context(char_id2) is True
        assert context.character_knows_context(char_id3) is False
    
    def test_get_character_reaction_existing(self):
        """Test get_character_reaction returns reaction for existing character."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        char_id3 = uuid4()
        
        context = NarrativeContext(
            context_id="char-reaction-test",
            context_type=ContextType.SOCIAL,
            scope=ContextScope.CHAPTER,
            name="Character Reaction Test",
            description="Testing character reactions",
            character_reactions={
                char_id1: "excited_and_hopeful",
                char_id2: "worried_and_cautious"
            }
        )
        
        assert context.get_character_reaction(char_id1) == "excited_and_hopeful"
        assert context.get_character_reaction(char_id2) == "worried_and_cautious"
        assert context.get_character_reaction(char_id3) is None
    
    def test_conflicts_with_context_true(self):
        """Test conflicts_with_context returns True for conflicting context."""
        context = NarrativeContext(
            context_id="conflicts-test",
            context_type=ContextType.THEMATIC,
            scope=ContextScope.ARC,
            name="Conflicts Test",
            description="Testing context conflicts",
            conflicting_contexts={"peaceful_times", "celebration_mood", "naive_optimism"}
        )
        
        assert context.conflicts_with_context("peaceful_times") is True
        assert context.conflicts_with_context("celebration_mood") is True
        assert context.conflicts_with_context("war_preparation") is False
    
    def test_reinforces_context_true(self):
        """Test reinforces_context returns True for reinforcing context."""
        context = NarrativeContext(
            context_id="reinforces-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Reinforces Test",
            description="Testing context reinforcement",
            reinforcing_contexts={"ancient_prophecy", "divine_mandate", "destiny_theme"}
        )
        
        assert context.reinforces_context("ancient_prophecy") is True
        assert context.reinforces_context("divine_mandate") is True
        assert context.reinforces_context("random_chance") is False
    
    def test_requires_context_true(self):
        """Test requires_context returns True for prerequisite context."""
        context = NarrativeContext(
            context_id="requires-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Requires Test",
            description="Testing context requirements",
            prerequisite_contexts={"royal_death", "succession_crisis", "political_instability"}
        )
        
        assert context.requires_context("royal_death") is True
        assert context.requires_context("succession_crisis") is True
        assert context.requires_context("economic_boom") is False
    
    def test_get_mood_influence_existing(self):
        """Test get_mood_influence returns correct value for existing mood."""
        context = NarrativeContext(
            context_id="mood-influence-test",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.SCENE,
            name="Mood Influence Test",
            description="Testing mood influences",
            mood_influences={
                "melancholy": Decimal('6.5'),
                "hope": Decimal('-2.0'),
                "tension": Decimal('8.0')
            }
        )
        
        assert context.get_mood_influence("melancholy") == Decimal('6.5')
        assert context.get_mood_influence("hope") == Decimal('-2.0')
        assert context.get_mood_influence("tension") == Decimal('8.0')
    
    def test_get_mood_influence_default(self):
        """Test get_mood_influence returns default value for non-existing mood."""
        context = NarrativeContext(
            context_id="mood-default-test",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="Mood Default Test",
            description="Testing mood default",
            mood_influences={"gloom": Decimal('4.0')}
        )
        
        # Should return 0 for non-existing mood types
        assert context.get_mood_influence("joy") == Decimal('0')
        assert context.get_mood_influence("fear") == Decimal('0')
        # Should return actual value for existing mood
        assert context.get_mood_influence("gloom") == Decimal('4.0')
    
    def test_get_tension_modifier_existing(self):
        """Test get_tension_modifier returns correct value for existing tension type."""
        context = NarrativeContext(
            context_id="tension-modifier-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.CHAPTER,
            name="Tension Modifier Test",
            description="Testing tension modifiers",
            tension_modifiers={
                "romantic": Decimal('5.5'),
                "conflict": Decimal('7.0'),
                "mystery": Decimal('-1.5')
            }
        )
        
        assert context.get_tension_modifier("romantic") == Decimal('5.5')
        assert context.get_tension_modifier("conflict") == Decimal('7.0')
        assert context.get_tension_modifier("mystery") == Decimal('-1.5')
        assert context.get_tension_modifier("comic") == Decimal('0')
    
    def test_get_pacing_effect_existing(self):
        """Test get_pacing_effect returns correct value for existing pacing aspect."""
        context = NarrativeContext(
            context_id="pacing-effect-test",
            context_type=ContextType.THEMATIC,
            scope=ContextScope.ARC,
            name="Pacing Effect Test",
            description="Testing pacing effects",
            pacing_effects={
                "urgency": Decimal('6.0'),
                "contemplation": Decimal('-3.0'),
                "action_frequency": Decimal('4.5')
            }
        )
        
        assert context.get_pacing_effect("urgency") == Decimal('6.0')
        assert context.get_pacing_effect("contemplation") == Decimal('-3.0')
        assert context.get_pacing_effect("action_frequency") == Decimal('4.5')
        assert context.get_pacing_effect("dialogue_focus") == Decimal('0')
    
    def test_get_contextual_summary(self):
        """Test get_contextual_summary returns comprehensive summary dict."""
        char_id = uuid4()
        
        context = NarrativeContext(
            context_id="summary-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.ARC,
            name="Magic System Context",
            description="The underlying magical laws and constraints",
            is_persistent=True,
            applies_from_sequence=5,
            applies_to_sequence=95,
            affected_characters={char_id},
            locations={"magic_academy", "enchanted_forest"},
            hidden_information=["Secret about magic origins", "Origins are forgotten"],
            narrative_constraints=["Magic requires sacrifice", "Limited spell uses"],
            mood_influences={"wonder": Decimal('7.0')},
            pacing_effects={"mystery": Decimal('5.0')},
            prerequisite_contexts={"magic_discovery"},
            conflicting_contexts={"anti_magic_era"},
            reinforcing_contexts={"ancient_prophecy", "magical_awakening"},
            key_facts=["Magic is real", "It has rules"],
            implicit_knowledge=["Everyone knows magic exists"]
        )
        
        summary = context.get_contextual_summary()
        
        assert summary['context_id'] == "summary-test"
        assert summary['type'] == "magical"
        assert summary['scope'] == "arc"
        assert summary['name'] == "Magic System Context"
        assert summary['is_persistent'] is True
        assert summary['has_sequence_range'] is True
        assert summary['sequence_range'] == [5, 95]
        assert summary['affects_characters'] is True
        assert summary['character_count'] == 1
        assert summary['location_count'] == 2
        assert isinstance(summary['influence_strength'], float)
        assert isinstance(summary['complexity_score'], float)
        assert summary['has_hidden_information'] is True
        assert summary['has_constraints'] is True
        assert summary['influences_mood'] is True
        assert summary['influences_pacing'] is True
        assert summary['relationship_counts']['prerequisites'] == 1
        assert summary['relationship_counts']['conflicts'] == 1
        assert summary['relationship_counts']['reinforces'] == 2
        assert summary['information_layers']['key_facts'] == 2
        assert summary['information_layers']['implicit_knowledge'] == 1
        assert summary['information_layers']['hidden_information'] == 2


class TestNarrativeContextStringRepresentation:
    """Test suite for NarrativeContext string representation methods."""
    
    def test_str_representation(self):
        """Test human-readable string representation."""
        context = NarrativeContext(
            context_id="str-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Renaissance Period",
            description="A time of cultural and intellectual flowering"
        )
        
        str_repr = str(context)
        expected = "NarrativeContext('Renaissance Period', historical, global)"
        assert str_repr == expected
    
    def test_repr_representation(self):
        """Test developer representation for debugging."""
        context = NarrativeContext(
            context_id="repr-test-id",
            context_type=ContextType.TECHNOLOGICAL,
            scope=ContextScope.ARC,
            name="Steampunk Era",
            description="Age of steam-powered technology"
        )
        
        repr_str = repr(context)
        expected = (
            "NarrativeContext(id='repr-test-id', "
            "type=technological, "
            "scope=arc, "
            "name='Steampunk Era')"
        )
        assert repr_str == expected
    
    def test_string_representations_different(self):
        """Test that str and repr provide different information."""
        context = NarrativeContext(
            context_id="different-repr-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.CHAPTER,
            name="Festival Season",
            description="Time of celebration and cultural expression"
        )
        
        str_repr = str(context)
        repr_str = repr(context)
        
        # They should be different
        assert str_repr != repr_str
        # str should be more human-readable
        assert "Festival Season" in str_repr
        # repr should include more technical details
        assert "different-repr-test" in repr_str
        assert "cultural" in repr_str


class TestNarrativeContextEdgeCasesAndBoundaryConditions:
    """Test suite for edge cases and boundary conditions."""
    
    def test_creation_with_fixed_timestamp(self):
        """Test creation with explicitly set timestamp."""
        fixed_time = datetime(2024, 9, 15, 16, 45, 30, tzinfo=timezone.utc)
        
        context = NarrativeContext(
            context_id="timestamp-test",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="Fixed Timestamp Context",
            description="Testing fixed timestamp",
            creation_timestamp=fixed_time
        )
        
        assert context.creation_timestamp == fixed_time
    
    def test_large_collections_handling(self):
        """Test handling of large collections."""
        many_locations = {f"location_{i}" for i in range(100)}
        many_regions = {f"region_{i}" for i in range(50)}
        many_characters = {uuid4() for _ in range(75)}
        many_knowledge_chars = {uuid4() for _ in range(25)}
        many_reactions = {uuid4(): f"reaction_{i}" for i in range(30)}
        many_facts = [f"fact_{i}" for i in range(80)]
        many_implicit = [f"implicit_{i}" for i in range(40)]
        many_hidden = [f"hidden_{i}" for i in range(20)]
        many_constraints = [f"constraint_{i}" for i in range(35)]
        many_behaviors = [f"behavior_{i}" for i in range(45)]
        many_implications = [f"implication_{i}" for i in range(25)]
        many_moods = {f"mood_{i}": Decimal(str(i % 10)) for i in range(15)}
        many_tensions = {f"tension_{i}": Decimal(str((i % 20) - 10)) for i in range(12)}
        many_pacing = {f"pacing_{i}": Decimal(str((i % 15) - 5)) for i in range(18)}
        many_prerequisites = {f"prereq_{i}" for i in range(8)}
        many_conflicts = {f"conflict_{i}" for i in range(10)}
        many_reinforces = {f"reinforce_{i}" for i in range(12)}
        many_tags = {f"tag_{i}" for i in range(30)}
        
        context = NarrativeContext(
            context_id="large-collections-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.GLOBAL,
            name="Complex Magic World",
            description="A world with incredibly complex magical systems and interactions",
            locations=many_locations,
            affected_regions=many_regions,
            affected_characters=many_characters,
            character_knowledge_required=many_knowledge_chars,
            character_reactions=many_reactions,
            key_facts=many_facts,
            implicit_knowledge=many_implicit,
            hidden_information=many_hidden,
            narrative_constraints=many_constraints,
            behavioral_influences=many_behaviors,
            plot_implications=many_implications,
            mood_influences=many_moods,
            tension_modifiers=many_tensions,
            pacing_effects=many_pacing,
            prerequisite_contexts=many_prerequisites,
            conflicting_contexts=many_conflicts,
            reinforcing_contexts=many_reinforces,
            tags=many_tags
        )
        
        assert len(context.locations) == 100
        assert len(context.affected_regions) == 50
        assert len(context.affected_characters) == 75
        assert len(context.character_knowledge_required) == 25
        assert len(context.character_reactions) == 30
        assert len(context.key_facts) == 80
        assert len(context.implicit_knowledge) == 40
        assert len(context.hidden_information) == 20
        assert len(context.narrative_constraints) == 35
        assert len(context.behavioral_influences) == 45
        assert len(context.plot_implications) == 25
        assert len(context.mood_influences) == 15
        assert len(context.tension_modifiers) == 12
        assert len(context.pacing_effects) == 18
        assert len(context.prerequisite_contexts) == 8
        assert len(context.conflicting_contexts) == 10
        assert len(context.reinforcing_contexts) == 12
        assert len(context.tags) == 30
        assert context.affects_characters is True
        assert context.has_hidden_information is True
        assert context.has_narrative_constraints is True
        assert context.influences_mood is True
        assert context.influences_pacing is True
        assert context.has_prerequisites is True
        assert context.has_conflicts is True
    
    def test_decimal_precision_handling(self):
        """Test handling of decimal precision for influence and score values."""
        context = NarrativeContext(
            context_id="precision-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.SCENE,
            name="Precision Test",
            description="Testing decimal precision",
            narrative_importance=Decimal('7.123456789'),
            visibility_level=Decimal('8.987654321'),
            complexity_level=Decimal('6.555555555'),
            evolution_rate=Decimal('0.123456789'),
            stability=Decimal('0.987654321'),
            mood_influences={
                "precise_mood": Decimal('5.123456789')
            },
            tension_modifiers={
                "precise_tension": Decimal('-3.987654321')
            },
            pacing_effects={
                "precise_pacing": Decimal('2.555555555')
            }
        )
        
        # Values should maintain precision
        assert context.narrative_importance == Decimal('7.123456789')
        assert context.visibility_level == Decimal('8.987654321')
        assert context.complexity_level == Decimal('6.555555555')
        assert context.evolution_rate == Decimal('0.123456789')
        assert context.stability == Decimal('0.987654321')
        assert context.mood_influences["precise_mood"] == Decimal('5.123456789')
        assert context.tension_modifiers["precise_tension"] == Decimal('-3.987654321')
        assert context.pacing_effects["precise_pacing"] == Decimal('2.555555555')
        
        # Scores should use precise calculation
        influence_score = context.overall_influence_strength
        complexity_score = context.contextual_complexity_score
        assert isinstance(influence_score, Decimal)
        assert isinstance(complexity_score, Decimal)
    
    def test_unicode_text_handling(self):
        """Test handling of unicode characters in text fields."""
        context = NarrativeContext(
            context_id="unicode-test-🌍",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.GLOBAL,
            name="世界文化 World Culture 🏛️",
            description="A rich tapestry of cultures: αβγ 中文 العربية русский हिन्दी 🌟",
            geographical_scope="全球范围 Global scope",
            source_material="多文化研究 Multicultural research",
            research_notes="Sources include: 文献、books, كتب, книги, पुस्तकें 📚"
        )
        
        assert "🌍" in context.context_id
        assert "世界文化" in context.name
        assert "🏛️" in context.name
        assert "αβγ" in context.description
        assert "العربية" in context.description
        assert "हिन्दी" in context.description
        assert "🌟" in context.description
        assert "全球范围" in context.geographical_scope
        assert "多文化研究" in context.source_material
        assert "📚" in context.research_notes
    
    def test_complex_metadata_handling(self):
        """Test handling of complex metadata structures."""
        complex_metadata = {
            "world_building": {
                "inspiration_sources": ["Tolkien", "Martin", "Sanderson"],
                "cultural_influences": {
                    "european": ["medieval", "renaissance"],
                    "asian": ["feudal_japan", "ancient_china"],
                    "fantasy": ["high_fantasy", "dark_fantasy"]
                }
            },
            "narrative_analysis": {
                "themes_explored": ["power", "corruption", "redemption"],
                "character_archetypes": [
                    {"type": "hero", "count": 3},
                    {"type": "mentor", "count": 2},
                    {"type": "shadow", "count": 1}
                ]
            },
            "unicode_research_🔬": {
                "multilingual_sources": {
                    "english": "Primary language",
                    "中文": "Chinese historical records",
                    "日本語": "Japanese cultural studies",
                    "العربية": "Arabic philosophical texts"
                }
            }
        }
        
        context = NarrativeContext(
            context_id="complex-metadata-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Complex World Context",
            description="A richly detailed world with complex cultural interactions",
            metadata=complex_metadata
        )
        
        # Should store complex metadata as-is
        assert context.metadata == complex_metadata
        assert context.metadata["world_building"]["inspiration_sources"] == ["Tolkien", "Martin", "Sanderson"]
        assert context.metadata["unicode_research_🔬"]["multilingual_sources"]["中文"] == "Chinese historical records"
        assert "العربية" in context.metadata["unicode_research_🔬"]["multilingual_sources"]


class TestNarrativeContextCollectionsAndComparison:
    """Test suite for NarrativeContext behavior in collections and comparisons."""
    
    def test_contexts_in_list(self):
        """Test NarrativeContext objects in list operations."""
        context1 = NarrativeContext(
            context_id="list-test-1",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="First Context",
            description="First test context"
        )
        
        context2 = NarrativeContext(
            context_id="list-test-2",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.CHAPTER,
            name="Second Context",
            description="Second test context"
        )
        
        context_list = [context1, context2]
        
        assert len(context_list) == 2
        assert context1 in context_list
        assert context2 in context_list
    
    def test_contexts_sorting_by_influence_strength(self):
        """Test sorting NarrativeContext objects by overall influence strength."""
        contexts = [
            NarrativeContext(
                context_id=f"sort-test-{i}",
                context_type=ContextType.THEMATIC,
                scope=scope,
                name=f"Context {i}",
                description=f"Context number {i}",
                narrative_importance=importance,
                visibility_level=visibility,
                mood_influences={f"mood_{j}": Decimal('5.0') for j in range(mood_count)}
            )
            for i, (scope, importance, visibility, mood_count) in enumerate([
                (ContextScope.MOMENT, Decimal('3.0'), Decimal('4.0'), 1),
                (ContextScope.GLOBAL, Decimal('9.0'), Decimal('8.0'), 5),
                (ContextScope.SCENE, Decimal('5.0'), Decimal('6.0'), 2),
                (ContextScope.ARC, Decimal('8.0'), Decimal('9.0'), 3)
            ])
        ]
        
        sorted_contexts = sorted(contexts, key=lambda c: c.overall_influence_strength, reverse=True)
        
        # Highest influence should be first
        assert sorted_contexts[0].overall_influence_strength >= sorted_contexts[1].overall_influence_strength
        assert sorted_contexts[1].overall_influence_strength >= sorted_contexts[2].overall_influence_strength
        assert sorted_contexts[2].overall_influence_strength >= sorted_contexts[3].overall_influence_strength
    
    def test_context_equality_identity(self):
        """Test that identical NarrativeContext objects are considered equal."""
        context1 = NarrativeContext(
            context_id="equality-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Equal Context",
            description="Testing equality"
        )
        
        context2 = NarrativeContext(
            context_id="equality-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Equal Context",
            description="Testing equality"
        )
        
        # Frozen dataclasses with same values should be equal
        assert context1 == context2
        # But they should be different objects
        assert context1 is not context2
    
    def test_context_inequality(self):
        """Test that different NarrativeContext objects are not equal."""
        context1 = NarrativeContext(
            context_id="different-1",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.GLOBAL,
            name="First Context",
            description="First context description"
        )
        
        context2 = NarrativeContext(
            context_id="different-2",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.GLOBAL,
            name="Second Context",
            description="Second context description"
        )
        
        assert context1 != context2
        assert not (context1 == context2)
    
    def test_context_hashing_consistency(self):
        """Test that equal NarrativeContext objects have same hash."""
        context1 = NarrativeContext(
            context_id="hash-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.CHAPTER,
            name="Hash Test Context",
            description="Testing hash consistency"
        )
        
        context2 = NarrativeContext(
            context_id="hash-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.CHAPTER,
            name="Hash Test Context",
            description="Testing hash consistency"
        )
        
        # Equal objects should have equal hashes
        assert context1 == context2
        assert hash(context1) == hash(context2)
    
    def test_contexts_in_set(self):
        """Test NarrativeContext objects in set operations."""
        context1 = NarrativeContext(
            context_id="set-test-1",
            context_type=ContextType.TECHNOLOGICAL,
            scope=ContextScope.ARC,
            name="Tech Context",
            description="Technology context"
        )
        
        context2 = NarrativeContext(
            context_id="set-test-2",
            context_type=ContextType.ENVIRONMENTAL,
            scope=ContextScope.GLOBAL,
            name="Environment Context",
            description="Environmental context"
        )
        
        # Identical context
        context1_duplicate = NarrativeContext(
            context_id="set-test-1",
            context_type=ContextType.TECHNOLOGICAL,
            scope=ContextScope.ARC,
            name="Tech Context",
            description="Technology context"
        )
        
        context_set = {context1, context2, context1_duplicate}
        
        # Set should deduplicate identical objects
        assert len(context_set) == 2  # context1 and context1_duplicate are the same
        assert context1 in context_set
        assert context2 in context_set
        assert context1_duplicate in context_set  # Should find context1
    
    def test_contexts_as_dict_keys(self):
        """Test using NarrativeContext objects as dictionary keys."""
        context1 = NarrativeContext(
            context_id="dict-key-1",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Historical Context",
            description="Important historical period"
        )
        
        context2 = NarrativeContext(
            context_id="dict-key-2",
            context_type=ContextType.SOCIAL,
            scope=ContextScope.ARC,
            name="Social Context",
            description="Social dynamics and relationships"
        )
        
        context_dict = {
            context1: "historical_data",
            context2: "social_data"
        }
        
        assert context_dict[context1] == "historical_data"
        assert context_dict[context2] == "social_data"
        
        # Test with equivalent context
        equivalent_context1 = NarrativeContext(
            context_id="dict-key-1",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Historical Context",
            description="Important historical period"
        )
        
        # Should find the same entry
        assert context_dict[equivalent_context1] == "historical_data"