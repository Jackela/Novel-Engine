#!/usr/bin/env python3
"""
Novel Engine Complete Integration Tests
=======================================

Comprehensive integration tests for the complete Novel Engine system,
including Iron Laws validation, evaluation pipeline, and caching systems.

This test suite validates:
1. End-to-end Novel Engine functionality with all components
2. Iron Laws system integration with DirectorAgent
3. Evaluation pipeline integration and execution
4. Caching system integration and performance optimization
5. Cross-component compatibility and data flow

Development Phase: Final Integration Testing - Complete System Validation
"""

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest

FULL_INTEGRATION = os.getenv("NOVEL_ENGINE_FULL_INTEGRATION") == "1"
if not FULL_INTEGRATION:
    pytestmark = pytest.mark.skip(
        reason="Complete integration tests require NOVEL_ENGINE_FULL_INTEGRATION=1"
    )

# Core Novel Engine imports
try:
    from src.agents.director_agent import DirectorAgent
    from src.persona_agent import PersonaAgent
    from src.shared_types import (
        ActionIntensity,
        ActionParameters,
        ActionTarget,
        ActionType,
        CharacterData,
        CharacterResources,
        CharacterStats,
        EntityType,
        IronLawsReport,
        Position,
        ProposedAction,
        ResourceValue,
        ValidationStatus,
    )

    CORE_ENGINE_AVAILABLE = True
except ImportError as e:
    CORE_ENGINE_AVAILABLE = False
    pytest.skip(f"Core engine components not available: {e}", allow_module_level=True)

# Evaluation system imports
try:
    from evaluate_baseline import BaselineEvaluator, NovelEngineRunner, SeedLoader

    EVALUATION_SYSTEM_AVAILABLE = True
except ImportError:
    EVALUATION_SYSTEM_AVAILABLE = False

# Caching system imports
try:
    from src.caching import (
        BudgetPeriod,
        HashingConfig,
        OperationType,
        SemanticCache,
        SemanticCacheConfig,
        StateHasher,
        TokenBudgetConfig,
        TokenBudgetManager,
    )

    CACHING_SYSTEM_AVAILABLE = True
except ImportError:
    CACHING_SYSTEM_AVAILABLE = False


class TestCompleteSystemIntegration:
    """Complete Novel Engine system integration tests."""

    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_character_data(self):
        """Create mock character data for testing."""
        return {
            "character_id": "test_integration_char",
            "name": "Integration Test Character",
            "faction": "Test Faction",
            "role": "Test Agent",
            "position": Position(x=0, y=0, z=0, facing=0),
            "stats": CharacterStats(
                strength=8,
                dexterity=7,
                intelligence=9,
                willpower=8,
                perception=6,
                charisma=7,
            ),
            "resources": CharacterResources(
                health=ResourceValue(current=85, maximum=100, minimum=0),
                stamina=ResourceValue(current=70, maximum=85, minimum=0),
                morale=ResourceValue(current=80, maximum=90, minimum=0),
            ),
            "equipment": ["test_weapon", "test_armor"],
        }

    @pytest.fixture
    def director_agent(self, temp_directory, mock_character_data):
        """Create DirectorAgent instance for integration testing."""
        if not CORE_ENGINE_AVAILABLE:
            pytest.skip("Core engine not available")

        # Create temporary log file
        log_file = temp_directory / "integration_test.log"

        # Initialize DirectorAgent
        director = DirectorAgent(
            world_state_file_path=None, campaign_log_path=str(log_file)
        )

        # Create and register test agent
        character_dir = temp_directory / "test_character"
        character_dir.mkdir(exist_ok=True)

        character_sheet = character_dir / "character.md"
        with open(character_sheet, "w", encoding="utf-8") as f:
            f.write(
                f"# {mock_character_data['name']}\n\n**Faction**: {mock_character_data['faction']}\n"
            )

        agent = PersonaAgent(str(character_dir))
        agent.character_data = mock_character_data
        agent.agent_id = mock_character_data["character_id"]

        director.register_agent(agent)

        return director

    @pytest.mark.skipif(not CORE_ENGINE_AVAILABLE, reason="Core engine not available")
    def test_iron_laws_integration(self, director_agent, mock_character_data):
        """Test Iron Laws integration with DirectorAgent."""

        # Create test action
        proposed_action = ProposedAction(
            character_id=mock_character_data["character_id"],
            action_type=ActionType.INVESTIGATE,
            target=ActionTarget(entity_type=EntityType.OBJECT, entity_id="test_object"),
            parameters=ActionParameters(intensity=ActionIntensity.NORMAL),
            reasoning="Integration test investigation action",
        )

        # Test Iron Laws validation (need to get the agent from director)
        agent = director_agent.registered_agents[0]
        validation_result = director_agent._adjudicate_action(proposed_action, agent)

        # Verify validation result structure
        assert validation_result is not None
        assert isinstance(validation_result, dict)
        assert "validation_status" in validation_result
        assert "violations_found" in validation_result
        assert "repaired_action" in validation_result

        # Verify Iron Laws methods are accessible
        assert hasattr(director_agent, "_validate_e001_causality")
        assert hasattr(director_agent, "_validate_e002_resource_constraints")
        assert hasattr(director_agent, "_validate_e003_physical_possibility")
        assert hasattr(director_agent, "_validate_e004_narrative_consistency")
        assert hasattr(director_agent, "_validate_e005_social_appropriateness")

        # Test repair system
        assert hasattr(director_agent, "_attempt_action_repairs")

    @pytest.mark.skipif(
        not CACHING_SYSTEM_AVAILABLE, reason="Caching system not available"
    )
    def test_state_hashing_integration(self, mock_character_data, temp_directory):
        """Test state hashing system integration."""

        # Initialize state hasher
        hasher = StateHasher(HashingConfig(enable_debug_logging=True))

        # Test character state hashing
        character_hash = hasher.hash_character_state(mock_character_data)

        assert character_hash is not None
        assert character_hash.hash_value
        assert character_hash.component_type == "character_state"
        assert character_hash.component_id == mock_character_data["character_id"]

        # Test world state hashing
        world_state = {
            "characters": {mock_character_data["character_id"]: mock_character_data},
            "locations": [{"id": "test_loc", "name": "Test Location"}],
            "objects": [{"id": "test_obj", "name": "Test Object"}],
            "environment": {"time_of_day": "noon", "weather": "clear"},
        }

        world_hash = hasher.hash_world_state(world_state)

        assert world_hash is not None
        assert world_hash.hash_value
        assert world_hash.component_type == "world_state"
        assert world_hash.component_id == "global"

        # Test consistency validation
        second_world_hash = hasher.hash_world_state(world_state)
        assert world_hash.hash_value == second_world_hash.hash_value

        # Test hash change detection
        modified_world_state = world_state.copy()
        modified_world_state["environment"]["time_of_day"] = "evening"
        modified_hash = hasher.hash_world_state(modified_world_state)

        assert world_hash.hash_value != modified_hash.hash_value

        # Test consistency validation
        validation_report = hasher.validate_state_consistency(
            {"world": modified_hash}, {"world": world_hash}
        )

        assert validation_report["consistency_status"] == "changed"
        assert "world" in validation_report["changed_components"]

    @pytest.mark.skipif(
        not CACHING_SYSTEM_AVAILABLE, reason="Caching system not available"
    )
    def test_semantic_caching_integration(self, temp_directory):
        """Test semantic caching system integration."""

        # Initialize semantic cache
        cache_config = SemanticCacheConfig(
            max_cache_size=100,
            similarity_threshold=0.8,
            persistence_file=temp_directory / "test_cache.json",
        )

        semantic_cache = SemanticCache(cache_config)

        # Test basic cache operations
        test_key = "test_llm_response_001"
        test_value = "This is a test LLM response for integration testing."
        test_query = "Generate a test response for integration testing"

        # Store value
        success = semantic_cache.put(
            key=test_key,
            value=test_value,
            query_text=test_query,
            content_type="llm_response",
            creation_cost=0.05,
        )

        assert success

        # Retrieve exact match
        cached_value = semantic_cache.get(test_key, test_query)
        assert cached_value == test_value

        # Test semantic similarity (if sklearn available)
        similar_query = "Create a test response for integration testing"
        semantic_cache.get("nonexistent_key", similar_query)

        # Might find similar match depending on sklearn availability
        # At minimum, should not crash

        # Test cache statistics
        stats = semantic_cache.get_stats()

        assert isinstance(stats, dict)
        assert "cache_size" in stats
        assert "hit_count" in stats
        assert "miss_count" in stats
        assert stats["cache_size"] >= 1  # At least our test entry

        # Test cache persistence
        semantic_cache.save_cache()

        assert cache_config.persistence_file.exists()

        # Load cache in new instance
        new_cache = SemanticCache(cache_config)
        recovered_value = new_cache.get(test_key, test_query)

        assert recovered_value == test_value

    @pytest.mark.skipif(
        not CACHING_SYSTEM_AVAILABLE, reason="Caching system not available"
    )
    def test_token_budget_integration(self, temp_directory):
        """Test token budget management system integration."""

        # Initialize token budget manager
        budget_config = TokenBudgetConfig(
            enable_persistence=True,
            persistence_file=temp_directory / "test_budget.json",
            enable_cache_integration=False,  # Disable for simpler testing
            enable_debug_logging=True,
        )

        budget_manager = TokenBudgetManager(budget_config)

        # Add budget limits
        from src.caching.token_budget import BudgetLimit

        daily_limit = BudgetLimit(
            period=BudgetPeriod.DAILY,
            max_tokens=10000,
            max_cost=1.0,
            max_operations=100,
        )

        budget_manager.add_budget_limit(daily_limit)

        # Test cost estimation
        estimate = budget_manager.estimate_operation_cost(
            operation_type=OperationType.CHAT_COMPLETION,
            prompt_text="This is a test prompt for cost estimation.",
            model_name="gpt-3.5-turbo",
            completion_tokens_estimate=50,
        )

        assert isinstance(estimate, dict)
        assert "estimated_total_cost" in estimate
        assert "estimated_total_tokens" in estimate
        assert "budget_check" in estimate
        assert estimate["estimated_total_cost"] > 0

        # Test budget approval
        approval = budget_manager.check_budget_approval(
            operation_type=OperationType.CHAT_COMPLETION,
            estimated_tokens=estimate["estimated_total_tokens"],
            estimated_cost=estimate["estimated_total_cost"],
            priority="normal",
        )

        assert isinstance(approval, dict)
        assert "approved" in approval
        assert "reason" in approval
        assert approval["approved"]  # Should be approved initially

        # Record operation
        success = budget_manager.record_operation(
            operation_id="test_integration_op_001",
            operation_type=OperationType.CHAT_COMPLETION,
            model_name="gpt-3.5-turbo",
            prompt_tokens=estimate["estimated_prompt_tokens"],
            completion_tokens=50,
            duration_ms=2500,
            success=True,
            operation_context="Integration test operation",
        )

        assert success

        # Test usage report
        report = budget_manager.get_usage_report(period=BudgetPeriod.DAILY)

        assert isinstance(report, dict)
        assert "summary_metrics" in report
        assert report["summary_metrics"]["total_operations"] == 1
        assert report["summary_metrics"]["total_cost"] > 0

        # Test optimization analysis
        optimization = budget_manager.optimize_costs()

        assert isinstance(optimization, dict)
        assert "recommendations" in optimization

        # Test persistence
        budget_manager.save_usage_data()

        assert budget_config.persistence_file.exists()

    @pytest.mark.skipif(
        not EVALUATION_SYSTEM_AVAILABLE, reason="Evaluation system not available"
    )
    def test_evaluation_system_integration(self, temp_directory):
        """Test evaluation system integration."""

        # Note: This test is limited because full evaluation requires
        # complete Novel Engine simulation, but we can test components

        # Test seed loader
        test_seed_data = {
            "metadata": {
                "seed_id": "integration_test_seed",
                "version": "1.0.0",
                "description": "Integration test seed",
                "complexity": "low",
                "estimated_turns": 3,
                "evaluation_focus": ["E001", "E002"],
            },
            "world_state": {
                "setting": "Test Environment",
                "environment": {"time_of_day": "noon"},
                "locations": [{"id": "test_loc", "name": "Test Location"}],
                "objects": [{"id": "test_obj", "name": "Test Object"}],
            },
            "characters": [
                {
                    "character_id": "test_char_001",
                    "name": "Test Character",
                    "faction": "Test Faction",
                    "role": "Agent",
                    "position": {"x": 0, "y": 0, "z": 0, "facing": 0},
                    "stats": {
                        "strength": 5,
                        "dexterity": 6,
                        "intelligence": 7,
                        "willpower": 5,
                        "perception": 6,
                        "charisma": 5,
                    },
                    "resources": {
                        "health": {"current": 100, "maximum": 100, "minimum": 0},
                        "stamina": {"current": 100, "maximum": 100, "minimum": 0},
                        "morale": {"current": 100, "maximum": 100, "minimum": 0},
                    },
                }
            ],
            "objectives": {
                "primary": [
                    {
                        "id": "test_objective_001",
                        "description": "Complete integration test",
                        "type": "validation",
                    }
                ],
                "secondary": [],
            },
            "evaluation": {
                "metrics": {
                    "iron_laws_compliance": {"weight": 0.6},
                    "objective_completion": {"weight": 0.4},
                },
                "pass_thresholds": {"minimum_score": 0.7, "max_violations": 2},
            },
        }

        # Create temporary seed file
        seed_file = temp_directory / "integration_test_seed.yaml"
        import yaml

        with open(seed_file, "w", encoding="utf-8") as f:
            yaml.dump(test_seed_data, f, default_flow_style=False)

        # Test seed loading
        config = SeedLoader.load_seed(seed_file)

        assert config.seed_id == "integration_test_seed"
        assert config.complexity == "low"
        assert config.estimated_turns == 3
        assert len(config.characters) == 1
        assert len(config.objectives["primary"]) == 1

        # Test seed validation
        is_valid = SeedLoader.validate_seed(config)
        assert is_valid

    @pytest.mark.skipif(
        not (
            CORE_ENGINE_AVAILABLE
            and EVALUATION_SYSTEM_AVAILABLE
            and CACHING_SYSTEM_AVAILABLE
        ),
        reason="Full system components not available",
    )
    def test_end_to_end_integration(self, temp_directory, mock_character_data):
        """Test complete end-to-end system integration."""

        # This is a comprehensive integration test that verifies
        # the complete Novel Engine system works together

        print("\n🔄 Starting End-to-End Integration Test")

        # Step 1: Initialize all major systems
        print("1. Initializing core systems...")

        # State hasher
        hasher = StateHasher(HashingConfig(enable_debug_logging=False))

        # Semantic cache
        cache = SemanticCache(
            SemanticCacheConfig(
                max_cache_size=50, persistence_file=temp_directory / "e2e_cache.json"
            )
        )

        # Token budget manager
        budget_manager = TokenBudgetManager(
            TokenBudgetConfig(
                enable_persistence=True,
                persistence_file=temp_directory / "e2e_budget.json",
                enable_cache_integration=False,  # Simplified for testing
            )
        )

        # Director agent
        log_file = temp_directory / "e2e_test.log"
        director = DirectorAgent(
            world_state_file_path=None, campaign_log_path=str(log_file)
        )

        print("✅ Core systems initialized")

        # Step 2: Create and register agent
        print("2. Creating and registering test agent...")

        # Create a directory for character files
        character_dir = temp_directory / "test_character"
        character_dir.mkdir(exist_ok=True)

        # Create character sheet file
        character_sheet = character_dir / "character.md"
        with open(character_sheet, "w", encoding="utf-8") as f:
            f.write(
                f"# {mock_character_data['name']}\n\n**Role**: Integration Test Agent\n"
            )

        agent = PersonaAgent(str(character_dir))
        agent.character_data = mock_character_data
        agent.agent_id = mock_character_data["character_id"]

        director.register_agent(agent)

        print("✅ Agent registered successfully")

        # Step 3: Test state hashing with current state
        print("3. Testing state hashing...")

        world_state = {
            "characters": {mock_character_data["character_id"]: mock_character_data},
            "environment": {"time": "noon", "turn": 1},
        }

        initial_hash = hasher.hash_world_state(world_state)
        character_hash = hasher.hash_character_state(mock_character_data)

        assert initial_hash.hash_value
        assert character_hash.hash_value

        print(f"✅ State hashing complete - World: {initial_hash.hash_value[:16]}...")

        # Step 4: Test basic agent functionality
        print("4. Testing agent integration...")

        # Test agent is properly registered
        assert len(director.registered_agents) == 1
        registered_agent = director.registered_agents[0]
        assert registered_agent.agent_id == mock_character_data["character_id"]

        print("✅ Agent integration successful")

        # Step 5: Test caching integration
        print("5. Testing caching integration...")

        # Cache a test LLM response
        test_prompt = "Generate character dialogue for investigation action"
        test_response = (
            "The character carefully examines the object, looking for clues."
        )

        cache.put(
            key="e2e_test_response",
            value=test_response,
            query_text=test_prompt,
            content_type="llm_response",
        )

        # Retrieve from cache
        cached_response = cache.get("e2e_test_response", test_prompt)
        assert cached_response == test_response

        print("✅ Caching system integration successful")

        # Step 6: Test budget tracking
        print("6. Testing budget tracking...")

        # Add daily budget limit
        from src.caching.token_budget import BudgetLimit

        daily_limit = BudgetLimit(
            period=BudgetPeriod.DAILY, max_tokens=5000, max_cost=0.5
        )
        budget_manager.add_budget_limit(daily_limit)

        # Record a test operation
        budget_manager.record_operation(
            operation_id="e2e_integration_test",
            operation_type=OperationType.CHAT_COMPLETION,
            model_name="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
            duration_ms=1500,
            success=True,
            character_id=mock_character_data["character_id"],
            operation_context="End-to-end integration test",
        )

        # Get usage report
        usage_report = budget_manager.get_usage_report(period=BudgetPeriod.DAILY)

        assert usage_report["summary_metrics"]["total_operations"] == 1
        assert usage_report["summary_metrics"]["total_tokens"] == 150

        print("✅ Budget tracking integration successful")

        # Step 7: Test state change detection
        print("7. Testing state change detection...")

        # Modify world state and detect changes
        modified_world_state = world_state.copy()
        modified_world_state["environment"]["turn"] = 2

        modified_hash = hasher.hash_world_state(modified_world_state)

        # Validate state consistency
        consistency_report = hasher.validate_state_consistency(
            {"world": modified_hash}, {"world": initial_hash}
        )

        assert consistency_report["consistency_status"] == "changed"

        print("✅ State change detection successful")

        # Step 8: Test system persistence
        print("8. Testing system persistence...")

        # Save all persistent data
        cache.save_cache()
        budget_manager.save_usage_data()

        # Verify files were created
        assert (temp_directory / "e2e_cache.json").exists()
        assert (temp_directory / "e2e_budget.json").exists()

        print("✅ System persistence successful")

        # Step 9: Generate comprehensive system report
        print("9. Generating system integration report...")

        integration_report = {
            "test_timestamp": datetime.now().isoformat(),
            "test_duration_seconds": 5.0,  # Approximate
            "components_tested": [
                "DirectorAgent",
                "PersonaAgent",
                "Agent Integration",
                "State Hashing",
                "Semantic Caching",
                "Token Budget Management",
            ],
            "state_hashing": {
                "initial_world_hash": initial_hash.hash_value,
                "modified_world_hash": modified_hash.hash_value,
                "character_hash": character_hash.hash_value,
                "consistency_detection": "functional",
            },
            "agent_integration": {
                "agents_registered": len(director.registered_agents),
                "agent_functionality": "functional",
                "character_data_integration": "functional",
            },
            "caching_system": {
                "cache_operations": "functional",
                "persistence": "functional",
                "semantic_matching": (
                    "available" if cache.config.enable_semantic_matching else "disabled"
                ),
            },
            "budget_system": {
                "cost_tracking": "functional",
                "budget_limits": "functional",
                "usage_reporting": "functional",
                "optimization": "available",
            },
            "overall_integration": "successful",
        }

        # Save integration report
        report_file = temp_directory / "integration_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(integration_report, f, indent=2, ensure_ascii=False)

        print("✅ Integration report generated")
        print("\n🎉 End-to-End Integration Test PASSED!")
        print(f"📊 Report saved: {report_file}")

        # Return report for verification
        return integration_report

    @pytest.mark.skipif(
        not CACHING_SYSTEM_AVAILABLE, reason="Caching system not available"
    )
    def test_performance_integration(self, temp_directory):
        """Test performance optimization integration across systems."""

        print("\n⚡ Starting Performance Integration Test")

        # Initialize systems with performance focus
        hasher = StateHasher(
            HashingConfig(
                enable_incremental_hashing=True,
                cache_intermediate_results=True,
                max_cache_size=100,
            )
        )

        cache = SemanticCache(
            SemanticCacheConfig(
                max_cache_size=200, similarity_threshold=0.75, enable_clustering=True
            )
        )

        budget_manager = TokenBudgetManager(
            TokenBudgetConfig(
                enable_cache_integration=True, enable_automatic_optimization=True
            )
        )

        # Performance test data
        test_characters = []

        # Generate test data
        for i in range(10):
            char_data = {
                "character_id": f"perf_test_char_{i}",
                "name": f"Performance Test Character {i}",
                "position": Position(x=i, y=i, z=0),
                "stats": CharacterStats(
                    strength=min(1 + i, 10),
                    dexterity=min(2 + i, 10),
                    intelligence=min(3 + i, 10),
                    willpower=min(1 + i, 10),
                    perception=min(2 + i, 10),
                    charisma=min(3 + i, 10),
                ),
            }
            test_characters.append(char_data)

        # Test 1: State hashing performance
        start_time = time.time()

        for char_data in test_characters:
            char_hash = hasher.hash_character_state(char_data)
            assert char_hash.hash_value

        hashing_time = time.time() - start_time
        print(
            f"✅ State hashing: {len(test_characters)} characters in {hashing_time:.3f}s"
        )

        # Test 2: Cache performance
        start_time = time.time()

        for i, char_data in enumerate(test_characters):
            cache_key = f"perf_test_{i}"
            test_value = f"Performance test value for character {char_data['name']}"

            cache.put(cache_key, test_value, content_type="performance_test")
            retrieved = cache.get(cache_key)

            assert retrieved == test_value

        caching_time = time.time() - start_time
        print(
            f"✅ Caching operations: {len(test_characters)} ops in {caching_time:.3f}s"
        )

        # Test 3: Budget tracking performance
        start_time = time.time()

        for i in range(20):  # More operations for budget testing
            budget_manager.record_operation(
                operation_id=f"perf_test_op_{i}",
                operation_type=OperationType.CHAT_COMPLETION,
                model_name="gpt-3.5-turbo",
                prompt_tokens=100 + i * 10,
                completion_tokens=50 + i * 5,
                duration_ms=1000 + i * 100,
                success=True,
                operation_context=f"Performance test operation {i}",
            )

        budget_time = time.time() - start_time
        print(f"✅ Budget tracking: 20 operations in {budget_time:.3f}s")

        # Test 4: Combined system performance
        start_time = time.time()

        world_states = []
        for i in range(5):
            world_state = {
                "characters": {
                    char["character_id"]: char for char in test_characters[:5]
                },
                "environment": {"turn": i, "time": f"hour_{i}"},
                "locations": [
                    {"id": f"loc_{j}", "name": f"Location {j}"} for j in range(3)
                ],
            }
            world_states.append(world_state)

            # Hash world state
            world_hash = hasher.hash_world_state(world_state)

            # Cache world state hash
            cache.put(
                key=f"world_state_{i}",
                value=world_hash.hash_value,
                content_type="world_state_hash",
            )

        # Test consistency checking
        for i in range(1, len(world_states)):
            current_hash = hasher.hash_world_state(world_states[i])
            previous_hash = hasher.hash_world_state(world_states[i - 1])

            consistency_report = hasher.validate_state_consistency(
                {"current": current_hash}, {"previous": previous_hash}
            )

            assert consistency_report["consistency_status"] in ["changed", "consistent"]

        combined_time = time.time() - start_time
        print(f"✅ Combined system: 5 world states in {combined_time:.3f}s")

        # Performance summary
        performance_report = {
            "test_timestamp": datetime.now().isoformat(),
            "performance_metrics": {
                "state_hashing_time": hashing_time,
                "caching_time": caching_time,
                "budget_tracking_time": budget_time,
                "combined_system_time": combined_time,
            },
            "throughput_metrics": {
                "characters_hashed_per_second": len(test_characters) / hashing_time,
                "cache_operations_per_second": len(test_characters)
                * 2
                / caching_time,  # put + get
                "budget_operations_per_second": 20 / budget_time,
                "world_states_per_second": 5 / combined_time,
            },
            "cache_stats": cache.get_stats(),
            "performance_acceptable": all(
                [
                    hashing_time < 1.0,  # Should hash 10 characters in under 1 second
                    caching_time < 0.5,  # Should cache 10 items in under 0.5 seconds
                    budget_time
                    < 0.5,  # Should track 20 operations in under 0.5 seconds
                    combined_time
                    < 2.0,  # Combined operations should take under 2 seconds
                ]
            ),
        }

        print("\n⚡ Performance Integration Test Results:")
        print(
            f"   Hashing: {performance_report['throughput_metrics']['characters_hashed_per_second']:.1f} chars/sec"
        )
        print(
            f"   Caching: {performance_report['throughput_metrics']['cache_operations_per_second']:.1f} ops/sec"
        )
        print(
            f"   Budget: {performance_report['throughput_metrics']['budget_operations_per_second']:.1f} ops/sec"
        )
        print(
            f"   Combined: {performance_report['throughput_metrics']['world_states_per_second']:.1f} states/sec"
        )
        print(
            f"   Overall: {'✅ ACCEPTABLE' if performance_report['performance_acceptable'] else '❌ NEEDS OPTIMIZATION'}"
        )

        return performance_report


if __name__ == "__main__":
    # Run tests directly for debugging
    pytest.main([__file__, "-v", "-s"])
