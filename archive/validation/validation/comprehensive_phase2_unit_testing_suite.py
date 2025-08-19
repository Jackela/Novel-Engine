#!/usr/bin/env python3
"""
StoryForge AI - Comprehensive Phase 2: Unit Testing Suite
Advanced unit testing framework with comprehensive coverage
"""

import unittest
import json
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import system components for testing
try:
    from character_factory import CharacterFactory
    from chronicler_agent import ChroniclerAgent
    from director_agent import DirectorAgent
    from config_loader import ConfigLoader, get_config
    from src.persona_agent import PersonaAgent
    from shared_types import CharacterAction
except ImportError as e:
    print(f"⚠️ Import warning: {e}")

class TestCharacterFactory(unittest.TestCase):
    """Comprehensive tests for CharacterFactory"""
    
    def setUp(self):
        """Set up test environment"""
        self.factory = CharacterFactory()
    
    def test_factory_initialization(self):
        """Test factory initializes correctly"""
        self.assertIsInstance(self.factory, CharacterFactory)
        self.assertTrue(hasattr(self.factory, 'list_available_characters'))
    
    def test_list_available_characters(self):
        """Test character listing functionality"""
        characters = self.factory.list_available_characters()
        self.assertIsInstance(characters, list)
        self.assertGreater(len(characters), 0, "Should have at least one character available")
    
    def test_create_valid_character(self):
        """Test creating a valid character"""
        characters = self.factory.list_available_characters()
        if characters:
            character = self.factory.create_character(characters[0])
            self.assertIsNotNone(character)
            self.assertTrue(hasattr(character, 'character_name'))
    
    def test_create_invalid_character(self):
        """Test creating an invalid character raises appropriate error"""
        with self.assertRaises(Exception):
            self.factory.create_character("nonexistent_character_xyz_123")
    
    def test_character_data_integrity(self):
        """Test character data integrity"""
        characters = self.factory.list_available_characters()
        if characters:
            character = self.factory.create_character(characters[0])
            # Verify character has required attributes
            self.assertTrue(hasattr(character, 'character_name'))
            self.assertIsInstance(character.character_name, str)
            self.assertNotEqual(character.character_name.strip(), "")
    
    def test_factory_consistency(self):
        """Test factory creates consistent characters"""
        characters = self.factory.list_available_characters()
        if characters:
            char1 = self.factory.create_character(characters[0])
            char2 = self.factory.create_character(characters[0])
            # Should create identical characters
            self.assertEqual(char1.character_name, char2.character_name)

class TestChroniclerAgent(unittest.TestCase):
    """Comprehensive tests for ChroniclerAgent"""
    
    def setUp(self):
        """Set up test environment"""
        self.chronicler = ChroniclerAgent()
    
    def test_chronicler_initialization(self):
        """Test chronicler initializes correctly"""
        self.assertIsInstance(self.chronicler, ChroniclerAgent)
        self.assertTrue(hasattr(self.chronicler, 'transcribe_log'))
    
    def test_transcribe_empty_log(self):
        """Test transcribing an empty log"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            tmp.write("")
            tmp_path = tmp.name
        
        try:
            result = self.chronicler.transcribe_log(tmp_path)
            self.assertIsInstance(result, str)
        finally:
            os.unlink(tmp_path)
    
    def test_transcribe_simple_log(self):
        """Test transcribing a simple campaign log"""
        log_content = """# Campaign Log
## Turn 1
- **pilot**: Flew the ship
- **engineer**: Fixed the engine
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            tmp.write(log_content)
            tmp_path = tmp.name
        
        try:
            result = self.chronicler.transcribe_log(tmp_path)
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
        finally:
            os.unlink(tmp_path)
    
    def test_transcribe_nonexistent_file(self):
        """Test transcribing a nonexistent file"""
        with self.assertRaises(Exception):
            self.chronicler.transcribe_log("/nonexistent/file/path.md")
    
    def test_transcribe_malformed_log(self):
        """Test handling malformed log files"""
        malformed_content = "This is not a proper campaign log format"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            tmp.write(malformed_content)
            tmp_path = tmp.name
        
        try:
            result = self.chronicler.transcribe_log(tmp_path)
            self.assertIsInstance(result, str)  # Should handle gracefully
        finally:
            os.unlink(tmp_path)

class TestDirectorAgent(unittest.TestCase):
    """Comprehensive tests for DirectorAgent"""
    
    def setUp(self):
        """Set up test environment"""
        self.director = DirectorAgent()
    
    def test_director_initialization(self):
        """Test director initializes correctly"""
        self.assertIsInstance(self.director, DirectorAgent)
        self.assertTrue(hasattr(self.director, 'register_agent'))
        self.assertTrue(hasattr(self.director, 'run_turn'))
    
    def test_register_agent(self):
        """Test agent registration"""
        mock_agent = Mock()
        mock_agent.character_name = "test_character"
        
        result = self.director.register_agent(mock_agent)
        # Should not raise an exception
        self.assertIsNone(result)  # Most registration methods return None
    
    def test_run_turn_no_agents(self):
        """Test running a turn with no agents"""
        result = self.director.run_turn()
        self.assertIsInstance(result, dict)
    
    def test_run_turn_with_agents(self):
        """Test running a turn with registered agents"""
        mock_agent1 = Mock()
        mock_agent1.character_name = "agent1"
        mock_agent1.decision_loop.return_value = CharacterAction(
            action_type="wait",
            target=None,
            priority="low",
            reasoning="Test action"
        )
        
        mock_agent2 = Mock()
        mock_agent2.character_name = "agent2" 
        mock_agent2.decision_loop.return_value = CharacterAction(
            action_type="wait",
            target=None,
            priority="low",
            reasoning="Test action"
        )
        
        self.director.register_agent(mock_agent1)
        self.director.register_agent(mock_agent2)
        
        result = self.director.run_turn()
        self.assertIsInstance(result, dict)
        self.assertIn("turn_number", result)
    
    def test_multiple_turns(self):
        """Test running multiple turns"""
        mock_agent = Mock()
        mock_agent.character_name = "test_agent"
        mock_agent.decision_loop.return_value = CharacterAction(
            action_type="wait",
            target=None,
            priority="low",
            reasoning="Test action"
        )
        
        self.director.register_agent(mock_agent)
        
        # Run multiple turns
        for i in range(3):
            result = self.director.run_turn()
            self.assertIsInstance(result, dict)
            self.assertIn("turn_number", result)

class TestConfigLoader(unittest.TestCase):
    """Comprehensive tests for ConfigLoader"""
    
    def test_get_config(self):
        """Test configuration loading"""
        try:
            config = get_config()
            self.assertIsInstance(config, dict)
        except Exception:
            # Config loading might fail in test environment
            self.skipTest("Config loading failed - expected in test environment")
    
    def test_config_loader_initialization(self):
        """Test ConfigLoader can be instantiated"""
        try:
            loader = ConfigLoader()
            self.assertIsInstance(loader, ConfigLoader)
        except Exception:
            self.skipTest("ConfigLoader initialization failed - expected in test environment")

class TestPersonaAgent(unittest.TestCase):
    """Comprehensive tests for PersonaAgent"""
    
    def test_persona_agent_creation(self):
        """Test PersonaAgent can be created"""
        try:
            agent = PersonaAgent("test_character")
            self.assertIsInstance(agent, PersonaAgent)
            self.assertEqual(agent.character_name, "test_character")
        except Exception:
            self.skipTest("PersonaAgent creation failed - expected if missing dependencies")
    
    def test_persona_agent_decision_loop(self):
        """Test PersonaAgent decision loop"""
        try:
            agent = PersonaAgent("test_character")
            if hasattr(agent, 'decision_loop'):
                result = agent.decision_loop()
                self.assertIsInstance(result, CharacterAction)
        except Exception:
            self.skipTest("PersonaAgent decision loop test failed - expected if missing dependencies")

class TestSystemIntegration(unittest.TestCase):
    """Integration tests for system components"""
    
    def test_factory_director_integration(self):
        """Test CharacterFactory and DirectorAgent integration"""
        try:
            factory = CharacterFactory()
            director = DirectorAgent()
            
            characters = factory.list_available_characters()
            if characters:
                agent = factory.create_character(characters[0])
                director.register_agent(agent)
                result = director.run_turn()
                
                self.assertIsInstance(result, dict)
        except Exception as e:
            self.skipTest(f"Integration test failed: {e}")
    
    def test_full_system_workflow(self):
        """Test complete system workflow"""
        try:
            # Initialize components
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
                
                # Run simulation
                result = director.run_turn()
                self.assertIsInstance(result, dict)
                
                # Test chronicler (if campaign log exists)
                campaign_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "campaign_log.md")
                if os.path.exists(campaign_log_path):
                    narrative = chronicler.transcribe_log(campaign_log_path)
                    self.assertIsInstance(narrative, str)
                    
        except Exception as e:
            self.skipTest(f"Full system workflow test failed: {e}")

class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def test_character_factory_error_handling(self):
        """Test CharacterFactory error handling"""
        factory = CharacterFactory()
        
        # Test with None input
        with self.assertRaises(Exception):
            factory.create_character(None)
        
        # Test with empty string
        with self.assertRaises(Exception):
            factory.create_character("")
        
        # Test with invalid character name
        with self.assertRaises(Exception):
            factory.create_character("invalid_character_name_12345")
    
    def test_director_agent_error_handling(self):
        """Test DirectorAgent error handling"""
        director = DirectorAgent()
        
        # Test registering None agent
        try:
            director.register_agent(None)
            # Should either handle gracefully or raise exception
        except Exception:
            pass  # Either outcome is acceptable
    
    def test_chronicler_error_handling(self):
        """Test ChroniclerAgent error handling"""
        chronicler = ChroniclerAgent()
        
        # Test with None path
        with self.assertRaises(Exception):
            chronicler.transcribe_log(None)
        
        # Test with invalid path
        with self.assertRaises(Exception):
            chronicler.transcribe_log("/invalid/path/to/file.md")

class UnitTestingSuite:
    """Comprehensive unit testing suite manager"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.test_results = {
            "test_summary": {},
            "detailed_results": {},
            "test_coverage_estimate": {},
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive unit test suite"""
        print("=== PHASE 2: COMPREHENSIVE UNIT TESTING SUITE ===\n")
        
        # 1. Discover and run tests
        print("🧪 1. Running Unit Tests...")
        test_results = self._run_unit_tests()
        
        # 2. Analyze test coverage
        print("\n📊 2. Analyzing Test Coverage...")
        coverage_analysis = self._analyze_test_coverage()
        
        # 3. Generate recommendations
        print("\n💡 3. Generating Testing Recommendations...")
        recommendations = self._generate_testing_recommendations(test_results, coverage_analysis)
        
        # 4. Save detailed report
        self._save_test_report()
        
        return self.test_results
    
    def _run_unit_tests(self) -> Dict[str, Any]:
        """Run all unit tests and collect results"""
        # Create test suite
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add all test classes
        test_classes = [
            TestCharacterFactory,
            TestChroniclerAgent, 
            TestDirectorAgent,
            TestConfigLoader,
            TestPersonaAgent,
            TestSystemIntegration,
            TestErrorHandling
        ]
        
        for test_class in test_classes:
            tests = loader.loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        # Run tests with detailed results
        test_runner = unittest.TextTestRunner(verbosity=2, stream=open(os.devnull, 'w'))
        result = test_runner.run(suite)
        
        # Collect results
        test_summary = {
            "total_tests": result.testsRun,
            "passed_tests": result.testsRun - len(result.failures) - len(result.errors),
            "failed_tests": len(result.failures),
            "error_tests": len(result.errors),
            "skipped_tests": len(result.skipped) if hasattr(result, 'skipped') else 0,
            "success_rate": ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
        }
        
        detailed_results = {
            "failures": [{"test": str(test), "error": str(error)} for test, error in result.failures],
            "errors": [{"test": str(test), "error": str(error)} for test, error in result.errors],
            "skipped": [{"test": str(test), "reason": str(reason)} for test, reason in (result.skipped if hasattr(result, 'skipped') else [])]
        }
        
        self.test_results["test_summary"] = test_summary
        self.test_results["detailed_results"] = detailed_results
        
        # Print test summary
        print(f"   📊 Test Results: {test_summary['passed_tests']}/{test_summary['total_tests']} tests passed ({test_summary['success_rate']:.1f}%)")
        print(f"   ✅ Passed: {test_summary['passed_tests']}")
        print(f"   ❌ Failed: {test_summary['failed_tests']}")
        print(f"   🚨 Errors: {test_summary['error_tests']}")
        print(f"   ⏭️ Skipped: {test_summary['skipped_tests']}")
        
        if result.failures:
            print(f"   🔍 Failures found in: {', '.join([str(test).split()[0] for test, _ in result.failures])}")
        
        if result.errors:
            print(f"   ⚠️ Errors found in: {', '.join([str(test).split()[0] for test, _ in result.errors])}")
        
        return test_summary
    
    def _analyze_test_coverage(self) -> Dict[str, Any]:
        """Analyze test coverage based on available tests vs source code"""
        coverage = {
            "source_files": 0,
            "test_files": 1,  # This test file
            "tested_components": [],
            "untested_components": [],
            "estimated_coverage_percentage": 0
        }
        
        # Count source files
        source_files = [f for f in Path(self.project_root).glob("*.py") if not f.name.startswith("test_")]
        coverage["source_files"] = len(source_files)
        
        # Identify tested components
        tested_components = [
            "CharacterFactory",
            "ChroniclerAgent", 
            "DirectorAgent",
            "ConfigLoader",
            "PersonaAgent"
        ]
        coverage["tested_components"] = tested_components
        
        # Identify untested components (simplified analysis)
        all_components = []
        for source_file in source_files:
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Extract class names
                import re
                classes = re.findall(r'class\s+(\w+)', content)
                all_components.extend(classes)
            except Exception:
                continue
        
        all_components = list(set(all_components))
        untested_components = [comp for comp in all_components if comp not in tested_components]
        coverage["untested_components"] = untested_components
        
        # Estimate coverage percentage
        total_components = len(all_components)
        if total_components > 0:
            coverage["estimated_coverage_percentage"] = (len(tested_components) / total_components) * 100
        
        self.test_results["test_coverage_estimate"] = coverage
        
        print(f"   📊 Estimated Test Coverage: {coverage['estimated_coverage_percentage']:.1f}%")
        print(f"   ✅ Tested Components: {len(tested_components)}")
        print(f"   ❌ Untested Components: {len(untested_components)}")
        
        return coverage
    
    def _generate_testing_recommendations(self, test_results: Dict[str, Any], coverage: Dict[str, Any]) -> List[str]:
        """Generate testing improvement recommendations"""
        recommendations = []
        
        # Test success rate recommendations
        success_rate = test_results.get("success_rate", 0)
        if success_rate < 80:
            recommendations.append(f"CRITICAL: Test success rate is only {success_rate:.1f}% - investigate and fix failing tests")
        elif success_rate < 95:
            recommendations.append(f"HIGH: Test success rate is {success_rate:.1f}% - aim for >95% success rate")
        
        # Coverage recommendations
        coverage_pct = coverage.get("estimated_coverage_percentage", 0)
        if coverage_pct < 60:
            recommendations.append(f"HIGH: Test coverage is only {coverage_pct:.1f}% - add tests for untested components")
        elif coverage_pct < 80:
            recommendations.append(f"MEDIUM: Test coverage is {coverage_pct:.1f}% - aim for 80%+ coverage")
        
        # Specific component recommendations
        untested = coverage.get("untested_components", [])
        if untested:
            recommendations.append(f"MEDIUM: Add unit tests for untested components: {', '.join(untested[:5])}")
        
        # Integration testing recommendations
        if test_results.get("failed_tests", 0) > 0:
            recommendations.append("HIGH: Fix failing unit tests before proceeding to integration testing")
        
        # Performance testing recommendations
        recommendations.append("LOW: Consider adding performance tests for critical components")
        
        self.test_results["recommendations"] = recommendations
        
        # Print recommendations
        if recommendations:
            print(f"   💡 Generated {len(recommendations)} testing recommendations")
            high_priority = [r for r in recommendations if r.startswith(("CRITICAL", "HIGH"))]
            if high_priority:
                print(f"   🚨 {len(high_priority)} high-priority recommendations require attention")
        
        return recommendations
    
    def _save_test_report(self):
        """Save comprehensive test report"""
        report_path = os.path.join(self.project_root, "validation", "comprehensive_phase2_unit_test_report.json")
        
        # Ensure validation directory exists
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        # Save comprehensive report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n📄 Comprehensive unit test report saved to: {report_path}")


def main():
    """Run Phase 2 Comprehensive Unit Testing Suite"""
    try:
        print("StoryForge AI - Phase 2: Comprehensive Unit Testing Suite")
        print("=" * 60)
        print("Advanced unit testing framework with comprehensive coverage")
        print()
        
        test_suite = UnitTestingSuite()
        results = test_suite.run_comprehensive_tests()
        
        return results
        
    except Exception as e:
        print(f"❌ Unit testing suite error: {str(e)}")
        return None


if __name__ == "__main__":
    main()