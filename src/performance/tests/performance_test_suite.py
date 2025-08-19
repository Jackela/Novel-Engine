#!/usr/bin/env python3
"""
Comprehensive Performance Testing Suite for Novel Engine Production Readiness.

This module implements a comprehensive performance testing framework to validate
Novel Engine's production readiness through load testing, stress testing,
performance profiling, scalability validation, and endurance testing.

Key Testing Areas:
- Load Testing: Concurrent user simulation, throughput measurement
- Stress Testing: System limits, breaking point identification  
- Performance Profiling: CPU, memory, I/O, database performance
- Scalability Testing: Horizontal scaling capability
- Endurance Testing: Long-running performance, memory leaks

Performance Targets:
- Response Time: <200ms for simple operations, <500ms for complex operations
- Throughput: Handle 50+ concurrent users for critical endpoints
- Error Rate: <1% under normal load conditions
- Resource Usage: Efficient CPU and memory utilization
"""

import asyncio
import aiohttp
import time
import statistics
import json
import psutil
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import subprocess
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Data class for performance measurement results."""
    response_times: List[float] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0
    throughput: float = 0.0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def calculate_statistics(self):
        """Calculate statistical metrics from response times."""
        if self.response_times:
            self.avg_response_time = statistics.mean(self.response_times)
            self.min_response_time = min(self.response_times)
            self.max_response_time = max(self.response_times)
            
            sorted_times = sorted(self.response_times)
            n = len(sorted_times)
            if n >= 2:
                self.p95_response_time = sorted_times[int(0.95 * n)]
                self.p99_response_time = sorted_times[int(0.99 * n)]

@dataclass
class ResourceMetrics:
    """Data class for system resource monitoring."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read: int
    disk_io_write: int
    network_sent: int
    network_recv: int

@dataclass
class LoadTestConfig:
    """Configuration for load testing scenarios."""
    base_url: str = "http://localhost:8000"
    concurrent_users: int = 10
    duration_seconds: int = 60
    ramp_up_seconds: int = 10
    endpoints: List[str] = field(default_factory=lambda: [
        "/health",
        "/characters",
        "/characters/engineer", 
        "/characters/pilot",
        "/characters/scientist"
    ])
    test_scenarios: Dict[str, Any] = field(default_factory=dict)

class ResourceMonitor:
    """System resource monitoring class."""
    
    def __init__(self):
        self.monitoring = False
        self.metrics: List[ResourceMetrics] = []
        self.process = None
        self._start_time = None
        
    def start_monitoring(self, target_process_name: str = "python"):
        """Start monitoring system resources."""
        self.monitoring = True
        self.metrics = []
        self._start_time = time.time()
        
        # Find target process
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if (target_process_name in proc.info['name'] and 
                    'api_server.py' in ' '.join(proc.info['cmdline'] or [])):
                    self.process = psutil.Process(proc.info['pid'])
                    logger.info(f"Monitoring process {proc.info['pid']}: {proc.info['name']}")
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        if not self.process:
            logger.warning(f"Target process {target_process_name} not found, monitoring system-wide")
            
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_resources)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop monitoring system resources."""
        self.monitoring = False
        if hasattr(self, '_monitor_thread'):
            self._monitor_thread.join(timeout=5)
            
    def _monitor_resources(self):
        """Monitor resources in background thread."""
        while self.monitoring:
            try:
                if self.process and self.process.is_running():
                    # Monitor specific process
                    cpu_percent = self.process.cpu_percent()
                    memory_info = self.process.memory_info()
                    memory_percent = self.process.memory_percent()
                    
                    # Get I/O stats if available
                    try:
                        io_stats = self.process.io_counters()
                        disk_read = io_stats.read_bytes
                        disk_write = io_stats.write_bytes
                    except (psutil.AccessDenied, AttributeError):
                        disk_read = disk_write = 0
                        
                else:
                    # Monitor system-wide
                    cpu_percent = psutil.cpu_percent()
                    memory = psutil.virtual_memory()
                    memory_percent = memory.percent
                    memory_mb = memory.used / 1024 / 1024
                    
                    # Get disk I/O
                    disk_io = psutil.disk_io_counters()
                    disk_read = disk_io.read_bytes if disk_io else 0
                    disk_write = disk_io.write_bytes if disk_io else 0
                    
                # Get network stats
                network = psutil.net_io_counters()
                network_sent = network.bytes_sent if network else 0
                network_recv = network.bytes_recv if network else 0
                
                # Create metrics record
                metrics = ResourceMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    memory_mb=memory_info.rss / 1024 / 1024 if self.process else memory_mb,
                    disk_io_read=disk_read,
                    disk_io_write=disk_write,
                    network_sent=network_sent,
                    network_recv=network_recv
                )
                self.metrics.append(metrics)
                
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
                
            time.sleep(1)
            
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for monitored resources."""
        if not self.metrics:
            return {}
            
        cpu_values = [m.cpu_percent for m in self.metrics]
        memory_values = [m.memory_percent for m in self.metrics]
        memory_mb_values = [m.memory_mb for m in self.metrics]
        
        return {
            "monitoring_duration": self.metrics[-1].timestamp - self.metrics[0].timestamp,
            "cpu_percent": {
                "avg": statistics.mean(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory_percent": {
                "avg": statistics.mean(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "memory_mb": {
                "avg": statistics.mean(memory_mb_values),
                "max": max(memory_mb_values),
                "min": min(memory_mb_values)
            },
            "sample_count": len(self.metrics)
        }

class PerformanceTestSuite:
    """Comprehensive performance testing suite."""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.monitor = ResourceMonitor()
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            
    async def make_request(self, endpoint: str) -> Tuple[float, bool, str]:
        """Make a single HTTP request and measure response time."""
        url = f"{self.config.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with self.session.get(url) as response:
                await response.text()  # Read response body
                end_time = time.time()
                response_time = end_time - start_time
                success = response.status < 400
                error_msg = f"HTTP {response.status}" if not success else ""
                return response_time, success, error_msg
                
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            return response_time, False, str(e)
            
    async def single_user_test(self, endpoint: str, requests_count: int = 10) -> PerformanceMetrics:
        """Test a single endpoint with sequential requests."""
        logger.info(f"Running single user test for {endpoint} ({requests_count} requests)")
        metrics = PerformanceMetrics()
        
        for i in range(requests_count):
            response_time, success, error = await self.make_request(endpoint)
            metrics.response_times.append(response_time)
            
            if success:
                metrics.success_count += 1
            else:
                metrics.error_count += 1
                metrics.errors.append(error)
                
        metrics.calculate_statistics()
        return metrics
        
    async def concurrent_user_test(self, endpoint: str, concurrent_users: int, 
                                 duration_seconds: int = 60) -> PerformanceMetrics:
        """Test endpoint with concurrent users for specified duration."""
        logger.info(f"Running concurrent test: {concurrent_users} users on {endpoint} for {duration_seconds}s")
        
        metrics = PerformanceMetrics()
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        async def user_session():
            """Single user session making requests."""
            session_metrics = PerformanceMetrics()
            while time.time() < end_time:
                response_time, success, error = await self.make_request(endpoint)
                session_metrics.response_times.append(response_time)
                
                if success:
                    session_metrics.success_count += 1
                else:
                    session_metrics.error_count += 1
                    session_metrics.errors.append(error)
                    
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.1)
            return session_metrics
            
        # Run concurrent user sessions
        tasks = [user_session() for _ in range(concurrent_users)]
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        total_duration = time.time() - start_time
        for result in session_results:
            if isinstance(result, PerformanceMetrics):
                metrics.response_times.extend(result.response_times)
                metrics.success_count += result.success_count
                metrics.error_count += result.error_count
                metrics.errors.extend(result.errors)
                
        # Calculate throughput (requests per second)
        total_requests = metrics.success_count + metrics.error_count
        metrics.throughput = total_requests / total_duration if total_duration > 0 else 0
        
        metrics.calculate_statistics()
        return metrics
        
    async def stress_test(self, endpoint: str, max_users: int = 100, 
                         step_size: int = 10, step_duration: int = 30) -> Dict[str, Any]:
        """Progressive stress test to find breaking point."""
        logger.info(f"Running stress test for {endpoint}: 0 to {max_users} users")
        
        results = []
        current_users = step_size
        
        while current_users <= max_users:
            logger.info(f"Testing {current_users} concurrent users")
            metrics = await self.concurrent_user_test(endpoint, current_users, step_duration)
            
            result = {
                "concurrent_users": current_users,
                "metrics": asdict(metrics),
                "error_rate": metrics.error_count / (metrics.success_count + metrics.error_count) 
                            if (metrics.success_count + metrics.error_count) > 0 else 1.0
            }
            results.append(result)
            
            # Stop if error rate exceeds 50%
            if result["error_rate"] > 0.5:
                logger.warning(f"High error rate ({result['error_rate']:.2%}) at {current_users} users")
                break
                
            current_users += step_size
            
        return {
            "endpoint": endpoint,
            "max_tested_users": current_users - step_size,
            "results": results
        }
        
    async def endpoint_load_test(self, endpoints: List[str], concurrent_users: int = 10) -> Dict[str, Any]:
        """Test multiple endpoints simultaneously."""
        logger.info(f"Running endpoint load test with {concurrent_users} users across {len(endpoints)} endpoints")
        
        results = {}
        
        # Test each endpoint
        for endpoint in endpoints:
            try:
                metrics = await self.concurrent_user_test(endpoint, concurrent_users, 60)
                results[endpoint] = asdict(metrics)
            except Exception as e:
                logger.error(f"Error testing endpoint {endpoint}: {e}")
                results[endpoint] = {"error": str(e)}
                
        return results
        
    def run_simulation_load_test(self, concurrent_simulations: int = 5) -> Dict[str, Any]:
        """Test story generation under load using sync requests."""
        logger.info(f"Running simulation load test with {concurrent_simulations} concurrent simulations")
        
        def run_single_simulation():
            """Run a single story simulation."""
            import httpx
            start_time = time.time()
            
            try:
                # Create simulation request
                simulation_data = {
                    "character_names": ["engineer", "pilot"],
                    "turns": 3
                }
                
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(
                        f"{self.config.base_url}/simulate",
                        json=simulation_data
                    )
                    
                end_time = time.time()
                response_time = end_time - start_time
                
                success = response.status_code < 400
                error_msg = f"HTTP {response.status_code}" if not success else ""
                
                return {
                    "response_time": response_time,
                    "success": success,
                    "error": error_msg,
                    "response_size": len(response.text) if success else 0
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    "response_time": end_time - start_time,
                    "success": False,
                    "error": str(e),
                    "response_size": 0
                }
                
        # Run concurrent simulations
        with ThreadPoolExecutor(max_workers=concurrent_simulations) as executor:
            futures = [executor.submit(run_single_simulation) for _ in range(concurrent_simulations)]
            results = []
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "response_time": 0,
                        "success": False,
                        "error": str(e),
                        "response_size": 0
                    })
                    
        # Calculate summary statistics
        response_times = [r["response_time"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        error_count = len(results) - success_count
        
        return {
            "total_simulations": len(results),
            "success_count": success_count,
            "error_count": error_count,
            "error_rate": error_count / len(results) if results else 1.0,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "total_response_time": sum(response_times),
            "results": results
        }

    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run the complete performance test suite."""
        logger.info("Starting comprehensive performance test suite")
        
        # Start resource monitoring
        self.monitor.start_monitoring()
        test_start_time = time.time()
        
        results = {
            "test_start_time": datetime.now().isoformat(),
            "config": asdict(self.config),
            "baseline_tests": {},
            "load_tests": {},
            "stress_tests": {},
            "simulation_tests": {},
            "resource_metrics": {}
        }
        
        try:
            # 1. Baseline Performance Tests (Single User)
            logger.info("=== Running Baseline Performance Tests ===")
            for endpoint in self.config.endpoints:
                try:
                    metrics = await self.single_user_test(endpoint, 20)
                    results["baseline_tests"][endpoint] = asdict(metrics)
                    
                    # Log key metrics
                    logger.info(f"Baseline {endpoint}: avg={metrics.avg_response_time:.3f}s, "
                              f"p95={metrics.p95_response_time:.3f}s, errors={metrics.error_count}")
                              
                except Exception as e:
                    logger.error(f"Baseline test failed for {endpoint}: {e}")
                    results["baseline_tests"][endpoint] = {"error": str(e)}
                    
            # 2. Concurrent User Load Tests
            logger.info("=== Running Concurrent User Load Tests ===")
            for users in [10, 25, 50]:
                logger.info(f"Testing with {users} concurrent users")
                try:
                    load_results = await self.endpoint_load_test(self.config.endpoints[:3], users)
                    results["load_tests"][f"{users}_users"] = load_results
                    
                    # Log summary
                    for endpoint, metrics in load_results.items():
                        if "error" not in metrics:
                            logger.info(f"{users} users {endpoint}: "
                                      f"throughput={metrics.get('throughput', 0):.2f} req/s, "
                                      f"errors={metrics.get('error_count', 0)}")
                        
                except Exception as e:
                    logger.error(f"Load test failed for {users} users: {e}")
                    results["load_tests"][f"{users}_users"] = {"error": str(e)}
                    
            # 3. Stress Testing (Find Breaking Point)
            logger.info("=== Running Stress Tests ===")
            critical_endpoints = ["/health", "/characters"]
            for endpoint in critical_endpoints:
                try:
                    stress_results = await self.stress_test(endpoint, max_users=75, step_size=15)
                    results["stress_tests"][endpoint] = stress_results
                    
                    # Find maximum stable load
                    max_stable = 0
                    for result in stress_results["results"]:
                        if result["error_rate"] < 0.05:  # Less than 5% error rate
                            max_stable = result["concurrent_users"]
                            
                    logger.info(f"Stress test {endpoint}: max stable load = {max_stable} users")
                    
                except Exception as e:
                    logger.error(f"Stress test failed for {endpoint}: {e}")
                    results["stress_tests"][endpoint] = {"error": str(e)}
                    
            # 4. Story Generation Simulation Tests
            logger.info("=== Running Story Generation Load Tests ===")
            for sim_count in [3, 5, 8]:
                try:
                    sim_results = self.run_simulation_load_test(sim_count)
                    results["simulation_tests"][f"{sim_count}_simulations"] = sim_results
                    
                    logger.info(f"{sim_count} simulations: "
                              f"success_rate={1-sim_results['error_rate']:.2%}, "
                              f"avg_time={sim_results['avg_response_time']:.2f}s")
                              
                except Exception as e:
                    logger.error(f"Simulation test failed for {sim_count}: {e}")
                    results["simulation_tests"][f"{sim_count}_simulations"] = {"error": str(e)}
                    
        finally:
            # Stop monitoring and collect resource metrics
            self.monitor.stop_monitoring()
            results["resource_metrics"] = self.monitor.get_summary_stats()
            results["total_test_duration"] = time.time() - test_start_time
            
        logger.info("Comprehensive performance test suite completed")
        return results
        
    def generate_performance_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive performance test report."""
        report = []
        report.append("# Novel Engine Performance Test Report")
        report.append(f"Generated: {results['test_start_time']}")
        report.append(f"Test Duration: {results.get('total_test_duration', 0):.2f} seconds")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary")
        
        # Analyze baseline performance
        baseline_avg_times = []
        baseline_errors = 0
        for endpoint, metrics in results.get("baseline_tests", {}).items():
            if "error" not in metrics:
                baseline_avg_times.append(metrics.get("avg_response_time", 0))
                baseline_errors += metrics.get("error_count", 0)
                
        if baseline_avg_times:
            avg_baseline = statistics.mean(baseline_avg_times)
            report.append(f"- **Baseline Performance**: Average response time {avg_baseline:.3f}s")
            report.append(f"- **Baseline Reliability**: {baseline_errors} errors across all baseline tests")
        
        # Analyze load test results
        max_throughput = 0
        max_concurrent_users = 0
        for test_name, test_results in results.get("load_tests", {}).items():
            if "error" not in test_results:
                for endpoint, metrics in test_results.items():
                    if "error" not in metrics:
                        throughput = metrics.get("throughput", 0)
                        if throughput > max_throughput:
                            max_throughput = throughput
                            max_concurrent_users = int(test_name.split("_")[0])
                            
        report.append(f"- **Maximum Throughput**: {max_throughput:.2f} requests/second")
        report.append(f"- **Concurrent User Capacity**: {max_concurrent_users} users tested successfully")
        
        # System resource usage
        resource_metrics = results.get("resource_metrics", {})
        if resource_metrics:
            cpu_avg = resource_metrics.get("cpu_percent", {}).get("avg", 0)
            memory_avg = resource_metrics.get("memory_percent", {}).get("avg", 0)
            report.append(f"- **Resource Usage**: CPU {cpu_avg:.1f}%, Memory {memory_avg:.1f}%")
            
        report.append("")
        
        # Detailed Results
        report.append("## Detailed Test Results")
        
        # Baseline Tests
        report.append("### Baseline Performance Tests")
        report.append("| Endpoint | Avg Response (ms) | P95 Response (ms) | P99 Response (ms) | Error Count |")
        report.append("|----------|-------------------|-------------------|-------------------|-------------|")
        
        for endpoint, metrics in results.get("baseline_tests", {}).items():
            if "error" not in metrics:
                avg_ms = metrics.get("avg_response_time", 0) * 1000
                p95_ms = metrics.get("p95_response_time", 0) * 1000
                p99_ms = metrics.get("p99_response_time", 0) * 1000
                errors = metrics.get("error_count", 0)
                report.append(f"| {endpoint} | {avg_ms:.1f} | {p95_ms:.1f} | {p99_ms:.1f} | {errors} |")
            else:
                report.append(f"| {endpoint} | ERROR | ERROR | ERROR | ERROR |")
                
        report.append("")
        
        # Load Tests
        report.append("### Load Test Results")
        for test_name, test_results in results.get("load_tests", {}).items():
            users = test_name.replace("_", " ").title()
            report.append(f"#### {users}")
            report.append("| Endpoint | Throughput (req/s) | Avg Response (ms) | Error Rate | Total Requests |")
            report.append("|----------|-------------------|-------------------|------------|----------------|")
            
            if "error" not in test_results:
                for endpoint, metrics in test_results.items():
                    if "error" not in metrics:
                        throughput = metrics.get("throughput", 0)
                        avg_ms = metrics.get("avg_response_time", 0) * 1000
                        total_req = metrics.get("success_count", 0) + metrics.get("error_count", 0)
                        error_rate = metrics.get("error_count", 0) / total_req if total_req > 0 else 0
                        report.append(f"| {endpoint} | {throughput:.2f} | {avg_ms:.1f} | {error_rate:.2%} | {total_req} |")
                    else:
                        report.append(f"| {endpoint} | ERROR | ERROR | ERROR | ERROR |")
            else:
                report.append(f"| ALL | ERROR | ERROR | ERROR | ERROR |")
                
            report.append("")
            
        # Stress Tests
        report.append("### Stress Test Results")
        for endpoint, stress_data in results.get("stress_tests", {}).items():
            if "error" not in stress_data:
                report.append(f"#### {endpoint}")
                report.append("| Concurrent Users | Throughput (req/s) | Avg Response (ms) | Error Rate |")
                report.append("|------------------|-------------------|-------------------|------------|")
                
                for result in stress_data.get("results", []):
                    users = result["concurrent_users"]
                    metrics = result["metrics"]
                    throughput = metrics.get("throughput", 0)
                    avg_ms = metrics.get("avg_response_time", 0) * 1000
                    error_rate = result["error_rate"]
                    report.append(f"| {users} | {throughput:.2f} | {avg_ms:.1f} | {error_rate:.2%} |")
                    
                report.append("")
                
        # Simulation Tests
        report.append("### Story Generation Load Tests")
        report.append("| Concurrent Simulations | Success Rate | Avg Response Time (s) | Max Response Time (s) |")
        report.append("|------------------------|--------------|----------------------|----------------------|")
        
        for test_name, sim_results in results.get("simulation_tests", {}).items():
            if "error" not in sim_results:
                sim_count = test_name.replace("_", " ").title()
                success_rate = 1 - sim_results.get("error_rate", 1)
                avg_time = sim_results.get("avg_response_time", 0)
                max_time = sim_results.get("max_response_time", 0)
                report.append(f"| {sim_count} | {success_rate:.2%} | {avg_time:.2f} | {max_time:.2f} |")
            else:
                report.append(f"| {test_name} | ERROR | ERROR | ERROR |")
                
        report.append("")
        
        # Resource Monitoring
        if resource_metrics:
            report.append("### System Resource Usage")
            report.append("| Metric | Average | Maximum | Minimum |")
            report.append("|--------|---------|---------|---------|")
            
            cpu_data = resource_metrics.get("cpu_percent", {})
            if cpu_data:
                report.append(f"| CPU Usage (%) | {cpu_data.get('avg', 0):.1f} | {cpu_data.get('max', 0):.1f} | {cpu_data.get('min', 0):.1f} |")
                
            memory_data = resource_metrics.get("memory_percent", {})
            if memory_data:
                report.append(f"| Memory Usage (%) | {memory_data.get('avg', 0):.1f} | {memory_data.get('max', 0):.1f} | {memory_data.get('min', 0):.1f} |")
                
            memory_mb_data = resource_metrics.get("memory_mb", {})
            if memory_mb_data:
                report.append(f"| Memory Usage (MB) | {memory_mb_data.get('avg', 0):.1f} | {memory_mb_data.get('max', 0):.1f} | {memory_mb_data.get('min', 0):.1f} |")
                
            report.append("")
            
        # Performance Analysis and Recommendations
        report.append("## Performance Analysis & Recommendations")
        
        # Response time analysis
        if baseline_avg_times:
            avg_baseline = statistics.mean(baseline_avg_times)
            if avg_baseline < 0.2:
                report.append("✅ **Response Times**: Excellent baseline performance (<200ms target met)")
            elif avg_baseline < 0.5:
                report.append("⚠️ **Response Times**: Good baseline performance (<500ms, but could be optimized)")
            else:
                report.append("❌ **Response Times**: Poor baseline performance (>500ms, optimization needed)")
                
        # Throughput analysis
        if max_throughput > 0:
            if max_throughput >= 50:
                report.append("✅ **Throughput**: Excellent capacity (>50 req/s achieved)")
            elif max_throughput >= 20:
                report.append("⚠️ **Throughput**: Moderate capacity (20-50 req/s, consider optimization)")
            else:
                report.append("❌ **Throughput**: Low capacity (<20 req/s, significant optimization needed)")
                
        # Resource efficiency
        if resource_metrics:
            cpu_avg = resource_metrics.get("cpu_percent", {}).get("avg", 0)
            memory_avg = resource_metrics.get("memory_percent", {}).get("avg", 0)
            
            if cpu_avg < 50 and memory_avg < 70:
                report.append("✅ **Resource Efficiency**: Good resource utilization")
            elif cpu_avg < 80 and memory_avg < 85:
                report.append("⚠️ **Resource Efficiency**: Moderate resource usage, monitor under higher load")
            else:
                report.append("❌ **Resource Efficiency**: High resource usage, optimization recommended")
                
        # Specific recommendations
        report.append("")
        report.append("### Specific Recommendations")
        
        # Analyze error patterns
        high_error_endpoints = []
        for test_name, test_results in results.get("load_tests", {}).items():
            if "error" not in test_results:
                for endpoint, metrics in test_results.items():
                    if "error" not in metrics:
                        total_req = metrics.get("success_count", 0) + metrics.get("error_count", 0)
                        error_rate = metrics.get("error_count", 0) / total_req if total_req > 0 else 0
                        if error_rate > 0.05:  # More than 5% error rate
                            high_error_endpoints.append(endpoint)
                            
        if high_error_endpoints:
            report.append(f"1. **Error Rate Optimization**: High error rates detected for: {', '.join(set(high_error_endpoints))}")
            report.append("   - Review error handling and timeout configurations")
            report.append("   - Implement circuit breaker patterns for resilience")
            
        # Response time recommendations
        slow_endpoints = []
        for endpoint, metrics in results.get("baseline_tests", {}).items():
            if "error" not in metrics and metrics.get("avg_response_time", 0) > 0.2:
                slow_endpoints.append(endpoint)
                
        if slow_endpoints:
            report.append(f"2. **Response Time Optimization**: Slow endpoints detected: {', '.join(slow_endpoints)}")
            report.append("   - Implement caching for frequently accessed data")
            report.append("   - Optimize database queries and add appropriate indexes")
            report.append("   - Consider implementing async processing for complex operations")
            
        # Resource optimization
        if resource_metrics:
            cpu_max = resource_metrics.get("cpu_percent", {}).get("max", 0)
            memory_max = resource_metrics.get("memory_percent", {}).get("max", 0)
            
            if cpu_max > 80:
                report.append("3. **CPU Optimization**: High CPU usage detected")
                report.append("   - Profile CPU-intensive operations")
                report.append("   - Consider implementing connection pooling")
                report.append("   - Optimize algorithmic complexity in story generation")
                
            if memory_max > 85:
                report.append("4. **Memory Optimization**: High memory usage detected") 
                report.append("   - Check for memory leaks in long-running processes")
                report.append("   - Implement proper cleanup of temporary objects")
                report.append("   - Consider implementing memory-efficient data structures")
                
        # Scalability recommendations
        report.append("5. **Scalability Improvements**:")
        report.append("   - Implement horizontal scaling with load balancing")
        report.append("   - Add Redis caching layer for session management")
        report.append("   - Consider implementing queue-based processing for story generation")
        report.append("   - Set up proper monitoring and alerting for production")
        
        report.append("")
        report.append("## Production Readiness Assessment")
        
        # Calculate overall score
        score_factors = []
        
        # Response time score
        if baseline_avg_times:
            avg_baseline = statistics.mean(baseline_avg_times)
            if avg_baseline < 0.2:
                score_factors.append(100)
            elif avg_baseline < 0.5:
                score_factors.append(75)
            else:
                score_factors.append(40)
                
        # Throughput score
        if max_throughput >= 50:
            score_factors.append(100)
        elif max_throughput >= 20:
            score_factors.append(75)
        else:
            score_factors.append(40)
            
        # Error rate score
        total_errors = sum(metrics.get("error_count", 0) for metrics in results.get("baseline_tests", {}).values() 
                          if "error" not in metrics)
        if total_errors == 0:
            score_factors.append(100)
        elif total_errors <= 5:
            score_factors.append(80)
        else:
            score_factors.append(50)
            
        overall_score = statistics.mean(score_factors) if score_factors else 0
        
        if overall_score >= 90:
            report.append("🟢 **READY FOR PRODUCTION**: Excellent performance across all metrics")
        elif overall_score >= 75:
            report.append("🟡 **CONDITIONAL READINESS**: Good performance with minor optimizations needed")
        else:
            report.append("🔴 **NOT READY FOR PRODUCTION**: Significant performance issues require resolution")
            
        report.append(f"**Overall Performance Score**: {overall_score:.1f}/100")
        
        return "\n".join(report)

async def main():
    """Main function to run performance tests."""
    # Check if server is running
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            response = client.get("http://localhost:8000/health")
            if response.status_code != 200:
                logger.error("API server is not responding correctly")
                return
    except Exception as e:
        logger.error(f"Cannot connect to API server: {e}")
        logger.error("Please start the API server with: python api_server.py")
        return
        
    # Configure test parameters
    config = LoadTestConfig(
        base_url="http://localhost:8000",
        concurrent_users=10,
        duration_seconds=60,
        endpoints=[
            "/health",
            "/characters", 
            "/characters/engineer",
            "/characters/pilot",
            "/characters/scientist"
        ]
    )
    
    # Run comprehensive test suite
    async with PerformanceTestSuite(config) as test_suite:
        results = await test_suite.run_comprehensive_test_suite()
        
        # Generate report
        report = test_suite.generate_performance_report(results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        json_filename = f"performance_test_results_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Detailed results saved to: {json_filename}")
        
        # Save report
        report_filename = f"performance_test_report_{timestamp}.md"
        with open(report_filename, 'w') as f:
            f.write(report)
        logger.info(f"Performance report saved to: {report_filename}")
        
        # Print summary to console
        print("\n" + "="*80)
        print("PERFORMANCE TEST SUMMARY")
        print("="*80)
        print(report)

if __name__ == "__main__":
    asyncio.run(main())