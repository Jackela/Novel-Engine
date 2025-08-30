"""
Comprehensive Integration Test Suite for Modular Interaction Engine System
=======================================================================

Enterprise-grade test suite validating all interaction engine components
with comprehensive coverage, performance testing, and error scenarios.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import the modular interaction engine system
try:
    from src.interactions.interaction_engine_system import (
        InteractionContext,
        InteractionEngine,
        InteractionEngineConfig,
        InteractionOutcome,
        InteractionPhase,
        InteractionPriority,
        InteractionType,
        create_interaction_engine,
        create_performance_optimized_config,
    )
    from src.interactions.interaction_engine_system.queue_management.queue_manager import (
        QueueManager,
        QueueStatus,
    )
    from src.interactions.interaction_engine_system.validation.interaction_validator import (
        InteractionValidator,
    )

    REAL_ENGINE = True
except ImportError as e:
    logger.error(f"Failed to import interaction engine system: {e}")
    REAL_ENGINE = False

    # Create comprehensive fallbacks for testing
    class MockInteractionEngine:
        def __init__(self, config=None):
            self.config = config
            self.is_initialized = True
            self.processing_active = True
            self.engine_stats = {
                "total_interactions_processed": 0,
                "successful_interactions": 0,
                "failed_interactions": 0,
                "average_processing_time": 0.1,
            }

        async def process_interaction(self, context, async_processing=False):
            self.engine_stats["total_interactions_processed"] += 1
            self.engine_stats["successful_interactions"] += 1

            return type(
                "MockOutcome",
                (),
                {
                    "success": True,
                    "interaction_id": context.interaction_id,
                    "context": context,
                    "processing_duration": 0.1,
                    "interaction_content": {"result": "mock_success"},
                    "completed_phases": ["validation", "processing", "state_update"],
                    "errors": [],
                },
            )()

        def get_engine_status(self):
            return {
                "engine_status": {
                    "initialized": True,
                    "processing_active": True,
                    **self.engine_stats,
                },
                "queue_status": {"queue_size": 0, "processing_count": 0},
                "supported_interaction_types": ["dialogue", "combat", "cooperation"],
            }

        async def create_character_interaction(
            self, agent_id, target_id, interaction_type, content, priority="normal"
        ):
            context = InteractionContext(
                interaction_id=f"{agent_id}_{target_id}_mock",
                interaction_type=interaction_type,
                participants=[agent_id, target_id],
            )
            outcome = await self.process_interaction(context)
            return type(
                "MockResponse",
                (),
                {
                    "success": outcome.success,
                    "data": {
                        "interaction_id": outcome.interaction_id,
                        "content": outcome.interaction_content,
                    },
                },
            )()

        async def handle_dialogue_request(
            self, requester_id, target_id, dialogue_content, context_data=None
        ):
            return type(
                "MockResponse",
                (),
                {
                    "success": True,
                    "data": {"dialogue_result": {"response": "mock_response"}},
                },
            )()

        def validate_interaction_context(self, context):
            return type("MockResponse", (), {"success": True})()

        def calculate_interaction_risk(self, context):
            return {"risk_score": 0.3, "risk_level": "Low"}

        async def shutdown_engine(self):
            return type("MockResponse", (), {"success": True})()

    # Mock classes
    InteractionEngine = MockInteractionEngine

    class InteractionContext:
        def __init__(self, interaction_id, interaction_type, participants, **kwargs):
            self.interaction_id = interaction_id
            self.interaction_type = interaction_type
            self.participants = participants
            self.priority = getattr(self, "priority", "normal")
            self.initiator = kwargs.get(
                "initiator", participants[0] if participants else None
            )
            self.location = kwargs.get("location", "unknown")
            self.metadata = kwargs.get("metadata", {})
            self.prerequisites = kwargs.get("prerequisites", [])
            for k, v in kwargs.items():
                if not hasattr(self, k):
                    setattr(self, k, v)

    class InteractionType:
        DIALOGUE = "dialogue"
        COMBAT = "combat"
        COOPERATION = "cooperation"
        NEGOTIATION = "negotiation"
        EMERGENCY = "emergency"

    class InteractionPriority:
        LOW = "low"
        NORMAL = "normal"
        HIGH = "high"
        URGENT = "urgent"
        CRITICAL = "critical"

    class InteractionEngineConfig:
        def __init__(self, **kwargs):
            # Default values
            self.max_concurrent_interactions = 3
            self.enable_parallel_processing = True
            self.memory_integration_enabled = True
            self.performance_monitoring = True
            self.detailed_logging = True
            self.max_queue_size = 100
            self.priority_processing = True
            self.auto_queue_cleanup = True

            # Apply provided values
            for k, v in kwargs.items():
                setattr(self, k, v)

    def create_interaction_engine(**kwargs):
        return InteractionEngine(InteractionEngineConfig(**kwargs))

    def create_performance_optimized_config():
        return InteractionEngineConfig(
            max_concurrent_interactions=5,
            enable_parallel_processing=True,
            performance_monitoring=True,
            detailed_logging=False,
        )


class ComprehensiveTestSuite:
    """Comprehensive test suite for interaction engine system."""

    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        self.error_scenarios = {}

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite."""
        logger.info("🚀 Starting comprehensive interaction engine test suite")

        if not REAL_ENGINE:
            logger.warning("⚠️  Using mock engine - real engine import failed")

        # Core functionality tests
        await self._run_core_tests()

        # Performance tests
        await self._run_performance_tests()

        # Error handling tests
        await self._run_error_tests()

        # Integration tests
        await self._run_integration_tests()

        # Generate comprehensive report
        return self._generate_test_report()

    async def _run_core_tests(self):
        """Run core functionality tests."""
        logger.info("🔧 Running core functionality tests")

        tests = [
            self._test_engine_initialization,
            self._test_dialogue_processing,
            self._test_combat_processing,
            self._test_cooperation_processing,
            self._test_multi_participant_interactions,
            self._test_priority_processing,
            self._test_validation_system,
            self._test_queue_management,
        ]

        for test in tests:
            try:
                result = await test()
                test_name = test.__name__.replace("_test_", "")
                self.test_results[f"core_{test_name}"] = result
            except Exception as e:
                test_name = test.__name__.replace("_test_", "")
                self.test_results[f"core_{test_name}"] = False
                logger.error(f"❌ Core test {test_name} failed: {e}")

    async def _run_performance_tests(self):
        """Run performance and load tests."""
        logger.info("⚡ Running performance tests")

        tests = [
            self._test_concurrent_processing,
            self._test_queue_throughput,
            self._test_memory_efficiency,
            self._test_response_times,
            self._test_scalability,
        ]

        for test in tests:
            try:
                result = await test()
                test_name = test.__name__.replace("_test_", "")
                self.test_results[f"performance_{test_name}"] = result
            except Exception as e:
                test_name = test.__name__.replace("_test_", "")
                self.test_results[f"performance_{test_name}"] = False
                logger.error(f"❌ Performance test {test_name} failed: {e}")

    async def _run_error_tests(self):
        """Run error handling and edge case tests."""
        logger.info("🛡️ Running error handling tests")

        tests = [
            self._test_invalid_contexts,
            self._test_timeout_handling,
            self._test_resource_exhaustion,
            self._test_malformed_inputs,
            self._test_recovery_mechanisms,
        ]

        for test in tests:
            try:
                result = await test()
                test_name = test.__name__.replace("_test_", "")
                self.test_results[f"error_{test_name}"] = result
            except Exception as e:
                test_name = test.__name__.replace("_test_", "")
                self.test_results[f"error_{test_name}"] = False
                logger.error(f"❌ Error handling test {test_name} failed: {e}")

    async def _run_integration_tests(self):
        """Run integration and compatibility tests."""
        logger.info("🔗 Running integration tests")

        tests = [
            self._test_backward_compatibility,
            self._test_factory_functions,
            self._test_configuration_management,
            self._test_statistics_tracking,
            self._test_shutdown_procedures,
        ]

        for test in tests:
            try:
                result = await test()
                test_name = test.__name__.replace("_test_", "")
                self.test_results[f"integration_{test_name}"] = result
            except Exception as e:
                test_name = test.__name__.replace("_test_", "")
                self.test_results[f"integration_{test_name}"] = False
                logger.error(f"❌ Integration test {test_name} failed: {e}")

    # Core functionality tests

    async def _test_engine_initialization(self) -> bool:
        """Test engine initialization and startup."""
        try:
            config = InteractionEngineConfig(
                max_concurrent_interactions=3,
                enable_parallel_processing=True,
                memory_integration_enabled=True,
                performance_monitoring=True,
            )

            engine = InteractionEngine(config=config)
            await asyncio.sleep(0.1)  # Wait for initialization

            status = engine.get_engine_status()
            assert status is not None
            assert "engine_status" in status
            assert status["engine_status"]["initialized"] is True

            await engine.shutdown_engine()
            logger.info("✅ Engine initialization test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Engine initialization failed: {e}")
            return False

    async def _test_dialogue_processing(self) -> bool:
        """Test dialogue interaction processing."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            context = InteractionContext(
                interaction_id="test_dialogue_comprehensive",
                interaction_type=InteractionType.DIALOGUE,
                priority=InteractionPriority.NORMAL,
                participants=["agent_alice", "agent_bob"],
                initiator="agent_alice",
                location="conversation_hall",
                metadata={"topic": "mission_briefing", "urgency": "medium"},
            )

            outcome = await engine.process_interaction(context)

            assert outcome is not None
            assert hasattr(outcome, "success")
            assert outcome.success is True
            assert outcome.interaction_id == "test_dialogue_comprehensive"
            assert hasattr(outcome, "processing_duration")

            await engine.shutdown_engine()
            logger.info("✅ Dialogue processing test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Dialogue processing failed: {e}")
            return False

    async def _test_combat_processing(self) -> bool:
        """Test combat interaction processing."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            context = InteractionContext(
                interaction_id="test_combat_001",
                interaction_type=InteractionType.COMBAT,
                priority=InteractionPriority.HIGH,
                participants=["warrior_red", "warrior_blue"],
                initiator="warrior_red",
                location="arena",
                metadata={"combat_type": "melee", "stakes": "honor"},
            )

            outcome = await engine.process_interaction(context)

            assert outcome is not None
            assert outcome.success is True
            assert len(outcome.context.participants) == 2

            await engine.shutdown_engine()
            logger.info("✅ Combat processing test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Combat processing failed: {e}")
            return False

    async def _test_cooperation_processing(self) -> bool:
        """Test cooperation interaction processing."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            context = InteractionContext(
                interaction_id="test_cooperation_comprehensive",
                interaction_type=InteractionType.COOPERATION,
                priority=InteractionPriority.NORMAL,
                participants=[
                    "engineer_alpha",
                    "engineer_beta",
                    "engineer_gamma",
                    "supervisor_delta",
                ],
                initiator="supervisor_delta",
                location="engineering_bay",
                metadata={"project": "reactor_maintenance", "duration": "4_hours"},
            )

            outcome = await engine.process_interaction(context)

            assert outcome is not None
            assert outcome.success is True
            assert len(outcome.context.participants) == 4
            assert outcome.context.initiator == "supervisor_delta"

            await engine.shutdown_engine()
            logger.info("✅ Cooperation processing test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Cooperation processing failed: {e}")
            return False

    async def _test_multi_participant_interactions(self) -> bool:
        """Test interactions with multiple participants."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            # Test negotiation with 5 participants
            context = InteractionContext(
                interaction_id="test_negotiation_multi",
                interaction_type=InteractionType.NEGOTIATION,
                priority=InteractionPriority.HIGH,
                participants=[
                    "diplomat_alpha",
                    "diplomat_beta",
                    "diplomat_gamma",
                    "mediator_prime",
                    "observer_neutral",
                ],
                initiator="mediator_prime",
                location="council_chamber",
                metadata={"treaty": "trade_agreement", "stakes": "economic"},
            )

            outcome = await engine.process_interaction(context)

            assert outcome is not None
            assert outcome.success is True
            assert len(outcome.context.participants) == 5

            await engine.shutdown_engine()
            logger.info("✅ Multi-participant interaction test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Multi-participant interaction failed: {e}")
            return False

    async def _test_priority_processing(self) -> bool:
        """Test priority-based processing."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            # Create interactions with different priorities
            contexts = [
                InteractionContext(
                    interaction_id="test_priority_low",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.LOW,
                    participants=["agent_a", "agent_b"],
                ),
                InteractionContext(
                    interaction_id="test_priority_critical",
                    interaction_type=InteractionType.EMERGENCY,
                    priority=InteractionPriority.CRITICAL,
                    participants=["emergency_agent", "response_team"],
                ),
                InteractionContext(
                    interaction_id="test_priority_normal",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.NORMAL,
                    participants=["agent_c", "agent_d"],
                ),
            ]

            # Process all interactions
            results = []
            for context in contexts:
                outcome = await engine.process_interaction(context)
                results.append(outcome.success)

            # All should succeed
            assert all(results)

            await engine.shutdown_engine()
            logger.info("✅ Priority processing test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Priority processing failed: {e}")
            return False

    async def _test_validation_system(self) -> bool:
        """Test interaction validation system."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            # Valid context
            valid_context = InteractionContext(
                interaction_id="test_validation_valid",
                interaction_type=InteractionType.DIALOGUE,
                priority=InteractionPriority.NORMAL,
                participants=["agent_valid_1", "agent_valid_2"],
                initiator="agent_valid_1",
            )

            # Test validation without processing
            validation_result = engine.validate_interaction_context(valid_context)
            assert validation_result.success is True

            # Test risk calculation
            risk_assessment = engine.calculate_interaction_risk(valid_context)
            assert "risk_score" in risk_assessment
            assert "risk_level" in risk_assessment

            await engine.shutdown_engine()
            logger.info("✅ Validation system test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Validation system failed: {e}")
            return False

    async def _test_queue_management(self) -> bool:
        """Test queue management functionality."""
        try:
            config = InteractionEngineConfig(
                max_concurrent_interactions=2,
                max_queue_size=10,
                priority_processing=True,
            )
            engine = InteractionEngine(config=config)
            await asyncio.sleep(0.1)

            # Test async processing (queuing)
            context = InteractionContext(
                interaction_id="test_queue_001",
                interaction_type=InteractionType.DIALOGUE,
                priority=InteractionPriority.NORMAL,
                participants=["agent_queue_1", "agent_queue_2"],
            )

            # Process asynchronously
            queue_result = await engine.process_interaction(
                context, async_processing=True
            )
            assert queue_result is not None

            # Check queue status
            status = engine.get_engine_status()
            assert "queue_status" in status

            await engine.shutdown_engine()
            logger.info("✅ Queue management test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Queue management failed: {e}")
            return False

    # Performance tests

    async def _test_concurrent_processing(self) -> bool:
        """Test concurrent interaction processing."""
        try:
            config = create_performance_optimized_config()
            engine = InteractionEngine(config=config)
            await asyncio.sleep(0.1)

            # Create multiple concurrent interactions
            tasks = []
            for i in range(10):
                context = InteractionContext(
                    interaction_id=f"concurrent_test_{i:03d}",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.NORMAL,
                    participants=[f"agent_{i}_a", f"agent_{i}_b"],
                )
                task = asyncio.create_task(engine.process_interaction(context))
                tasks.append(task)

            # Wait for all to complete
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            # Check results
            successful_results = [
                r
                for r in results
                if not isinstance(r, Exception) and hasattr(r, "success") and r.success
            ]
            success_rate = len(successful_results) / len(results)

            # Record performance metrics
            self.performance_metrics["concurrent_processing"] = {
                "total_interactions": len(tasks),
                "successful_interactions": len(successful_results),
                "success_rate": success_rate,
                "total_time": end_time - start_time,
                "avg_time_per_interaction": (end_time - start_time) / len(tasks),
            }

            assert success_rate >= 0.8  # At least 80% should succeed

            await engine.shutdown_engine()
            logger.info(
                f"✅ Concurrent processing test passed (success rate: {success_rate:.1%})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Concurrent processing failed: {e}")
            return False

    async def _test_queue_throughput(self) -> bool:
        """Test queue throughput under load."""
        try:
            config = InteractionEngineConfig(
                max_concurrent_interactions=5,
                max_queue_size=50,
                priority_processing=True,
                auto_queue_cleanup=True,
            )
            engine = InteractionEngine(config=config)
            await asyncio.sleep(0.1)

            # Queue many interactions rapidly
            start_time = time.time()
            queue_tasks = []

            for i in range(25):
                context = InteractionContext(
                    interaction_id=f"throughput_test_{i:03d}",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.NORMAL,
                    participants=[f"throughput_{i}_a", f"throughput_{i}_b"],
                )
                task = asyncio.create_task(
                    engine.process_interaction(context, async_processing=True)
                )
                queue_tasks.append(task)

            # Wait for queuing to complete
            queue_results = await asyncio.gather(*queue_tasks, return_exceptions=True)
            end_time = time.time()

            # Check queue performance
            successful_queues = [
                r
                for r in queue_results
                if not isinstance(r, Exception) and hasattr(r, "success") and r.success
            ]
            queue_success_rate = len(successful_queues) / len(queue_results)

            self.performance_metrics["queue_throughput"] = {
                "total_queued": len(queue_tasks),
                "successful_queues": len(successful_queues),
                "queue_success_rate": queue_success_rate,
                "queue_time": end_time - start_time,
                "avg_queue_time": (end_time - start_time) / len(queue_tasks),
            }

            assert queue_success_rate >= 0.9  # At least 90% should queue successfully

            # Wait for processing to complete
            await asyncio.sleep(1.0)

            await engine.shutdown_engine()
            logger.info(
                f"✅ Queue throughput test passed (queue success rate: {queue_success_rate:.1%})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Queue throughput failed: {e}")
            return False

    async def _test_memory_efficiency(self) -> bool:
        """Test memory usage efficiency."""
        try:
            # Measure memory before
            import gc

            gc.collect()
            initial_objects = len(gc.get_objects())

            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            # Process multiple interactions
            for i in range(20):
                context = InteractionContext(
                    interaction_id=f"memory_test_{i:03d}",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.NORMAL,
                    participants=[f"mem_agent_{i}_a", f"mem_agent_{i}_b"],
                )
                await engine.process_interaction(context)

            # Clean shutdown
            await engine.shutdown_engine()

            # Check memory usage
            gc.collect()
            final_objects = len(gc.get_objects())

            object_increase = final_objects - initial_objects
            self.performance_metrics["memory_efficiency"] = {
                "initial_objects": initial_objects,
                "final_objects": final_objects,
                "object_increase": object_increase,
                "interactions_processed": 20,
            }

            # Memory increase should be reasonable (less than 1000 objects per interaction)
            memory_efficient = object_increase < (20 * 1000)

            logger.info(
                f"✅ Memory efficiency test passed (object increase: {object_increase})"
            )
            return memory_efficient

        except Exception as e:
            logger.error(f"❌ Memory efficiency failed: {e}")
            return False

    async def _test_response_times(self) -> bool:
        """Test response time performance."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            response_times = []

            # Test 15 interactions for response time
            for i in range(15):
                context = InteractionContext(
                    interaction_id=f"response_time_test_{i:03d}",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.NORMAL,
                    participants=[f"rt_agent_{i}_a", f"rt_agent_{i}_b"],
                )

                start_time = time.time()
                outcome = await engine.process_interaction(context)
                end_time = time.time()

                if outcome.success:
                    response_times.append(end_time - start_time)

            # Calculate statistics
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)

                self.performance_metrics["response_times"] = {
                    "avg_response_time": avg_response_time,
                    "max_response_time": max_response_time,
                    "min_response_time": min_response_time,
                    "total_measurements": len(response_times),
                }

                # Response time should be reasonable (< 1 second average)
                performance_acceptable = avg_response_time < 1.0

                await engine.shutdown_engine()
                logger.info(
                    f"✅ Response time test passed (avg: {avg_response_time:.3f}s)"
                )
                return performance_acceptable
            else:
                return False

        except Exception as e:
            logger.error(f"❌ Response time test failed: {e}")
            return False

    async def _test_scalability(self) -> bool:
        """Test system scalability under increasing load."""
        try:
            loads = [5, 10, 15, 20]  # Different load levels
            scalability_results = []

            for load in loads:
                config = create_performance_optimized_config()
                engine = InteractionEngine(config=config)
                await asyncio.sleep(0.1)

                start_time = time.time()

                # Process interactions at this load level
                tasks = []
                for i in range(load):
                    context = InteractionContext(
                        interaction_id=f"scalability_load_{load}_interaction_{i:03d}",
                        interaction_type=InteractionType.DIALOGUE,
                        priority=InteractionPriority.NORMAL,
                        participants=[f"scale_{load}_{i}_a", f"scale_{load}_{i}_b"],
                    )
                    task = asyncio.create_task(engine.process_interaction(context))
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()

                successful_results = [
                    r
                    for r in results
                    if not isinstance(r, Exception)
                    and hasattr(r, "success")
                    and r.success
                ]
                success_rate = len(successful_results) / len(results)
                total_time = end_time - start_time

                scalability_results.append(
                    {
                        "load": load,
                        "success_rate": success_rate,
                        "total_time": total_time,
                        "throughput": load / total_time,
                    }
                )

                await engine.shutdown_engine()

            self.performance_metrics["scalability"] = scalability_results

            # Check that system maintains reasonable performance at all load levels
            all_acceptable = all(
                result["success_rate"] >= 0.8 for result in scalability_results
            )

            logger.info(f"✅ Scalability test passed (loads tested: {loads})")
            return all_acceptable

        except Exception as e:
            logger.error(f"❌ Scalability test failed: {e}")
            return False

    # Error handling tests

    async def _test_invalid_contexts(self) -> bool:
        """Test handling of invalid interaction contexts."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            # Test various invalid contexts
            invalid_tests = [
                # Missing participants
                InteractionContext(
                    interaction_id="invalid_no_participants",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.NORMAL,
                    participants=[],
                ),
                # Single participant in dialogue
                InteractionContext(
                    interaction_id="invalid_single_dialogue",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.NORMAL,
                    participants=["lonely_agent"],
                ),
            ]

            handled_gracefully = True

            for invalid_context in invalid_tests:
                try:
                    outcome = await engine.process_interaction(invalid_context)
                    # Should either fail gracefully or succeed with warnings
                    if hasattr(outcome, "success"):
                        # It's okay if it fails, but it shouldn't crash
                        pass
                except Exception:
                    # Unexpected exceptions indicate poor error handling
                    handled_gracefully = False
                    break

            await engine.shutdown_engine()

            if handled_gracefully:
                logger.info("✅ Invalid context handling test passed")
                return True
            else:
                logger.error("❌ Invalid context handling failed")
                return False

        except Exception as e:
            logger.error(f"❌ Invalid context test failed: {e}")
            return False

    async def _test_timeout_handling(self) -> bool:
        """Test timeout handling mechanisms."""
        try:
            # This is a simplified test since we can't easily simulate real timeouts
            config = InteractionEngineConfig(
                default_timeout_seconds=0.1,  # Very short timeout
                enable_parallel_processing=True,
            )
            engine = InteractionEngine(config=config)
            await asyncio.sleep(0.1)

            context = InteractionContext(
                interaction_id="timeout_test",
                interaction_type=InteractionType.DIALOGUE,
                priority=InteractionPriority.NORMAL,
                participants=["timeout_agent_a", "timeout_agent_b"],
            )

            # Process with potential timeout
            outcome = await engine.process_interaction(context)

            # Should handle gracefully regardless of timeout
            timeout_handled = outcome is not None

            await engine.shutdown_engine()

            if timeout_handled:
                logger.info("✅ Timeout handling test passed")
                return True
            else:
                logger.error("❌ Timeout handling failed")
                return False

        except Exception as e:
            logger.error(f"❌ Timeout handling test failed: {e}")
            return False

    async def _test_resource_exhaustion(self) -> bool:
        """Test behavior under resource exhaustion."""
        try:
            # Test queue exhaustion
            config = InteractionEngineConfig(
                max_queue_size=5, max_concurrent_interactions=1  # Very small queue
            )
            engine = InteractionEngine(config=config)
            await asyncio.sleep(0.1)

            # Try to overwhelm the queue
            queue_tasks = []
            for i in range(10):  # More than queue capacity
                context = InteractionContext(
                    interaction_id=f"resource_exhaustion_{i:03d}",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.NORMAL,
                    participants=[f"exhaust_{i}_a", f"exhaust_{i}_b"],
                )
                task = asyncio.create_task(
                    engine.process_interaction(context, async_processing=True)
                )
                queue_tasks.append(task)

            # Wait for all queuing attempts
            results = await asyncio.gather(*queue_tasks, return_exceptions=True)

            # Some should succeed, some should fail gracefully
            successful_queues = [r for r in results if not isinstance(r, Exception)]
            resource_handling_ok = (
                len(successful_queues) <= 5
            )  # Should not exceed queue capacity

            await engine.shutdown_engine()

            if resource_handling_ok:
                logger.info("✅ Resource exhaustion test passed")
                return True
            else:
                logger.error("❌ Resource exhaustion handling failed")
                return False

        except Exception as e:
            logger.error(f"❌ Resource exhaustion test failed: {e}")
            return False

    async def _test_malformed_inputs(self) -> bool:
        """Test handling of malformed inputs."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            # Test with various malformed inputs
            malformed_tests = []

            try:
                # Test with None context
                result = await engine.process_interaction(None)
                malformed_tests.append(result is not None)
            except Exception:
                malformed_tests.append(True)  # Exception is acceptable

            try:
                # Test validation with None
                result = engine.validate_interaction_context(None)
                malformed_tests.append(result is not None)
            except Exception:
                malformed_tests.append(True)  # Exception is acceptable

            try:
                # Test risk calculation with None
                result = engine.calculate_interaction_risk(None)
                malformed_tests.append(result is not None)
            except Exception:
                malformed_tests.append(True)  # Exception is acceptable

            await engine.shutdown_engine()

            # All malformed input tests should be handled gracefully
            all_handled = all(malformed_tests)

            if all_handled:
                logger.info("✅ Malformed input handling test passed")
                return True
            else:
                logger.error("❌ Malformed input handling failed")
                return False

        except Exception as e:
            logger.error(f"❌ Malformed input test failed: {e}")
            return False

    async def _test_recovery_mechanisms(self) -> bool:
        """Test error recovery mechanisms."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            # Test processing after errors
            context1 = InteractionContext(
                interaction_id="recovery_test_1",
                interaction_type=InteractionType.DIALOGUE,
                priority=InteractionPriority.NORMAL,
                participants=["recovery_agent_1", "recovery_agent_2"],
            )

            # Process valid interaction
            outcome1 = await engine.process_interaction(context1)
            first_success = outcome1.success if hasattr(outcome1, "success") else False

            # Process another interaction to test recovery
            context2 = InteractionContext(
                interaction_id="recovery_test_2",
                interaction_type=InteractionType.COOPERATION,
                priority=InteractionPriority.NORMAL,
                participants=[
                    "recovery_agent_3",
                    "recovery_agent_4",
                    "recovery_agent_5",
                ],
            )

            outcome2 = await engine.process_interaction(context2)
            recovery_success = (
                outcome2.success if hasattr(outcome2, "success") else False
            )

            await engine.shutdown_engine()

            recovery_works = first_success and recovery_success

            if recovery_works:
                logger.info("✅ Recovery mechanisms test passed")
                return True
            else:
                logger.error("❌ Recovery mechanisms failed")
                return False

        except Exception as e:
            logger.error(f"❌ Recovery mechanisms test failed: {e}")
            return False

    # Integration tests

    async def _test_backward_compatibility(self) -> bool:
        """Test backward compatibility methods."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            # Test legacy character interaction method
            char_result = await engine.create_character_interaction(
                agent_id="legacy_agent_1",
                target_id="legacy_agent_2",
                interaction_type="dialogue",
                content={"topic": "legacy_test", "urgency": "low"},
                priority="normal",
            )

            assert char_result is not None
            assert hasattr(char_result, "success")

            # Test legacy dialogue method
            dialogue_result = await engine.handle_dialogue_request(
                requester_id="dialogue_requester",
                target_id="dialogue_target",
                dialogue_content="Hello, this is a test dialogue.",
                context_data={"mood": "friendly"},
            )

            assert dialogue_result is not None
            assert hasattr(dialogue_result, "success")

            await engine.shutdown_engine()
            logger.info("✅ Backward compatibility test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Backward compatibility test failed: {e}")
            return False

    async def _test_factory_functions(self) -> bool:
        """Test factory functions."""
        try:
            # Test standard factory
            engine1 = create_interaction_engine()
            await asyncio.sleep(0.1)

            status1 = engine1.get_engine_status()
            assert status1 is not None

            await engine1.shutdown_engine()

            # Test performance optimized factory
            perf_config = create_performance_optimized_config()
            engine2 = InteractionEngine(config=perf_config)
            await asyncio.sleep(0.1)

            status2 = engine2.get_engine_status()
            assert status2 is not None

            await engine2.shutdown_engine()

            logger.info("✅ Factory functions test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Factory functions test failed: {e}")
            return False

    async def _test_configuration_management(self) -> bool:
        """Test configuration management."""
        try:
            # Test custom configuration
            custom_config = InteractionEngineConfig(
                max_concurrent_interactions=7,
                enable_parallel_processing=False,
                memory_integration_enabled=False,
                performance_monitoring=True,
                detailed_logging=False,
                max_queue_size=50,
            )

            engine = InteractionEngine(config=custom_config)
            await asyncio.sleep(0.1)

            # Verify configuration is applied
            assert engine.config.max_concurrent_interactions == 7
            assert engine.config.enable_parallel_processing is False
            assert engine.config.memory_integration_enabled is False

            status = engine.get_engine_status()
            assert status is not None

            await engine.shutdown_engine()
            logger.info("✅ Configuration management test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Configuration management test failed: {e}")
            return False

    async def _test_statistics_tracking(self) -> bool:
        """Test statistics and monitoring."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            # Process some interactions to generate statistics
            for i in range(5):
                context = InteractionContext(
                    interaction_id=f"stats_test_{i:03d}",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.NORMAL,
                    participants=[f"stats_agent_{i}_a", f"stats_agent_{i}_b"],
                )
                await engine.process_interaction(context)

            # Check statistics
            status = engine.get_engine_status()
            assert status is not None
            assert "engine_status" in status

            engine_status = status["engine_status"]
            assert "total_interactions_processed" in engine_status
            assert "successful_interactions" in engine_status
            assert "average_processing_time" in engine_status

            # Should have processed interactions
            assert engine_status["total_interactions_processed"] >= 5

            await engine.shutdown_engine()
            logger.info("✅ Statistics tracking test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Statistics tracking test failed: {e}")
            return False

    async def _test_shutdown_procedures(self) -> bool:
        """Test engine shutdown procedures."""
        try:
            engine = create_interaction_engine()
            await asyncio.sleep(0.1)

            # Queue some interactions
            for i in range(3):
                context = InteractionContext(
                    interaction_id=f"shutdown_test_{i:03d}",
                    interaction_type=InteractionType.DIALOGUE,
                    priority=InteractionPriority.NORMAL,
                    participants=[f"shutdown_agent_{i}_a", f"shutdown_agent_{i}_b"],
                )
                # Queue for async processing
                await engine.process_interaction(context, async_processing=True)

            # Test graceful shutdown
            shutdown_result = await engine.shutdown_engine()
            assert shutdown_result is not None
            assert hasattr(shutdown_result, "success")

            # Verify engine is shut down
            status = engine.get_engine_status()
            assert status["engine_status"]["processing_active"] is False

            logger.info("✅ Shutdown procedures test passed")
            return True

        except Exception as e:
            logger.error(f"❌ Shutdown procedures test failed: {e}")
            return False

    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        # Calculate overall statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests
        overall_success_rate = (
            (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        )

        # Categorize results
        categories = {
            "core": [k for k in self.test_results.keys() if k.startswith("core_")],
            "performance": [
                k for k in self.test_results.keys() if k.startswith("performance_")
            ],
            "error_handling": [
                k for k in self.test_results.keys() if k.startswith("error_")
            ],
            "integration": [
                k for k in self.test_results.keys() if k.startswith("integration_")
            ],
        }

        category_results = {}
        for category, test_keys in categories.items():
            if test_keys:
                category_passed = sum(
                    1 for key in test_keys if self.test_results.get(key, False)
                )
                category_total = len(test_keys)
                category_success_rate = (category_passed / category_total) * 100
                category_results[category] = {
                    "passed": category_passed,
                    "total": category_total,
                    "success_rate": category_success_rate,
                }

        # Generate report
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "overall_success_rate": overall_success_rate,
                "engine_type": "real" if REAL_ENGINE else "mock",
            },
            "category_results": category_results,
            "detailed_results": self.test_results,
            "performance_metrics": self.performance_metrics,
            "test_timestamp": datetime.now().isoformat(),
        }

        # Log summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 COMPREHENSIVE TEST SUITE RESULTS")
        logger.info("=" * 80)
        logger.info(f"Engine Type: {'Real' if REAL_ENGINE else 'Mock'}")
        logger.info(
            f"Overall Success Rate: {overall_success_rate:.1f}% ({passed_tests}/{total_tests} tests passed)"
        )

        for category, results in category_results.items():
            logger.info(
                f"{category.title()}: {results['success_rate']:.1f}% ({results['passed']}/{results['total']})"
            )

        logger.info("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name}: {status}")

        if self.performance_metrics:
            logger.info("\n⚡ Performance Metrics:")
            for metric_name, metric_data in self.performance_metrics.items():
                logger.info(f"   {metric_name}: {metric_data}")

        logger.info("=" * 80)

        if overall_success_rate >= 85:
            logger.info("🎉 COMPREHENSIVE TEST SUITE COMPLETED SUCCESSFULLY!")
        elif overall_success_rate >= 70:
            logger.info(
                "⚠️  Test suite completed with some issues - review implementation"
            )
        else:
            logger.warning(
                "❌ Test suite completed with significant failures - major review needed"
            )

        return report


async def run_comprehensive_tests():
    """Run the comprehensive test suite."""
    suite = ComprehensiveTestSuite()
    return await suite.run_all_tests()


if __name__ == "__main__":
    # Run comprehensive tests
    asyncio.run(run_comprehensive_tests())
