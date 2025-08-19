#!/usr/bin/env python3
"""
PHASE 2.2: Integration Testing Suite
===================================

Comprehensive integration tests covering:
1. API endpoint integration
2. Component interaction workflows  
3. End-to-end story generation
4. Database and file system integration
5. Error propagation and recovery
6. Performance under load
"""

import sys
import os
import json
import time
import threading
import tempfile
import requests
from typing import Dict, List, Any, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class IntegrationTester:
    """Comprehensive integration testing framework."""
    
    def __init__(self):
        self.project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.test_results = []
        self.api_base_url = "http://localhost:8000"
        self.server_process = None
        
    def test_api_endpoint_integration(self) -> Dict[str, Any]:
        """Test API endpoint integration and responses."""
        
        print("🌐 TESTING API ENDPOINT INTEGRATION")
        print("=" * 60)
        
        api_tests = {
            'health_check': {'method': 'GET', 'endpoint': '/health', 'expected_status': 200},
            'system_status': {'method': 'GET', 'endpoint': '/meta/system-status', 'expected_status': 200},
            'character_listing': {'method': 'GET', 'endpoint': '/characters', 'expected_status': 200},
            'simulation_execution': {
                'method': 'POST', 
                'endpoint': '/simulations',
                'data': {
                    'character_names': ['pilot', 'engineer'],
                    'narrative_style': 'detailed',
                    'turns': 1
                },
                'expected_status': 200
            }
        }
        
        results = {
            'tests_run': 0,
            'tests_passed': 0,
            'test_details': {},
            'overall_success': True
        }
        
        for test_name, test_config in api_tests.items():
            print(f"🧪 Testing: {test_name}")
            
            try:
                start_time = time.time()
                
                if test_config['method'] == 'GET':
                    response = requests.get(
                        f"{self.api_base_url}{test_config['endpoint']}", 
                        timeout=30
                    )
                elif test_config['method'] == 'POST':
                    response = requests.post(
                        f"{self.api_base_url}{test_config['endpoint']}",
                        json=test_config.get('data', {}),
                        headers={'Content-Type': 'application/json'},
                        timeout=60
                    )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                # Validate response
                status_match = response.status_code == test_config['expected_status']
                has_content = len(response.text) > 0
                
                if status_match and has_content:
                    print(f"   ✅ PASS - Status: {response.status_code}, Time: {response_time:.2f}s")
                    results['tests_passed'] += 1
                    
                    # Additional validation for specific endpoints
                    if test_name == 'simulation_execution' and response.status_code == 200:
                        try:
                            response_data = response.json()
                            story_quality = self._validate_story_quality(response_data.get('story', ''))
                            print(f"      📖 Story Quality Score: {story_quality:.1%}")
                        except Exception as e:
                            print(f"      ⚠️ Story validation failed: {e}")
                else:
                    print(f"   ❌ FAIL - Status: {response.status_code} (expected {test_config['expected_status']})")
                    results['overall_success'] = False
                
                results['test_details'][test_name] = {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'content_length': len(response.text),
                    'passed': status_match and has_content
                }
                
            except requests.exceptions.RequestException as e:
                print(f"   ❌ FAIL - Connection error: {e}")
                results['test_details'][test_name] = {
                    'error': str(e),
                    'passed': False
                }
                results['overall_success'] = False
            except Exception as e:
                print(f"   ❌ FAIL - Unexpected error: {e}")
                results['test_details'][test_name] = {
                    'error': str(e),
                    'passed': False
                }
                results['overall_success'] = False
            
            results['tests_run'] += 1
        
        success_rate = results['tests_passed'] / results['tests_run'] if results['tests_run'] > 0 else 0
        
        print(f"\n📊 API INTEGRATION SUMMARY:")
        print(f"   🧪 Tests run: {results['tests_run']}")
        print(f"   ✅ Passed: {results['tests_passed']}")
        print(f"   📈 Success rate: {success_rate:.1%}")
        
        return results
    
    def _validate_story_quality(self, story: str) -> float:
        """Validate story quality metrics."""
        if not story:
            return 0.0
        
        quality_score = 0.0
        checks = 0
        
        # Length check
        if len(story) >= 1000:
            quality_score += 0.2
        checks += 1
        
        # Character name presence
        character_names = ['pilot', 'engineer', 'scientist']
        name_mentions = sum(1 for name in character_names if name.lower() in story.lower())
        if name_mentions >= 2:
            quality_score += 0.3
        checks += 1
        
        # No "For Unknown" segments
        if "For Unknown" not in story:
            quality_score += 0.3
        checks += 1
        
        # Coherent structure
        if story.count('.') >= 5:  # Multiple sentences
            quality_score += 0.1
        checks += 1
        
        # Sci-fi atmosphere
        sci_fi_terms = ['galaxy', 'cosmic', 'space', 'stellar', 'mission', 'operative']
        sci_fi_mentions = sum(1 for term in sci_fi_terms if term.lower() in story.lower())
        if sci_fi_mentions >= 3:
            quality_score += 0.1
        checks += 1
        
        return quality_score
    
    def test_component_interaction_workflows(self) -> Dict[str, Any]:
        """Test component interaction workflows."""
        
        print("\n🔄 TESTING COMPONENT INTERACTION WORKFLOWS")
        print("=" * 60)
        
        workflows = {
            'character_creation_workflow': self._test_character_creation_workflow,
            'story_generation_workflow': self._test_story_generation_workflow,
            'error_recovery_workflow': self._test_error_recovery_workflow,
            'concurrent_simulation_workflow': self._test_concurrent_simulation_workflow
        }
        
        results = {
            'workflows_tested': 0,
            'workflows_passed': 0,
            'workflow_details': {},
            'overall_success': True
        }
        
        for workflow_name, workflow_test in workflows.items():
            print(f"🔗 Testing: {workflow_name}")
            
            try:
                start_time = time.time()
                workflow_result = workflow_test()
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                if workflow_result.get('success', False):
                    print(f"   ✅ PASS - Time: {execution_time:.2f}s")
                    results['workflows_passed'] += 1
                else:
                    print(f"   ❌ FAIL - {workflow_result.get('error', 'Unknown error')}")
                    results['overall_success'] = False
                
                results['workflow_details'][workflow_name] = {
                    'success': workflow_result.get('success', False),
                    'execution_time': execution_time,
                    'details': workflow_result
                }
                
            except Exception as e:
                print(f"   ❌ FAIL - Exception: {e}")
                results['workflow_details'][workflow_name] = {
                    'success': False,
                    'error': str(e)
                }
                results['overall_success'] = False
            
            results['workflows_tested'] += 1
        
        success_rate = results['workflows_passed'] / results['workflows_tested'] if results['workflows_tested'] > 0 else 0
        
        print(f"\n📊 WORKFLOW INTEGRATION SUMMARY:")
        print(f"   🔗 Workflows tested: {results['workflows_tested']}")
        print(f"   ✅ Passed: {results['workflows_passed']}")
        print(f"   📈 Success rate: {success_rate:.1%}")
        
        return results
    
    def _test_character_creation_workflow(self) -> Dict[str, Any]:
        """Test character creation workflow integration."""
        
        try:
            from character_factory import CharacterFactory
            
            factory = CharacterFactory()
            
            # Test character listing
            characters = factory.list_available_characters()
            if len(characters) < 3:
                return {'success': False, 'error': f"Expected at least 3 characters, got {len(characters)}"}
            
            # Test character creation
            test_characters = ['pilot', 'engineer', 'scientist']
            created_agents = []
            
            for char_name in test_characters:
                agent = factory.create_character(char_name)
                if not agent or not agent.agent_id:
                    return {'success': False, 'error': f"Failed to create character: {char_name}"}
                created_agents.append(agent)
            
            return {
                'success': True,
                'characters_available': len(characters),
                'characters_created': len(created_agents),
                'character_ids': [agent.agent_id for agent in created_agents]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_story_generation_workflow(self) -> Dict[str, Any]:
        """Test story generation workflow integration."""
        
        try:
            from character_factory import CharacterFactory
            from director_agent import DirectorAgent
            from chronicler_agent import ChroniclerAgent
            
            # Step 1: Create characters
            factory = CharacterFactory()
            agents = [factory.create_character('pilot'), factory.create_character('engineer')]
            
            # Step 2: Set up simulation
            with tempfile.NamedTemporaryFile(mode='w', suffix='_campaign_log.md', delete=False) as f:
                temp_log_path = f.name
            
            director = DirectorAgent(campaign_log_path=temp_log_path)
            
            for agent in agents:
                if not director.register_agent(agent):
                    return {'success': False, 'error': f"Failed to register agent: {agent.agent_id}"}
            
            # Step 3: Run simulation
            turn_result = director.run_turn()
            if not turn_result or turn_result.get('turn_number', 0) != 1:
                return {'success': False, 'error': 'Turn execution failed'}
            
            # Step 4: Generate story
            chronicler = ChroniclerAgent(
                narrative_style="sci_fi_dramatic",
                character_names=['pilot', 'engineer']
            )
            
            story = chronicler.transcribe_log(temp_log_path)
            
            # Cleanup
            os.unlink(temp_log_path)
            
            # Validate story quality
            quality_score = self._validate_story_quality(story)
            
            if quality_score < 0.5:
                return {'success': False, 'error': f"Story quality too low: {quality_score:.1%}"}
            
            return {
                'success': True,
                'agents_created': len(agents),
                'turns_executed': turn_result.get('turn_number', 0),
                'story_length': len(story),
                'story_quality': quality_score,
                'no_unknown_segments': "For Unknown" not in story
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_error_recovery_workflow(self) -> Dict[str, Any]:
        """Test error recovery and graceful degradation."""
        
        try:
            from chronicler_agent import ChroniclerAgent
            
            chronicler = ChroniclerAgent()
            
            # Test 1: Non-existent file handling
            try:
                chronicler.transcribe_log("nonexistent_file.md")
                return {'success': False, 'error': 'Expected FileNotFoundError was not raised'}
            except FileNotFoundError:
                pass  # Expected behavior
            
            # Test 2: Empty log handling
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("# Empty Campaign Log\n\n## Campaign Events\n\n")
                temp_empty_log = f.name
            
            try:
                empty_narrative = chronicler.transcribe_log(temp_empty_log)
                
                # Should generate something even for empty log
                if not empty_narrative or len(empty_narrative) < 100:
                    return {'success': False, 'error': 'Failed to handle empty log gracefully'}
                
                os.unlink(temp_empty_log)
                
            except Exception as e:
                os.unlink(temp_empty_log)
                return {'success': False, 'error': f'Empty log handling failed: {e}'}
            
            return {
                'success': True,
                'error_handling_tests': 2,
                'graceful_degradation': True
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_concurrent_simulation_workflow(self) -> Dict[str, Any]:
        """Test concurrent simulation handling."""
        
        def run_simulation(simulation_id: int) -> Dict[str, Any]:
            """Run a single simulation."""
            try:
                from character_factory import CharacterFactory
                from director_agent import DirectorAgent
                from chronicler_agent import ChroniclerAgent
                
                factory = CharacterFactory()
                agent = factory.create_character('pilot')
                
                with tempfile.NamedTemporaryFile(mode='w', suffix=f'_sim_{simulation_id}_campaign_log.md', delete=False) as f:
                    temp_log_path = f.name
                
                director = DirectorAgent(campaign_log_path=temp_log_path)
                director.register_agent(agent)
                director.run_turn()
                
                chronicler = ChroniclerAgent(character_names=['pilot'])
                story = chronicler.transcribe_log(temp_log_path)
                
                os.unlink(temp_log_path)
                
                return {
                    'simulation_id': simulation_id,
                    'success': True,
                    'story_length': len(story),
                    'quality_score': self._validate_story_quality(story)
                }
                
            except Exception as e:
                return {
                    'simulation_id': simulation_id,
                    'success': False,
                    'error': str(e)
                }
        
        try:
            # Run 3 concurrent simulations
            concurrent_count = 3
            simulation_results = []
            
            with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
                future_to_sim = {executor.submit(run_simulation, i): i for i in range(concurrent_count)}
                
                for future in as_completed(future_to_sim):
                    result = future.result()
                    simulation_results.append(result)
            
            # Analyze results
            successful_sims = [r for r in simulation_results if r.get('success', False)]
            success_rate = len(successful_sims) / len(simulation_results)
            
            return {
                'success': success_rate >= 0.8,  # At least 80% should succeed
                'concurrent_simulations': concurrent_count,
                'successful_simulations': len(successful_sims),
                'success_rate': success_rate,
                'simulation_results': simulation_results
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_performance_integration(self) -> Dict[str, Any]:
        """Test performance characteristics under integration scenarios."""
        
        print("\n⚡ TESTING PERFORMANCE INTEGRATION")
        print("=" * 60)
        
        performance_tests = {
            'api_response_times': self._test_api_response_times,
            'story_generation_speed': self._test_story_generation_speed,
            'concurrent_load_handling': self._test_concurrent_load_handling,
            'memory_usage_stability': self._test_memory_usage_stability
        }
        
        results = {
            'tests_run': 0,
            'tests_passed': 0,
            'performance_metrics': {},
            'overall_success': True
        }
        
        for test_name, test_func in performance_tests.items():
            print(f"⚡ Testing: {test_name}")
            
            try:
                test_result = test_func()
                
                if test_result.get('success', False):
                    print(f"   ✅ PASS - {test_result.get('summary', '')}")
                    results['tests_passed'] += 1
                else:
                    print(f"   ❌ FAIL - {test_result.get('error', 'Performance threshold not met')}")
                    results['overall_success'] = False
                
                results['performance_metrics'][test_name] = test_result
                
            except Exception as e:
                print(f"   ❌ FAIL - Exception: {e}")
                results['performance_metrics'][test_name] = {'success': False, 'error': str(e)}
                results['overall_success'] = False
            
            results['tests_run'] += 1
        
        return results
    
    def _test_api_response_times(self) -> Dict[str, Any]:
        """Test API response time performance."""
        
        try:
            endpoints = ['/health', '/characters', '/meta/system-status']
            response_times = []
            
            for endpoint in endpoints:
                start_time = time.time()
                response = requests.get(f"{self.api_base_url}{endpoint}", timeout=10)
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
            
            if not response_times:
                return {'success': False, 'error': 'No successful API calls'}
            
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            # Performance thresholds
            avg_threshold = 2.0  # 2 seconds average
            max_threshold = 5.0  # 5 seconds maximum
            
            success = avg_response_time <= avg_threshold and max_response_time <= max_threshold
            
            return {
                'success': success,
                'avg_response_time': avg_response_time,
                'max_response_time': max_response_time,
                'endpoints_tested': len(endpoints),
                'summary': f"Avg: {avg_response_time:.2f}s, Max: {max_response_time:.2f}s"
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_story_generation_speed(self) -> Dict[str, Any]:
        """Test story generation performance."""
        
        try:
            from character_factory import CharacterFactory
            from director_agent import DirectorAgent
            from chronicler_agent import ChroniclerAgent
            
            # Create test setup
            factory = CharacterFactory()
            agent = factory.create_character('pilot')
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='_perf_campaign_log.md', delete=False) as f:
                temp_log_path = f.name
            
            director = DirectorAgent(campaign_log_path=temp_log_path)
            director.register_agent(agent)
            
            # Run multiple turns to create substantial content
            for _ in range(5):
                director.run_turn()
            
            # Time story generation
            chronicler = ChroniclerAgent(character_names=['pilot'])
            
            start_time = time.time()
            story = chronicler.transcribe_log(temp_log_path)
            end_time = time.time()
            
            generation_time = end_time - start_time
            os.unlink(temp_log_path)
            
            # Performance thresholds
            time_threshold = 30.0  # 30 seconds maximum
            min_story_length = 1000  # Minimum story length
            
            success = generation_time <= time_threshold and len(story) >= min_story_length
            
            return {
                'success': success,
                'generation_time': generation_time,
                'story_length': len(story),
                'words_per_second': len(story.split()) / generation_time if generation_time > 0 else 0,
                'summary': f"Generated {len(story)} chars in {generation_time:.2f}s"
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_concurrent_load_handling(self) -> Dict[str, Any]:
        """Test concurrent load handling."""
        
        def make_api_request(request_id: int) -> Dict[str, Any]:
            """Make a single API request."""
            try:
                start_time = time.time()
                response = requests.get(f"{self.api_base_url}/characters", timeout=30)
                end_time = time.time()
                
                return {
                    'request_id': request_id,
                    'success': response.status_code == 200,
                    'response_time': end_time - start_time,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'request_id': request_id,
                    'success': False,
                    'error': str(e)
                }
        
        try:
            # Make 10 concurrent requests
            concurrent_requests = 10
            
            with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
                future_to_req = {executor.submit(make_api_request, i): i for i in range(concurrent_requests)}
                
                results = []
                for future in as_completed(future_to_req):
                    result = future.result()
                    results.append(result)
            
            # Analyze results
            successful_requests = [r for r in results if r.get('success', False)]
            success_rate = len(successful_requests) / len(results)
            
            if successful_requests:
                avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
                max_response_time = max(r['response_time'] for r in successful_requests)
            else:
                avg_response_time = 0
                max_response_time = 0
            
            # Success criteria: 80% success rate, average response time < 10s
            success = success_rate >= 0.8 and avg_response_time <= 10.0
            
            return {
                'success': success,
                'concurrent_requests': concurrent_requests,
                'successful_requests': len(successful_requests),
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'max_response_time': max_response_time,
                'summary': f"{success_rate:.1%} success rate, avg {avg_response_time:.2f}s"
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _test_memory_usage_stability(self) -> Dict[str, Any]:
        """Test memory usage stability during operations."""
        
        try:
            import psutil
            import gc
            
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform multiple story generation cycles
            from character_factory import CharacterFactory
            from director_agent import DirectorAgent
            from chronicler_agent import ChroniclerAgent
            
            factory = CharacterFactory()
            
            for cycle in range(3):
                # Create simulation
                agent = factory.create_character('pilot')
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='_mem_campaign_log.md', delete=False) as f:
                    temp_log_path = f.name
                
                director = DirectorAgent(campaign_log_path=temp_log_path)
                director.register_agent(agent)
                director.run_turn()
                
                # Generate story
                chronicler = ChroniclerAgent(character_names=['pilot'])
                story = chronicler.transcribe_log(temp_log_path)
                
                # Cleanup
                os.unlink(temp_log_path)
                del director, chronicler, agent, story
                gc.collect()
            
            # Get final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB for 3 cycles)
            memory_threshold = 100.0  # MB
            success = memory_increase <= memory_threshold
            
            return {
                'success': success,
                'initial_memory_mb': initial_memory,
                'final_memory_mb': final_memory,
                'memory_increase_mb': memory_increase,
                'cycles_performed': 3,
                'summary': f"Memory increased by {memory_increase:.1f}MB over 3 cycles"
            }
            
        except ImportError:
            return {'success': True, 'error': 'psutil not available - memory test skipped'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_integration_report(self) -> Dict[str, Any]:
        """Generate comprehensive integration test report."""
        
        print("\n" + "=" * 80)
        print("🏁 PHASE 2.2: INTEGRATION TESTING SUMMARY")
        print("=" * 80)
        
        # Run all integration tests
        api_results = self.test_api_endpoint_integration()
        workflow_results = self.test_component_interaction_workflows()
        performance_results = self.test_performance_integration()
        
        # Calculate overall success metrics
        total_tests = (
            api_results.get('tests_run', 0) + 
            workflow_results.get('workflows_tested', 0) + 
            performance_results.get('tests_run', 0)
        )
        
        total_passed = (
            api_results.get('tests_passed', 0) + 
            workflow_results.get('workflows_passed', 0) + 
            performance_results.get('tests_passed', 0)
        )
        
        overall_success_rate = total_passed / total_tests if total_tests > 0 else 0
        
        overall_success = (
            api_results.get('overall_success', False) and
            workflow_results.get('overall_success', False) and
            performance_results.get('overall_success', False)
        )
        
        print(f"\n📊 INTEGRATION TEST METRICS:")
        print(f"   🧪 Total Tests: {total_tests}")
        print(f"   ✅ Total Passed: {total_passed}")
        print(f"   📈 Success Rate: {overall_success_rate:.1%}")
        print(f"   🌐 API Tests: {api_results.get('tests_passed', 0)}/{api_results.get('tests_run', 0)}")
        print(f"   🔗 Workflow Tests: {workflow_results.get('workflows_passed', 0)}/{workflow_results.get('workflows_tested', 0)}")
        print(f"   ⚡ Performance Tests: {performance_results.get('tests_passed', 0)}/{performance_results.get('tests_run', 0)}")
        
        if overall_success and overall_success_rate >= 0.8:
            print(f"\n✅ INTEGRATION TESTS: EXCELLENT - System ready for validation phase")
        elif overall_success_rate >= 0.6:
            print(f"\n⚠️  INTEGRATION TESTS: GOOD - Minor issues to address")
        else:
            print(f"\n❌ INTEGRATION TESTS: ISSUES DETECTED - Address failures before proceeding")
        
        return {
            'api_results': api_results,
            'workflow_results': workflow_results,
            'performance_results': performance_results,
            'overall_metrics': {
                'total_tests': total_tests,
                'total_passed': total_passed,
                'success_rate': overall_success_rate,
                'overall_success': overall_success
            }
        }


def main():
    """Execute Phase 2.2 Integration Testing."""
    
    print("🔗 STORYFORGE AI - PHASE 2.2: INTEGRATION TESTING")
    print("=" * 80)
    print("Comprehensive testing of component integration and system workflows")
    print("=" * 80)
    
    tester = IntegrationTester()
    
    # Check if API server is running
    try:
        response = requests.get(f"{tester.api_base_url}/health", timeout=5)
        if response.status_code != 200:
            print("⚠️  WARNING: API server health check failed - some tests may not run")
    except requests.exceptions.RequestException:
        print("⚠️  WARNING: API server not accessible - API tests will be skipped")
    
    report = tester.generate_integration_report()
    
    # Save report
    output_dir = Path(__file__).parent
    report_path = output_dir / 'phase2_2_integration_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n💾 Integration test report saved: {report_path}")
    
    return report['overall_metrics']['success_rate'] >= 0.7

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)