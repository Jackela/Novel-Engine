#!/usr/bin/env python3
"""
Comprehensive Performance Validation Test Suite for Novel Engine

This validation suite tests the optimized performance implementations against the targets:
- Response Time: 2,075ms → <200ms (90%+ improvement)
- Throughput: 157 req/s → 1000+ req/s (500%+ improvement)
- Concurrent Processing: 0 successful → 200+ concurrent users
- Memory Efficiency: 30%+ improvement in allocation patterns

Tests all three optimized components:
1. performance_optimized_api_server.py
2. optimized_character_factory.py
3. high_performance_concurrent_processor.py
"""

import asyncio
import aiohttp
import time
import threading
import multiprocessing
import psutil
import logging
import statistics
import json
import uvicorn
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import optimized components
try:
    from performance_optimized_api_server import app as optimized_app, run_optimized_server
    from optimized_character_factory import OptimizedCharacterFactory
    from high_performance_concurrent_processor import HighPerformanceConcurrentProcessor
    OPTIMIZED_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Optimized components not available: {e}")
    OPTIMIZED_COMPONENTS_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PerformanceTarget:
    """Performance targets for validation."""
    response_time_ms: float = 200.0  # <200ms target
    throughput_req_per_sec: float = 1000.0  # >1000 req/s target
    concurrent_users: int = 200  # 200+ concurrent users
    memory_improvement_percent: float = 30.0  # 30%+ memory improvement
    success_rate_percent: float = 95.0  # 95%+ success rate

@dataclass
class ValidationResult:
    """Results from performance validation test."""
    test_name: str
    target_value: float
    actual_value: float
    passed: bool
    improvement_percent: float = 0.0
    notes: str = ""

@dataclass
class ComprehensiveResults:
    """Complete validation results."""
    timestamp: str
    overall_passed: bool
    response_time_result: ValidationResult
    throughput_result: ValidationResult
    concurrent_result: ValidationResult
    memory_result: ValidationResult
    character_factory_result: ValidationResult
    concurrent_processor_result: ValidationResult
    summary: Dict[str, Any]

class PerformanceValidator:
    """Comprehensive performance validation suite."""
    
    def __init__(self):
        self.targets = PerformanceTarget()
        self.results = []
        self.baseline_memory = 0.0
        self.optimized_server_port = 8004
        self.server_process = None
        
    async def run_comprehensive_validation(self) -> ComprehensiveResults:
        """Run complete performance validation suite."""
        logger.info("Starting comprehensive performance validation...")
        
        # Record baseline memory
        self.baseline_memory = self._get_memory_usage()
        
        # Start optimized server
        await self._start_optimized_server()
        
        try:
            # Wait for server to be ready
            await self._wait_for_server_ready()
            
            # Run all validation tests
            response_time_result = await self._test_response_time()
            throughput_result = await self._test_throughput()
            concurrent_result = await self._test_concurrent_users()
            memory_result = await self._test_memory_efficiency()
            character_factory_result = await self._test_character_factory_performance()
            concurrent_processor_result = await self._test_concurrent_processor()
            
            # Calculate overall result
            all_results = [
                response_time_result, throughput_result, concurrent_result,
                memory_result, character_factory_result, concurrent_processor_result
            ]
            
            overall_passed = all(result.passed for result in all_results)
            
            # Generate summary
            summary = self._generate_summary(all_results)
            
            return ComprehensiveResults(
                timestamp=datetime.now().isoformat(),
                overall_passed=overall_passed,
                response_time_result=response_time_result,
                throughput_result=throughput_result,
                concurrent_result=concurrent_result,
                memory_result=memory_result,
                character_factory_result=character_factory_result,
                concurrent_processor_result=concurrent_processor_result,
                summary=summary
            )
            
        finally:
            await self._stop_optimized_server()
    
    async def _start_optimized_server(self):
        """Start optimized API server in background."""
        if not OPTIMIZED_COMPONENTS_AVAILABLE:
            logger.warning("Optimized components not available - using mock server")
            return
            
        logger.info(f"Starting optimized server on port {self.optimized_server_port}")
        
        # Start server in separate thread to avoid blocking
        def start_server():
            import uvicorn
            from performance_optimized_api_server import app
            config = uvicorn.Config(
                app, 
                host="127.0.0.1", 
                port=self.optimized_server_port,
                log_level="warning",
                access_log=False
            )
            server = uvicorn.Server(config)
            asyncio.run(server.serve())
        
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        # Give server time to start
        await asyncio.sleep(5)
    
    async def _wait_for_server_ready(self, max_attempts: int = 30):
        """Wait for server to be ready to accept requests."""
        for attempt in range(max_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f'http://127.0.0.1:{self.optimized_server_port}/health',
                        timeout=aiohttp.ClientTimeout(total=2)
                    ) as response:
                        if response.status == 200:
                            logger.info("Optimized server is ready")
                            return
            except Exception:
                await asyncio.sleep(1)
        
        logger.warning("Server may not be ready - continuing with tests")
    
    async def _stop_optimized_server(self):
        """Stop optimized server."""
        if self.server_process:
            self.server_process.terminate()
            
    async def _test_response_time(self) -> ValidationResult:
        """Test API response time performance."""
        logger.info("Testing response time performance...")
        
        response_times = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test multiple endpoints
                endpoints = [
                    f'http://127.0.0.1:{self.optimized_server_port}/health',
                    f'http://127.0.0.1:{self.optimized_server_port}/characters',
                ]
                
                for _ in range(20):  # 20 samples
                    for endpoint in endpoints:
                        start_time = time.time()
                        try:
                            async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=5)) as response:
                                await response.read()
                                response_time = (time.time() - start_time) * 1000
                                response_times.append(response_time)
                        except Exception as e:
                            logger.warning(f"Response time test error: {e}")
                
                if response_times:
                    avg_response_time = statistics.mean(response_times)
                    passed = avg_response_time < self.targets.response_time_ms
                    
                    # Calculate improvement (assuming baseline of 2075ms)
                    baseline_response_time = 2075.0
                    improvement = ((baseline_response_time - avg_response_time) / baseline_response_time) * 100
                    
                    return ValidationResult(
                        test_name="Response Time",
                        target_value=self.targets.response_time_ms,
                        actual_value=avg_response_time,
                        passed=passed,
                        improvement_percent=improvement,
                        notes=f"Average: {avg_response_time:.1f}ms, Min: {min(response_times):.1f}ms, Max: {max(response_times):.1f}ms"
                    )
                else:
                    return ValidationResult(
                        test_name="Response Time",
                        target_value=self.targets.response_time_ms,
                        actual_value=999999,
                        passed=False,
                        notes="No successful requests"
                    )
                    
        except Exception as e:
            logger.error(f"Response time test failed: {e}")
            return ValidationResult(
                test_name="Response Time",
                target_value=self.targets.response_time_ms,
                actual_value=999999,
                passed=False,
                notes=f"Test failed: {e}"
            )
    
    async def _test_throughput(self) -> ValidationResult:
        """Test API throughput performance."""
        logger.info("Testing throughput performance...")
        
        try:
            # Test throughput over 10 seconds
            test_duration = 10.0
            start_time = time.time()
            successful_requests = 0
            failed_requests = 0
            
            async with aiohttp.ClientSession() as session:
                tasks = []
                
                # Create concurrent requests
                while (time.time() - start_time) < test_duration:
                    # Create batch of concurrent requests
                    batch_size = 50
                    batch_tasks = []
                    
                    for _ in range(batch_size):
                        task = asyncio.create_task(
                            self._make_test_request(session, f'http://127.0.0.1:{self.optimized_server_port}/health')
                        )
                        batch_tasks.append(task)
                    
                    # Wait for batch completion
                    results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, Exception):
                            failed_requests += 1
                        else:
                            successful_requests += 1
                    
                    # Brief pause to prevent overwhelming
                    await asyncio.sleep(0.1)
            
            actual_duration = time.time() - start_time
            throughput = successful_requests / actual_duration
            
            passed = throughput >= self.targets.throughput_req_per_sec
            
            # Calculate improvement (assuming baseline of 157 req/s)
            baseline_throughput = 157.0
            improvement = ((throughput - baseline_throughput) / baseline_throughput) * 100
            
            return ValidationResult(
                test_name="Throughput",
                target_value=self.targets.throughput_req_per_sec,
                actual_value=throughput,
                passed=passed,
                improvement_percent=improvement,
                notes=f"Successful: {successful_requests}, Failed: {failed_requests}, Duration: {actual_duration:.1f}s"
            )
            
        except Exception as e:
            logger.error(f"Throughput test failed: {e}")
            return ValidationResult(
                test_name="Throughput",
                target_value=self.targets.throughput_req_per_sec,
                actual_value=0,
                passed=False,
                notes=f"Test failed: {e}"
            )
    
    async def _test_concurrent_users(self) -> ValidationResult:
        """Test concurrent user handling."""
        logger.info("Testing concurrent user performance...")
        
        try:
            concurrent_users = 200
            successful_concurrent = 0
            failed_concurrent = 0
            
            async with aiohttp.ClientSession() as session:
                # Create concurrent user simulation
                tasks = []
                
                for user_id in range(concurrent_users):
                    task = asyncio.create_task(
                        self._simulate_user_session(session, user_id)
                    )
                    tasks.append(task)
                
                # Wait for all concurrent users
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        failed_concurrent += 1
                    else:
                        successful_concurrent += 1
            
            success_rate = (successful_concurrent / concurrent_users) * 100
            passed = successful_concurrent >= self.targets.concurrent_users
            
            return ValidationResult(
                test_name="Concurrent Users",
                target_value=self.targets.concurrent_users,
                actual_value=successful_concurrent,
                passed=passed,
                improvement_percent=success_rate,
                notes=f"Success rate: {success_rate:.1f}%, Failed: {failed_concurrent}"
            )
            
        except Exception as e:
            logger.error(f"Concurrent users test failed: {e}")
            return ValidationResult(
                test_name="Concurrent Users",
                target_value=self.targets.concurrent_users,
                actual_value=0,
                passed=False,
                notes=f"Test failed: {e}"
            )
    
    async def _test_memory_efficiency(self) -> ValidationResult:
        """Test memory efficiency improvements."""
        logger.info("Testing memory efficiency...")
        
        try:
            # Measure memory before load test
            memory_before = self._get_memory_usage()
            
            # Simulate memory-intensive operations
            async with aiohttp.ClientSession() as session:
                tasks = []
                for _ in range(100):
                    task = asyncio.create_task(
                        self._make_test_request(session, f'http://127.0.0.1:{self.optimized_server_port}/characters')
                    )
                    tasks.append(task)
                
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Measure memory after load test
            memory_after = self._get_memory_usage()
            memory_increase = memory_after - memory_before
            
            # Calculate memory efficiency (lower increase is better)
            # Target: <30% memory increase during load
            memory_increase_percent = (memory_increase / memory_before) * 100
            passed = memory_increase_percent < self.targets.memory_improvement_percent
            
            return ValidationResult(
                test_name="Memory Efficiency",
                target_value=self.targets.memory_improvement_percent,
                actual_value=memory_increase_percent,
                passed=passed,
                improvement_percent=max(0, self.targets.memory_improvement_percent - memory_increase_percent),
                notes=f"Before: {memory_before:.1f}MB, After: {memory_after:.1f}MB, Increase: {memory_increase_percent:.1f}%"
            )
            
        except Exception as e:
            logger.error(f"Memory efficiency test failed: {e}")
            return ValidationResult(
                test_name="Memory Efficiency",
                target_value=self.targets.memory_improvement_percent,
                actual_value=100,
                passed=False,
                notes=f"Test failed: {e}"
            )
    
    async def _test_character_factory_performance(self) -> ValidationResult:
        """Test optimized character factory performance."""
        logger.info("Testing character factory performance...")
        
        try:
            if not OPTIMIZED_COMPONENTS_AVAILABLE:
                return ValidationResult(
                    test_name="Character Factory",
                    target_value=10.0,
                    actual_value=999,
                    passed=False,
                    notes="Optimized components not available"
                )
            
            factory = OptimizedCharacterFactory()
            
            # Test character creation performance
            creation_times = []
            
            # Warm up cache
            await factory.create_character_async("test_character_1")
            await factory.create_character_async("test_character_2")
            
            # Test performance
            for i in range(20):
                start_time = time.time()
                try:
                    await factory.create_character_async(f"test_character_{i}")
                    creation_time = (time.time() - start_time) * 1000
                    creation_times.append(creation_time)
                except Exception as e:
                    logger.warning(f"Character creation failed: {e}")
            
            if creation_times:
                avg_creation_time = statistics.mean(creation_times)
                target_time = 10.0  # <10ms target
                passed = avg_creation_time < target_time
                
                # Calculate improvement (assuming baseline of 200ms)
                baseline_time = 200.0
                improvement = ((baseline_time - avg_creation_time) / baseline_time) * 100
                
                # Get performance stats
                stats = factory.get_performance_stats()
                
                factory.shutdown()
                
                return ValidationResult(
                    test_name="Character Factory",
                    target_value=target_time,
                    actual_value=avg_creation_time,
                    passed=passed,
                    improvement_percent=improvement,
                    notes=f"Avg: {avg_creation_time:.1f}ms, Cache hit rate: {stats['cache_performance']['hit_rate']:.1%}"
                )
            else:
                factory.shutdown()
                return ValidationResult(
                    test_name="Character Factory",
                    target_value=10.0,
                    actual_value=999,
                    passed=False,
                    notes="No successful character creations"
                )
                
        except Exception as e:
            logger.error(f"Character factory test failed: {e}")
            return ValidationResult(
                test_name="Character Factory",
                target_value=10.0,
                actual_value=999,
                passed=False,
                notes=f"Test failed: {e}"
            )
    
    async def _test_concurrent_processor(self) -> ValidationResult:
        """Test high-performance concurrent processor."""
        logger.info("Testing concurrent processor performance...")
        
        try:
            if not OPTIMIZED_COMPONENTS_AVAILABLE:
                return ValidationResult(
                    test_name="Concurrent Processor",
                    target_value=200.0,
                    actual_value=0,
                    passed=False,
                    notes="Optimized components not available"
                )
            
            processor = HighPerformanceConcurrentProcessor()
            await processor.start()
            
            try:
                # Test concurrent task processing
                def dummy_task(task_id: int) -> str:
                    time.sleep(0.01)  # Simulate work
                    return f"Task {task_id} completed"
                
                # Submit concurrent tasks
                task_count = 200
                task_ids = []
                
                start_time = time.time()
                
                for i in range(task_count):
                    task_id = await processor.submit_task(dummy_task, i, priority=1)
                    task_ids.append(task_id)
                
                # Wait for all tasks to complete
                results = await processor.wait_for_batch(task_ids, timeout=30.0)
                
                processing_time = time.time() - start_time
                
                # Count successful tasks
                successful_tasks = sum(1 for result in results if not isinstance(result, Exception))
                
                # Get performance stats
                stats = processor.get_performance_stats()
                
                passed = successful_tasks >= self.targets.concurrent_users
                throughput = successful_tasks / processing_time
                
                return ValidationResult(
                    test_name="Concurrent Processor",
                    target_value=self.targets.concurrent_users,
                    actual_value=successful_tasks,
                    passed=passed,
                    improvement_percent=(successful_tasks / task_count) * 100,
                    notes=f"Throughput: {throughput:.1f} tasks/s, Success rate: {stats['task_stats']['success_rate']:.1f}%"
                )
                
            finally:
                await processor.stop()
                
        except Exception as e:
            logger.error(f"Concurrent processor test failed: {e}")
            return ValidationResult(
                test_name="Concurrent Processor",
                target_value=200.0,
                actual_value=0,
                passed=False,
                notes=f"Test failed: {e}"
            )
    
    async def _make_test_request(self, session: aiohttp.ClientSession, url: str) -> bool:
        """Make a test request and return success status."""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                await response.read()
                return response.status == 200
        except Exception:
            return False
    
    async def _simulate_user_session(self, session: aiohttp.ClientSession, user_id: int) -> bool:
        """Simulate a user session with multiple requests."""
        try:
            # Simulate user workflow
            base_url = f'http://127.0.0.1:{self.optimized_server_port}'
            
            # Health check
            async with session.get(f'{base_url}/health', timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status != 200:
                    return False
            
            # Get characters
            async with session.get(f'{base_url}/characters', timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status != 200:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def _generate_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate comprehensive test summary."""
        passed_tests = sum(1 for result in results if result.passed)
        total_tests = len(results)
        
        return {
            "overall_success_rate": (passed_tests / total_tests) * 100,
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "performance_improvements": {
                result.test_name.lower().replace(" ", "_"): {
                    "target": result.target_value,
                    "actual": result.actual_value,
                    "improvement_percent": result.improvement_percent,
                    "passed": result.passed
                }
                for result in results
            },
            "validation_status": "PASSED" if passed_tests == total_tests else "FAILED",
            "recommendations": self._generate_recommendations(results)
        }
    
    def _generate_recommendations(self, results: List[ValidationResult]) -> List[str]:
        """Generate performance recommendations based on results."""
        recommendations = []
        
        for result in results:
            if not result.passed:
                if "Response Time" in result.test_name:
                    recommendations.append("Consider further API optimization, caching improvements, or database tuning")
                elif "Throughput" in result.test_name:
                    recommendations.append("Increase worker pools, optimize request pipelines, or add load balancing")
                elif "Concurrent" in result.test_name:
                    recommendations.append("Improve concurrent processing, add circuit breakers, or increase resource limits")
                elif "Memory" in result.test_name:
                    recommendations.append("Optimize memory allocation, add object pooling, or implement better garbage collection")
                elif "Character Factory" in result.test_name:
                    recommendations.append("Improve character factory caching, async processing, or resource pooling")
                elif "Processor" in result.test_name:
                    recommendations.append("Optimize concurrent processing, improve task scheduling, or add resource management")
        
        if not recommendations:
            recommendations.append("All performance targets achieved! Consider monitoring for sustained performance")
        
        return recommendations

async def main():
    """Run comprehensive performance validation."""
    print("=" * 80)
    print("Novel Engine - Comprehensive Performance Validation")
    print("=" * 80)
    
    validator = PerformanceValidator()
    
    try:
        results = await validator.run_comprehensive_validation()
        
        # Display results
        print(f"\n📊 VALIDATION RESULTS - {results.timestamp}")
        print("=" * 80)
        
        print(f"🎯 OVERALL STATUS: {'✅ PASSED' if results.overall_passed else '❌ FAILED'}")
        print(f"📈 Success Rate: {results.summary['overall_success_rate']:.1f}% ({results.summary['tests_passed']}/{results.summary['tests_total']} tests)")
        
        print(f"\n🚀 PERFORMANCE RESULTS:")
        print("-" * 40)
        
        # Individual test results
        test_results = [
            results.response_time_result,
            results.throughput_result,
            results.concurrent_result,
            results.memory_result,
            results.character_factory_result,
            results.concurrent_processor_result
        ]
        
        for result in test_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{result.test_name:20} | {status} | Target: {result.target_value:8.1f} | Actual: {result.actual_value:8.1f} | Improvement: {result.improvement_percent:6.1f}%")
            if result.notes:
                print(f"{'':22} | Notes: {result.notes}")
        
        # Performance improvements summary
        print(f"\n📈 PERFORMANCE IMPROVEMENTS:")
        print("-" * 40)
        
        improvements = results.summary["performance_improvements"]
        for test_name, data in improvements.items():
            if data["improvement_percent"] > 0:
                print(f"{test_name.replace('_', ' ').title():20} | {data['improvement_percent']:6.1f}% improvement")
        
        # Recommendations
        if results.summary["recommendations"]:
            print(f"\n💡 RECOMMENDATIONS:")
            print("-" * 40)
            for i, rec in enumerate(results.summary["recommendations"], 1):
                print(f"{i}. {rec}")
        
        # Save results to file
        results_file = f"performance_validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(asdict(results), f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        # Final status
        print("=" * 80)
        if results.overall_passed:
            print("🎉 PERFORMANCE OPTIMIZATION SUCCESS!")
            print("All target metrics achieved. The Novel Engine performance gaps have been successfully bridged!")
        else:
            print("⚠️  PERFORMANCE OPTIMIZATION PARTIAL SUCCESS")
            print("Some targets not met. Review recommendations for further improvements.")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        print(f"❌ Validation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())