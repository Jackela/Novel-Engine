#!/usr/bin/env python3
"""
Corrected Production System Stability Validation Suite.

Fixed to use correct API endpoints and provide comprehensive stability testing.
"""

import time
import json
import requests
import logging
import concurrent.futures
import psutil
import statistics
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CriticalStabilityResults:
    """Critical stability test results for production certification."""
    api_health: bool = False
    character_listing: bool = False
    story_generation: bool = False
    error_handling: bool = False
    memory_stability: bool = False
    concurrent_performance: bool = False
    response_time_p95: float = 0.0
    success_rate: float = 0.0
    memory_increase_mb: float = 0.0

class ProductionStabilityValidator:
    """Fast, focused production stability validator."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = CriticalStabilityResults()
        
    def test_api_health(self) -> bool:
        """Test API health endpoint."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            success = response.status_code == 200 and response.json().get("status") == "healthy"
            logger.info(f"API Health: {'PASS' if success else 'FAIL'}")
            return success
        except Exception as e:
            logger.error(f"API Health: FAIL - {e}")
            return False
    
    def test_character_listing(self) -> bool:
        """Test character listing functionality."""
        try:
            response = requests.get(f"{self.base_url}/characters", timeout=10)
            success = response.status_code == 200 and len(response.json().get("characters", [])) > 0
            logger.info(f"Character Listing: {'PASS' if success else 'FAIL'}")
            return success
        except Exception as e:
            logger.error(f"Character Listing: FAIL - {e}")
            return False
    
    def test_story_generation(self) -> bool:
        """Test story generation with correct endpoint."""
        try:
            # Get characters first
            char_response = requests.get(f"{self.base_url}/characters", timeout=10)
            if char_response.status_code != 200:
                logger.error("Story Generation: FAIL - Cannot get characters")
                return False
            
            characters = char_response.json().get("characters", [])
            if len(characters) < 2:
                logger.error("Story Generation: FAIL - Insufficient characters")
                return False
            
            # Test story generation with correct endpoint
            payload = {
                "character_names": characters[:2],
                "turns": 2
            }
            
            response = requests.post(f"{self.base_url}/simulations", json=payload, timeout=30)
            success = response.status_code == 200 and len(response.json().get("story", "")) > 0
            logger.info(f"Story Generation: {'PASS' if success else 'FAIL'}")
            return success
        except Exception as e:
            logger.error(f"Story Generation: FAIL - {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling robustness."""
        try:
            # Test invalid endpoint
            invalid_response = requests.get(f"{self.base_url}/invalid", timeout=10)
            invalid_ok = invalid_response.status_code == 404
            
            # Test malformed request
            malformed_response = requests.post(f"{self.base_url}/simulations", 
                                             json={"invalid": "data"}, timeout=10)
            malformed_ok = malformed_response.status_code in [400, 422]
            
            # Verify system still responsive
            health_response = requests.get(f"{self.base_url}/health", timeout=10)
            system_ok = health_response.status_code == 200
            
            success = invalid_ok and malformed_ok and system_ok
            logger.info(f"Error Handling: {'PASS' if success else 'FAIL'}")
            return success
        except Exception as e:
            logger.error(f"Error Handling: FAIL - {e}")
            return False
    
    def test_memory_stability(self) -> float:
        """Test memory stability - returns memory increase in MB."""
        try:
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Perform 10 health checks
            for _ in range(10):
                requests.get(f"{self.base_url}/health", timeout=10)
                time.sleep(0.1)
            
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
            
            success = memory_increase < 10.0  # Less than 10MB increase
            logger.info(f"Memory Stability: {'PASS' if success else 'FAIL'} (Δ{memory_increase:+.1f}MB)")
            self.results.memory_stability = success
            return memory_increase
        except Exception as e:
            logger.error(f"Memory Stability: FAIL - {e}")
            return 999.0  # Indicate failure
    
    def test_concurrent_performance(self) -> tuple[float, float]:
        """Test concurrent performance - returns (P95 response time, success rate)."""
        try:
            response_times = []
            successes = 0
            failures = 0
            
            def make_request():
                nonlocal successes, failures
                try:
                    start = time.time()
                    response = requests.get(f"{self.base_url}/health", timeout=10)
                    duration_ms = (time.time() - start) * 1000
                    
                    if response.status_code == 200:
                        successes += 1
                        response_times.append(duration_ms)
                    else:
                        failures += 1
                except Exception:
                    failures += 1
            
            # Run 20 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(20)]
                concurrent.futures.wait(futures)
            
            if response_times:
                p95 = sorted(response_times)[int(0.95 * len(response_times))]
                success_rate = (successes / (successes + failures)) * 100
                
                perf_ok = p95 < 1000 and success_rate >= 95  # P95 < 1s, 95% success
                logger.info(f"Concurrent Performance: {'PASS' if perf_ok else 'FAIL'} (P95: {p95:.0f}ms, {success_rate:.1f}% success)")
                self.results.concurrent_performance = perf_ok
                return p95, success_rate
            else:
                logger.error("Concurrent Performance: FAIL - No successful requests")
                return 9999.0, 0.0
        except Exception as e:
            logger.error(f"Concurrent Performance: FAIL - {e}")
            return 9999.0, 0.0
    
    def run_fast_stability_check(self) -> Dict[str, Any]:
        """Run focused stability check for production readiness."""
        logger.info("Starting fast production stability check...")
        start_time = time.time()
        
        # Run critical tests
        self.results.api_health = self.test_api_health()
        self.results.character_listing = self.test_character_listing()
        self.results.story_generation = self.test_story_generation()
        self.results.error_handling = self.test_error_handling()
        self.results.memory_increase_mb = self.test_memory_stability()
        self.results.response_time_p95, self.results.success_rate = self.test_concurrent_performance()
        
        # Calculate overall metrics
        critical_tests = [
            self.results.api_health,
            self.results.character_listing,
            self.results.story_generation,
            self.results.error_handling,
            self.results.memory_stability,
            self.results.concurrent_performance
        ]
        
        passed_tests = sum(critical_tests)
        total_tests = len(critical_tests)
        overall_success_rate = (passed_tests / total_tests) * 100
        
        # Production readiness criteria
        production_ready = (
            overall_success_rate >= 95.0 and
            self.results.api_health and
            self.results.character_listing and
            self.results.error_handling  # Core functionality must work
        )
        
        # Generate detailed report
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_duration_seconds": time.time() - start_time,
            "overall_status": "PRODUCTION_READY" if production_ready else "NOT_READY",
            "production_ready": production_ready,
            "critical_test_results": {
                "api_health": self.results.api_health,
                "character_listing": self.results.character_listing,
                "story_generation": self.results.story_generation,
                "error_handling": self.results.error_handling,
                "memory_stability": self.results.memory_stability,
                "concurrent_performance": self.results.concurrent_performance
            },
            "performance_metrics": {
                "response_time_p95_ms": self.results.response_time_p95,
                "concurrent_success_rate": self.results.success_rate,
                "memory_increase_mb": self.results.memory_increase_mb
            },
            "production_criteria_met": {
                "api_responsive": self.results.api_health,
                "basic_functionality": self.results.character_listing,
                "story_generation": self.results.story_generation,
                "error_resilience": self.results.error_handling,
                "memory_efficient": self.results.memory_stability,
                "performance_acceptable": self.results.concurrent_performance,
                "response_time_under_1s": self.results.response_time_p95 < 1000,
                "high_success_rate": self.results.success_rate >= 95.0
            },
            "summary": {
                "tests_passed": passed_tests,
                "total_tests": total_tests,
                "success_rate": overall_success_rate
            }
        }
        
        logger.info(f"Stability check complete: {passed_tests}/{total_tests} critical tests passed ({overall_success_rate:.1f}%)")
        return report

def main():
    """Main execution function."""
    validator = ProductionStabilityValidator()
    
    # Run fast stability check
    report = validator.run_fast_stability_check()
    
    # Save report
    report_file = f"production_stability_corrected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "="*80)
    print("PRODUCTION STABILITY VALIDATION RESULTS")
    print("="*80)
    print(f"Overall Status: {report['overall_status']}")
    print(f"Production Ready: {report['production_ready']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(f"Tests Passed: {report['summary']['tests_passed']}/{report['summary']['total_tests']}")
    
    print("\nCritical Test Results:")
    for test, result in report['critical_test_results'].items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test}: {status}")
    
    print(f"\nPerformance Metrics:")
    print(f"  Response Time P95: {report['performance_metrics']['response_time_p95_ms']:.0f}ms")
    print(f"  Concurrent Success Rate: {report['performance_metrics']['concurrent_success_rate']:.1f}%")
    print(f"  Memory Increase: {report['performance_metrics']['memory_increase_mb']:+.1f}MB")
    
    print(f"\nReport saved to: {report_file}")
    
    if report['production_ready']:
        print("\n🎉 SYSTEM IS PRODUCTION READY")
        return 0
    else:
        print("\n⚠️  SYSTEM HAS STABILITY ISSUES")
        return 1

if __name__ == "__main__":
    exit(main())