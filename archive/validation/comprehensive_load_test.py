#!/usr/bin/env python3
"""
Comprehensive Load Testing Suite for Novel Engine Performance Validation.

Tests the high-performance API server under various load conditions to validate:
- Response time targets (<100ms)
- Throughput targets (1000+ RPS)
- Concurrent user handling (200+ users)
- Memory and resource utilization
"""

import asyncio
import aiohttp
import time
import json
import statistics
import psutil
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    base_url: str = "http://localhost:8000"
    concurrent_users: int = 200
    requests_per_user: int = 10
    test_duration_seconds: int = 60
    ramp_up_seconds: int = 10
    think_time_ms: int = 100
    timeout_seconds: int = 30
    
@dataclass
class TestMetrics:
    """Metrics collected during load testing."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    throughput_rps: float = 0.0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    memory_usage_mb: List[float] = field(default_factory=list)
    cpu_usage_percent: List[float] = field(default_factory=list)

class PerformanceMonitor:
    """Monitor system performance during load testing."""
    
    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.monitor_task = None
    
    async def start_monitoring(self):
        """Start performance monitoring."""
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitoring stopped")
    
    async def _monitor_loop(self):
        """Performance monitoring loop."""
        while self.monitoring:
            try:
                # System metrics
                memory_info = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent()
                
                # Process metrics
                process = psutil.Process()
                process_memory = process.memory_info().rss / (1024 * 1024)  # MB
                process_cpu = process.cpu_percent()
                
                metric = {
                    'timestamp': time.time(),
                    'system_memory_percent': memory_info.percent,
                    'system_cpu_percent': cpu_percent,
                    'process_memory_mb': process_memory,
                    'process_cpu_percent': process_cpu,
                    'system_memory_available_mb': memory_info.available / (1024 * 1024)
                }
                
                self.metrics.append(metric)
                
                # Keep only last 1000 metrics
                if len(self.metrics) > 1000:
                    self.metrics = self.metrics[-1000:]
                
                await asyncio.sleep(1)  # Monitor every second
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(1)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance monitoring summary."""
        if not self.metrics:
            return {}
        
        memory_values = [m['process_memory_mb'] for m in self.metrics]
        cpu_values = [m['process_cpu_percent'] for m in self.metrics]
        
        return {
            'avg_memory_mb': statistics.mean(memory_values),
            'max_memory_mb': max(memory_values),
            'min_memory_mb': min(memory_values),
            'avg_cpu_percent': statistics.mean(cpu_values),
            'max_cpu_percent': max(cpu_values),
            'samples_collected': len(self.metrics)
        }

class LoadTestClient:
    """Individual load test client."""
    
    def __init__(self, client_id: int, config: LoadTestConfig, session: aiohttp.ClientSession):
        self.client_id = client_id
        self.config = config
        self.session = session
        self.metrics = TestMetrics()
        
    async def run_load_test(self) -> TestMetrics:
        """Run load test for this client."""
        logger.debug(f"Client {self.client_id} starting load test")
        
        self.metrics.start_time = time.time()
        
        for request_num in range(self.config.requests_per_user):
            try:
                # Execute test scenario
                await self._execute_test_scenario()
                
                # Think time between requests
                if self.config.think_time_ms > 0:
                    await asyncio.sleep(self.config.think_time_ms / 1000.0)
                    
            except Exception as e:
                self.metrics.failed_requests += 1
                self.metrics.errors.append(f"Client {self.client_id}: {str(e)}")
                logger.error(f"Client {self.client_id} request {request_num} failed: {e}")
        
        self.metrics.end_time = time.time()
        
        # Calculate metrics
        if self.metrics.response_times:
            self.metrics.avg_response_time = statistics.mean(self.metrics.response_times)
            self.metrics.min_response_time = min(self.metrics.response_times)
            self.metrics.max_response_time = max(self.metrics.response_times)
            
            sorted_times = sorted(self.metrics.response_times)
            self.metrics.p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
            self.metrics.p99_response_time = sorted_times[int(len(sorted_times) * 0.99)]
        
        total_time = self.metrics.end_time - self.metrics.start_time
        if total_time > 0:
            self.metrics.throughput_rps = self.metrics.total_requests / total_time
        
        logger.debug(f"Client {self.client_id} completed load test")
        return self.metrics
    
    async def _execute_test_scenario(self):
        """Execute a test scenario with multiple endpoints."""
        scenarios = [
            self._test_health_check,
            self._test_root_endpoint,
            self._test_characters_list,
            self._test_optimized_characters,
            self._test_performance_metrics,
            self._test_character_detail
        ]
        
        # Select scenario (round-robin based on request count)
        scenario_index = self.metrics.total_requests % len(scenarios)
        scenario = scenarios[scenario_index]
        
        await scenario()
    
    async def _test_health_check(self):
        """Test health check endpoint."""
        await self._make_request("GET", "/health")
    
    async def _test_root_endpoint(self):
        """Test root endpoint."""
        await self._make_request("GET", "/")
    
    async def _test_characters_list(self):
        """Test characters list endpoint."""
        await self._make_request("GET", "/characters")
    
    async def _test_optimized_characters(self):
        """Test optimized characters endpoint."""
        await self._make_request("GET", "/api/v1/characters/optimized")
    
    async def _test_performance_metrics(self):
        """Test performance metrics endpoint."""
        await self._make_request("GET", "/metrics")
    
    async def _test_character_detail(self):
        """Test character detail endpoint."""
        # Use a test character that should exist
        await self._make_request("GET", "/characters/test_character")
    
    async def _test_optimized_simulation(self):
        """Test optimized simulation endpoint."""
        payload = {
            "character_names": ["test_character_1", "test_character_2"],
            "turns": 3
        }
        await self._make_request("POST", "/api/v1/simulations/optimized", json=payload)
    
    async def _make_request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request and record metrics."""
        url = f"{self.config.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            
            async with self.session.request(
                method, url, timeout=timeout, **kwargs
            ) as response:
                # Read response to ensure complete transfer
                await response.read()
                
                response_time = time.time() - start_time
                self.metrics.response_times.append(response_time)
                self.metrics.total_requests += 1
                
                if response.status < 400:
                    self.metrics.successful_requests += 1
                else:
                    self.metrics.failed_requests += 1
                    self.metrics.errors.append(f"HTTP {response.status} for {method} {endpoint}")
                
                # Log slow requests
                if response_time > 0.1:  # >100ms
                    logger.warning(f"Slow request: {method} {endpoint} took {response_time:.3f}s")
                
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.errors.append(f"Timeout for {method} {endpoint}")
            logger.error(f"Request timeout: {method} {endpoint}")
            
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.errors.append(f"Error for {method} {endpoint}: {str(e)}")
            logger.error(f"Request error: {method} {endpoint}: {e}")

class ComprehensiveLoadTester:
    """Comprehensive load testing orchestrator."""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.monitor = PerformanceMonitor()
        self.clients: List[LoadTestClient] = []
        
    async def run_load_test(self) -> Dict[str, Any]:
        """Execute comprehensive load test."""
        logger.info(f"Starting comprehensive load test with {self.config.concurrent_users} concurrent users")
        logger.info(f"Test configuration: {self.config}")
        
        # Start performance monitoring
        await self.monitor.start_monitoring()
        
        test_start_time = time.time()
        
        try:
            # Create HTTP session with connection pooling
            connector = aiohttp.TCPConnector(
                limit=self.config.concurrent_users * 2,
                limit_per_host=self.config.concurrent_users * 2,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as session:
                
                # Test server availability first
                await self._verify_server_availability(session)
                
                # Execute load test with ramp-up
                client_metrics = await self._execute_ramped_load_test(session)
                
        finally:
            # Stop performance monitoring
            await self.monitor.stop_monitoring()
        
        test_end_time = time.time()
        
        # Aggregate results
        results = self._aggregate_results(client_metrics, test_start_time, test_end_time)
        
        logger.info("Load test completed successfully")
        return results
    
    async def _verify_server_availability(self, session: aiohttp.ClientSession):
        """Verify server is available before starting load test."""
        logger.info("Verifying server availability...")
        
        try:
            async with session.get(f"{self.config.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Server is available: {data.get('status', 'unknown')}")
                else:
                    raise Exception(f"Server health check failed: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Server availability check failed: {e}")
            raise Exception(f"Cannot connect to server at {self.config.base_url}: {e}")
    
    async def _execute_ramped_load_test(self, session: aiohttp.ClientSession) -> List[TestMetrics]:
        """Execute load test with gradual ramp-up."""
        logger.info("Starting ramped load test execution")
        
        # Calculate ramp-up timing
        ramp_up_delay = self.config.ramp_up_seconds / self.config.concurrent_users
        
        # Create and start clients with ramp-up
        client_tasks = []
        
        for client_id in range(self.config.concurrent_users):
            # Create client
            client = LoadTestClient(client_id, self.config, session)
            self.clients.append(client)
            
            # Start client task
            task = asyncio.create_task(client.run_load_test())
            client_tasks.append(task)
            
            # Ramp-up delay
            if ramp_up_delay > 0 and client_id < self.config.concurrent_users - 1:
                await asyncio.sleep(ramp_up_delay)
        
        logger.info(f"All {self.config.concurrent_users} clients started")
        
        # Wait for all clients to complete
        client_metrics = await asyncio.gather(*client_tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_metrics = []
        for i, metrics in enumerate(client_metrics):
            if isinstance(metrics, Exception):
                logger.error(f"Client {i} failed: {metrics}")
            else:
                valid_metrics.append(metrics)
        
        logger.info(f"Load test execution completed: {len(valid_metrics)}/{self.config.concurrent_users} clients successful")
        return valid_metrics
    
    def _aggregate_results(self, client_metrics: List[TestMetrics], 
                          test_start_time: float, test_end_time: float) -> Dict[str, Any]:
        """Aggregate results from all clients."""
        if not client_metrics:
            return {"error": "No valid client metrics collected"}
        
        # Aggregate metrics
        total_requests = sum(m.total_requests for m in client_metrics)
        successful_requests = sum(m.successful_requests for m in client_metrics)
        failed_requests = sum(m.failed_requests for m in client_metrics)
        
        all_response_times = []
        all_errors = []
        
        for metrics in client_metrics:
            all_response_times.extend(metrics.response_times)
            all_errors.extend(metrics.errors)
        
        # Calculate aggregate statistics
        test_duration = test_end_time - test_start_time
        overall_throughput = total_requests / test_duration if test_duration > 0 else 0
        
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        if all_response_times:
            sorted_times = sorted(all_response_times)
            avg_response_time = statistics.mean(all_response_times)
            p50_response_time = sorted_times[int(len(sorted_times) * 0.50)]
            p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
            p99_response_time = sorted_times[int(len(sorted_times) * 0.99)]
            min_response_time = min(all_response_times)
            max_response_time = max(all_response_times)
        else:
            avg_response_time = p50_response_time = p95_response_time = p99_response_time = 0
            min_response_time = max_response_time = 0
        
        # Performance goals validation
        performance_goals = {
            "response_time_target_ms": 100,
            "throughput_target_rps": 1000,
            "concurrent_users_target": 200,
            "success_rate_target_percent": 99
        }
        
        goal_achievements = {
            "avg_response_time_goal": (avg_response_time * 1000) <= performance_goals["response_time_target_ms"],
            "p95_response_time_goal": (p95_response_time * 1000) <= performance_goals["response_time_target_ms"],
            "throughput_goal": overall_throughput >= performance_goals["throughput_target_rps"],
            "concurrent_users_goal": self.config.concurrent_users >= performance_goals["concurrent_users_target"],
            "success_rate_goal": success_rate >= performance_goals["success_rate_target_percent"]
        }
        
        # Get performance monitoring summary
        monitoring_summary = self.monitor.get_summary()
        
        results = {
            "test_summary": {
                "test_duration_seconds": test_duration,
                "concurrent_users": self.config.concurrent_users,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate_percent": success_rate,
                "error_rate_percent": error_rate
            },
            "performance_metrics": {
                "avg_response_time_ms": avg_response_time * 1000,
                "p50_response_time_ms": p50_response_time * 1000,
                "p95_response_time_ms": p95_response_time * 1000,
                "p99_response_time_ms": p99_response_time * 1000,
                "min_response_time_ms": min_response_time * 1000,
                "max_response_time_ms": max_response_time * 1000,
                "throughput_rps": overall_throughput
            },
            "performance_goals": performance_goals,
            "goal_achievements": goal_achievements,
            "goals_met": all(goal_achievements.values()),
            "system_performance": monitoring_summary,
            "errors": {
                "total_errors": len(all_errors),
                "unique_errors": len(set(all_errors)),
                "error_samples": all_errors[:10] if all_errors else []
            },
            "test_configuration": {
                "base_url": self.config.base_url,
                "concurrent_users": self.config.concurrent_users,
                "requests_per_user": self.config.requests_per_user,
                "test_duration_seconds": self.config.test_duration_seconds,
                "ramp_up_seconds": self.config.ramp_up_seconds
            }
        }
        
        return results

async def run_comprehensive_load_test(config: LoadTestConfig) -> Dict[str, Any]:
    """Run comprehensive load test with the given configuration."""
    tester = ComprehensiveLoadTester(config)
    return await tester.run_load_test()

def save_results(results: Dict[str, Any], output_file: str):
    """Save test results to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_file}_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Results saved to {filename}")
    return filename

def print_results_summary(results: Dict[str, Any]):
    """Print a summary of test results."""
    print("\n" + "="*60)
    print("COMPREHENSIVE LOAD TEST RESULTS")
    print("="*60)
    
    summary = results.get("test_summary", {})
    performance = results.get("performance_metrics", {})
    goals = results.get("goal_achievements", {})
    
    print(f"\nTest Configuration:")
    print(f"  Concurrent Users: {summary.get('concurrent_users', 0)}")
    print(f"  Total Requests: {summary.get('total_requests', 0)}")
    print(f"  Test Duration: {summary.get('test_duration_seconds', 0):.1f}s")
    
    print(f"\nPerformance Results:")
    print(f"  Average Response Time: {performance.get('avg_response_time_ms', 0):.1f}ms")
    print(f"  P95 Response Time: {performance.get('p95_response_time_ms', 0):.1f}ms")
    print(f"  P99 Response Time: {performance.get('p99_response_time_ms', 0):.1f}ms")
    print(f"  Throughput: {performance.get('throughput_rps', 0):.1f} RPS")
    print(f"  Success Rate: {summary.get('success_rate_percent', 0):.1f}%")
    
    print(f"\nPerformance Goals:")
    for goal, achieved in goals.items():
        status = "✓ PASS" if achieved else "✗ FAIL"
        print(f"  {goal.replace('_', ' ').title()}: {status}")
    
    overall_result = "PASS" if results.get("goals_met", False) else "FAIL"
    print(f"\nOVERALL RESULT: {overall_result}")
    print("="*60)

def main():
    """Main entry point for load testing."""
    parser = argparse.ArgumentParser(description="Comprehensive Load Testing for Novel Engine")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for testing")
    parser.add_argument("--users", type=int, default=200, help="Number of concurrent users")
    parser.add_argument("--requests", type=int, default=10, help="Requests per user")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--rampup", type=int, default=10, help="Ramp-up time in seconds")
    parser.add_argument("--output", default="load_test_results", help="Output file prefix")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create configuration
    config = LoadTestConfig(
        base_url=args.url,
        concurrent_users=args.users,
        requests_per_user=args.requests,
        test_duration_seconds=args.duration,
        ramp_up_seconds=args.rampup
    )
    
    logger.info("Starting comprehensive load test")
    
    try:
        # Run load test
        results = asyncio.run(run_comprehensive_load_test(config))
        
        # Save and display results
        output_file = save_results(results, args.output)
        print_results_summary(results)
        
        # Exit with appropriate code
        exit_code = 0 if results.get("goals_met", False) else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Load test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Load test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()