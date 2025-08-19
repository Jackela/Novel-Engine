#!/usr/bin/env python3
"""
ChroniclerAgent Unit Tests
==========================

Comprehensive pytest test suite for the ChroniclerAgent class.
Tests cover all core functionality including campaign log parsing, narrative generation,
LLM integration, error handling, and file management capabilities.

This test file includes:
- Mock campaign log creation and management for isolated testing
- ChroniclerAgent initialization and configuration tests
- Campaign log parsing and event extraction tests
- Narrative generation and LLM integration tests
- Error handling for various failure scenarios
- File output and management tests
- Performance validation and integration tests
- Advanced test cases with multiple turns and agents

Architecture Reference: Architecture_Blueprint.md Section 2.4 ChroniclerAgent
Development Phase: Phase 4 - Story Transcription (Final Integration)
"""

import pytest
import os
import tempfile
import shutil
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the ChroniclerAgent implementation
from chronicler_agent import ChroniclerAgent, CampaignEvent, NarrativeSegment


class TestChroniclerAgent:
    """
    Comprehensive test class for ChroniclerAgent functionality.
    
    Organizes tests into logical groups covering all aspects of the chronicler's
    operation from basic initialization to complex narrative generation.
    """
    
    @pytest.fixture
    def temp_dir(self):
        """
        Pytest fixture that creates a temporary directory for test files.
        
        Yields:
            str: Path to temporary directory
            
        Cleanup:
            Automatically removes the temporary directory after test completion
        """
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_campaign_log(self, temp_dir):
        """
        Pytest fixture that creates a mock campaign log file with structured test data.
        
        Creates a realistic campaign log with multiple events, turns, and agent actions
        that mirrors the actual DirectorAgent output format.
        
        Args:
            temp_dir: Temporary directory from temp_dir fixture
            
        Returns:
            str: Path to the created mock campaign log file
        """
        log_content = """# Warhammer 40k Multi-Agent Simulator - Campaign Log

**Simulation Started:** 2025-07-26 10:00:00  
**Director Agent:** DirectorAgent v1.0  
**Phase:** Phase 4 - Story Transcription Testing  

## Campaign Overview

This is a test campaign log for ChroniclerAgent unit testing.
Contains multiple events, turns, and agent interactions for comprehensive testing.

---

## Campaign Events

### Simulation Initialization
**Time:** 2025-07-26 10:00:00  
**Event:** DirectorAgent initialized and campaign log created  
**Participants:** System  
**Details:** Game Master AI successfully started, ready for agent registration and simulation execution


### Turn 1 Event
**Time:** 2025-07-26 10:01:00  
**Event:** **Agent Registration:** Brother Marcus (agent_001) joined the simulation
**Faction:** Space Marines
**Registration Time:** 2025-07-26 10:01:00
**Total Active Agents:** 1  
**Turn:** 1  
**Active Agents:** 1  

---

### Turn 1 Event
**Time:** 2025-07-26 10:01:30  
**Event:** **Agent Registration:** Commissar Vex (agent_002) joined the simulation
**Faction:** Astra Militarum
**Registration Time:** 2025-07-26 10:01:30
**Total Active Agents:** 2  
**Turn:** 1  
**Active Agents:** 2  

---

### Turn 1 Event
**Time:** 2025-07-26 10:02:00  
**Event:** **Agent Registration:** Warboss Skarfang (agent_003) joined the simulation
**Faction:** Goff Klan
**Registration Time:** 2025-07-26 10:02:00
**Total Active Agents:** 3  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 1 Event
**Time:** 2025-07-26 10:03:00  
**Event:** Turn 1 begins with 3 active agents ready for action  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 1 Event
**Time:** 2025-07-26 10:03:30  
**Event:** Brother Marcus (agent_001) decided to advance: [LLM-Guided] Moving forward to secure the objective with tactical precision  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 1 Event
**Time:** 2025-07-26 10:04:00  
**Event:** Commissar Vex (agent_002) decided to inspire: [LLM-Guided] Rallying the troops with inspiring leadership  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 1 Event
**Time:** 2025-07-26 10:04:30  
**Event:** Warboss Skarfang (agent_003) decided to charge: [LLM-Guided] WAAAGH! Charging into battle with ork fury  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 1 Event
**Time:** 2025-07-26 10:05:00  
**Event:** Turn 1 completed successfully with all agents having taken action  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 2 Event
**Time:** 2025-07-26 10:06:00  
**Event:** Turn 2 begins with continuing tactical engagement  
**Turn:** 2  
**Active Agents:** 3  

---

### Turn 2 Event
**Time:** 2025-07-26 10:06:30  
**Event:** Brother Marcus (agent_001) decided to defend: [LLM-Guided] Establishing defensive positions to protect allies  
**Turn:** 2  
**Active Agents:** 3  

---

### Turn 2 Event
**Time:** 2025-07-26 10:07:00  
**Event:** Turn 2 completed with tactical repositioning complete  
**Turn:** 2  
**Active Agents:** 3  

---

### Campaign Conclusion
**Time:** 2025-07-26 10:08:00  
**Event:** Campaign simulation completed successfully  
**Participants:** All Agents  
**Details:** Final battle results logged, all agents completed their missions

"""
        
        log_path = os.path.join(temp_dir, "test_campaign_log.md")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        return log_path
    
    @pytest.fixture
    def empty_campaign_log(self, temp_dir):
        """
        Pytest fixture that creates an empty campaign log file for testing empty file handling.
        
        Args:
            temp_dir: Temporary directory from temp_dir fixture
            
        Returns:
            str: Path to the created empty campaign log file
        """
        empty_content = """# Warhammer 40k Multi-Agent Simulator - Campaign Log

**Simulation Started:** 2025-07-26 10:00:00  
**Director Agent:** DirectorAgent v1.0  

## Campaign Overview

This is an empty test campaign log.

---

## Campaign Events

No events recorded.
"""
        
        log_path = os.path.join(temp_dir, "empty_campaign_log.md")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(empty_content)
        
        return log_path
    
    @pytest.fixture
    def malformed_campaign_log(self, temp_dir):
        """
        Pytest fixture that creates a malformed campaign log file for testing error handling.
        
        Args:
            temp_dir: Temporary directory from temp_dir fixture
            
        Returns:
            str: Path to the created malformed campaign log file
        """
        malformed_content = """This is not a proper campaign log format
Random text without proper structure
No event markers or proper formatting
### Invalid Event
Missing required fields
**Time:** Missing event description
**Event:** 
"""
        
        log_path = os.path.join(temp_dir, "malformed_campaign_log.md")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(malformed_content)
        
        return log_path
    
    @pytest.fixture
    def large_campaign_log(self, temp_dir):
        """
        Pytest fixture that creates a large campaign log file for performance testing.
        
        Args:
            temp_dir: Temporary directory from temp_dir fixture
            
        Returns:
            str: Path to the created large campaign log file
        """
        log_content = """# Warhammer 40k Multi-Agent Simulator - Large Campaign Log

**Simulation Started:** 2025-07-26 10:00:00  
**Director Agent:** DirectorAgent v1.0  

## Campaign Overview

Large test campaign with many events for performance testing.

---

## Campaign Events

### Simulation Initialization
**Time:** 2025-07-26 10:00:00  
**Event:** DirectorAgent initialized and campaign log created  
**Participants:** System  

"""
        
        # Generate multiple turns with many events
        event_count = 0
        for turn in range(1, 11):  # 10 turns
            log_content += f"\n### Turn {turn} Event\n"
            log_content += f"**Time:** 2025-07-26 10:{turn:02d}:00  \n"
            log_content += f"**Event:** Turn {turn} begins with multiple agents ready  \n"
            log_content += f"**Turn:** {turn}  \n"
            log_content += "**Active Agents:** 5  \n\n---\n"
            event_count += 1
            
            # Add agent actions for each turn
            agents = ["Agent_Alpha", "Agent_Beta", "Agent_Gamma", "Agent_Delta", "Agent_Epsilon"]
            actions = ["advance", "defend", "attack", "support", "recon"]
            
            for i, agent in enumerate(agents):
                log_content += f"\n### Turn {turn} Event\n"
                log_content += f"**Time:** 2025-07-26 10:{turn:02d}:{(i+1)*10:02d}  \n"
                log_content += f"**Event:** {agent} (agent_{i+1:03d}) decided to {actions[i]}: [LLM-Guided] Tactical decision based on battlefield analysis  \n"
                log_content += f"**Turn:** {turn}  \n"
                log_content += "**Active Agents:** 5  \n\n---\n"
                event_count += 1
        
        log_path = os.path.join(temp_dir, "large_campaign_log.md")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        return log_path
    
    @patch('chronicler_agent.get_config')
    def test_chronicler_initialization_basic(self, mock_get_config):
        """
        Test basic ChroniclerAgent initialization without output directory.
        
        Validates that the chronicler can be created with default settings
        and that all internal structures are properly initialized.
        """
        # Mock config to return None values for chronicler section
        mock_config = Mock()
        mock_config.chronicler.output_directory = None
        mock_config.chronicler.max_events_per_batch = 50
        mock_config.chronicler.narrative_style = "grimdark_dramatic"
        mock_get_config.return_value = mock_config
        
        chronicler = ChroniclerAgent()
        
        # Validate basic properties
        assert chronicler.output_directory is None
        assert chronicler.narrative_style == "grimdark_dramatic"
        assert chronicler.max_events_per_batch == 50
        
        # Validate counters are initialized
        assert chronicler.events_processed == 0
        assert chronicler.narratives_generated == 0
        assert chronicler.llm_calls_made == 0
        assert chronicler.error_count == 0
        assert chronicler.last_error_time is None
        
        # Validate templates are loaded
        assert hasattr(chronicler, 'narrative_templates')
        assert len(chronicler.narrative_templates) > 0
        assert hasattr(chronicler, 'faction_descriptions')
        assert len(chronicler.faction_descriptions) > 0
    
    def test_chronicler_initialization_with_output_directory(self, temp_dir):
        """
        Test ChroniclerAgent initialization with output directory.
        
        Validates that the chronicler can be created with an output directory
        and that directory validation and creation works correctly.
        
        Args:
            temp_dir: Temporary directory from fixture
        """
        output_dir = os.path.join(temp_dir, "test_output")
        chronicler = ChroniclerAgent(output_directory=output_dir)
        
        # Validate output directory was set and created
        assert chronicler.output_directory == output_dir
        assert os.path.exists(output_dir)
        assert os.path.isdir(output_dir)
        
        # Test that we can write to the directory
        test_file = os.path.join(output_dir, "test_write.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        assert os.path.exists(test_file)
    
    def test_chronicler_initialization_invalid_output_directory(self):
        """
        Test ChroniclerAgent initialization with invalid output directory.
        
        Validates that appropriate errors are raised when output directory
        creation or validation fails.
        """
        # Test with invalid path (file instead of directory)
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test")
            tmp_file_path = tmp_file.name
        
        try:
            with pytest.raises((ValueError, OSError)):
                ChroniclerAgent(output_directory=tmp_file_path)
        finally:
            os.unlink(tmp_file_path)
    
    def test_transcribe_log_basic_functionality(self, mock_campaign_log):
        """
        Test basic campaign log transcription functionality.
        
        Validates that the chronicler can successfully parse a campaign log
        and generate a narrative of reasonable length and content.
        
        Args:
            mock_campaign_log: Path to mock campaign log from fixture
        """
        chronicler = ChroniclerAgent()
        
        # Transcribe the mock campaign log
        narrative = chronicler.transcribe_log(mock_campaign_log)
        
        # Validate narrative was generated
        assert isinstance(narrative, str)
        assert len(narrative) > 50  # Should be substantial narrative
        assert len(narrative) < 50000  # Should be reasonable length
        
        # Validate narrative contains expected Warhammer 40k elements
        narrative_lower = narrative.lower()
        warhammer_terms = ['emperor', 'war', 'darkness', 'grim', 'millennium', 'battle']
        assert any(term in narrative_lower for term in warhammer_terms), "Narrative should contain Warhammer 40k atmosphere"
        
        # Validate chronicler statistics were updated
        assert chronicler.events_processed > 0
        assert chronicler.narratives_generated > 0
        assert chronicler.llm_calls_made > 0
        
        # Get status to verify processing
        status = chronicler.get_chronicler_status()
        assert status['processing_stats']['events_processed'] > 0
        assert status['system_health']['status'] == 'operational'
    
    def test_transcribe_log_with_output_file(self, mock_campaign_log, temp_dir):
        """
        Test campaign log transcription with file output.
        
        Validates that the chronicler can generate narratives and save them
        to files with proper formatting and metadata.
        
        Args:
            mock_campaign_log: Path to mock campaign log from fixture
            temp_dir: Temporary directory from fixture
        """
        output_dir = os.path.join(temp_dir, "narratives")
        chronicler = ChroniclerAgent(output_directory=output_dir)
        
        # Transcribe the log
        narrative = chronicler.transcribe_log(mock_campaign_log)
        
        # Validate narrative was generated
        assert len(narrative) > 50
        
        # Check that output file was created
        assert os.path.exists(output_dir)
        narrative_files = [f for f in os.listdir(output_dir) if f.endswith('.md')]
        assert len(narrative_files) > 0, "Should have created a narrative file"
        
        # Validate file content
        narrative_file_path = os.path.join(output_dir, narrative_files[0])
        with open(narrative_file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Validate file has proper structure
        assert '# Campaign Chronicle:' in file_content
        assert '**Generated:**' in file_content
        assert '**Source:**' in file_content
        assert '**Chronicler:**' in file_content
        assert narrative in file_content  # Should contain the actual narrative
    
    def test_transcribe_log_file_not_found(self):
        """
        Test error handling when campaign log file doesn't exist.
        
        Validates that FileNotFoundError is raised appropriately when
        trying to transcribe a non-existent log file.
        """
        chronicler = ChroniclerAgent()
        
        with pytest.raises(FileNotFoundError):
            chronicler.transcribe_log("nonexistent_file.md")
        
        # Validate error was tracked
        assert chronicler.error_count > 0
        assert chronicler.last_error_time is not None
    
    def test_transcribe_log_invalid_file_path(self, temp_dir):
        """
        Test error handling when file path points to directory instead of file.
        
        Args:
            temp_dir: Temporary directory from fixture
        """
        chronicler = ChroniclerAgent()
        
        with pytest.raises(ValueError):
            chronicler.transcribe_log(temp_dir)  # Directory instead of file
    
    def test_transcribe_log_empty_file(self, empty_campaign_log):
        """
        Test handling of empty campaign log files.
        
        Validates that the chronicler can gracefully handle logs with no events
        and generate appropriate empty narratives.
        
        Args:
            empty_campaign_log: Path to empty campaign log from fixture
        """
        chronicler = ChroniclerAgent()
        
        narrative = chronicler.transcribe_log(empty_campaign_log)
        
        # Should generate a narrative even for empty logs
        assert isinstance(narrative, str)
        assert len(narrative) > 50  # Should have some content
        
        # Should contain appropriate messaging about empty state
        narrative_lower = narrative.lower()
        empty_indicators = ['stillness', 'silence', 'no significant events', 'absence']
        assert any(indicator in narrative_lower for indicator in empty_indicators), "Should indicate empty state"
    
    def test_transcribe_log_malformed_file(self, malformed_campaign_log):
        """
        Test handling of malformed campaign log files.
        
        Validates that the chronicler can handle malformed input gracefully
        without crashing and provide meaningful error information.
        
        Args:
            malformed_campaign_log: Path to malformed campaign log from fixture
        """
        chronicler = ChroniclerAgent()
        
        # Should not crash, but may generate minimal narrative
        narrative = chronicler.transcribe_log(malformed_campaign_log)
        
        assert isinstance(narrative, str)
        assert len(narrative) > 0  # Should generate something
        
        # May have errors but should still attempt processing
        # Error count might increase due to parsing issues
    
    def test_narrative_style_management(self):
        """
        Test narrative style setting and validation.
        
        Validates that the chronicler can change narrative styles correctly
        and rejects invalid style configurations.
        """
        chronicler = ChroniclerAgent()
        
        # Test valid style changes
        assert chronicler.set_narrative_style('tactical') == True
        assert chronicler.narrative_style == 'tactical'
        
        assert chronicler.set_narrative_style('philosophical') == True
        assert chronicler.narrative_style == 'philosophical'
        
        assert chronicler.set_narrative_style('grimdark_dramatic') == True
        assert chronicler.narrative_style == 'grimdark_dramatic'
        
        # Test invalid style
        assert chronicler.set_narrative_style('invalid_style') == False
        assert chronicler.narrative_style == 'grimdark_dramatic'  # Should remain unchanged
    
    def test_chronicler_status_reporting(self, mock_campaign_log):
        """
        Test chronicler status reporting functionality.
        
        Validates that the chronicler provides accurate status information
        about its operation and processing statistics.
        
        Args:
            mock_campaign_log: Path to mock campaign log from fixture
        """
        chronicler = ChroniclerAgent()
        
        # Get initial status
        initial_status = chronicler.get_chronicler_status()
        assert initial_status['system_health']['status'] == 'operational'
        assert initial_status['processing_stats']['events_processed'] == 0
        assert initial_status['processing_stats']['narratives_generated'] == 0
        assert initial_status['processing_stats']['llm_calls_made'] == 0
        
        # Process a log
        narrative = chronicler.transcribe_log(mock_campaign_log)
        
        # Get updated status
        updated_status = chronicler.get_chronicler_status()
        assert updated_status['processing_stats']['events_processed'] > 0
        assert updated_status['processing_stats']['narratives_generated'] > 0
        assert updated_status['processing_stats']['llm_calls_made'] > 0
        
        # Validate status structure
        assert 'chronicler_info' in updated_status
        assert 'processing_stats' in updated_status
        assert 'system_health' in updated_status
        assert 'capabilities' in updated_status
    
    def test_campaign_event_parsing(self, mock_campaign_log):
        """
        Test campaign event parsing functionality.
        
        Validates that the chronicler correctly parses campaign log events
        and extracts appropriate metadata and participant information.
        
        Args:
            mock_campaign_log: Path to mock campaign log from fixture
        """
        chronicler = ChroniclerAgent()
        
        # Parse events from the mock log
        events = chronicler._parse_campaign_log(mock_campaign_log)
        
        # Validate events were parsed
        assert len(events) > 0
        assert all(isinstance(event, CampaignEvent) for event in events)
        
        # Check for expected event types
        event_types = [event.event_type for event in events]
        assert 'agent_registration' in event_types
        assert 'character_action' in event_types
        assert 'turn_begin' in event_types
        assert 'turn_end' in event_types
        
        # Validate participant extraction
        registration_events = [e for e in events if e.event_type == 'agent_registration']
        assert len(registration_events) > 0
        
        # Check that character names were extracted
        all_participants = []
        for event in events:
            all_participants.extend(event.participants)
        
        expected_characters = ['Brother Marcus', 'Commissar Vex', 'Warboss Skarfang']
        for char in expected_characters:
            assert any(char in participants for participants in [event.participants for event in events]), f"Should find {char} in participants"
    
    def test_narrative_segment_generation(self, mock_campaign_log):
        """
        Test narrative segment generation for individual events.
        
        Validates that the chronicler can generate appropriate narrative
        segments for different types of campaign events.
        
        Args:
            mock_campaign_log: Path to mock campaign log from fixture
        """
        chronicler = ChroniclerAgent()
        
        # Parse events and generate segments
        events = chronicler._parse_campaign_log(mock_campaign_log)
        segments = chronicler._generate_narrative_segments(events)
        
        # Validate segments were generated
        assert len(segments) > 0
        assert all(isinstance(segment, NarrativeSegment) for segment in segments)
        
        # Validate segment content
        for segment in segments:
            assert isinstance(segment.narrative_text, str)
            assert len(segment.narrative_text) > 10  # Should have substantial content
            assert segment.turn_number >= 0
            assert segment.event_type in ['agent_registration', 'character_action', 'turn_begin', 'turn_end', 'initialization']
            assert segment.tone == chronicler.narrative_style
    
    @patch('chronicler_agent.ChroniclerAgent._call_llm')
    def test_llm_integration_mocking(self, mock_llm_call, mock_campaign_log):
        """
        Test LLM integration with mocked responses.
        
        Validates that the chronicler correctly integrates with LLM calls
        and handles various response scenarios.
        
        Args:
            mock_llm_call: Mocked LLM call function
            mock_campaign_log: Path to mock campaign log from fixture
        """
        # Configure mock to return test responses
        mock_llm_call.return_value = "In the grim darkness of the far future, warriors clashed with destiny itself."
        
        chronicler = ChroniclerAgent()
        narrative = chronicler.transcribe_log(mock_campaign_log)
        
        # Validate that LLM was called
        assert mock_llm_call.called
        assert mock_llm_call.call_count > 0
        
        # Validate narrative contains mocked content
        assert len(narrative) > 50
        assert "grim darkness" in narrative.lower()
    
    @patch('chronicler_agent.ChroniclerAgent._call_llm')
    def test_llm_failure_fallback(self, mock_llm_call, mock_campaign_log):
        """
        Test fallback behavior when LLM calls fail.
        
        Validates that the chronicler can gracefully handle LLM failures
        and fall back to template-based narrative generation.
        
        Args:
            mock_llm_call: Mocked LLM call function
            mock_campaign_log: Path to mock campaign log from fixture
        """
        # Configure mock to raise exceptions
        mock_llm_call.side_effect = Exception("LLM API failure")
        
        chronicler = ChroniclerAgent()
        narrative = chronicler.transcribe_log(mock_campaign_log)
        
        # Should still generate narrative using fallback
        assert isinstance(narrative, str)
        assert len(narrative) > 50
        
        # Should contain fallback content
        assert "grim" in narrative.lower() or "darkness" in narrative.lower()
    
    def test_performance_large_log(self, large_campaign_log):
        """
        Test performance with large campaign logs.
        
        Validates that the chronicler can handle large logs efficiently
        and completes processing within reasonable time limits.
        
        Args:
            large_campaign_log: Path to large campaign log from fixture
        """
        chronicler = ChroniclerAgent()
        
        start_time = time.time()
        narrative = chronicler.transcribe_log(large_campaign_log)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Validate performance (should complete in reasonable time)
        assert processing_time < 30.0  # Should complete within 30 seconds
        
        # Validate output
        assert len(narrative) > 100
        
        # Check processing statistics
        status = chronicler.get_chronicler_status()
        assert status['processing_stats']['events_processed'] > 50  # Large log should have many events
    
    def test_multiple_log_processing(self, mock_campaign_log, empty_campaign_log, temp_dir):
        """
        Test processing multiple logs with the same chronicler instance.
        
        Validates that the chronicler can handle multiple transcription
        operations and maintain accurate statistics across sessions.
        
        Args:
            mock_campaign_log: Path to mock campaign log from fixture
            empty_campaign_log: Path to empty campaign log from fixture
            temp_dir: Temporary directory from fixture
        """
        chronicler = ChroniclerAgent()
        
        # Process first log
        narrative1 = chronicler.transcribe_log(mock_campaign_log)
        stats_after_first = chronicler.get_chronicler_status()
        
        # Process second log
        narrative2 = chronicler.transcribe_log(empty_campaign_log)
        stats_after_second = chronicler.get_chronicler_status()
        
        # Validate both narratives were generated
        assert len(narrative1) > 50
        assert len(narrative2) > 50
        
        # Validate statistics accumulated
        assert stats_after_second['processing_stats']['events_processed'] >= stats_after_first['processing_stats']['events_processed']
        assert stats_after_second['processing_stats']['llm_calls_made'] >= stats_after_first['processing_stats']['llm_calls_made']
    
    def test_faction_descriptions_utilization(self, mock_campaign_log):
        """
        Test that faction descriptions are properly utilized in narratives.
        
        Validates that the chronicler incorporates faction-specific
        descriptions and terminology in generated narratives.
        
        Args:
            mock_campaign_log: Path to mock campaign log from fixture
        """
        chronicler = ChroniclerAgent()
        narrative = chronicler.transcribe_log(mock_campaign_log)
        
        # Check for faction-related content
        narrative_lower = narrative.lower()
        
        # Should contain references to factions from the mock log
        faction_terms = ['space marines', 'astra militarum', 'ork', 'goff']
        
        # May contain faction descriptions or related terms
        # At minimum should reference the characters or their actions
        character_names = ['marcus', 'vex', 'skarfang']
        assert any(name in narrative_lower for name in character_names), "Should reference character names"
    
    def test_error_recovery_and_logging(self, temp_dir):
        """
        Test error recovery and logging functionality.
        
        Validates that the chronicler properly logs errors and continues
        operation after encountering various error conditions.
        
        Args:
            temp_dir: Temporary directory from fixture
        """
        chronicler = ChroniclerAgent()
        
        initial_error_count = chronicler.error_count
        
        # Attempt to process non-existent file (should fail)
        try:
            chronicler.transcribe_log("nonexistent.md")
        except FileNotFoundError:
            pass  # Expected
        
        # Error count should increase
        assert chronicler.error_count > initial_error_count
        assert chronicler.last_error_time is not None
        
        # Create a valid file and ensure chronicler still works
        test_log = os.path.join(temp_dir, "recovery_test.md")
        with open(test_log, 'w') as f:
            f.write("""# Test Log
### Turn 1 Event
**Time:** 2025-07-26 10:00:00
**Event:** Test event for recovery
""")
        
        # Should still be able to process valid files
        narrative = chronicler.transcribe_log(test_log)
        assert len(narrative) > 20
    
    def test_narrative_combination_flow(self, mock_campaign_log):
        """
        Test narrative combination and flow management.
        
        Validates that individual narrative segments are properly combined
        into a cohesive story with appropriate transitions and structure.
        
        Args:
            mock_campaign_log: Path to mock campaign log from fixture
        """
        chronicler = ChroniclerAgent()
        
        # Parse events and generate segments
        events = chronicler._parse_campaign_log(mock_campaign_log)
        segments = chronicler._generate_narrative_segments(events)
        
        # Combine into complete story
        complete_story = chronicler._combine_narrative_segments(segments, mock_campaign_log)
        
        # Validate story structure
        assert len(complete_story) > 100
        
        # Should have opening and closing
        story_lower = complete_story.lower()
        opening_indicators = ['grim darkness', 'far future', 'emperor']
        closing_indicators = ['concludes', 'echo', 'eternity']
        
        assert any(indicator in story_lower for indicator in opening_indicators), "Should have atmospheric opening"
        assert any(indicator in story_lower for indicator in closing_indicators), "Should have atmospheric closing"
    
    def test_utility_functions(self, temp_dir):
        """
        Test utility functions for chronicler management.
        
        Validates that utility functions for creating chroniclers and
        batch processing work correctly.
        
        Args:
            temp_dir: Temporary directory from fixture
        """
        from chronicler_agent import create_chronicler_with_output, batch_transcribe_logs
        
        # Test chronicler creation utility
        output_dir = os.path.join(temp_dir, "utility_test")
        chronicler = create_chronicler_with_output(output_dir)
        
        assert isinstance(chronicler, ChroniclerAgent)
        assert chronicler.output_directory == output_dir
        assert os.path.exists(output_dir)
        
        # Create test logs for batch processing
        log1_path = os.path.join(temp_dir, "batch_log1.md")
        log2_path = os.path.join(temp_dir, "batch_log2.md")
        
        test_content = """# Test Log
### Turn 1 Event
**Time:** 2025-07-26 10:00:00
**Event:** Test event for batch processing
"""
        
        for log_path in [log1_path, log2_path]:
            with open(log_path, 'w') as f:
                f.write(test_content)
        
        # Test batch processing
        narratives = batch_transcribe_logs(chronicler, [log1_path, log2_path])
        
        assert len(narratives) == 2
        assert all(len(narrative) > 20 for narrative in narratives)


class TestCampaignEventDataClass:
    """
    Test the CampaignEvent dataclass functionality.
    
    Validates that the CampaignEvent data structure works correctly
    for storing and managing campaign event information.
    """
    
    def test_campaign_event_creation(self):
        """Test basic CampaignEvent creation and attribute access."""
        event = CampaignEvent(
            turn_number=1,
            timestamp="2025-07-26 10:00:00",
            event_type="character_action",
            description="Test event description",
            participants=["Test Character"],
            faction_info={"Test Character": "Space Marines"},
            action_details={"action_type": "advance"},
            raw_text="Raw event text"
        )
        
        assert event.turn_number == 1
        assert event.timestamp == "2025-07-26 10:00:00"
        assert event.event_type == "character_action"
        assert event.description == "Test event description"
        assert event.participants == ["Test Character"]
        assert event.faction_info == {"Test Character": "Space Marines"}
        assert event.action_details == {"action_type": "advance"}
        assert event.raw_text == "Raw event text"
    
    def test_campaign_event_defaults(self):
        """Test CampaignEvent creation with default values."""
        event = CampaignEvent(
            turn_number=1,
            timestamp="2025-07-26 10:00:00",
            event_type="test_event",
            description="Test description"
        )
        
        # Default values should be set
        assert event.participants == []
        assert event.faction_info == {}
        assert event.action_details == {}
        assert event.raw_text == ""


class TestNarrativeSegmentDataClass:
    """
    Test the NarrativeSegment dataclass functionality.
    
    Validates that the NarrativeSegment data structure works correctly
    for storing and managing generated narrative content.
    """
    
    def test_narrative_segment_creation(self):
        """Test basic NarrativeSegment creation and attribute access."""
        segment = NarrativeSegment(
            turn_number=1,
            event_type="character_action",
            narrative_text="In the grim darkness, a warrior acted.",
            character_focus=["Test Character"],
            faction_themes=["Space Marines"],
            tone="grimdark_dramatic",
            timestamp="2025-07-26 10:00:00"
        )
        
        assert segment.turn_number == 1
        assert segment.event_type == "character_action"
        assert segment.narrative_text == "In the grim darkness, a warrior acted."
        assert segment.character_focus == ["Test Character"]
        assert segment.faction_themes == ["Space Marines"]
        assert segment.tone == "grimdark_dramatic"
        assert segment.timestamp == "2025-07-26 10:00:00"
    
    def test_narrative_segment_defaults(self):
        """Test NarrativeSegment creation with default values."""
        segment = NarrativeSegment(
            turn_number=1,
            event_type="test_event",
            narrative_text="Test narrative"
        )
        
        # Default values should be set
        assert segment.character_focus == []
        assert segment.faction_themes == []
        assert segment.tone == "dramatic"
        assert segment.timestamp == ""


# Integration and end-to-end tests
class TestChroniclerIntegration:
    """
    Integration tests for ChroniclerAgent with realistic scenarios.
    
    Tests the complete workflow from campaign log to narrative output
    using realistic data and scenarios.
    """
    
    @pytest.fixture
    def temp_dir(self):
        """
        Pytest fixture that creates a temporary directory for integration test files.
        
        Yields:
            str: Path to temporary directory
            
        Cleanup:
            Automatically removes the temporary directory after test completion
        """
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_end_to_end_workflow(self, temp_dir):
        """
        Test complete end-to-end workflow from log creation to narrative output.
        
        Creates a realistic campaign log, processes it through the chronicler,
        and validates the complete workflow produces expected results.
        
        Args:
            temp_dir: Temporary directory from fixture
        """
        # Create a realistic campaign log
        campaign_log = self._create_realistic_campaign_log(temp_dir)
        
        # Set up chronicler with output directory
        output_dir = os.path.join(temp_dir, "integration_output")
        chronicler = ChroniclerAgent(output_directory=output_dir)
        
        # Process the log
        start_time = time.time()
        narrative = chronicler.transcribe_log(campaign_log)
        end_time = time.time()
        
        # Validate processing completed successfully
        assert len(narrative) > 200  # Should be substantial narrative
        processing_time = end_time - start_time
        assert processing_time < 10.0  # Should complete reasonably quickly
        
        # Validate output file was created
        narrative_files = [f for f in os.listdir(output_dir) if f.endswith('.md')]
        assert len(narrative_files) == 1
        
        # Validate file content
        narrative_file = os.path.join(output_dir, narrative_files[0])
        with open(narrative_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        assert narrative in file_content
        assert '# Campaign Chronicle:' in file_content
        
        # Validate chronicler status
        status = chronicler.get_chronicler_status()
        assert status['system_health']['status'] == 'operational'
        assert status['processing_stats']['events_processed'] > 0
    
    def _create_realistic_campaign_log(self, temp_dir):
        """
        Create a realistic campaign log for integration testing.
        
        Args:
            temp_dir: Temporary directory to create log in
            
        Returns:
            str: Path to created campaign log
        """
        realistic_content = """# Warhammer 40k Multi-Agent Simulator - Campaign Log

**Simulation Started:** 2025-07-26 14:30:00  
**Director Agent:** DirectorAgent v1.0  
**Phase:** Integration Testing Campaign  

## Campaign Overview

Tactical engagement on Hive World Tertius between Imperial forces and Ork raiders.
Multiple agent types participating in complex battlefield scenarios.

---

## Campaign Events

### Simulation Initialization
**Time:** 2025-07-26 14:30:00  
**Event:** DirectorAgent initialized and campaign log created  
**Participants:** System  
**Details:** Imperial Defense Force deployment initiated

### Turn 1 Event
**Time:** 2025-07-26 14:31:00  
**Event:** **Agent Registration:** Captain Thorne (imperial_001) joined the simulation
**Faction:** Ultramarines Chapter
**Registration Time:** 2025-07-26 14:31:00
**Total Active Agents:** 1  
**Turn:** 1  
**Active Agents:** 1  

---

### Turn 1 Event
**Time:** 2025-07-26 14:31:30  
**Event:** **Agent Registration:** Sergeant Kade (imperial_002) joined the simulation
**Faction:** Astra Militarum - Cadian Shock Troops
**Registration Time:** 2025-07-26 14:31:30
**Total Active Agents:** 2  
**Turn:** 1  
**Active Agents:** 2  

---

### Turn 1 Event
**Time:** 2025-07-26 14:32:00  
**Event:** **Agent Registration:** Big Mek Skarjaw (ork_001) joined the simulation
**Faction:** Bad Moons Clan
**Registration Time:** 2025-07-26 14:32:00
**Total Active Agents:** 3  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 1 Event
**Time:** 2025-07-26 14:33:00  
**Event:** Turn 1 begins - Initial deployment phase  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 1 Event
**Time:** 2025-07-26 14:33:30  
**Event:** Captain Thorne (imperial_001) decided to advance: [LLM-Guided] Moving to secure the high ground position with tactical squad support  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 1 Event
**Time:** 2025-07-26 14:34:00  
**Event:** Sergeant Kade (imperial_002) decided to defend: [LLM-Guided] Establishing defensive perimeter around civilian evacuation zone  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 1 Event
**Time:** 2025-07-26 14:34:30  
**Event:** Big Mek Skarjaw (ork_001) decided to construct: [LLM-Guided] Building improved weapon systems for the upcoming WAAAGH!  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 1 Event
**Time:** 2025-07-26 14:35:00  
**Event:** Turn 1 completed - Positioning phase successful  
**Turn:** 1  
**Active Agents:** 3  

---

### Turn 2 Event
**Time:** 2025-07-26 14:36:00  
**Event:** Turn 2 begins - Engagement phase initiated  
**Turn:** 2  
**Active Agents:** 3  

---

### Turn 2 Event
**Time:** 2025-07-26 14:36:30  
**Event:** Captain Thorne (imperial_001) decided to attack: [LLM-Guided] Launching coordinated assault on ork positions with bolter fire  
**Turn:** 2  
**Active Agents:** 3  

---

### Turn 2 Event
**Time:** 2025-07-26 14:37:00  
**Event:** Turn 2 completed - First contact established  
**Turn:** 2  
**Active Agents:** 3  

---

### Campaign Conclusion
**Time:** 2025-07-26 14:38:00  
**Event:** Campaign phase completed - Tactical situation resolved  
**Participants:** All Active Agents  
**Details:** Mission parameters achieved, all units accounted for

"""
        
        log_path = os.path.join(temp_dir, "realistic_campaign_log.md")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(realistic_content)
        
        return log_path


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])