#!/usr/bin/env python3
"""
Production System Stability Validation Suite.

Comprehensive stability testing for Novel Engine production deployment validation.
Tests all critical systems under normal and stress conditions.
"""

import time
import json
import asyncio
import requests
import logging
import threading
import concurrent.futures
import gc
import sys
import psutil
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import sqlite3
import uuid
import os
from pathlib import Path

# Configure logging for comprehensive monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_stability_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class StabilityTestResult:
    """Result from a stability test."""
    test_name: str
    success: bool
    duration: float
    message: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PerformanceMetrics:
    """Performance metrics collection."""
    response_times: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)
    concurrent_users: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    
    def add_response_time(self, time_ms: float):
        self.response_times.append(time_ms)
    
    def add_system_metrics(self, memory_mb: float, cpu_percent: float):
        self.memory_usage.append(memory_mb)
        self.cpu_usage.append(cpu_percent)
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.response_times:
            return {"error": "No data collected"}
        
        return {
            "response_time_stats": {
                "mean": statistics.mean(self.response_times),
                "median": statistics.median(self.response_times),
                "p95": sorted(self.response_times)[int(0.95 * len(self.response_times))],
                "p99": sorted(self.response_times)[int(0.99 * len(self.response_times))],
                "max": max(self.response_times),
                "min": min(self.response_times)
            },
            "system_stats": {
                "avg_memory_mb": statistics.mean(self.memory_usage) if self.memory_usage else 0,
                "peak_memory_mb": max(self.memory_usage) if self.memory_usage else 0,
                "avg_cpu_percent": statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
                "peak_cpu_percent": max(self.cpu_usage) if self.cpu_usage else 0
            },
            "request_stats": {
                "total_requests": self.successful_requests + self.failed_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate": (self.successful_requests / (self.successful_requests + self.failed_requests)) * 100 if (self.successful_requests + self.failed_requests) > 0 else 0
            },
            "duration_seconds": (datetime.now() - self.start_time).total_seconds()
        }

class ProductionStabilityValidator:
    """Comprehensive production stability validation suite."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[StabilityTestResult] = []
        self.test_start_time = datetime.now()
        
    def log_result(self, result: StabilityTestResult):
        """Log test result."""
        self.results.append(result)
        status = "PASS" if result.success else "FAIL"
        logger.info(f"[{status}] {result.test_name}: {result.message} ({result.duration:.3f}s)")
    
    def test_api_health_stability(self) -> StabilityTestResult:
        """Test API health endpoint stability."""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    return StabilityTestResult(
                        "API Health Check",
                        True,
                        duration,
                        f"API healthy, response: {data}",
                        {"response_time_ms": duration * 1000}
                    )
                else:
                    return StabilityTestResult("API Health Check", False, duration, f"API unhealthy: {data}")
            else:
                return StabilityTestResult("API Health Check", False, duration, f"HTTP {response.status_code}")
        except Exception as e:
            duration = time.time() - start_time
            return StabilityTestResult("API Health Check", False, duration, f"Error: {e}")
    
    def test_character_list_stability(self) -> StabilityTestResult:
        """Test character listing endpoint stability."""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/characters", timeout=10)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                character_count = len(data.get("characters", []))
                return StabilityTestResult(
                    "Character List",
                    True,
                    duration,
                    f"Found {character_count} characters",
                    {"character_count": character_count, "response_time_ms": duration * 1000}
                )
            else:
                return StabilityTestResult("Character List", False, duration, f"HTTP {response.status_code}")
        except Exception as e:
            duration = time.time() - start_time
            return StabilityTestResult("Character List", False, duration, f"Error: {e}")
    
    def test_concurrent_api_access(self, concurrent_users: int = 10, requests_per_user: int = 5) -> StabilityTestResult:
        """Test API under concurrent load."""
        start_time = time.time()
        metrics = PerformanceMetrics()
        metrics.concurrent_users = concurrent_users
        
        def make_request():
            try:
                req_start = time.time()
                response = requests.get(f"{self.base_url}/health", timeout=10)
                req_duration = (time.time() - req_start) * 1000  # Convert to ms
                
                if response.status_code == 200:
                    metrics.successful_requests += 1
                    metrics.add_response_time(req_duration)
                else:
                    metrics.failed_requests += 1
                return True
            except Exception as e:
                metrics.failed_requests += 1
                logger.warning(f"Request failed: {e}")
                return False
        
        # Monitor system resources during test
        def monitor_resources():
            while not getattr(monitor_resources, 'stop', False):
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                metrics.add_system_metrics(memory_mb, cpu_percent)
                time.sleep(0.5)
        
        monitor_thread = threading.Thread(target=monitor_resources)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            # Execute concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = []
                for user in range(concurrent_users):
                    for _ in range(requests_per_user):
                        futures.append(executor.submit(make_request))
                
                # Wait for all requests to complete
                concurrent.futures.wait(futures)
            
            # Stop monitoring
            monitor_resources.stop = True
            monitor_thread.join(timeout=1)
            
            duration = time.time() - start_time
            stats = metrics.get_stats()
            
            success = (stats["request_stats"]["success_rate"] >= 95.0 and 
                      stats["response_time_stats"]["p95"] <= 1000)  # 95% success rate, P95 < 1s
            
            message = f"Concurrent test: {stats['request_stats']['success_rate']:.1f}% success rate, P95: {stats['response_time_stats']['p95']:.0f}ms"
            
            return StabilityTestResult(
                "Concurrent API Access",
                success,
                duration,
                message,
                stats
            )
            
        except Exception as e:
            monitor_resources.stop = True
            duration = time.time() - start_time
            return StabilityTestResult("Concurrent API Access", False, duration, f"Error: {e}")
    
    def test_story_generation_stability(self) -> StabilityTestResult:
        """Test story generation endpoint stability."""
        start_time = time.time()
        try:
            # First get available characters
            char_response = requests.get(f"{self.base_url}/characters", timeout=10)
            if char_response.status_code != 200:
                return StabilityTestResult("Story Generation", False, time.time() - start_time, 
                                         "Failed to get characters list")
            
            characters = char_response.json().get("characters", [])
            if len(characters) < 2:
                return StabilityTestResult("Story Generation", False, time.time() - start_time, 
                                         "Insufficient characters for story generation")
            
            # Request story generation
            payload = {
                "character_names": characters[:2],
                "turns": 2
            }
            
            response = requests.post(f"{self.base_url}/simulate", json=payload, timeout=30)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                story_length = len(data.get("story", ""))
                return StabilityTestResult(
                    "Story Generation",
                    True,
                    duration,
                    f"Generated story with {story_length} characters",
                    {"story_length": story_length, "response_time_ms": duration * 1000}
                )
            else:
                return StabilityTestResult("Story Generation", False, duration, f"HTTP {response.status_code}")
        except Exception as e:
            duration = time.time() - start_time
            return StabilityTestResult("Story Generation", False, duration, f"Error: {e}")
    
    def test_memory_leak_detection(self, iterations: int = 20) -> StabilityTestResult:
        """Test for memory leaks during repeated operations."""
        start_time = time.time()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_readings = [initial_memory]
        
        try:
            for i in range(iterations):
                # Perform memory-intensive operation
                response = requests.get(f"{self.base_url}/health", timeout=10)
                if response.status_code != 200:
                    break
                
                # Force garbage collection
                gc.collect()
                
                # Record memory usage
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_readings.append(current_memory)
                
                # Brief pause to allow cleanup
                time.sleep(0.1)
            
            duration = time.time() - start_time
            final_memory = memory_readings[-1]
            memory_increase = final_memory - initial_memory
            
            # Consider it a leak if memory increased by more than 50MB
            has_leak = memory_increase > 50
            
            return StabilityTestResult(
                "Memory Leak Detection",
                not has_leak,
                duration,
                f"Memory: {initial_memory:.1f}MB → {final_memory:.1f}MB (Δ{memory_increase:+.1f}MB)",
                {
                    "initial_memory_mb": initial_memory,
                    "final_memory_mb": final_memory,
                    "memory_increase_mb": memory_increase,
                    "iterations": iterations,
                    "memory_readings": memory_readings
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return StabilityTestResult("Memory Leak Detection", False, duration, f"Error: {e}")
    
    def test_error_handling_resilience(self) -> StabilityTestResult:
        """Test error handling and recovery mechanisms."""
        start_time = time.time()
        error_scenarios = []
        
        try:
            # Test invalid endpoint
            try:
                response = requests.get(f"{self.base_url}/invalid_endpoint", timeout=10)
                error_scenarios.append(("Invalid endpoint", response.status_code == 404))
            except Exception as e:
                error_scenarios.append(("Invalid endpoint", False))
            
            # Test malformed request
            try:
                response = requests.post(f"{self.base_url}/simulate", json={"invalid": "data"}, timeout=10)
                error_scenarios.append(("Malformed request", response.status_code in [400, 422]))
            except Exception as e:
                error_scenarios.append(("Malformed request", False))
            
            # Test empty character list
            try:
                response = requests.post(f"{self.base_url}/simulate", json={"character_names": []}, timeout=10)
                error_scenarios.append(("Empty character list", response.status_code in [400, 422]))
            except Exception as e:
                error_scenarios.append(("Empty character list", False))
            
            # Verify system still responsive after errors
            health_response = requests.get(f"{self.base_url}/health", timeout=10)
            system_responsive = health_response.status_code == 200
            
            duration = time.time() - start_time
            passed_scenarios = sum(1 for _, success in error_scenarios if success)
            total_scenarios = len(error_scenarios)
            
            success = (passed_scenarios == total_scenarios and system_responsive)
            
            return StabilityTestResult(
                "Error Handling Resilience",
                success,
                duration,
                f"Passed {passed_scenarios}/{total_scenarios} error scenarios, system responsive: {system_responsive}",
                {"error_scenarios": error_scenarios, "system_responsive": system_responsive}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return StabilityTestResult("Error Handling Resilience", False, duration, f"Error: {e}")
    
    def test_long_running_stability(self, duration_minutes: int = 2) -> StabilityTestResult:
        """Test system stability under continuous load."""
        test_duration = duration_minutes * 60  # Convert to seconds
        start_time = time.time()
        end_time = start_time + test_duration
        
        metrics = PerformanceMetrics()
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        try:
            while time.time() < end_time:
                try:
                    req_start = time.time()
                    response = requests.get(f"{self.base_url}/health", timeout=10)
                    req_duration = (time.time() - req_start) * 1000
                    
                    if response.status_code == 200:
                        metrics.successful_requests += 1
                        metrics.add_response_time(req_duration)
                        consecutive_failures = 0
                    else:
                        metrics.failed_requests += 1
                        consecutive_failures += 1
                    
                    # Record system metrics
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    cpu_percent = process.cpu_percent()
                    metrics.add_system_metrics(memory_mb, cpu_percent)
                    
                    # Check for system failure
                    if consecutive_failures >= max_consecutive_failures:
                        break
                    
                    # Brief pause between requests
                    time.sleep(1)
                    
                except Exception as e:
                    metrics.failed_requests += 1
                    consecutive_failures += 1
                    logger.warning(f"Request failed during long-running test: {e}")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        break
            
            duration = time.time() - start_time
            stats = metrics.get_stats()
            
            # Consider successful if >95% success rate and no extended outages
            success = (stats["request_stats"]["success_rate"] >= 95.0 and 
                      consecutive_failures < max_consecutive_failures)
            
            message = f"Long-running test: {stats['request_stats']['success_rate']:.1f}% success rate over {duration/60:.1f} minutes"
            
            return StabilityTestResult(
                "Long Running Stability",
                success,
                duration,
                message,
                stats
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return StabilityTestResult("Long Running Stability", False, duration, f"Error: {e}")
    
    def run_comprehensive_stability_test(self) -> Dict[str, Any]:
        """Run complete stability validation suite."""
        logger.info("Starting comprehensive stability validation...")
        
        # Core stability tests
        self.log_result(self.test_api_health_stability())
        self.log_result(self.test_character_list_stability())
        self.log_result(self.test_story_generation_stability())
        self.log_result(self.test_error_handling_resilience())
        self.log_result(self.test_memory_leak_detection())
        
        # Performance and load tests
        self.log_result(self.test_concurrent_api_access(concurrent_users=5, requests_per_user=3))
        self.log_result(self.test_concurrent_api_access(concurrent_users=10, requests_per_user=5))
        self.log_result(self.test_long_running_stability(duration_minutes=1))  # Short test for demo
        
        # Calculate overall metrics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        total_duration = (datetime.now() - self.test_start_time).total_seconds()
        
        # Production readiness criteria
        success_rate = (passed_tests / total_tests) * 100
        production_ready = (
            success_rate >= 95.0 and
            all(r.success for r in self.results if r.test_name in [
                "API Health Check", "Character List", "Error Handling Resilience"
            ])
        )
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_duration_seconds": total_duration,
            "overall_status": "PRODUCTION_READY" if production_ready else "NOT_READY",
            "production_ready": production_ready,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": success_rate
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration": r.duration,
                    "message": r.message,
                    "metrics": r.metrics,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.results
            ],
            "production_criteria": {
                "api_health_responsive": any(r.success for r in self.results if r.test_name == "API Health Check"),
                "basic_functionality": any(r.success for r in self.results if r.test_name == "Character List"),
                "error_handling": any(r.success for r in self.results if r.test_name == "Error Handling Resilience"),
                "memory_stable": any(r.success for r in self.results if r.test_name == "Memory Leak Detection"),
                "concurrent_load": any(r.success for r in self.results if r.test_name == "Concurrent API Access"),
                "story_generation": any(r.success for r in self.results if r.test_name == "Story Generation")
            }
        }
        
        logger.info(f"Stability validation complete: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        return report

def main():
    """Main execution function."""
    validator = ProductionStabilityValidator()
    
    # Run comprehensive stability test
    report = validator.run_comprehensive_stability_test()
    
    # Save detailed report
    report_file = f"production_stability_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "="*80)
    print("PRODUCTION STABILITY VALIDATION SUMMARY")
    print("="*80)
    print(f"Overall Status: {report['overall_status']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(f"Tests Passed: {report['summary']['passed_tests']}/{report['summary']['total_tests']}")
    print(f"Test Duration: {report['test_duration_seconds']:.1f} seconds")
    print(f"Report saved to: {report_file}")
    
    if report['production_ready']:
        print("\n✅ SYSTEM IS PRODUCTION READY")
        return 0
    else:
        print("\n❌ SYSTEM NOT READY FOR PRODUCTION")
        return 1

if __name__ == "__main__":
    sys.exit(main())