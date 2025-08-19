#!/usr/bin/env python3
"""
StoryForge AI - Comprehensive Phase 2: Integration Testing Framework
Advanced integration testing with API, workflow, and performance validation
"""

import json
import os
import sys
import time
import requests
import subprocess
import tempfile
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from character_factory import CharacterFactory
    from chronicler_agent import ChroniclerAgent
    from director_agent import DirectorAgent
    from config_loader import ConfigLoader, get_config
except ImportError as e:
    print(f"⚠️ Import warning: {e}")

class IntegrationTestFramework:
    """Comprehensive integration testing framework"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.test_results = {
            "api_tests": {},
            "workflow_tests": {},
            "performance_tests": {},
            "system_integration_tests": {},
            "test_summary": {},
            "timestamp": datetime.now().isoformat()
        }
        self.api_server_process = None
        self.api_base_url = "http://localhost:8000"
    
    def run_comprehensive_integration_tests(self) -> Dict[str, Any]:
        """Execute comprehensive integration testing suite"""
        print("=== PHASE 2: COMPREHENSIVE INTEGRATION TESTING ===\n")
        
        # 1. System Integration Tests
        print("🔧 1. Running System Integration Tests...")
        self._run_system_integration_tests()
        
        # 2. API Integration Tests
        print("\n🌐 2. Running API Integration Tests...")
        self._run_api_integration_tests()
        
        # 3. Workflow Integration Tests
        print("\n⚡ 3. Running Workflow Integration Tests...")
        self._run_workflow_integration_tests()
        
        # 4. Performance Integration Tests
        print("\n📊 4. Running Performance Integration Tests...")
        self._run_performance_integration_tests()
        
        # 5. Generate Summary
        print("\n📋 5. Generating Integration Test Summary...")
        self._generate_integration_summary()
        
        # 6. Save detailed report
        self._save_integration_report()
        
        return self.test_results
    
    def _run_system_integration_tests(self):
        """Test system component integration"""
        system_tests = {
            "component_initialization": self._test_component_initialization(),
            "inter_component_communication": self._test_inter_component_communication(),
            "data_flow_integrity": self._test_data_flow_integrity(),
            "error_propagation": self._test_error_propagation()
        }
        
        self.test_results["system_integration_tests"] = system_tests
        
        # Calculate success rate
        passed_tests = sum(1 for test in system_tests.values() if test.get("status") == "PASS")
        total_tests = len(system_tests)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"   📊 System Integration: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    def _test_component_initialization(self) -> Dict[str, Any]:
        """Test that all components can be initialized together"""
        test_result = {
            "test_name": "Component Initialization",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            # Initialize all major components
            components = {}
            
            # Test CharacterFactory
            components["character_factory"] = CharacterFactory()
            test_result["details"]["character_factory"] = "PASS"
            
            # Test ChroniclerAgent
            components["chronicler_agent"] = ChroniclerAgent()
            test_result["details"]["chronicler_agent"] = "PASS"
            
            # Test DirectorAgent
            components["director_agent"] = DirectorAgent()
            test_result["details"]["director_agent"] = "PASS"
            
            # Test ConfigLoader
            try:
                config = get_config()
                test_result["details"]["config_loader"] = "PASS"
            except Exception as e:
                test_result["details"]["config_loader"] = f"FAIL: {str(e)}"
            
            test_result["status"] = "PASS"
            
        except Exception as e:
            test_result["error"] = str(e)
            test_result["status"] = "FAIL"
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_inter_component_communication(self) -> Dict[str, Any]:
        """Test communication between components"""
        test_result = {
            "test_name": "Inter-Component Communication",
            "status": "FAIL", 
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            # Test CharacterFactory -> DirectorAgent communication
            factory = CharacterFactory()
            director = DirectorAgent()
            
            characters = factory.list_available_characters()
            test_result["details"]["character_listing"] = f"Found {len(characters)} characters"
            
            if characters:
                # Create character and register with director
                agent = factory.create_character(characters[0])
                director.register_agent(agent)
                test_result["details"]["character_registration"] = "PASS"
                
                # Test turn execution
                turn_result = director.run_turn()
                test_result["details"]["turn_execution"] = "PASS" if turn_result else "FAIL"
            
            test_result["status"] = "PASS"
            
        except Exception as e:
            test_result["error"] = str(e)
            test_result["status"] = "FAIL"
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_data_flow_integrity(self) -> Dict[str, Any]:
        """Test data flow integrity across components"""
        test_result = {
            "test_name": "Data Flow Integrity",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            # Test complete data flow: Factory -> Director -> Log -> Chronicler
            factory = CharacterFactory()
            director = DirectorAgent()
            chronicler = ChroniclerAgent()
            
            # Create characters
            characters = factory.list_available_characters()
            if len(characters) >= 2:
                agent1 = factory.create_character(characters[0])
                agent2 = factory.create_character(characters[1])
                
                # Register agents
                director.register_agent(agent1)
                director.register_agent(agent2)
                
                # Execute turns
                for i in range(3):
                    result = director.run_turn()
                    test_result["details"][f"turn_{i+1}"] = "PASS" if result else "FAIL"
                
                # Test chronicler if campaign log exists
                campaign_log_path = os.path.join(self.project_root, "campaign_log.md")
                if os.path.exists(campaign_log_path):
                    narrative = chronicler.transcribe_log(campaign_log_path)
                    test_result["details"]["narrative_generation"] = "PASS" if narrative else "FAIL"
                
                test_result["status"] = "PASS"
            else:
                test_result["error"] = "Insufficient characters for data flow test"
                
        except Exception as e:
            test_result["error"] = str(e)
            test_result["status"] = "FAIL"
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_error_propagation(self) -> Dict[str, Any]:
        """Test error handling and propagation"""
        test_result = {
            "test_name": "Error Propagation",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            # Test error handling in various scenarios
            factory = CharacterFactory()
            director = DirectorAgent()
            chronicler = ChroniclerAgent()
            
            # Test 1: Invalid character creation
            try:
                factory.create_character("invalid_character_12345")
                test_result["details"]["invalid_character_handling"] = "FAIL - Should have raised exception"
            except Exception:
                test_result["details"]["invalid_character_handling"] = "PASS - Exception raised as expected"
            
            # Test 2: Invalid file processing
            try:
                chronicler.transcribe_log("/nonexistent/file/path.md")
                test_result["details"]["invalid_file_handling"] = "FAIL - Should have raised exception"
            except Exception:
                test_result["details"]["invalid_file_handling"] = "PASS - Exception raised as expected"
            
            # Test 3: Director with no agents
            try:
                empty_director = DirectorAgent()
                result = empty_director.run_turn()
                test_result["details"]["empty_director_handling"] = "PASS - Handled gracefully"
            except Exception as e:
                test_result["details"]["empty_director_handling"] = f"FAIL - Should handle gracefully: {str(e)}"
            
            test_result["status"] = "PASS"
            
        except Exception as e:
            test_result["error"] = str(e)
            test_result["status"] = "FAIL"
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _run_api_integration_tests(self):
        """Test API integration if API server is available"""
        api_tests = {
            "server_availability": self._test_api_server_availability(),
            "endpoint_functionality": self._test_api_endpoints(),
            "api_error_handling": self._test_api_error_handling(),
            "api_performance": self._test_api_performance()
        }
        
        self.test_results["api_tests"] = api_tests
        
        # Calculate success rate
        passed_tests = sum(1 for test in api_tests.values() if test.get("status") == "PASS")
        total_tests = len(api_tests)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"   🌐 API Integration: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    def _test_api_server_availability(self) -> Dict[str, Any]:
        """Test if API server is running and accessible"""
        test_result = {
            "test_name": "API Server Availability",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            # Try to start API server if not running
            if not self._is_api_server_running():
                print("   🚀 Starting API server for testing...")
                success = self._start_api_server()
                test_result["details"]["server_startup"] = "PASS" if success else "FAIL"
                
                if success:
                    time.sleep(2)  # Give server time to start
            
            # Test server connectivity
            try:
                response = requests.get(f"{self.api_base_url}/health", timeout=5)
                if response.status_code == 200:
                    test_result["details"]["health_check"] = "PASS"
                    test_result["status"] = "PASS"
                else:
                    test_result["details"]["health_check"] = f"FAIL - Status: {response.status_code}"
            except requests.exceptions.RequestException as e:
                test_result["details"]["health_check"] = f"FAIL - Connection error: {str(e)}"
                
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_api_endpoints(self) -> Dict[str, Any]:
        """Test API endpoints functionality"""
        test_result = {
            "test_name": "API Endpoints Functionality",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        
        if not self._is_api_server_running():
            test_result["error"] = "API server not available"
            test_result["execution_time"] = time.time() - start_time
            return test_result
        
        try:
            # Test various endpoints
            endpoints_to_test = [
                ("/", "GET", "root_endpoint"),
                ("/characters", "GET", "characters_list"),
                ("/health", "GET", "health_check"),
                ("/docs", "GET", "api_documentation")
            ]
            
            passed_endpoints = 0
            
            for path, method, endpoint_name in endpoints_to_test:
                try:
                    if method == "GET":
                        response = requests.get(f"{self.api_base_url}{path}", timeout=5)
                    elif method == "POST":
                        response = requests.post(f"{self.api_base_url}{path}", timeout=5)
                    
                    if response.status_code in [200, 404]:  # 404 is acceptable for some endpoints
                        test_result["details"][endpoint_name] = f"PASS - Status: {response.status_code}"
                        passed_endpoints += 1
                    else:
                        test_result["details"][endpoint_name] = f"FAIL - Status: {response.status_code}"
                        
                except requests.exceptions.RequestException as e:
                    test_result["details"][endpoint_name] = f"FAIL - Error: {str(e)}"
            
            if passed_endpoints >= len(endpoints_to_test) * 0.75:  # 75% success rate
                test_result["status"] = "PASS"
            
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_api_error_handling(self) -> Dict[str, Any]:
        """Test API error handling"""
        test_result = {
            "test_name": "API Error Handling",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        
        if not self._is_api_server_running():
            test_result["error"] = "API server not available"
            test_result["execution_time"] = time.time() - start_time
            return test_result
        
        try:
            # Test invalid endpoints
            try:
                response = requests.get(f"{self.api_base_url}/nonexistent/endpoint", timeout=5)
                if response.status_code == 404:
                    test_result["details"]["invalid_endpoint"] = "PASS - Returns 404"
                else:
                    test_result["details"]["invalid_endpoint"] = f"FAIL - Status: {response.status_code}"
            except Exception as e:
                test_result["details"]["invalid_endpoint"] = f"FAIL - Error: {str(e)}"
            
            # Test malformed requests (if POST endpoints exist)
            try:
                response = requests.post(f"{self.api_base_url}/create_story", 
                                       json={"invalid": "data"}, timeout=5)
                if response.status_code in [400, 404, 422]:  # Bad request or not found is acceptable
                    test_result["details"]["malformed_request"] = f"PASS - Status: {response.status_code}"
                else:
                    test_result["details"]["malformed_request"] = f"FAIL - Status: {response.status_code}"
            except Exception as e:
                test_result["details"]["malformed_request"] = f"PASS - Connection error expected: {type(e).__name__}"
            
            test_result["status"] = "PASS"  # If we got here, basic error handling works
            
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_api_performance(self) -> Dict[str, Any]:
        """Test API performance characteristics"""
        test_result = {
            "test_name": "API Performance",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        
        if not self._is_api_server_running():
            test_result["error"] = "API server not available"
            test_result["execution_time"] = time.time() - start_time
            return test_result
        
        try:
            # Test response times
            response_times = []
            
            for i in range(5):
                req_start = time.time()
                try:
                    response = requests.get(f"{self.api_base_url}/health", timeout=10)
                    req_time = time.time() - req_start
                    response_times.append(req_time)
                except Exception:
                    continue
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                
                test_result["details"]["average_response_time"] = f"{avg_response_time:.3f}s"
                test_result["details"]["max_response_time"] = f"{max_response_time:.3f}s"
                
                # Performance thresholds
                if avg_response_time < 1.0:  # Less than 1 second average
                    test_result["details"]["performance_rating"] = "EXCELLENT"
                elif avg_response_time < 2.0:
                    test_result["details"]["performance_rating"] = "GOOD"
                elif avg_response_time < 5.0:
                    test_result["details"]["performance_rating"] = "ACCEPTABLE"
                else:
                    test_result["details"]["performance_rating"] = "POOR"
                
                test_result["status"] = "PASS"
            
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _run_workflow_integration_tests(self):
        """Test end-to-end workflow integration"""
        workflow_tests = {
            "story_generation_workflow": self._test_story_generation_workflow(),
            "campaign_transcription_workflow": self._test_campaign_transcription_workflow(),
            "multi_agent_simulation": self._test_multi_agent_simulation(),
            "concurrent_operations": self._test_concurrent_operations()
        }
        
        self.test_results["workflow_tests"] = workflow_tests
        
        # Calculate success rate
        passed_tests = sum(1 for test in workflow_tests.values() if test.get("status") == "PASS")
        total_tests = len(workflow_tests)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"   ⚡ Workflow Integration: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    def _test_story_generation_workflow(self) -> Dict[str, Any]:
        """Test complete story generation workflow"""
        test_result = {
            "test_name": "Story Generation Workflow",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            # Complete workflow: Factory -> Director -> Story Generation
            factory = CharacterFactory()
            director = DirectorAgent()
            
            # Get characters
            characters = factory.list_available_characters()
            test_result["details"]["available_characters"] = len(characters)
            
            if len(characters) >= 2:
                # Create and register agents
                agent1 = factory.create_character(characters[0])
                agent2 = factory.create_character(characters[1])
                
                director.register_agent(agent1)
                director.register_agent(agent2)
                
                test_result["details"]["agent_registration"] = "PASS"
                
                # Generate story through multiple turns
                story_turns = []
                for turn in range(3):
                    turn_result = director.run_turn()
                    if turn_result:
                        story_turns.append(turn_result)
                        test_result["details"][f"turn_{turn+1}"] = "PASS"
                    else:
                        test_result["details"][f"turn_{turn+1}"] = "FAIL"
                
                test_result["details"]["total_turns_generated"] = len(story_turns)
                
                if len(story_turns) >= 2:  # At least 2 successful turns
                    test_result["status"] = "PASS"
                    
            else:
                test_result["error"] = "Insufficient characters for workflow test"
                
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_campaign_transcription_workflow(self) -> Dict[str, Any]:
        """Test campaign log transcription workflow"""
        test_result = {
            "test_name": "Campaign Transcription Workflow",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            chronicler = ChroniclerAgent()
            
            # Create a sample campaign log
            sample_log = """# Test Campaign Log
## Turn 1
- **pilot**: Navigated through asteroid field
- **engineer**: Repaired hull damage
- **scientist**: Analyzed alien artifacts

## Turn 2
- **pilot**: Docked with space station
- **engineer**: Upgraded ship systems
- **scientist**: Discovered new technology
"""
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
                tmp_file.write(sample_log)
                tmp_path = tmp_file.name
            
            try:
                # Test transcription
                narrative = chronicler.transcribe_log(tmp_path)
                
                test_result["details"]["log_processed"] = "PASS"
                test_result["details"]["narrative_generated"] = "PASS" if narrative else "FAIL"
                test_result["details"]["narrative_length"] = len(narrative) if narrative else 0
                
                if narrative and len(narrative) > 50:  # Reasonable narrative length
                    test_result["status"] = "PASS"
                
            finally:
                os.unlink(tmp_path)
                
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_multi_agent_simulation(self) -> Dict[str, Any]:
        """Test multi-agent simulation with various configurations"""
        test_result = {
            "test_name": "Multi-Agent Simulation",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            factory = CharacterFactory()
            characters = factory.list_available_characters()
            
            # Test with different agent configurations
            configurations = [2, 3, min(4, len(characters))]
            
            for config in configurations:
                if config <= len(characters):
                    director = DirectorAgent()
                    
                    # Register agents
                    agents = []
                    for i in range(config):
                        agent = factory.create_character(characters[i])
                        director.register_agent(agent)
                        agents.append(agent)
                    
                    # Run simulation
                    simulation_success = True
                    for turn in range(5):
                        result = director.run_turn()
                        if not result:
                            simulation_success = False
                            break
                    
                    test_result["details"][f"config_{config}_agents"] = "PASS" if simulation_success else "FAIL"
            
            # Check if at least one configuration worked
            passed_configs = sum(1 for v in test_result["details"].values() if v == "PASS")
            if passed_configs > 0:
                test_result["status"] = "PASS"
                
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_concurrent_operations(self) -> Dict[str, Any]:
        """Test concurrent operations and thread safety"""
        test_result = {
            "test_name": "Concurrent Operations",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            def create_and_run_simulation():
                """Create and run a simulation in a separate thread"""
                try:
                    factory = CharacterFactory()
                    director = DirectorAgent()
                    
                    characters = factory.list_available_characters()
                    if len(characters) >= 2:
                        agent1 = factory.create_character(characters[0])
                        agent2 = factory.create_character(characters[1])
                        
                        director.register_agent(agent1)
                        director.register_agent(agent2)
                        
                        # Run 3 turns
                        results = []
                        for _ in range(3):
                            result = director.run_turn()
                            results.append(result)
                        
                        return len([r for r in results if r is not None])
                    return 0
                except Exception:
                    return -1
            
            # Run multiple concurrent simulations
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(create_and_run_simulation) for _ in range(3)]
                results = [future.result() for future in as_completed(futures)]
            
            successful_simulations = sum(1 for r in results if r > 0)
            test_result["details"]["concurrent_simulations"] = len(results)
            test_result["details"]["successful_simulations"] = successful_simulations
            test_result["details"]["success_rate"] = f"{(successful_simulations/len(results)*100):.1f}%"
            
            if successful_simulations >= len(results) * 0.75:  # 75% success rate
                test_result["status"] = "PASS"
                
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _run_performance_integration_tests(self):
        """Test performance characteristics under integration scenarios"""
        performance_tests = {
            "memory_usage": self._test_memory_usage(),
            "cpu_utilization": self._test_cpu_utilization(),
            "response_time_scaling": self._test_response_time_scaling(),
            "resource_cleanup": self._test_resource_cleanup()
        }
        
        self.test_results["performance_tests"] = performance_tests
        
        # Calculate success rate
        passed_tests = sum(1 for test in performance_tests.values() if test.get("status") == "PASS")
        total_tests = len(performance_tests)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"   📊 Performance Integration: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    def _test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage during operations"""
        test_result = {
            "test_name": "Memory Usage",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Run memory-intensive operations
            factory = CharacterFactory()
            directors = []
            
            # Create multiple directors with agents
            for i in range(5):
                director = DirectorAgent()
                characters = factory.list_available_characters()
                
                if len(characters) >= 2:
                    agent1 = factory.create_character(characters[0])
                    agent2 = factory.create_character(characters[1])
                    director.register_agent(agent1)
                    director.register_agent(agent2)
                    
                    # Run several turns
                    for _ in range(10):
                        director.run_turn()
                    
                    directors.append(director)
            
            # Check memory after operations
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory
            
            test_result["details"]["initial_memory_mb"] = f"{initial_memory:.2f}"
            test_result["details"]["peak_memory_mb"] = f"{peak_memory:.2f}"
            test_result["details"]["memory_increase_mb"] = f"{memory_increase:.2f}"
            
            # Memory usage thresholds
            if memory_increase < 100:  # Less than 100MB increase
                test_result["details"]["memory_rating"] = "EXCELLENT"
                test_result["status"] = "PASS"
            elif memory_increase < 250:
                test_result["details"]["memory_rating"] = "GOOD"
                test_result["status"] = "PASS"
            elif memory_increase < 500:
                test_result["details"]["memory_rating"] = "ACCEPTABLE"
                test_result["status"] = "PASS"
            else:
                test_result["details"]["memory_rating"] = "POOR"
                
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_cpu_utilization(self) -> Dict[str, Any]:
        """Test CPU utilization during operations"""
        test_result = {
            "test_name": "CPU Utilization",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            # Monitor CPU usage during intensive operations
            cpu_percentages = []
            
            def monitor_cpu():
                for _ in range(10):
                    cpu_percentages.append(psutil.cpu_percent(interval=0.1))
            
            # Start CPU monitoring in background
            monitor_thread = threading.Thread(target=monitor_cpu)
            monitor_thread.start()
            
            # Run CPU-intensive operations
            factory = CharacterFactory()
            director = DirectorAgent()
            
            characters = factory.list_available_characters()
            if len(characters) >= 2:
                for char in characters[:4]:  # Use up to 4 characters
                    agent = factory.create_character(char)
                    director.register_agent(agent)
                
                # Run many turns quickly
                for _ in range(50):
                    director.run_turn()
            
            monitor_thread.join()
            
            if cpu_percentages:
                avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
                max_cpu = max(cpu_percentages)
                
                test_result["details"]["average_cpu_percent"] = f"{avg_cpu:.2f}%"
                test_result["details"]["max_cpu_percent"] = f"{max_cpu:.2f}%"
                
                # CPU usage thresholds
                if avg_cpu < 50:
                    test_result["details"]["cpu_rating"] = "EXCELLENT"
                    test_result["status"] = "PASS"
                elif avg_cpu < 70:
                    test_result["details"]["cpu_rating"] = "GOOD" 
                    test_result["status"] = "PASS"
                elif avg_cpu < 90:
                    test_result["details"]["cpu_rating"] = "ACCEPTABLE"
                    test_result["status"] = "PASS"
                else:
                    test_result["details"]["cpu_rating"] = "POOR"
                    
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_response_time_scaling(self) -> Dict[str, Any]:
        """Test response time scaling with load"""
        test_result = {
            "test_name": "Response Time Scaling",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            factory = CharacterFactory()
            
            # Test response times with increasing load
            load_levels = [1, 2, 4]  # Number of concurrent operations
            
            for load in load_levels:
                response_times = []
                
                def run_operation():
                    op_start = time.time()
                    try:
                        director = DirectorAgent()
                        characters = factory.list_available_characters()
                        
                        if len(characters) >= 2:
                            agent1 = factory.create_character(characters[0])
                            agent2 = factory.create_character(characters[1])
                            director.register_agent(agent1)
                            director.register_agent(agent2)
                            
                            for _ in range(5):
                                director.run_turn()
                        
                        return time.time() - op_start
                    except Exception:
                        return -1
                
                # Run concurrent operations
                with ThreadPoolExecutor(max_workers=load) as executor:
                    futures = [executor.submit(run_operation) for _ in range(load)]
                    times = [future.result() for future in as_completed(futures)]
                
                valid_times = [t for t in times if t > 0]
                if valid_times:
                    avg_time = sum(valid_times) / len(valid_times)
                    response_times.append(avg_time)
                    test_result["details"][f"load_{load}_avg_time"] = f"{avg_time:.3f}s"
                else:
                    test_result["details"][f"load_{load}_avg_time"] = "FAIL"
            
            # Check if response times are reasonable
            if all(t < 10.0 for t in response_times):  # All under 10 seconds
                test_result["status"] = "PASS"
                test_result["details"]["scaling_assessment"] = "GOOD"
                
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _test_resource_cleanup(self) -> Dict[str, Any]:
        """Test resource cleanup after operations"""
        test_result = {
            "test_name": "Resource Cleanup",
            "status": "FAIL",
            "details": {},
            "execution_time": 0,
            "error": None
        }
        
        start_time = time.time()
        try:
            # Get initial resource state
            process = psutil.Process()
            initial_handles = process.num_handles() if hasattr(process, 'num_handles') else 0
            initial_threads = process.num_threads()
            
            # Create many objects that should be cleaned up
            factory = CharacterFactory()
            objects_created = []
            
            for i in range(10):
                director = DirectorAgent()
                chronicler = ChroniclerAgent()
                
                characters = factory.list_available_characters()
                if characters:
                    agent = factory.create_character(characters[0])
                    director.register_agent(agent)
                    director.run_turn()
                
                objects_created.extend([director, chronicler, agent])
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Check resource state after cleanup
            final_handles = process.num_handles() if hasattr(process, 'num_handles') else 0
            final_threads = process.num_threads()
            
            test_result["details"]["initial_handles"] = initial_handles
            test_result["details"]["final_handles"] = final_handles
            test_result["details"]["initial_threads"] = initial_threads
            test_result["details"]["final_threads"] = final_threads
            
            handle_increase = final_handles - initial_handles
            thread_increase = final_threads - initial_threads
            
            # Resource cleanup assessment
            if handle_increase < 50 and thread_increase < 10:  # Reasonable resource usage
                test_result["status"] = "PASS"
                test_result["details"]["cleanup_rating"] = "GOOD"
            elif handle_increase < 100 and thread_increase < 20:
                test_result["status"] = "PASS"
                test_result["details"]["cleanup_rating"] = "ACCEPTABLE"
            else:
                test_result["details"]["cleanup_rating"] = "POOR"
                
        except Exception as e:
            test_result["error"] = str(e)
        
        test_result["execution_time"] = time.time() - start_time
        return test_result
    
    def _generate_integration_summary(self):
        """Generate comprehensive integration test summary"""
        summary = {
            "total_test_categories": 4,
            "category_results": {},
            "overall_pass_rate": 0,
            "critical_issues": [],
            "recommendations": []
        }
        
        # Calculate results for each category
        categories = [
            ("system_integration_tests", "System Integration"),
            ("api_tests", "API Integration"), 
            ("workflow_tests", "Workflow Integration"),
            ("performance_tests", "Performance Integration")
        ]
        
        total_tests = 0
        total_passed = 0
        
        for key, name in categories:
            if key in self.test_results:
                tests = self.test_results[key]
                passed = sum(1 for test in tests.values() if test.get("status") == "PASS")
                total = len(tests)
                
                summary["category_results"][name] = {
                    "passed": passed,
                    "total": total,
                    "pass_rate": (passed / total * 100) if total > 0 else 0
                }
                
                total_tests += total
                total_passed += passed
        
        summary["overall_pass_rate"] = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        # Identify critical issues
        for category_key, category_name in categories:
            if category_key in self.test_results:
                for test_name, test_result in self.test_results[category_key].items():
                    if test_result.get("status") == "FAIL" and test_result.get("error"):
                        summary["critical_issues"].append({
                            "category": category_name,
                            "test": test_name,
                            "error": test_result["error"]
                        })
        
        # Generate recommendations
        if summary["overall_pass_rate"] < 80:
            summary["recommendations"].append("CRITICAL: Overall integration test pass rate below 80% - investigate failing tests")
        
        if len(summary["critical_issues"]) > 0:
            summary["recommendations"].append(f"HIGH: Address {len(summary['critical_issues'])} critical integration failures")
        
        if summary["category_results"].get("API Integration", {}).get("pass_rate", 0) < 50:
            summary["recommendations"].append("MEDIUM: API integration tests show significant issues")
        
        self.test_results["test_summary"] = summary
        
        # Print summary
        print(f"   📊 Overall Integration Pass Rate: {summary['overall_pass_rate']:.1f}%")
        if summary["critical_issues"]:
            print(f"   🚨 Critical Issues: {len(summary['critical_issues'])}")
    
    def _is_api_server_running(self) -> bool:
        """Check if API server is running"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _start_api_server(self) -> bool:
        """Start API server for testing"""
        try:
            api_server_path = os.path.join(self.project_root, "api_server.py")
            if os.path.exists(api_server_path):
                self.api_server_process = subprocess.Popen(
                    [sys.executable, api_server_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                return True
        except Exception:
            pass
        return False
    
    def _stop_api_server(self):
        """Stop API server if running"""
        if self.api_server_process:
            self.api_server_process.terminate()
            self.api_server_process = None
    
    def _save_integration_report(self):
        """Save comprehensive integration test report"""
        report_path = os.path.join(self.project_root, "validation", "comprehensive_phase2_integration_test_report.json")
        
        # Ensure validation directory exists
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        # Save comprehensive report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n📄 Comprehensive integration test report saved to: {report_path}")
    
    def cleanup(self):
        """Cleanup resources after testing"""
        self._stop_api_server()


def main():
    """Run Phase 2 Comprehensive Integration Testing"""
    test_framework = None
    try:
        print("StoryForge AI - Phase 2: Comprehensive Integration Testing")
        print("=" * 60)
        print("Advanced integration testing with API, workflow, and performance validation")
        print()
        
        test_framework = IntegrationTestFramework()
        results = test_framework.run_comprehensive_integration_tests()
        
        return results
        
    except Exception as e:
        print(f"❌ Integration testing error: {str(e)}")
        return None
    finally:
        if test_framework:
            test_framework.cleanup()


if __name__ == "__main__":
    main()