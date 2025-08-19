#!/usr/bin/env python3
"""
Comprehensive Performance and Load Testing Suite for Novel Engine

This comprehensive testing suite evaluates Novel Engine's production readiness
across multiple performance dimensions with detailed metrics and analysis.
"""

import asyncio
import aiohttp
import time
import statistics
import json
import psutil
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    endpoint: str
    test_type: str
    concurrent_users: int
    duration_seconds: float
    response_times: List[float]
    success_count: int
    error_count: int
    
    # Calculated metrics
    avg_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0
    
    def calculate_statistics(self):
        """Calculate all statistical metrics."""
        if not self.response_times:
            return
            
        self.response_times.sort()
        n = len(self.response_times)
        
        self.avg_response_time = statistics.mean(self.response_times)
        self.min_response_time = self.response_times[0]
        self.max_response_time = self.response_times[-1]
        
        if n >= 2:
            self.p50_response_time = self.response_times[int(0.50 * n)]
            self.p95_response_time = self.response_times[int(0.95 * n)]
            self.p99_response_time = self.response_times[int(0.99 * n)]
            
        total_requests = self.success_count + self.error_count
        if total_requests > 0:
            self.error_rate = self.error_count / total_requests
            if self.duration_seconds > 0:
                self.throughput = total_requests / self.duration_seconds

@dataclass  
class ResourceSnapshot:
    """System resource usage snapshot."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    process_count: int

class SystemMonitor:
    """System resource monitoring."""
    
    def __init__(self):
        self.monitoring = False
        self.snapshots: List[ResourceSnapshot] = []
        self.api_process = None
        
    def start_monitoring(self):
        """Start resource monitoring."""
        self.monitoring = True
        self.snapshots = []
        
        # Find API server process
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if ('python' in proc.info['name'] and 
                    proc.info['cmdline'] and
                    'api_server.py' in ' '.join(proc.info['cmdline'])):
                    self.api_process = psutil.Process(proc.info['pid'])
                    logger.info(f"Monitoring API process PID: {proc.info['pid']}")
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        self._monitor_thread = threading.Thread(target=self._monitor_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring = False
        if hasattr(self, '_monitor_thread'):
            self._monitor_thread.join(timeout=5)
            
    def _monitor_loop(self):
        """Resource monitoring loop."""
        while self.monitoring:
            try:
                if self.api_process and self.api_process.is_running():
                    # Monitor specific process
                    cpu_percent = self.api_process.cpu_percent()
                    memory_info = self.api_process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    memory_percent = self.api_process.memory_percent()
                    process_count = len(self.api_process.children(recursive=True)) + 1
                else:
                    # System-wide monitoring
                    cpu_percent = psutil.cpu_percent()
                    memory = psutil.virtual_memory()
                    memory_percent = memory.percent
                    memory_mb = memory.used / 1024 / 1024
                    process_count = len(psutil.pids())
                    
                snapshot = ResourceSnapshot(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    memory_mb=memory_mb,
                    process_count=process_count
                )
                self.snapshots.append(snapshot)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                
            time.sleep(1)
            
    def get_summary(self) -> Dict[str, Any]:
        """Get monitoring summary."""
        if not self.snapshots:
            return {}
            
        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_percent for s in self.snapshots]
        memory_mb_values = [s.memory_mb for s in self.snapshots]
        
        return {
            "duration_seconds": self.snapshots[-1].timestamp - self.snapshots[0].timestamp,
            "sample_count": len(self.snapshots),
            "cpu_percent": {
                "avg": statistics.mean(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values),
                "p95": sorted(cpu_values)[int(0.95 * len(cpu_values))] if len(cpu_values) > 1 else cpu_values[0]
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
            }
        }

class LoadTestSuite:
    """Comprehensive load testing suite."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.monitor = SystemMonitor()
        
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=200, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            
    async def make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Tuple[float, bool, int, str]:
        """Make HTTP request and measure performance."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url) as response:
                    await response.text()
                    end_time = time.time()
                    return (end_time - start_time, response.status < 400, 
                           response.status, "")
            else:
                async with self.session.post(url, json=data) as response:
                    await response.text()
                    end_time = time.time()
                    return (end_time - start_time, response.status < 400,
                           response.status, "")
                           
        except Exception as e:
            end_time = time.time()
            return (end_time - start_time, False, 0, str(e))
            
    async def baseline_test(self, endpoint: str, requests: int = 20) -> PerformanceMetrics:
        """Sequential baseline performance test."""
        logger.info(f"Baseline test: {endpoint} ({requests} requests)")
        
        metrics = PerformanceMetrics(
            endpoint=endpoint,
            test_type="baseline",
            concurrent_users=1,
            duration_seconds=0,
            response_times=[],
            success_count=0,
            error_count=0
        )
        
        start_time = time.time()
        
        for i in range(requests):
            response_time, success, status, error = await self.make_request(endpoint)
            metrics.response_times.append(response_time)
            
            if success:
                metrics.success_count += 1
            else:
                metrics.error_count += 1
                
        metrics.duration_seconds = time.time() - start_time
        metrics.calculate_statistics()
        return metrics
        
    async def load_test(self, endpoint: str, concurrent_users: int, 
                       duration: int = 30, method: str = "GET", 
                       data: Dict = None) -> PerformanceMetrics:
        """Concurrent load testing."""
        logger.info(f"Load test: {endpoint} with {concurrent_users} users for {duration}s")
        
        metrics = PerformanceMetrics(
            endpoint=endpoint,
            test_type="load",
            concurrent_users=concurrent_users,
            duration_seconds=duration,
            response_times=[],
            success_count=0,
            error_count=0
        )
        
        start_time = time.time()
        end_time = start_time + duration
        
        async def user_session():
            """Single user session."""
            session_results = []
            while time.time() < end_time:
                response_time, success, status, error = await self.make_request(endpoint, method, data)
                session_results.append((response_time, success))
                await asyncio.sleep(0.1)  # Small delay
            return session_results
            
        # Run concurrent users
        tasks = [user_session() for _ in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for result in results:
            if isinstance(result, list):
                for response_time, success in result:
                    metrics.response_times.append(response_time)
                    if success:
                        metrics.success_count += 1
                    else:
                        metrics.error_count += 1
                        
        metrics.duration_seconds = time.time() - start_time
        metrics.calculate_statistics()
        return metrics
        
    async def stress_test(self, endpoint: str, max_users: int = 50, 
                         step_size: int = 10, step_duration: int = 20) -> List[PerformanceMetrics]:
        """Progressive stress testing to find breaking point."""
        logger.info(f"Stress test: {endpoint} from {step_size} to {max_users} users")
        
        results = []
        current_users = step_size
        
        while current_users <= max_users:
            metrics = await self.load_test(endpoint, current_users, step_duration)
            results.append(metrics)
            
            logger.info(f"{current_users} users: {metrics.throughput:.2f} req/s, "
                       f"{metrics.error_rate:.2%} errors, {metrics.avg_response_time:.3f}s avg")
            
            # Stop if error rate is too high or performance degrades significantly
            if metrics.error_rate > 0.5 or metrics.avg_response_time > 5.0:
                logger.warning(f"Breaking point reached at {current_users} users")
                break
                
            current_users += step_size
            await asyncio.sleep(2)  # Brief pause between tests
            
        return results
        
    def simulation_load_test(self, concurrent_simulations: int = 3) -> Dict[str, Any]:
        """Test story generation simulation under load."""
        logger.info(f"Simulation load test: {concurrent_simulations} concurrent simulations")
        
        def run_simulation():
            """Run single simulation."""
            import httpx
            start_time = time.time()
            
            try:
                simulation_data = {
                    "character_names": ["engineer", "pilot"],
                    "turns": 2
                }
                
                with httpx.Client(timeout=45.0) as client:
                    response = client.post(
                        f"{self.base_url}/simulations",
                        json=simulation_data
                    )
                    
                end_time = time.time()
                return {
                    "response_time": end_time - start_time,
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "content_length": len(response.text) if response.status_code < 400 else 0
                }
                
            except Exception as e:
                return {
                    "response_time": time.time() - start_time,
                    "success": False,
                    "status_code": 0,
                    "error": str(e)
                }
                
        # Run concurrent simulations
        with ThreadPoolExecutor(max_workers=concurrent_simulations) as executor:
            futures = [executor.submit(run_simulation) for _ in range(concurrent_simulations)]
            results = []
            
            for future in as_completed(futures, timeout=90):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "response_time": 0,
                        "success": False,
                        "error": str(e)
                    })
                    
        # Calculate metrics
        response_times = [r["response_time"] for r in results if r["response_time"] > 0]
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "concurrent_simulations": concurrent_simulations,
            "total_simulations": len(results),
            "success_count": success_count,
            "error_count": len(results) - success_count,
            "success_rate": success_count / len(results) if results else 0,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "results": results
        }
        
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run complete test suite."""
        logger.info("Starting comprehensive performance test suite")
        
        # Start monitoring
        self.monitor.start_monitoring()
        test_start = time.time()
        
        results = {
            "test_metadata": {
                "start_time": datetime.now().isoformat(),
                "base_url": self.base_url,
                "test_suite_version": "1.0"
            },
            "baseline_tests": {},
            "load_tests": {},
            "stress_tests": {},
            "simulation_tests": {},
            "resource_metrics": {}
        }
        
        try:
            # 1. Baseline Performance Tests
            logger.info("=== Baseline Performance Tests ===")
            endpoints = ["/health", "/characters"]
            
            for endpoint in endpoints:
                try:
                    metrics = await self.baseline_test(endpoint, 20)
                    results["baseline_tests"][endpoint] = asdict(metrics)
                    logger.info(f"Baseline {endpoint}: avg={metrics.avg_response_time:.3f}s, "
                              f"p95={metrics.p95_response_time:.3f}s, errors={metrics.error_count}")
                except Exception as e:
                    logger.error(f"Baseline test failed for {endpoint}: {e}")
                    results["baseline_tests"][endpoint] = {"error": str(e)}
                    
            # 2. Load Testing
            logger.info("=== Load Testing ===")
            load_configs = [
                {"users": 5, "duration": 20},
                {"users": 10, "duration": 20}, 
                {"users": 25, "duration": 30},
                {"users": 50, "duration": 30}
            ]
            
            for config in load_configs:
                users = config["users"]
                duration = config["duration"]
                test_name = f"{users}_users"
                results["load_tests"][test_name] = {}
                
                for endpoint in ["/health", "/characters"]:
                    try:
                        metrics = await self.load_test(endpoint, users, duration)
                        results["load_tests"][test_name][endpoint] = asdict(metrics)
                        logger.info(f"{users} users {endpoint}: {metrics.throughput:.2f} req/s, "
                                  f"{metrics.error_rate:.2%} errors")
                    except Exception as e:
                        logger.error(f"Load test failed: {users} users, {endpoint}: {e}")
                        results["load_tests"][test_name][endpoint] = {"error": str(e)}
                        
            # 3. Stress Testing
            logger.info("=== Stress Testing ===")
            for endpoint in ["/health", "/characters"]:
                try:
                    stress_results = await self.stress_test(endpoint, max_users=60, step_size=15)
                    results["stress_tests"][endpoint] = [asdict(m) for m in stress_results]
                except Exception as e:
                    logger.error(f"Stress test failed for {endpoint}: {e}")
                    results["stress_tests"][endpoint] = {"error": str(e)}
                    
            # 4. Simulation Load Testing
            logger.info("=== Simulation Load Testing ===")
            for sim_count in [2, 3, 5]:
                try:
                    sim_results = self.simulation_load_test(sim_count)
                    results["simulation_tests"][f"{sim_count}_simulations"] = sim_results
                    logger.info(f"{sim_count} simulations: success_rate={sim_results['success_rate']:.2%}, "
                              f"avg_time={sim_results['avg_response_time']:.2f}s")
                except Exception as e:
                    logger.error(f"Simulation test failed for {sim_count}: {e}")
                    results["simulation_tests"][f"{sim_count}_simulations"] = {"error": str(e)}
                    
        finally:
            # Stop monitoring
            self.monitor.stop_monitoring()
            results["resource_metrics"] = self.monitor.get_summary()
            results["test_metadata"]["total_duration"] = time.time() - test_start
            
        logger.info("Comprehensive test suite completed")
        return results

def analyze_performance_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze test results and provide assessment."""
    analysis = {
        "overall_score": 0,
        "performance_grade": "Unknown",
        "ready_for_production": False,
        "key_findings": [],
        "recommendations": [],
        "bottlenecks": [],
        "capacity_analysis": {}
    }
    
    score_components = []
    
    # Analyze baseline performance
    baseline_metrics = []
    for endpoint, data in results.get("baseline_tests", {}).items():
        if "error" not in data:
            baseline_metrics.append(data["avg_response_time"])
            if data["avg_response_time"] > 0.5:  # >500ms is concerning
                analysis["bottlenecks"].append(f"Slow baseline response: {endpoint}")
                
    if baseline_metrics:
        avg_baseline = statistics.mean(baseline_metrics)
        if avg_baseline < 0.1:
            score_components.append(95)
            analysis["key_findings"].append("Excellent baseline response times (<100ms)")
        elif avg_baseline < 0.2:
            score_components.append(85)
            analysis["key_findings"].append("Good baseline response times (<200ms)")
        elif avg_baseline < 0.5:
            score_components.append(70)
            analysis["key_findings"].append("Acceptable baseline response times (<500ms)")
        else:
            score_components.append(40)
            analysis["key_findings"].append("Poor baseline response times (>500ms)")
            analysis["recommendations"].append("Optimize slow endpoints for better response times")
            
    # Analyze load testing capacity
    max_throughput = 0
    max_stable_users = 0
    
    for test_name, test_data in results.get("load_tests", {}).items():
        if isinstance(test_data, dict) and "error" not in test_data:
            users = int(test_name.split("_")[0])
            for endpoint, metrics in test_data.items():
                if "error" not in metrics:
                    throughput = metrics.get("throughput", 0)
                    error_rate = metrics.get("error_rate", 1.0)
                    
                    if throughput > max_throughput:
                        max_throughput = throughput
                        
                    if error_rate < 0.05:  # Less than 5% errors
                        max_stable_users = max(max_stable_users, users)
                        
    analysis["capacity_analysis"]["max_throughput"] = max_throughput
    analysis["capacity_analysis"]["max_stable_users"] = max_stable_users
    
    if max_throughput > 100:
        score_components.append(95)
        analysis["key_findings"].append(f"Excellent throughput capacity ({max_throughput:.0f} req/s)")
    elif max_throughput > 50:
        score_components.append(85)
        analysis["key_findings"].append(f"Good throughput capacity ({max_throughput:.0f} req/s)")
    elif max_throughput > 20:
        score_components.append(70)
        analysis["key_findings"].append(f"Moderate throughput capacity ({max_throughput:.0f} req/s)")
    else:
        score_components.append(50)
        analysis["key_findings"].append(f"Limited throughput capacity ({max_throughput:.0f} req/s)")
        analysis["recommendations"].append("Improve system throughput and concurrent handling")
        
    # Analyze error rates
    error_rates = []
    for test_name, test_data in results.get("load_tests", {}).items():
        if isinstance(test_data, dict):
            for endpoint, metrics in test_data.items():
                if "error" not in metrics:
                    error_rates.append(metrics.get("error_rate", 0))
                    
    if error_rates:
        avg_error_rate = statistics.mean(error_rates)
        if avg_error_rate < 0.01:
            score_components.append(95)
            analysis["key_findings"].append("Excellent reliability (<1% error rate)")
        elif avg_error_rate < 0.05:
            score_components.append(85)
            analysis["key_findings"].append("Good reliability (<5% error rate)")
        elif avg_error_rate < 0.1:
            score_components.append(70)
            analysis["key_findings"].append("Acceptable reliability (<10% error rate)")
        else:
            score_components.append(50)
            analysis["key_findings"].append("Poor reliability (>10% error rate)")
            analysis["recommendations"].append("Improve error handling and system stability")
            
    # Analyze simulation performance
    sim_success_rates = []
    for test_name, sim_data in results.get("simulation_tests", {}).items():
        if "error" not in sim_data:
            sim_success_rates.append(sim_data.get("success_rate", 0))
            
    if sim_success_rates:
        avg_sim_success = statistics.mean(sim_success_rates)
        if avg_sim_success > 0.9:
            score_components.append(90)
            analysis["key_findings"].append("Excellent story generation reliability")
        elif avg_sim_success > 0.7:
            score_components.append(75)
            analysis["key_findings"].append("Good story generation reliability")
        else:
            score_components.append(50)
            analysis["key_findings"].append("Poor story generation reliability")
            analysis["recommendations"].append("Improve story generation endpoint stability")
    else:
        analysis["key_findings"].append("Story generation testing failed")
        analysis["recommendations"].append("Fix story generation endpoint issues")
        
    # Calculate overall score
    if score_components:
        analysis["overall_score"] = statistics.mean(score_components)
    
    # Determine grade and production readiness
    score = analysis["overall_score"]
    if score >= 90:
        analysis["performance_grade"] = "A"
        analysis["ready_for_production"] = True
        analysis["key_findings"].append("System ready for production deployment")
    elif score >= 80:
        analysis["performance_grade"] = "B"
        analysis["ready_for_production"] = True
        analysis["key_findings"].append("System ready for production with monitoring")
    elif score >= 70:
        analysis["performance_grade"] = "C"
        analysis["ready_for_production"] = False
        analysis["key_findings"].append("System needs optimization before production")
    else:
        analysis["performance_grade"] = "D"
        analysis["ready_for_production"] = False
        analysis["key_findings"].append("System requires significant improvement")
        
    # Resource usage analysis
    resource_metrics = results.get("resource_metrics", {})
    if resource_metrics:
        cpu_max = resource_metrics.get("cpu_percent", {}).get("max", 0)
        memory_max = resource_metrics.get("memory_percent", {}).get("max", 0)
        
        if cpu_max > 80:
            analysis["bottlenecks"].append("High CPU usage detected")
            analysis["recommendations"].append("Optimize CPU-intensive operations")
            
        if memory_max > 80:
            analysis["bottlenecks"].append("High memory usage detected") 
            analysis["recommendations"].append("Optimize memory usage and check for leaks")
            
    return analysis

def generate_performance_report(results: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """Generate comprehensive performance report."""
    report = []
    
    # Header
    report.append("# Novel Engine Performance Test Report")
    report.append(f"Generated: {results['test_metadata']['start_time']}")
    report.append(f"Test Duration: {results['test_metadata'].get('total_duration', 0):.2f} seconds")
    report.append("")
    
    # Executive Summary
    report.append("## Executive Summary")
    report.append(f"**Performance Grade**: {analysis['performance_grade']}")
    report.append(f"**Overall Score**: {analysis['overall_score']:.1f}/100")
    report.append(f"**Production Ready**: {'✅ Yes' if analysis['ready_for_production'] else '❌ No'}")
    report.append("")
    
    # Key Findings
    report.append("### Key Findings")
    for finding in analysis["key_findings"]:
        report.append(f"- {finding}")
    report.append("")
    
    # Capacity Analysis
    capacity = analysis.get("capacity_analysis", {})
    if capacity:
        report.append("### Capacity Analysis")
        report.append(f"- **Maximum Throughput**: {capacity.get('max_throughput', 0):.0f} requests/second")
        report.append(f"- **Stable Concurrent Users**: {capacity.get('max_stable_users', 0)} users")
        report.append("")
    
    # Detailed Results
    report.append("## Detailed Test Results")
    
    # Baseline Tests
    report.append("### Baseline Performance")
    report.append("| Endpoint | Avg (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Error Count |")
    report.append("|----------|----------|----------|----------|----------|-------------|")
    
    for endpoint, data in results.get("baseline_tests", {}).items():
        if "error" not in data:
            avg = data["avg_response_time"] * 1000
            p50 = data["p50_response_time"] * 1000
            p95 = data["p95_response_time"] * 1000
            p99 = data["p99_response_time"] * 1000
            errors = data["error_count"]
            report.append(f"| {endpoint} | {avg:.1f} | {p50:.1f} | {p95:.1f} | {p99:.1f} | {errors} |")
        else:
            report.append(f"| {endpoint} | ERROR | ERROR | ERROR | ERROR | ERROR |")
    report.append("")
    
    # Load Tests
    report.append("### Load Test Results")
    for test_name, test_data in results.get("load_tests", {}).items():
        users = test_name.replace("_", " ").title()
        report.append(f"#### {users}")
        report.append("| Endpoint | Throughput (req/s) | Avg (ms) | P95 (ms) | Error Rate |")
        report.append("|----------|-------------------|----------|----------|------------|")
        
        if isinstance(test_data, dict) and "error" not in test_data:
            for endpoint, metrics in test_data.items():
                if "error" not in metrics:
                    throughput = metrics["throughput"]
                    avg_ms = metrics["avg_response_time"] * 1000
                    p95_ms = metrics["p95_response_time"] * 1000
                    error_rate = metrics["error_rate"]
                    report.append(f"| {endpoint} | {throughput:.1f} | {avg_ms:.1f} | {p95_ms:.1f} | {error_rate:.2%} |")
                else:
                    report.append(f"| {endpoint} | ERROR | ERROR | ERROR | ERROR |")
        report.append("")
    
    # Simulation Tests
    report.append("### Story Generation Load Tests")
    report.append("| Concurrent Sims | Success Rate | Avg Time (s) | Max Time (s) |")
    report.append("|----------------|--------------|--------------|--------------|")
    
    for test_name, sim_data in results.get("simulation_tests", {}).items():
        if "error" not in sim_data:
            sims = test_name.replace("_", " ").title()
            success_rate = sim_data["success_rate"]
            avg_time = sim_data["avg_response_time"]
            max_time = sim_data["max_response_time"]
            report.append(f"| {sims} | {success_rate:.1%} | {avg_time:.2f} | {max_time:.2f} |")
        else:
            report.append(f"| {test_name} | ERROR | ERROR | ERROR |")
    report.append("")
    
    # Resource Usage
    resource_metrics = results.get("resource_metrics", {})
    if resource_metrics:
        report.append("### Resource Usage")
        report.append("| Metric | Average | Maximum | Peak |")
        report.append("|--------|---------|---------|------|")
        
        cpu_data = resource_metrics.get("cpu_percent", {})
        if cpu_data:
            report.append(f"| CPU Usage (%) | {cpu_data.get('avg', 0):.1f} | {cpu_data.get('max', 0):.1f} | {cpu_data.get('p95', 0):.1f} |")
            
        memory_data = resource_metrics.get("memory_percent", {})
        if memory_data:
            report.append(f"| Memory Usage (%) | {memory_data.get('avg', 0):.1f} | {memory_data.get('max', 0):.1f} | N/A |")
            
        memory_mb_data = resource_metrics.get("memory_mb", {})
        if memory_mb_data:
            report.append(f"| Memory Usage (MB) | {memory_mb_data.get('avg', 0):.0f} | {memory_mb_data.get('max', 0):.0f} | N/A |")
        report.append("")
    
    # Bottlenecks and Recommendations
    if analysis["bottlenecks"]:
        report.append("## Performance Bottlenecks")
        for bottleneck in analysis["bottlenecks"]:
            report.append(f"- ⚠️ {bottleneck}")
        report.append("")
    
    if analysis["recommendations"]:
        report.append("## Recommendations")
        for i, recommendation in enumerate(analysis["recommendations"], 1):
            report.append(f"{i}. {recommendation}")
        report.append("")
    
    # Production Deployment Guidance
    report.append("## Production Deployment Guidance")
    if analysis["ready_for_production"]:
        report.append("✅ **System is ready for production deployment**")
        report.append("")
        report.append("### Recommended Production Configuration")
        report.append("- Monitor response times and error rates")
        report.append("- Set up alerting for performance degradation")
        report.append("- Implement proper logging and observability")
        report.append("- Consider load balancing for high availability")
    else:
        report.append("❌ **System requires optimization before production**")
        report.append("")
        report.append("### Critical Issues to Address")
        report.append("- Address performance bottlenecks identified above")
        report.append("- Implement recommended optimizations")
        report.append("- Re-run performance tests after improvements")
        report.append("- Ensure error rates are below 5% under normal load")
    
    return "\n".join(report)

async def main():
    """Run comprehensive performance testing."""
    # Server connectivity check
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            response = client.get("http://localhost:8000/health")
            if response.status_code != 200:
                logger.error("API server not responding correctly")
                return
    except Exception as e:
        logger.error(f"Cannot connect to API server: {e}")
        logger.error("Please start the API server with: python api_server.py")
        return
        
    # Run comprehensive tests
    async with LoadTestSuite() as test_suite:
        results = await test_suite.run_comprehensive_tests()
        analysis = analyze_performance_results(results)
        report = generate_performance_report(results, analysis)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        json_file = f"performance_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({"results": results, "analysis": analysis}, f, indent=2, default=str)
        
        # Save report
        report_file = f"performance_report_{timestamp}.md"
        with open(report_file, 'w') as f:
            f.write(report)
            
        logger.info(f"Results saved to: {json_file}")
        logger.info(f"Report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("NOVEL ENGINE PERFORMANCE TEST SUMMARY")
        print("="*80)
        print(report)

if __name__ == "__main__":
    asyncio.run(main())