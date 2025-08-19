#!/usr/bin/env python3
"""
Quick Performance Test for Novel Engine - Immediate Results

A lightweight performance testing script that provides fast results for
production readiness assessment.
"""

import asyncio
import aiohttp
import time
import statistics
import json
import psutil
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QuickMetrics:
    """Quick performance metrics."""
    endpoint: str
    test_type: str
    response_times: List[float]
    success_count: int
    error_count: int
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    throughput: float = 0.0
    
    def calculate_stats(self):
        if self.response_times:
            self.avg_response_time = statistics.mean(self.response_times)
            sorted_times = sorted(self.response_times)
            n = len(sorted_times)
            if n >= 2:
                self.p95_response_time = sorted_times[int(0.95 * n)]

class QuickPerformanceTest:
    """Quick performance testing class."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def test_endpoint(self, endpoint: str, requests: int = 10) -> QuickMetrics:
        """Test a single endpoint with multiple requests."""
        url = f"{self.base_url}{endpoint}"
        metrics = QuickMetrics(
            endpoint=endpoint,
            test_type="sequential",
            response_times=[],
            success_count=0,
            error_count=0
        )
        
        for _ in range(requests):
            start_time = time.time()
            try:
                async with self.session.get(url) as response:
                    await response.text()
                    end_time = time.time()
                    response_time = end_time - start_time
                    metrics.response_times.append(response_time)
                    
                    if response.status < 400:
                        metrics.success_count += 1
                    else:
                        metrics.error_count += 1
                        
            except Exception as e:
                end_time = time.time()
                response_time = end_time - start_time
                metrics.response_times.append(response_time)
                metrics.error_count += 1
                
        metrics.calculate_stats()
        return metrics
        
    async def test_concurrent_load(self, endpoint: str, concurrent_users: int = 5, duration: int = 15) -> QuickMetrics:
        """Test endpoint with concurrent users for short duration."""
        url = f"{self.base_url}{endpoint}"
        metrics = QuickMetrics(
            endpoint=endpoint,
            test_type=f"concurrent_{concurrent_users}",
            response_times=[],
            success_count=0,
            error_count=0
        )
        
        start_time = time.time()
        end_time = start_time + duration
        
        async def user_session():
            session_metrics = []
            while time.time() < end_time:
                req_start = time.time()
                try:
                    async with self.session.get(url) as response:
                        await response.text()
                        req_end = time.time()
                        response_time = req_end - req_start
                        success = response.status < 400
                        session_metrics.append((response_time, success))
                        
                except Exception:
                    req_end = time.time()
                    response_time = req_end - req_start
                    session_metrics.append((response_time, False))
                    
                await asyncio.sleep(0.05)  # Brief pause
            return session_metrics
            
        # Run concurrent sessions
        tasks = [user_session() for _ in range(concurrent_users)]
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        total_duration = time.time() - start_time
        total_requests = 0
        
        for result in session_results:
            if isinstance(result, list):
                for response_time, success in result:
                    metrics.response_times.append(response_time)
                    total_requests += 1
                    if success:
                        metrics.success_count += 1
                    else:
                        metrics.error_count += 1
                        
        metrics.throughput = total_requests / total_duration if total_duration > 0 else 0
        metrics.calculate_stats()
        return metrics
        
    def test_story_generation(self, concurrent_sims: int = 2) -> Dict[str, Any]:
        """Test story generation with concurrent simulations."""
        import httpx
        
        def run_simulation():
            start_time = time.time()
            try:
                simulation_data = {
                    "character_names": ["engineer", "pilot"],
                    "turns": 2
                }
                
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        f"{self.base_url}/simulate",
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
                    "content_length": 0,
                    "error": str(e)
                }
                
        # Run concurrent simulations
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=concurrent_sims) as executor:
            futures = [executor.submit(run_simulation) for _ in range(concurrent_sims)]
            results = []
            
            for future in as_completed(futures, timeout=60):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "response_time": 0,
                        "success": False,
                        "error": str(e)
                    })
                    
        # Calculate summary
        response_times = [r["response_time"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "concurrent_simulations": concurrent_sims,
            "total_simulations": len(results),
            "success_count": success_count,
            "success_rate": success_count / len(results) if results else 0,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "results": results
        }

def get_system_info():
    """Get basic system information."""
    return {
        "cpu_count": psutil.cpu_count(),
        "memory_total_gb": psutil.virtual_memory().total / (1024**3),
        "python_version": sys.version,
        "timestamp": datetime.now().isoformat()
    }

async def main():
    """Run quick performance tests."""
    logger.info("Starting Quick Performance Test Suite")
    
    # Check server availability
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            response = client.get("http://localhost:8000/health")
            if response.status_code != 200:
                logger.error("API server not responding correctly")
                return
    except Exception as e:
        logger.error(f"Cannot connect to API server: {e}")
        return
        
    results = {
        "system_info": get_system_info(),
        "baseline_tests": {},
        "load_tests": {},
        "story_generation": {}
    }
    
    async with QuickPerformanceTest() as tester:
        # 1. Baseline Tests (Quick)
        logger.info("=== Baseline Performance Tests ===")
        endpoints = ["/health", "/characters"]
        
        for endpoint in endpoints:
            logger.info(f"Testing {endpoint}")
            metrics = await tester.test_endpoint(endpoint, requests=10)
            results["baseline_tests"][endpoint] = asdict(metrics)
            logger.info(f"{endpoint}: avg={metrics.avg_response_time:.3f}s, p95={metrics.p95_response_time:.3f}s, errors={metrics.error_count}")
            
        # 2. Quick Load Tests
        logger.info("=== Quick Load Tests ===")
        for users in [5, 10]:
            logger.info(f"Testing with {users} concurrent users")
            load_results = {}
            
            for endpoint in ["/health", "/characters"]:
                metrics = await tester.test_concurrent_load(endpoint, users, duration=10)
                load_results[endpoint] = asdict(metrics)
                logger.info(f"{users} users {endpoint}: throughput={metrics.throughput:.2f} req/s, errors={metrics.error_count}")
                
            results["load_tests"][f"{users}_users"] = load_results
            
        # 3. Story Generation Test
        logger.info("=== Story Generation Test ===")
        try:
            story_results = tester.test_story_generation(concurrent_sims=2)
            results["story_generation"] = story_results
            logger.info(f"Story generation: {story_results['success_count']}/{story_results['total_simulations']} successful, "
                       f"avg={story_results['avg_response_time']:.2f}s")
        except Exception as e:
            logger.error(f"Story generation test failed: {e}")
            results["story_generation"] = {"error": str(e)}
            
    # Generate quick report
    print("\n" + "="*60)
    print("QUICK PERFORMANCE TEST RESULTS")
    print("="*60)
    
    # Baseline summary
    print("\n📊 BASELINE PERFORMANCE:")
    for endpoint, metrics in results["baseline_tests"].items():
        avg_ms = metrics["avg_response_time"] * 1000
        p95_ms = metrics["p95_response_time"] * 1000
        errors = metrics["error_count"]
        status = "✅" if avg_ms < 200 and errors == 0 else "⚠️" if avg_ms < 500 else "❌"
        print(f"  {status} {endpoint}: {avg_ms:.1f}ms avg, {p95_ms:.1f}ms p95, {errors} errors")
        
    # Load test summary
    print("\n🚀 LOAD PERFORMANCE:")
    for test_name, test_data in results["load_tests"].items():
        users = test_name.replace("_", " ").title()
        print(f"  {users}:")
        for endpoint, metrics in test_data.items():
            throughput = metrics["throughput"]
            errors = metrics["error_count"]
            status = "✅" if throughput > 20 and errors == 0 else "⚠️" if throughput > 10 else "❌"
            print(f"    {status} {endpoint}: {throughput:.1f} req/s, {errors} errors")
            
    # Story generation summary
    print("\n📖 STORY GENERATION:")
    if "error" not in results["story_generation"]:
        story_data = results["story_generation"]
        success_rate = story_data["success_rate"]
        avg_time = story_data["avg_response_time"]
        status = "✅" if success_rate > 0.8 and avg_time < 10 else "⚠️" if success_rate > 0.5 else "❌"
        print(f"  {status} Success Rate: {success_rate:.1%}")
        print(f"  {status} Avg Response: {avg_time:.2f}s")
    else:
        print("  ❌ Story generation test failed")
        
    # Overall assessment
    print("\n🎯 PRODUCTION READINESS:")
    
    # Calculate readiness score
    score_factors = []
    
    # Check baseline performance
    baseline_good = all(
        metrics["avg_response_time"] < 0.2 and metrics["error_count"] == 0 
        for metrics in results["baseline_tests"].values()
    )
    score_factors.append(100 if baseline_good else 60)
    
    # Check load performance
    load_good = any(
        all(metrics["throughput"] > 20 for metrics in test_data.values())
        for test_data in results["load_tests"].values()
    )
    score_factors.append(100 if load_good else 70)
    
    # Check story generation
    if "error" not in results["story_generation"]:
        story_good = (results["story_generation"]["success_rate"] > 0.8 and 
                     results["story_generation"]["avg_response_time"] < 10)
        score_factors.append(100 if story_good else 60)
    else:
        score_factors.append(40)
        
    overall_score = statistics.mean(score_factors)
    
    if overall_score >= 90:
        print("  🟢 READY FOR PRODUCTION")
    elif overall_score >= 75:
        print("  🟡 CONDITIONAL READINESS")
    else:
        print("  🔴 NEEDS OPTIMIZATION")
        
    print(f"  Overall Score: {overall_score:.0f}/100")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"quick_performance_results_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📄 Detailed results saved to: {filename}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())