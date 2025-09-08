#!/usr/bin/env python3
"""
Focused Performance Validation Test for Novel Engine Optimizations

This test validates the performance improvements of the three key optimized components:
1. OptimizedCharacterFactory - Character creation performance
2. HighPerformanceConcurrentProcessor - Concurrent processing performance
3. Performance-optimized caching and resource management

Target Validations:
- Character creation: 200ms → <10ms (95%+ improvement)
- Concurrent processing: 0 successful → 200+ concurrent tasks
- Memory efficiency: Optimized allocation patterns
- Cache performance: High hit rates and fast lookups
"""

import asyncio
import json
import logging
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List

import psutil

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import optimized components
try:
    from high_performance_concurrent_processor import HighPerformanceConcurrentProcessor
    from optimized_character_factory import OptimizedCharacterFactory

    COMPONENTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Optimized components not available: {e}")
    COMPONENTS_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ComponentTestResult:
    """Results from individual component performance test."""

    component_name: str
    target_metric: str
    target_value: float
    actual_value: float
    improvement_percent: float
    passed: bool
    notes: str = ""
    performance_stats: Dict[str, Any] = None


class PerformanceValidator:
    """Focused performance validation for optimized components."""

    def __init__(self):
        self.results = []
        self.baseline_memory = self._get_memory_usage()

    async def run_validation(self) -> Dict[str, Any]:
        """Run all component performance validations."""
        logger.info("Starting focused performance validation...")

        if not COMPONENTS_AVAILABLE:
            logger.error("Optimized components not available - cannot run validation")
            return {"error": "Components not available"}

        # Test each optimized component
        character_factory_result = await self._test_character_factory()
        concurrent_processor_result = await self._test_concurrent_processor()
        cache_performance_result = await self._test_cache_performance()
        memory_efficiency_result = await self._test_memory_efficiency()

        # Compile results
        all_results = [
            character_factory_result,
            concurrent_processor_result,
            cache_performance_result,
            memory_efficiency_result,
        ]

        # Calculate overall metrics
        passed_tests = sum(1 for result in all_results if result.passed)
        success_rate = (passed_tests / len(all_results)) * 100

        overall_result = {
            "timestamp": datetime.now().isoformat(),
            "validation_status": (
                "PASSED" if passed_tests == len(all_results) else "PARTIAL"
            ),
            "success_rate": success_rate,
            "tests_passed": passed_tests,
            "tests_total": len(all_results),
            "component_results": [asdict(result) for result in all_results],
            "summary": self._generate_summary(all_results),
        }

        return overall_result

    async def _test_character_factory(self) -> ComponentTestResult:
        """Test optimized character factory performance."""
        logger.info("Testing OptimizedCharacterFactory performance...")

        try:
            factory = OptimizedCharacterFactory()
            creation_times = []

            # Warm up phase
            logger.info("Warming up character factory cache...")
            await factory.create_character_async("warmup_character_1")
            await factory.create_character_async("warmup_character_2")

            # Performance test phase
            logger.info("Running character creation performance test...")
            test_characters = 50

            for i in range(test_characters):
                start_time = time.time()
                try:
                    await factory.create_character_async(f"perf_test_char_{i}")
                    creation_time = (
                        time.time() - start_time
                    ) * 1000  # Convert to milliseconds
                    creation_times.append(creation_time)
                except Exception as e:
                    logger.warning(f"Character creation failed for char_{i}: {e}")

            # Calculate performance metrics
            if creation_times:
                avg_time = statistics.mean(creation_times)
                min_time = min(creation_times)
                max_time = max(creation_times)
                median_time = statistics.median(creation_times)

                # Get factory performance stats
                stats = factory.get_performance_stats()

                # Cleanup
                factory.shutdown()

                # Performance targets
                target_time = 10.0  # <10ms per character
                baseline_time = 200.0  # Original baseline from requirements

                improvement = ((baseline_time - avg_time) / baseline_time) * 100
                passed = avg_time < target_time

                return ComponentTestResult(
                    component_name="OptimizedCharacterFactory",
                    target_metric="Character Creation Time (ms)",
                    target_value=target_time,
                    actual_value=avg_time,
                    improvement_percent=improvement,
                    passed=passed,
                    notes=f"Min: {min_time:.1f}ms, Max: {max_time:.1f}ms, Median: {median_time:.1f}ms, Cache hit rate: {stats['cache_performance']['hit_rate']:.1%}",
                    performance_stats=stats,
                )
            else:
                factory.shutdown()
                return ComponentTestResult(
                    component_name="OptimizedCharacterFactory",
                    target_metric="Character Creation Time (ms)",
                    target_value=10.0,
                    actual_value=9999,
                    improvement_percent=0,
                    passed=False,
                    notes="No successful character creations",
                )

        except Exception as e:
            logger.error(f"Character factory test failed: {e}")
            return ComponentTestResult(
                component_name="OptimizedCharacterFactory",
                target_metric="Character Creation Time (ms)",
                target_value=10.0,
                actual_value=9999,
                improvement_percent=0,
                passed=False,
                notes=f"Test failed: {e}",
            )

    async def _test_concurrent_processor(self) -> ComponentTestResult:
        """Test high-performance concurrent processor."""
        logger.info("Testing HighPerformanceConcurrentProcessor performance...")

        try:
            processor = HighPerformanceConcurrentProcessor()
            await processor.start()

            try:
                # Define test workload
                def cpu_intensive_task(task_id: int) -> str:
                    """Simulate CPU-intensive work."""
                    # Simulate computation
                    result = 0
                    for i in range(1000):
                        result += i * task_id
                    time.sleep(0.01)  # Simulate I/O
                    return f"Task {task_id} result: {result}"

                # Test concurrent task processing
                logger.info("Submitting concurrent tasks...")
                task_count = 200  # Target: 200+ concurrent tasks

                start_time = time.time()

                # Submit all tasks
                task_ids = []
                for i in range(task_count):
                    task_id = await processor.submit_task(
                        cpu_intensive_task, i, priority=1, timeout=30.0
                    )
                    task_ids.append(task_id)

                # Wait for all tasks to complete
                logger.info(f"Waiting for {task_count} tasks to complete...")
                results = await processor.wait_for_batch(task_ids, timeout=60.0)

                total_time = time.time() - start_time

                # Analyze results
                successful_tasks = sum(
                    1 for result in results if not isinstance(result, Exception)
                )
                failed_tasks = task_count - successful_tasks

                tasks_per_second = successful_tasks / total_time

                # Get processor performance stats
                stats = processor.get_performance_stats()

                # Performance targets
                target_concurrent = 200  # 200+ concurrent tasks
                success_rate = (successful_tasks / task_count) * 100

                passed = successful_tasks >= target_concurrent and success_rate >= 95

                return ComponentTestResult(
                    component_name="HighPerformanceConcurrentProcessor",
                    target_metric="Concurrent Tasks Processed",
                    target_value=target_concurrent,
                    actual_value=successful_tasks,
                    improvement_percent=success_rate,
                    passed=passed,
                    notes=f"Throughput: {tasks_per_second:.1f} tasks/s, Success rate: {success_rate:.1f}%, Failed: {failed_tasks}, Peak concurrent: {stats['task_stats']['concurrent_peak']}",
                    performance_stats=stats,
                )

            finally:
                await processor.stop()

        except Exception as e:
            logger.error(f"Concurrent processor test failed: {e}")
            return ComponentTestResult(
                component_name="HighPerformanceConcurrentProcessor",
                target_metric="Concurrent Tasks Processed",
                target_value=200,
                actual_value=0,
                improvement_percent=0,
                passed=False,
                notes=f"Test failed: {e}",
            )

    async def _test_cache_performance(self) -> ComponentTestResult:
        """Test caching system performance."""
        logger.info("Testing cache performance...")

        try:
            # Import cache system from optimized server
            from performance_optimized_api_server import HighPerformanceCache

            cache = HighPerformanceCache(l1_size=256, l2_size=512)

            # Test cache operations
            cache_operations = 1000

            # Fill cache with test data
            logger.info("Filling cache with test data...")
            for i in range(cache_operations):
                await cache.set(f"test_key_{i}", f"test_value_{i}")

            # Test cache read performance
            logger.info("Testing cache read performance...")
            read_times = []
            hits = 0

            for i in range(cache_operations):
                start_time = time.time()
                value = await cache.get(f"test_key_{i}")
                read_time = (
                    time.time() - start_time
                ) * 1000000  # Convert to microseconds
                read_times.append(read_time)

                if value is not None:
                    hits += 1

            # Calculate metrics
            avg_read_time = statistics.mean(read_times)
            hit_rate = cache.get_hit_rate()

            # Performance targets
            target_hit_rate = 0.8  # 80% hit rate
            target_read_time = 100.0  # <100 microseconds per read

            passed = hit_rate >= target_hit_rate and avg_read_time < target_read_time

            return ComponentTestResult(
                component_name="HighPerformanceCache",
                target_metric="Cache Hit Rate",
                target_value=target_hit_rate,
                actual_value=hit_rate,
                improvement_percent=hit_rate * 100,
                passed=passed,
                notes=f"Avg read time: {avg_read_time:.1f}μs, L1 size: {len(cache.l1_cache)}, L2 size: {len(cache.l2_cache)}",
            )

        except Exception as e:
            logger.error(f"Cache performance test failed: {e}")
            return ComponentTestResult(
                component_name="HighPerformanceCache",
                target_metric="Cache Hit Rate",
                target_value=0.8,
                actual_value=0,
                improvement_percent=0,
                passed=False,
                notes=f"Test failed: {e}",
            )

    async def _test_memory_efficiency(self) -> ComponentTestResult:
        """Test memory efficiency improvements."""
        logger.info("Testing memory efficiency...")

        try:
            memory_before = self._get_memory_usage()

            # Create multiple optimized components to test memory usage
            factories = []
            processors = []

            # Create and use multiple instances
            for i in range(5):
                factory = OptimizedCharacterFactory()
                processor = HighPerformanceConcurrentProcessor()

                # Use the components
                await factory.create_character_async(f"memory_test_char_{i}")
                await processor.start()

                factories.append(factory)
                processors.append(processor)

            memory_peak = self._get_memory_usage()

            # Cleanup all instances
            for factory in factories:
                factory.shutdown()

            for processor in processors:
                await processor.stop()

            # Force garbage collection
            import gc

            gc.collect()

            # Wait for cleanup
            await asyncio.sleep(2)

            memory_after = self._get_memory_usage()

            # Calculate memory metrics
            memory_increase = memory_peak - memory_before
            memory_efficiency = ((memory_peak - memory_after) / memory_peak) * 100
            memory_increase_percent = (memory_increase / memory_before) * 100

            # Performance targets
            target_memory_increase = 50.0  # <50% memory increase during load
            target_cleanup_efficiency = 80.0  # >80% memory recovery after cleanup

            passed = (
                memory_increase_percent < target_memory_increase
                and memory_efficiency > target_cleanup_efficiency
            )

            return ComponentTestResult(
                component_name="MemoryEfficiency",
                target_metric="Memory Increase (%)",
                target_value=target_memory_increase,
                actual_value=memory_increase_percent,
                improvement_percent=memory_efficiency,
                passed=passed,
                notes=f"Before: {memory_before:.1f}MB, Peak: {memory_peak:.1f}MB, After: {memory_after:.1f}MB, Cleanup: {memory_efficiency:.1f}%",
            )

        except Exception as e:
            logger.error(f"Memory efficiency test failed: {e}")
            return ComponentTestResult(
                component_name="MemoryEfficiency",
                target_metric="Memory Increase (%)",
                target_value=50.0,
                actual_value=100,
                improvement_percent=0,
                passed=False,
                notes=f"Test failed: {e}",
            )

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def _generate_summary(self, results: List[ComponentTestResult]) -> Dict[str, Any]:
        """Generate test summary with performance insights."""
        passed_tests = sum(1 for result in results if result.passed)

        performance_summary = {}
        for result in results:
            performance_summary[result.component_name] = {
                "status": "PASSED" if result.passed else "FAILED",
                "target": result.target_value,
                "actual": result.actual_value,
                "improvement": result.improvement_percent,
                "metric": result.target_metric,
            }

        return {
            "performance_components": performance_summary,
            "overall_assessment": (
                "PASSED" if passed_tests == len(results) else "NEEDS_IMPROVEMENT"
            ),
            "key_achievements": self._get_key_achievements(results),
            "recommendations": self._get_recommendations(results),
        }

    def _get_key_achievements(self, results: List[ComponentTestResult]) -> List[str]:
        """Extract key performance achievements."""
        achievements = []

        for result in results:
            if result.passed and result.improvement_percent > 0:
                if "Character" in result.component_name:
                    achievements.append(
                        f"Character creation optimized: {result.improvement_percent:.1f}% improvement"
                    )
                elif "Concurrent" in result.component_name:
                    achievements.append(
                        f"Concurrent processing: {result.actual_value:.0f} tasks processed successfully"
                    )
                elif "Cache" in result.component_name:
                    achievements.append(
                        f"Cache performance: {result.actual_value:.1%} hit rate achieved"
                    )
                elif "Memory" in result.component_name:
                    achievements.append(
                        f"Memory efficiency: {result.improvement_percent:.1f}% cleanup efficiency"
                    )

        return achievements

    def _get_recommendations(self, results: List[ComponentTestResult]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        for result in results:
            if not result.passed:
                if "Character" in result.component_name:
                    recommendations.append(
                        "Consider further character factory optimization: async I/O, larger caches, or object pooling improvements"
                    )
                elif "Concurrent" in result.component_name:
                    recommendations.append(
                        "Improve concurrent processing: increase worker pools, optimize task scheduling, or add load balancing"
                    )
                elif "Cache" in result.component_name:
                    recommendations.append(
                        "Enhance caching: increase cache sizes, improve eviction policies, or add cache warming"
                    )
                elif "Memory" in result.component_name:
                    recommendations.append(
                        "Optimize memory usage: better object pooling, garbage collection tuning, or resource cleanup"
                    )

        if not recommendations:
            recommendations.append(
                "All performance targets achieved! Consider implementing continuous performance monitoring"
            )

        return recommendations


async def main():
    """Run focused performance validation."""
    print("=" * 80)
    print("Novel Engine - Focused Performance Component Validation")
    print("=" * 80)

    if not COMPONENTS_AVAILABLE:
        print("❌ ERROR: Optimized components not available for testing")
        print("Please ensure the optimized components are properly installed")
        return

    validator = PerformanceValidator()

    try:
        results = await validator.run_validation()

        if "error" in results:
            print(f"❌ Validation failed: {results['error']}")
            return

        # Display results
        print(f"\n📊 VALIDATION RESULTS - {results['timestamp']}")
        print("=" * 80)

        status_icon = "✅" if results["validation_status"] == "PASSED" else "⚠️"
        print(f"{status_icon} OVERALL STATUS: {results['validation_status']}")
        print(
            f"📈 Success Rate: {results['success_rate']:.1f}% ({results['tests_passed']}/{results['tests_total']} components)"
        )

        print("\n🧪 COMPONENT TEST RESULTS:")
        print("-" * 80)

        for result_data in results["component_results"]:
            status = "✅ PASS" if result_data["passed"] else "❌ FAIL"
            component = result_data["component_name"]
            target = result_data["target_value"]
            actual = result_data["actual_value"]
            improvement = result_data["improvement_percent"]

            print(
                f"{component:25} | {status} | Target: {target:8.1f} | Actual: {actual:8.1f} | Improvement: {improvement:6.1f}%"
            )
            if result_data["notes"]:
                print(f"{'':27} | Notes: {result_data['notes']}")

        # Key achievements
        if results["summary"]["key_achievements"]:
            print("\n🎯 KEY ACHIEVEMENTS:")
            print("-" * 40)
            for i, achievement in enumerate(results["summary"]["key_achievements"], 1):
                print(f"{i}. {achievement}")

        # Recommendations
        if results["summary"]["recommendations"]:
            print("\n💡 RECOMMENDATIONS:")
            print("-" * 40)
            for i, rec in enumerate(results["summary"]["recommendations"], 1):
                print(f"{i}. {rec}")

        # Save detailed results
        results_file = (
            f"performance_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n💾 Detailed results saved to: {results_file}")

        # Final status
        print("=" * 80)
        if results["validation_status"] == "PASSED":
            print("🎉 PERFORMANCE OPTIMIZATION SUCCESS!")
            print("All optimized components are performing within target parameters.")
            print(
                "The Novel Engine performance implementation gaps have been successfully bridged!"
            )
        else:
            print("⚠️  PERFORMANCE OPTIMIZATION PARTIAL SUCCESS")
            print(
                "Some components need further optimization. Review recommendations above."
            )
        print("=" * 80)

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        print(f"❌ Validation failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
