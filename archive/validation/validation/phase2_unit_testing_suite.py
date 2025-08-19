#!/usr/bin/env python3
"""
PHASE 2.1: Comprehensive Unit Testing Suite
==========================================

Implementation of thorough unit tests covering:
1. Core component functionality
2. Error handling and edge cases
3. Data flow validation
4. Configuration management
5. Character integration
6. Story generation pipeline
"""

import sys
import os
import unittest
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestCharacterFactory(unittest.TestCase):
    """Unit tests for CharacterFactory component."""
    
    def setUp(self):
        """Set up test fixtures."""
        from character_factory import CharacterFactory
        self.factory = CharacterFactory()
    
    def test_factory_initialization(self):
        """Test CharacterFactory initialization."""
        self.assertIsNotNone(self.factory)
        self.assertEqual(self.factory.base_character_path, "characters")
    
    def test_list_available_characters(self):
        """Test character listing functionality."""
        characters = self.factory.list_available_characters()
        self.assertIsInstance(characters, list)
        self.assertGreater(len(characters), 0)
        
        # Verify expected characters exist
        expected_chars = ['pilot', 'engineer', 'scientist']
        for char in expected_chars:
            self.assertIn(char, characters, f"Character '{char}' should be available")
    
    def test_create_character_success(self):
        """Test successful character creation."""
        agent = self.factory.create_character('pilot')
        
        self.assertIsNotNone(agent)
        self.assertEqual(agent.agent_id, 'pilot')
        self.assertIsNotNone(agent.character_data)
        self.assertIsInstance(agent.character_data, dict)
    
    def test_create_character_invalid_name(self):
        """Test character creation with invalid name."""
        with self.assertRaises(ValueError):
            self.factory.create_character("")
        
        with self.assertRaises(ValueError):
            self.factory.create_character(None)
    
    def test_create_character_not_found(self):
        """Test character creation for non-existent character."""
        with self.assertRaises(FileNotFoundError):
            self.factory.create_character('nonexistent_character')


class TestChroniclerAgent(unittest.TestCase):
    """Unit tests for ChroniclerAgent component."""
    
    def setUp(self):
        """Set up test fixtures."""
        from chronicler_agent import ChroniclerAgent
        self.chronicler = ChroniclerAgent(
            narrative_style="sci_fi_dramatic",
            character_names=['pilot', 'engineer', 'scientist']
        )
    
    def test_chronicler_initialization(self):
        """Test ChroniclerAgent initialization."""
        self.assertIsNotNone(self.chronicler)
        self.assertEqual(self.chronicler.character_names, ['pilot', 'engineer', 'scientist'])
        self.assertEqual(self.chronicler.narrative_style, 'sci_fi_dramatic')
    
    def test_character_name_injection(self):
        """Test that character names are properly injected."""
        self.assertEqual(self.chronicler.character_names, ['pilot', 'engineer', 'scientist'])
        
        # Test character name usage in response generation
        response = self.chronicler._generate_registration_response("test prompt")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        # Should contain one of the character names
        contains_character = any(name in response for name in ['pilot', 'engineer', 'scientist'])
        self.assertTrue(contains_character, "Response should contain a character name")
    
    def test_narrative_style_setting(self):
        """Test narrative style configuration."""
        success = self.chronicler.set_narrative_style('sci_fi_dramatic')
        self.assertTrue(success)
        
        # Test invalid style
        success = self.chronicler.set_narrative_style('invalid_style')
        self.assertFalse(success)
    
    def test_campaign_log_transcription(self):
        """Test campaign log transcription functionality."""
        # Create test campaign log
        test_log_content = """# Test Campaign Log

**Simulation Started:** 2025-08-13 23:30:00
**Director Agent:** DirectorAgent v1.0

## Campaign Events

### Turn 1 Event
**Time:** 2025-08-13 23:30:01
**Event:** **Agent Registration:** pilot (pilot_agent) joined the simulation
**Faction:** Test Faction
**Turn:** 1
**Active Agents:** 1

### Turn 2 Event
**Time:** 2025-08-13 23:30:02
**Event:** **Agent Action:** pilot decided to investigate the area
**Turn:** 2
**Active Agents:** 1
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_log_content)
            temp_log_path = f.name
        
        try:
            narrative = self.chronicler.transcribe_log(temp_log_path)
            
            # Validate narrative output
            self.assertIsInstance(narrative, str)
            self.assertGreater(len(narrative), 100)
            
            # Should contain character names
            for name in ['pilot', 'engineer', 'scientist']:
                if name in narrative.lower():
                    break
            else:
                self.fail("Narrative should contain at least one character name")
            
            # Should not contain "For Unknown"
            self.assertNotIn("For Unknown", narrative, "Narrative should not contain 'For Unknown'")
            
        finally:
            os.unlink(temp_log_path)


class TestDirectorAgent(unittest.TestCase):
    """Unit tests for DirectorAgent component."""
    
    def setUp(self):
        """Set up test fixtures."""
        from director_agent import DirectorAgent
        
        # Create temporary campaign log
        self.temp_log = tempfile.NamedTemporaryFile(mode='w', suffix='_campaign_log.md', delete=False)
        self.temp_log.close()
        
        self.director = DirectorAgent(campaign_log_path=self.temp_log.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_log.name):
            os.unlink(self.temp_log.name)
    
    def test_director_initialization(self):
        """Test DirectorAgent initialization."""
        self.assertIsNotNone(self.director)
        self.assertEqual(self.director.campaign_log_path, self.temp_log.name)
        self.assertEqual(len(self.director.registered_agents), 0)
    
    def test_campaign_log_creation(self):
        """Test campaign log file creation."""
        self.assertTrue(os.path.exists(self.temp_log.name))
        
        # Check log content
        with open(self.temp_log.name, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn("# Campaign Log", content)
        self.assertIn("DirectorAgent initialized", content)
    
    def test_agent_registration(self):
        """Test agent registration functionality."""
        from character_factory import CharacterFactory
        
        factory = CharacterFactory()
        agent = factory.create_character('pilot')
        
        # Test successful registration
        success = self.director.register_agent(agent)
        self.assertTrue(success)
        self.assertEqual(len(self.director.registered_agents), 1)
        
        # Test duplicate registration
        success = self.director.register_agent(agent)
        self.assertFalse(success)
        self.assertEqual(len(self.director.registered_agents), 1)
    
    def test_turn_execution(self):
        """Test simulation turn execution."""
        from character_factory import CharacterFactory
        
        factory = CharacterFactory()
        agent = factory.create_character('pilot')
        self.director.register_agent(agent)
        
        # Execute turn
        result = self.director.run_turn()
        
        self.assertIsInstance(result, dict)
        self.assertIn('turn_number', result)
        self.assertIn('participating_agents', result)
        self.assertIn('duration', result)
        self.assertEqual(result['turn_number'], 1)


class TestConfigLoader(unittest.TestCase):
    """Unit tests for configuration management."""
    
    def test_config_loading(self):
        """Test configuration loading."""
        from config_loader import get_config
        
        config = get_config()
        self.assertIsNotNone(config)
        
        # Test basic config structure
        self.assertTrue(hasattr(config, 'simulation'))
        self.assertTrue(hasattr(config.simulation, 'turns'))


class TestCharacterIntegration(unittest.TestCase):
    """Integration tests for character name flow."""
    
    def test_end_to_end_character_flow(self):
        """Test complete character name integration flow."""
        from character_factory import CharacterFactory
        from director_agent import DirectorAgent
        from chronicler_agent import ChroniclerAgent
        
        requested_names = ['pilot', 'engineer']
        
        # Step 1: Create characters
        factory = CharacterFactory()
        agents = []
        for name in requested_names:
            agent = factory.create_character(name)
            agents.append(agent)
        
        # Step 2: Run simulation
        with tempfile.NamedTemporaryFile(mode='w', suffix='_campaign_log.md', delete=False) as f:
            temp_log_path = f.name
        
        try:
            director = DirectorAgent(campaign_log_path=temp_log_path)
            
            for agent in agents:
                director.register_agent(agent)
            
            # Run one turn
            director.run_turn()
            
            # Step 3: Generate narrative with character name injection
            chronicler = ChroniclerAgent(
                narrative_style="sci_fi_dramatic",
                character_names=requested_names
            )
            
            narrative = chronicler.transcribe_log(temp_log_path)
            
            # Validate integration
            self.assertIsInstance(narrative, str)
            self.assertGreater(len(narrative), 100)
            
            # Check for character names in narrative
            name_mentions = sum(narrative.lower().count(name.lower()) for name in requested_names)
            self.assertGreater(name_mentions, 0, "Narrative should contain requested character names")
            
            # Verify no "For Unknown" segments
            self.assertNotIn("For Unknown", narrative)
            
        finally:
            if os.path.exists(temp_log_path):
                os.unlink(temp_log_path)


class TestErrorHandling(unittest.TestCase):
    """Unit tests for error handling scenarios."""
    
    def test_chronicler_invalid_log_file(self):
        """Test ChroniclerAgent with invalid log file."""
        from chronicler_agent import ChroniclerAgent
        
        chronicler = ChroniclerAgent()
        
        # Test non-existent file
        with self.assertRaises(FileNotFoundError):
            chronicler.transcribe_log("nonexistent_file.md")
    
    def test_director_invalid_agent(self):
        """Test DirectorAgent with invalid agent."""
        from director_agent import DirectorAgent
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='_campaign_log.md', delete=False) as f:
            temp_log_path = f.name
        
        try:
            director = DirectorAgent(campaign_log_path=temp_log_path)
            
            # Test invalid agent type
            success = director.register_agent("invalid_agent")
            self.assertFalse(success)
            
            # Test None agent
            success = director.register_agent(None)
            self.assertFalse(success)
            
        finally:
            if os.path.exists(temp_log_path):
                os.unlink(temp_log_path)
    
    def test_character_factory_error_handling(self):
        """Test CharacterFactory error handling."""
        from character_factory import CharacterFactory
        
        factory = CharacterFactory()
        
        # Test empty character name
        with self.assertRaises(ValueError):
            factory.create_character("")
        
        # Test whitespace-only name
        with self.assertRaises(ValueError):
            factory.create_character("   ")


class TestPerformanceBounds(unittest.TestCase):
    """Performance and boundary tests."""
    
    def test_chronicler_large_campaign_log(self):
        """Test ChroniclerAgent with large campaign log."""
        from chronicler_agent import ChroniclerAgent
        
        chronicler = ChroniclerAgent(character_names=['test_char'])
        
        # Create large test log
        large_log_content = """# Large Campaign Log

**Simulation Started:** 2025-08-13 23:30:00
**Director Agent:** DirectorAgent v1.0

## Campaign Events

"""
        
        # Add many events
        for i in range(50):
            large_log_content += f"""### Turn {i+1} Event
**Time:** 2025-08-13 23:30:{i:02d}
**Event:** **Agent Action:** test_char performed action {i+1}
**Turn:** {i+1}
**Active Agents:** 1

"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(large_log_content)
            temp_log_path = f.name
        
        try:
            import time
            start_time = time.time()
            
            narrative = chronicler.transcribe_log(temp_log_path)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Performance assertions
            self.assertLess(processing_time, 30.0, "Processing should complete within 30 seconds")
            self.assertIsInstance(narrative, str)
            self.assertGreater(len(narrative), 1000)
            
        finally:
            os.unlink(temp_log_path)


def run_unit_test_suite() -> Dict[str, Any]:
    """Execute comprehensive unit test suite."""
    
    print("🧪 STORYFORGE AI - PHASE 2.1: UNIT TESTING SUITE")
    print("=" * 80)
    
    # Create test suite
    test_classes = [
        TestCharacterFactory,
        TestChroniclerAgent, 
        TestDirectorAgent,
        TestConfigLoader,
        TestCharacterIntegration,
        TestErrorHandling,
        TestPerformanceBounds
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Generate summary
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    successes = total_tests - failures - errors
    
    print("\n" + "=" * 80)
    print("🏁 UNIT TEST SUITE SUMMARY")
    print("=" * 80)
    print(f"📊 Total Tests: {total_tests}")
    print(f"✅ Passed: {successes}")
    print(f"❌ Failed: {failures}")
    print(f"💥 Errors: {errors}")
    print(f"📈 Success Rate: {(successes/total_tests*100):.1f}%")
    
    if result.wasSuccessful():
        print("✅ UNIT TESTS: ALL PASSED - Components ready for integration testing")
    else:
        print("❌ UNIT TESTS: ISSUES DETECTED - Review failures before proceeding")
        
        if result.failures:
            print("\n🚨 FAILURES:")
            for test, traceback in result.failures:
                print(f"   • {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0] if 'AssertionError: ' in traceback else 'See details above'}")
        
        if result.errors:
            print("\n💥 ERRORS:")
            for test, traceback in result.errors:
                print(f"   • {test}: {traceback.split('\\n')[-2] if traceback else 'Unknown error'}")
    
    return {
        'total_tests': total_tests,
        'passed': successes,
        'failed': failures,
        'errors': errors,
        'success_rate': successes/total_tests if total_tests > 0 else 0,
        'overall_success': result.wasSuccessful()
    }


def main():
    """Execute Phase 2.1 Unit Testing Suite."""
    
    report = run_unit_test_suite()
    
    # Save report
    output_dir = Path(__file__).parent
    report_path = output_dir / 'phase2_1_unit_test_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Unit test report saved: {report_path}")
    
    return report['success_rate'] >= 0.8

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)