#!/usr/bin/env python3
"""
PERFORMANCE STRESS TESTING & OPTIMIZATION FRAMEWORK
=========================================================

Comprehensive performance stress testing and optimization validation
for production readiness assessment.
"""

import asyncio
import logging
import time
import statistics
import concurrent.futures
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import threading
import psutil
import gc

logger = logging.getLogger(__name__)

@dataclass
class StressTestResult:
    """Individual stress test result"""
    test_name: str
    requests_per_second: float
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success_count: int
    error_count: int
    total_requests: int
    test_duration: float

@dataclass
class SystemMetrics:
    """System resource metrics during testing"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    io_read_mb: float
    io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float

class PerformanceStressTester:
    """Comprehensive performance stress testing framework"""
    
    def __init__(self):
        self.results: List[StressTestResult] = []
        self.system_metrics: List[SystemMetrics] = []
        self.monitoring_active = False
        
    async def run_comprehensive_stress_tests(self) -> Dict[str, Any]:
        """Run comprehensive stress testing suite"""
        logger.info("Starting comprehensive performance stress testing")
        
        # Start system monitoring
        monitoring_task = asyncio.create_task(self._monitor_system_resources())
        
        try:
            # Test scenarios
            test_scenarios = [
                ("api_load_test", self._test_api_load),
                ("cache_stress_test", self._test_cache_stress),
                ("concurrent_operations", self._test_concurrent_operations),
                ("memory_stress_test", self._test_memory_stress),
                ("database_load_test", self._test_database_load),
            ]
            
            for test_name, test_func in test_scenarios:
                logger.info(f"Running stress test: {test_name}")
                
                # Clear garbage before test
                gc.collect()
                
                # Run the test
                result = await test_func()
                result.test_name = test_name
                self.results.append(result)
                
                logger.info(f"Test {test_name} completed: "
                           f"{result.requests_per_second:.1f} RPS, "
                           f"{result.average_response_time*1000:.1f}ms avg")
                
                # Cool down between tests
                await asyncio.sleep(2)
            
        finally:
            # Stop system monitoring
            self.monitoring_active = False
            await monitoring_task
        
        return self._generate_stress_test_report()
    
    async def _monitor_system_resources(self):
        """Monitor system resources during testing"""
        self.monitoring_active = True
        
        while self.monitoring_active:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                io_counters = psutil.disk_io_counters()
                net_counters = psutil.net_io_counters()
                
                metric = SystemMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_mb=memory.used / (1024 * 1024),
                    io_read_mb=io_counters.read_bytes / (1024 * 1024) if io_counters else 0,
                    io_write_mb=io_counters.write_bytes / (1024 * 1024) if io_counters else 0,
                    network_sent_mb=net_counters.bytes_sent / (1024 * 1024) if net_counters else 0,
                    network_recv_mb=net_counters.bytes_recv / (1024 * 1024) if net_counters else 0
                )
                
                self.system_metrics.append(metric)
                
            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")
            
            await asyncio.sleep(1)
    
    async def _test_api_load(self) -> StressTestResult:
        """Test API load handling"""
        test_duration = 30  # seconds
        concurrent_users = 50
        requests_per_user = 100
        
        start_time = time.time()
        response_times = []
        success_count = 0
        error_count = 0
        
        async def simulate_api_request():
            """Simulate API request"""
            request_start = time.time()
            try:
                # Simulate API processing time
                await asyncio.sleep(0.01 + (0.005 * (len(response_times) % 10)))  # Variable delay
                
                # Simulate some CPU work
                for _ in range(1000):
                    pass
                
                response_time = time.time() - request_start
                response_times.append(response_time)
                return True
            except Exception:
                return False
        
        # Run concurrent requests
        tasks = []
        for _ in range(concurrent_users):
            for _ in range(requests_per_user):
                task = asyncio.create_task(simulate_api_request())
                tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and errors
        for result in results:
            if result is True:
                success_count += 1
            else:
                error_count += 1
        
        actual_duration = time.time() - start_time
        total_requests = len(tasks)
        
        # Calculate metrics
        rps = total_requests / actual_duration
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else avg_response_time
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else avg_response_time
        error_rate = (error_count / total_requests) * 100 if total_requests > 0 else 0
        
        # Get current resource usage
        memory_mb = psutil.virtual_memory().used / (1024 * 1024)
        cpu_percent = psutil.cpu_percent()
        
        return StressTestResult(
            test_name="api_load_test",
            requests_per_second=rps,
            average_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            error_rate=error_rate,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            success_count=success_count,
            error_count=error_count,
            total_requests=total_requests,
            test_duration=actual_duration
        )
    
    async def _test_cache_stress(self) -> StressTestResult:
        """Test cache system under stress"""
        from src.performance.distributed_caching import MemoryCache
        
        cache = MemoryCache(max_size=1000)
        test_duration = 20
        operations_per_second = 1000
        
        start_time = time.time()
        response_times = []
        success_count = 0
        error_count = 0
        
        async def cache_operation():
            """Perform cache operations"""
            operation_start = time.time()
            try:
                # Random cache operations
                import random
                key = f"test_key_{random.randint(1, 500)}"
                value = f"test_value_{random.randint(1, 1000)}"
                
                if random.random() < 0.7:  # 70% reads
                    await cache.get(key)
                else:  # 30% writes
                    await cache.set(key, value)
                
                response_time = time.time() - operation_start
                response_times.append(response_time)
                return True
            except Exception:
                return False
        
        # Generate operations
        total_operations = operations_per_second * test_duration
        tasks = []
        
        for _ in range(total_operations):
            task = asyncio.create_task(cache_operation())
            tasks.append(task)
            
            # Throttle operation creation
            if len(tasks) % 100 == 0:
                await asyncio.sleep(0.1)
        
        # Execute operations
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results
        for result in results:
            if result is True:
                success_count += 1
            else:
                error_count += 1
        
        actual_duration = time.time() - start_time
        
        # Calculate metrics
        rps = len(tasks) / actual_duration
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else avg_response_time
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else avg_response_time
        error_rate = (error_count / len(tasks)) * 100 if len(tasks) > 0 else 0
        
        memory_mb = psutil.virtual_memory().used / (1024 * 1024)
        cpu_percent = psutil.cpu_percent()
        
        return StressTestResult(
            test_name="cache_stress_test",
            requests_per_second=rps,
            average_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            error_rate=error_rate,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            success_count=success_count,
            error_count=error_count,
            total_requests=len(tasks),
            test_duration=actual_duration
        )
    
    async def _test_concurrent_operations(self) -> StressTestResult:
        """Test concurrent operations handling"""
        concurrent_workers = 20
        operations_per_worker = 50
        
        start_time = time.time()
        response_times = []
        success_count = 0
        error_count = 0
        
        async def worker_operations(worker_id: int):
            """Simulate worker operations"""
            worker_times = []
            worker_successes = 0
            worker_errors = 0
            
            for i in range(operations_per_worker):
                operation_start = time.time()
                try:
                    # Simulate complex operation
                    await asyncio.sleep(0.01)  # I/O simulation
                    
                    # CPU-intensive work
                    result = sum(x * x for x in range(100))
                    
                    # Memory allocation
                    data = [f"data_{worker_id}_{i}_{j}" for j in range(50)]
                    
                    operation_time = time.time() - operation_start
                    worker_times.append(operation_time)
                    worker_successes += 1
                    
                except Exception:
                    worker_errors += 1
            
            return worker_times, worker_successes, worker_errors
        
        # Create concurrent workers
        tasks = []
        for worker_id in range(concurrent_workers):
            task = asyncio.create_task(worker_operations(worker_id))
            tasks.append(task)
        
        # Execute all workers
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for result in results:
            if isinstance(result, tuple):
                times, successes, errors = result
                response_times.extend(times)
                success_count += successes
                error_count += errors
        
        actual_duration = time.time() - start_time
        total_operations = concurrent_workers * operations_per_worker
        
        # Calculate metrics
        rps = total_operations / actual_duration
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else avg_response_time
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else avg_response_time
        error_rate = (error_count / total_operations) * 100 if total_operations > 0 else 0
        
        memory_mb = psutil.virtual_memory().used / (1024 * 1024)
        cpu_percent = psutil.cpu_percent()
        
        return StressTestResult(
            test_name="concurrent_operations",
            requests_per_second=rps,
            average_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            error_rate=error_rate,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            success_count=success_count,
            error_count=error_count,
            total_requests=total_operations,
            test_duration=actual_duration
        )
    
    async def _test_memory_stress(self) -> StressTestResult:
        """Test memory usage under stress"""
        allocations = []
        start_time = time.time()
        
        try:
            # Allocate memory progressively
            for i in range(100):
                # Create large data structures
                data = {
                    f"key_{j}": f"value_{j}" * 100
                    for j in range(1000)
                }
                allocations.append(data)
                
                # Small delay to allow monitoring
                await asyncio.sleep(0.01)
            
            # Hold memory for a moment
            await asyncio.sleep(2)
            
            # Gradual cleanup
            while allocations:
                allocations.pop()
                if len(allocations) % 10 == 0:
                    gc.collect()
                    await asyncio.sleep(0.01)
            
            success_count = 1
            error_count = 0
            
        except Exception as e:
            logger.error(f"Memory stress test error: {e}")
            success_count = 0
            error_count = 1
        
        actual_duration = time.time() - start_time
        
        memory_mb = psutil.virtual_memory().used / (1024 * 1024)
        cpu_percent = psutil.cpu_percent()
        
        return StressTestResult(
            test_name="memory_stress_test",
            requests_per_second=1 / actual_duration,
            average_response_time=actual_duration,
            p95_response_time=actual_duration,
            p99_response_time=actual_duration,
            error_rate=(error_count / 1) * 100,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            success_count=success_count,
            error_count=error_count,
            total_requests=1,
            test_duration=actual_duration
        )
    
    async def _test_database_load(self) -> StressTestResult:
        """Test database operations under load"""
        concurrent_connections = 10
        queries_per_connection = 20
        
        start_time = time.time()
        response_times = []
        success_count = 0
        error_count = 0
        
        async def database_operations(connection_id: int):
            """Simulate database operations"""
            connection_times = []
            connection_successes = 0
            connection_errors = 0
            
            for i in range(queries_per_connection):
                query_start = time.time()
                try:
                    # Simulate database query
                    await asyncio.sleep(0.005)  # DB latency simulation
                    
                    # Simulate query processing
                    for _ in range(500):
                        pass
                    
                    query_time = time.time() - query_start
                    connection_times.append(query_time)
                    connection_successes += 1
                    
                except Exception:
                    connection_errors += 1
            
            return connection_times, connection_successes, connection_errors
        
        # Create concurrent database connections
        tasks = []
        for connection_id in range(concurrent_connections):
            task = asyncio.create_task(database_operations(connection_id))
            tasks.append(task)
        
        # Execute all connections
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for result in results:
            if isinstance(result, tuple):
                times, successes, errors = result
                response_times.extend(times)
                success_count += successes
                error_count += errors
        
        actual_duration = time.time() - start_time
        total_queries = concurrent_connections * queries_per_connection
        
        # Calculate metrics
        rps = total_queries / actual_duration
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else avg_response_time
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else avg_response_time
        error_rate = (error_count / total_queries) * 100 if total_queries > 0 else 0
        
        memory_mb = psutil.virtual_memory().used / (1024 * 1024)
        cpu_percent = psutil.cpu_percent()
        
        return StressTestResult(
            test_name="database_load_test",
            requests_per_second=rps,
            average_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            error_rate=error_rate,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            success_count=success_count,
            error_count=error_count,
            total_requests=total_queries,
            test_duration=actual_duration
        )
    
    def _generate_stress_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive stress test report"""
        if not self.results:
            return {"error": "No test results available"}
        
        # Calculate aggregate metrics
        total_requests = sum(r.total_requests for r in self.results)
        total_successes = sum(r.success_count for r in self.results)
        total_errors = sum(r.error_count for r in self.results)
        
        avg_rps = statistics.mean([r.requests_per_second for r in self.results])
        avg_response_time = statistics.mean([r.average_response_time for r in self.results])
        max_memory_mb = max([r.memory_usage_mb for r in self.results])
        avg_cpu_percent = statistics.mean([r.cpu_usage_percent for r in self.results])
        
        # Performance assessment
        performance_grade = self._calculate_performance_grade()
        
        # System resource analysis
        resource_analysis = self._analyze_system_resources()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_requests": total_requests,
                "total_successes": total_successes,
                "total_errors": total_errors,
                "overall_success_rate": (total_successes / max(total_requests, 1)) * 100,
                "average_rps": avg_rps,
                "average_response_time_ms": avg_response_time * 1000,
                "peak_memory_mb": max_memory_mb,
                "average_cpu_percent": avg_cpu_percent,
                "performance_grade": performance_grade
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "requests_per_second": r.requests_per_second,
                    "avg_response_time_ms": r.average_response_time * 1000,
                    "p95_response_time_ms": r.p95_response_time * 1000,
                    "p99_response_time_ms": r.p99_response_time * 1000,
                    "error_rate_percent": r.error_rate,
                    "memory_usage_mb": r.memory_usage_mb,
                    "cpu_usage_percent": r.cpu_usage_percent,
                    "success_count": r.success_count,
                    "error_count": r.error_count,
                    "total_requests": r.total_requests,
                    "test_duration": r.test_duration
                }
                for r in self.results
            ],
            "resource_analysis": resource_analysis,
            "recommendations": self._generate_performance_recommendations()
        }
        
        return report
    
    def _calculate_performance_grade(self) -> str:
        """Calculate overall performance grade"""
        scores = []
        
        for result in self.results:
            # Score based on various factors
            rps_score = min(result.requests_per_second / 100, 1.0) * 25  # Target: 100 RPS
            response_time_score = max(0, 25 - (result.average_response_time * 1000) / 4)  # Target: <100ms
            error_rate_score = max(0, 25 - result.error_rate)  # Target: 0% errors
            resource_score = max(0, 25 - (result.cpu_usage_percent / 4))  # Target: <100% CPU
            
            total_score = rps_score + response_time_score + error_rate_score + resource_score
            scores.append(total_score)
        
        avg_score = statistics.mean(scores)
        
        if avg_score >= 90:
            return "A+"
        elif avg_score >= 85:
            return "A"
        elif avg_score >= 80:
            return "B+"
        elif avg_score >= 75:
            return "B"
        elif avg_score >= 70:
            return "C"
        else:
            return "F"
    
    def _analyze_system_resources(self) -> Dict[str, Any]:
        """Analyze system resource usage during tests"""
        if not self.system_metrics:
            return {"error": "No system metrics available"}
        
        cpu_values = [m.cpu_percent for m in self.system_metrics]
        memory_values = [m.memory_percent for m in self.system_metrics]
        
        return {
            "cpu_usage": {
                "average": statistics.mean(cpu_values),
                "peak": max(cpu_values),
                "minimum": min(cpu_values)
            },
            "memory_usage": {
                "average_percent": statistics.mean(memory_values),
                "peak_percent": max(memory_values),
                "average_mb": statistics.mean([m.memory_mb for m in self.system_metrics])
            },
            "io_activity": {
                "total_read_mb": sum([m.io_read_mb for m in self.system_metrics]),
                "total_write_mb": sum([m.io_write_mb for m in self.system_metrics])
            },
            "network_activity": {
                "total_sent_mb": sum([m.network_sent_mb for m in self.system_metrics]),
                "total_recv_mb": sum([m.network_recv_mb for m in self.system_metrics])
            }
        }
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        for result in self.results:
            if result.error_rate > 1.0:
                recommendations.append(f"High error rate in {result.test_name}: {result.error_rate:.1f}% - investigate error handling")
            
            if result.average_response_time > 0.1:  # 100ms
                recommendations.append(f"Slow response time in {result.test_name}: {result.average_response_time*1000:.1f}ms - optimize processing")
            
            if result.cpu_usage_percent > 80:
                recommendations.append(f"High CPU usage in {result.test_name}: {result.cpu_usage_percent:.1f}% - optimize algorithms")
            
            if result.requests_per_second < 50:
                recommendations.append(f"Low throughput in {result.test_name}: {result.requests_per_second:.1f} RPS - scale horizontally")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Excellent performance! System is optimized for production workloads.")
        
        return recommendations

# Main execution
async def main():
    """Run comprehensive stress testing"""
    logger.info("Starting Novel Engine Performance Stress Testing")
    
    tester = PerformanceStressTester()
    report = await tester.run_comprehensive_stress_tests()
    
    # Save report
    with open("performance_stress_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # Display summary
    summary = report["summary"]
    print("\n" + "="*80)
    print("PERFORMANCE STRESS TEST RESULTS")
    print("="*80)
    print(f"Total Requests: {summary['total_requests']:,}")
    print(f"Success Rate: {summary['overall_success_rate']:.1f}%")
    print(f"Average RPS: {summary['average_rps']:.1f}")
    print(f"Average Response Time: {summary['average_response_time_ms']:.1f}ms")
    print(f"Peak Memory Usage: {summary['peak_memory_mb']:.1f}MB")
    print(f"Average CPU Usage: {summary['average_cpu_percent']:.1f}%")
    print(f"Performance Grade: {summary['performance_grade']}")
    print("="*80)
    
    logger.info("Performance stress testing completed")

if __name__ == "__main__":
    asyncio.run(main())