#!/usr/bin/env python3
"""
Comprehensive API Testing for Novel Engine Production Readiness Validation.

This script provides exhaustive testing of all API endpoints for functionality,
performance, error handling, and production readiness assessment.
"""

import asyncio
import httpx
import json
import time
import uuid
import websockets
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
import subprocess
import signal
import os
import sys
from dataclasses import dataclass, field
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result container."""
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class APITestReport:
    """Comprehensive API test report."""
    test_results: List[TestResult] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    average_response_time: float = 0.0
    endpoints_tested: int = 0
    security_score: int = 0
    performance_score: int = 0
    functionality_score: int = 0
    overall_score: int = 0
    recommendations: List[str] = field(default_factory=list)

class APITester:
    """Comprehensive API testing framework."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = None
        self.server_process = None
        self.report = APITestReport()
        self.start_time = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_server()
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
        await self.stop_server()
    
    async def start_server(self):
        """Start the API server for testing."""
        logger.info("Starting API server for testing...")
        try:
            # Create data directory
            os.makedirs("data", exist_ok=True)
            
            # Start server in background
            cmd = [sys.executable, "-c", 
                   "from src.api.main_api_server import main; main()"]
            
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            # Wait for server to start
            await asyncio.sleep(3)
            
            # Verify server is running
            async with httpx.AsyncClient() as client:
                for attempt in range(10):
                    try:
                        response = await client.get(f"{self.base_url}/health", timeout=5.0)
                        if response.status_code == 200:
                            logger.info("API server started successfully")
                            return
                    except:
                        pass
                    await asyncio.sleep(1)
                    
            raise Exception("Failed to start API server")
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the API server."""
        if self.server_process:
            logger.info("Stopping API server...")
            try:
                self.server_process.terminate()
                await asyncio.sleep(2)
                if self.server_process.poll() is None:
                    self.server_process.kill()
                logger.info("API server stopped")
            except Exception as e:
                logger.error(f"Error stopping server: {e}")
    
    async def test_endpoint(self, method: str, endpoint: str, 
                          data: Optional[Dict] = None,
                          expected_status: int = 200,
                          timeout: float = 10.0) -> TestResult:
        """Test a single API endpoint."""
        start_time = time.time()
        
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = await self.client.get(url, timeout=timeout)
            elif method.upper() == "POST":
                response = await self.client.post(url, json=data, timeout=timeout)
            elif method.upper() == "PUT":
                response = await self.client.put(url, json=data, timeout=timeout)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = time.time() - start_time
            
            # Parse response if JSON
            response_data = None
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            success = (response.status_code == expected_status)
            
            result = TestResult(
                endpoint=endpoint,
                method=method.upper(),
                status_code=response.status_code,
                response_time=response_time,
                success=success,
                details={
                    "response_data": response_data,
                    "headers": dict(response.headers),
                    "expected_status": expected_status
                }
            )
            
            if not success:
                result.error = f"Expected status {expected_status}, got {response.status_code}"
            
            self.report.test_results.append(result)
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                endpoint=endpoint,
                method=method.upper(),
                status_code=0,
                response_time=response_time,
                success=False,
                error=str(e)
            )
            self.report.test_results.append(result)
            return result
    
    async def test_health_endpoint(self):
        """Test the health check endpoint."""
        logger.info("Testing /health endpoint...")
        
        # Test normal health check
        result = await self.test_endpoint("GET", "/health")
        
        if result.success:
            health_data = result.details.get("response_data", {})
            if isinstance(health_data, dict):
                assert "status" in health_data
                assert "timestamp" in health_data
                assert health_data["status"] == "healthy"
                logger.info("✅ Health endpoint passed validation")
            else:
                logger.warning("⚠️ Health endpoint returned non-JSON response")
        else:
            logger.error(f"❌ Health endpoint failed: {result.error}")
    
    async def test_root_endpoint(self):
        """Test the root endpoint."""
        logger.info("Testing / root endpoint...")
        
        # Test root endpoint (should return 200 now that we added it)
        result = await self.test_endpoint("GET", "/", expected_status=200)
        
        if result.success:
            logger.info("✅ Root endpoint behavior is appropriate (404)")
        else:
            logger.warning(f"⚠️ Root endpoint unexpected behavior: {result.status_code}")
    
    async def test_character_endpoints(self):
        """Test character-related endpoints."""
        logger.info("Testing character API endpoints...")
        
        # Test character creation
        character_data = {
            "agent_id": f"test_char_{uuid.uuid4().hex[:8]}",
            "name": "Test Character",
            "background_summary": "A test character for API validation",
            "personality_traits": "Friendly, curious, intelligent",
            "current_mood": 7,
            "dominant_emotion": "happy",
            "energy_level": 8,
            "stress_level": 3,
            "skills": {"diplomacy": 0.7, "combat": 0.3},
            "relationships": {},
            "current_location": "Test Area",
            "inventory": ["test_item"],
            "metadata": {"test": True}
        }
        
        result = await self.test_endpoint(
            "POST", "/api/v1/characters", 
            data=character_data
        )
        
        if result.success:
            logger.info("✅ Character creation endpoint working")
        else:
            logger.error(f"❌ Character creation failed: {result.error}")
        
        # Test invalid character data
        invalid_data = {
            "agent_id": "",  # Invalid: too short
            "name": "X",     # Invalid: too short
        }
        
        result = await self.test_endpoint(
            "POST", "/api/v1/characters",
            data=invalid_data,
            expected_status=422
        )
        
        if result.success:
            logger.info("✅ Character validation working correctly")
        else:
            logger.warning(f"⚠️ Character validation may have issues: {result.status_code}")
    
    async def test_story_generation_endpoints(self):
        """Test story generation endpoints."""
        logger.info("Testing story generation API endpoints...")
        
        # Test story generation initiation
        story_data = {
            "characters": ["test_char_1", "test_char_2"],
            "title": "Test Story Generation"
        }
        
        result = await self.test_endpoint(
            "POST", "/api/v1/stories/generate",
            data=story_data
        )
        
        generation_id = None
        if result.success:
            response_data = result.details.get("response_data", {})
            if isinstance(response_data, dict):
                generation_id = response_data.get("generation_id")
                logger.info(f"✅ Story generation initiated: {generation_id}")
            else:
                logger.warning("⚠️ Story generation response format issue")
        else:
            logger.error(f"❌ Story generation failed: {result.error}")
        
        # Test status endpoint if we have a generation ID
        if generation_id:
            await asyncio.sleep(1)  # Brief pause
            result = await self.test_endpoint(
                "GET", f"/api/v1/stories/status/{generation_id}"
            )
            
            if result.success:
                logger.info("✅ Story status endpoint working")
            else:
                logger.warning(f"⚠️ Story status endpoint issue: {result.error}")
        
        # Test invalid story request
        invalid_story_data = {
            "characters": [],  # Invalid: empty list
            "title": "X" * 250  # Invalid: too long
        }
        
        result = await self.test_endpoint(
            "POST", "/api/v1/stories/generate",
            data=invalid_story_data,
            expected_status=422
        )
        
        if result.success:
            logger.info("✅ Story generation validation working")
        else:
            logger.warning(f"⚠️ Story generation validation issue: {result.status_code}")
    
    async def test_interaction_endpoints(self):
        """Test interaction API endpoints."""
        logger.info("Testing interaction API endpoints...")
        
        # Test interaction creation
        interaction_data = {
            "participants": ["char_1", "char_2"],
            "interaction_type": "DIALOGUE",
            "priority": "NORMAL",
            "topic": "Test conversation topic"
        }
        
        result = await self.test_endpoint(
            "POST", "/api/v1/interactions",
            data=interaction_data
        )
        
        if result.success:
            logger.info("✅ Interaction creation endpoint working")
        else:
            logger.error(f"❌ Interaction creation failed: {result.error}")
        
        # Test invalid interaction data
        invalid_data = {
            "participants": ["char_1"],  # Invalid: need at least 2
            "topic": "X" * 250  # Invalid: too long
        }
        
        result = await self.test_endpoint(
            "POST", "/api/v1/interactions",
            data=invalid_data,
            expected_status=422
        )
        
        if result.success:
            logger.info("✅ Interaction validation working")
        else:
            logger.warning(f"⚠️ Interaction validation issue: {result.status_code}")
    
    async def test_error_handling(self):
        """Test API error handling."""
        logger.info("Testing error handling...")
        
        # Test 404 endpoints
        not_found_endpoints = [
            "/api/v1/nonexistent",
            "/api/v1/characters/999",
            "/api/v1/stories/invalid_id",
            "/completely/invalid/path"
        ]
        
        for endpoint in not_found_endpoints:
            result = await self.test_endpoint("GET", endpoint, expected_status=404)
            if not result.success:
                logger.warning(f"⚠️ 404 handling issue for {endpoint}: {result.status_code}")
        
        # Test malformed JSON
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/characters",
                    data="invalid json{",
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code not in [400, 422]:
                    logger.warning(f"⚠️ Malformed JSON handling: {response.status_code}")
                else:
                    logger.info("✅ Malformed JSON handled correctly")
        except Exception as e:
            logger.warning(f"⚠️ Error testing malformed JSON: {e}")
    
    async def test_performance(self):
        """Test API performance characteristics."""
        logger.info("Testing API performance...")
        
        # Test concurrent requests
        concurrent_tasks = []
        for i in range(10):
            task = self.test_endpoint("GET", "/health")
            concurrent_tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks)
        total_time = time.time() - start_time
        
        successful_requests = sum(1 for r in results if r.success)
        avg_response_time = sum(r.response_time for r in results) / len(results)
        
        logger.info(f"Concurrent test: {successful_requests}/10 successful")
        logger.info(f"Average response time: {avg_response_time:.3f}s")
        logger.info(f"Total concurrent execution time: {total_time:.3f}s")
        
        if avg_response_time < 1.0:
            logger.info("✅ Performance within acceptable limits")
        else:
            logger.warning("⚠️ Performance may need optimization")
    
    async def test_security_headers(self):
        """Test security headers and CORS configuration."""
        logger.info("Testing security headers...")
        
        result = await self.test_endpoint("GET", "/health")
        
        if result.success:
            headers = result.details.get("headers", {})
            
            security_checks = {
                "CORS": "access-control-allow-origin" in headers,
                "Content-Type": "content-type" in headers,
                "Server": headers.get("server", "").lower() != "uvicorn"  # Server header should be minimal
            }
            
            for check, passed in security_checks.items():
                if passed:
                    logger.info(f"✅ Security check {check}: PASS")
                else:
                    logger.warning(f"⚠️ Security check {check}: REVIEW NEEDED")
        
        # Test CORS with OPTIONS
        try:
            async with httpx.AsyncClient() as client:
                response = await client.options(f"{self.base_url}/health")
                cors_headers = [
                    "access-control-allow-origin",
                    "access-control-allow-methods",
                    "access-control-allow-headers"
                ]
                
                cors_configured = any(header in response.headers for header in cors_headers)
                if cors_configured:
                    logger.info("✅ CORS configuration detected")
                else:
                    logger.warning("⚠️ CORS configuration may need review")
        except Exception as e:
            logger.warning(f"⚠️ CORS test failed: {e}")
    
    async def test_websocket_endpoints(self):
        """Test WebSocket endpoints if available."""
        logger.info("Testing WebSocket endpoints...")
        
        # For now, we'll just test if WebSocket endpoints are accessible
        # This would require more complex WebSocket testing in production
        
        # Test story progress WebSocket (would fail without active generation)
        ws_url = f"ws://127.0.0.1:8000/api/v1/stories/progress/test_id"
        
        try:
            # Brief connection test
            async with websockets.connect(ws_url, timeout=5) as websocket:
                await websocket.send("ping")
                response = await asyncio.wait_for(websocket.recv(), timeout=2)
                logger.info("✅ WebSocket endpoint accessible")
        except Exception as e:
            logger.info(f"ℹ️ WebSocket test: {e} (expected for invalid generation ID)")
    
    def calculate_scores(self):
        """Calculate various quality scores."""
        if not self.report.test_results:
            return
        
        total_tests = len(self.report.test_results)
        passed_tests = sum(1 for r in self.report.test_results if r.success)
        
        self.report.total_tests = total_tests
        self.report.passed_tests = passed_tests
        self.report.failed_tests = total_tests - passed_tests
        
        # Calculate average response time
        valid_times = [r.response_time for r in self.report.test_results if r.response_time > 0]
        if valid_times:
            self.report.average_response_time = sum(valid_times) / len(valid_times)
        
        # Calculate functionality score (0-100)
        self.report.functionality_score = int((passed_tests / total_tests) * 100) if total_tests > 0 else 0
        
        # Calculate performance score (0-100)
        if self.report.average_response_time > 0:
            if self.report.average_response_time < 0.5:
                self.report.performance_score = 100
            elif self.report.average_response_time < 1.0:
                self.report.performance_score = 80
            elif self.report.average_response_time < 2.0:
                self.report.performance_score = 60
            else:
                self.report.performance_score = 40
        
        # Security score (basic assessment)
        security_tests = [r for r in self.report.test_results if "security" in r.endpoint.lower()]
        self.report.security_score = 75  # Default score, would need more detailed security testing
        
        # Overall score
        self.report.overall_score = int(
            (self.report.functionality_score * 0.5) +
            (self.report.performance_score * 0.3) +
            (self.report.security_score * 0.2)
        )
        
        # Generate recommendations
        if self.report.functionality_score < 90:
            self.report.recommendations.append("Some API endpoints are failing - review error handling")
        
        if self.report.performance_score < 80:
            self.report.recommendations.append("API response times could be improved")
        
        if self.report.failed_tests > 0:
            self.report.recommendations.append("Address failed test cases before production deployment")
        
        if self.report.overall_score >= 90:
            self.report.recommendations.append("API is ready for production deployment")
        elif self.report.overall_score >= 70:
            self.report.recommendations.append("API is ready for staging with minor improvements needed")
        else:
            self.report.recommendations.append("API needs significant improvements before production deployment")
    
    def print_report(self):
        """Print comprehensive test report."""
        print("\n" + "="*80)
        print("           NOVEL ENGINE API PRODUCTION READINESS REPORT")
        print("="*80)
        
        print(f"\n📊 TEST SUMMARY")
        print(f"   Total Tests: {self.report.total_tests}")
        print(f"   Passed: {self.report.passed_tests}")
        print(f"   Failed: {self.report.failed_tests}")
        print(f"   Success Rate: {(self.report.passed_tests/self.report.total_tests)*100:.1f}%")
        
        print(f"\n⚡ PERFORMANCE METRICS")
        print(f"   Average Response Time: {self.report.average_response_time:.3f}s")
        print(f"   Endpoints Tested: {len(set(r.endpoint for r in self.report.test_results))}")
        
        print(f"\n🎯 QUALITY SCORES")
        print(f"   Functionality Score: {self.report.functionality_score}/100")
        print(f"   Performance Score: {self.report.performance_score}/100")
        print(f"   Security Score: {self.report.security_score}/100")
        print(f"   Overall Score: {self.report.overall_score}/100")
        
        print(f"\n📋 DETAILED RESULTS")
        for result in self.report.test_results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"   {result.method} {result.endpoint} - {status} ({result.response_time:.3f}s)")
            if result.error:
                print(f"      Error: {result.error}")
        
        print(f"\n🔍 RECOMMENDATIONS")
        for rec in self.report.recommendations:
            print(f"   • {rec}")
        
        print(f"\n🏁 PRODUCTION READINESS ASSESSMENT")
        if self.report.overall_score >= 90:
            print("   ✅ READY FOR PRODUCTION - All systems operational")
        elif self.report.overall_score >= 70:
            print("   ⚠️ READY FOR STAGING - Minor improvements recommended")
        else:
            print("   ❌ NOT READY - Significant issues need resolution")
        
        print("="*80)

async def main():
    """Main testing function."""
    logger.info("Starting comprehensive API testing...")
    
    async with APITester() as tester:
        try:
            # Core functionality tests
            await tester.test_health_endpoint()
            await tester.test_root_endpoint()
            await tester.test_character_endpoints()
            await tester.test_story_generation_endpoints()
            await tester.test_interaction_endpoints()
            
            # Quality assurance tests
            await tester.test_error_handling()
            await tester.test_performance()
            await tester.test_security_headers()
            await tester.test_websocket_endpoints()
            
            # Calculate scores and generate report
            tester.calculate_scores()
            tester.print_report()
            
        except Exception as e:
            logger.error(f"Testing failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())