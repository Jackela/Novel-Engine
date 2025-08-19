#!/usr/bin/env python3
"""
Configuration Integration Test
=============================

Test script to verify that all components properly use the centralized
configuration system.
"""

import os
import tempfile
from config_loader import ConfigLoader, get_config, get_simulation_turns, get_default_character_sheets
from director_agent import DirectorAgent
from chronicler_agent import ChroniclerAgent

def test_config_loading():
    """Test basic configuration loading functionality."""
    print("Testing configuration loading...")
    
    # Test singleton pattern
    loader1 = ConfigLoader.get_instance()
    loader2 = ConfigLoader.get_instance()
    assert loader1 is loader2, "ConfigLoader should be a singleton"
    print("✓ Singleton pattern working")
    
    # Test configuration loading
    config = get_config()
    assert config is not None, "Configuration should load successfully"
    print("✓ Configuration loaded")
    
    # Test configuration values
    turns = get_simulation_turns()
    assert turns == 3, f"Expected 3 turns, got {turns}"
    print(f"✓ Simulation turns: {turns}")
    
    character_sheets = get_default_character_sheets()
    expected_sheets = ['characters/krieg', 'characters/ork']
    assert character_sheets == expected_sheets, f"Expected {expected_sheets}, got {character_sheets}"
    print(f"✓ Character sheets: {character_sheets}")
    
    print("Configuration loading tests passed!\n")

def test_director_agent_config():
    """Test DirectorAgent configuration integration."""
    print("Testing DirectorAgent configuration integration...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test campaign log in temp directory
        test_log_path = os.path.join(temp_dir, "test_campaign.md")
        
        # Create DirectorAgent with configuration
        director = DirectorAgent(campaign_log_path=test_log_path)
        
        # Verify configuration values are used
        assert director.campaign_log_path == test_log_path, "Campaign log path should be set"
        assert director.max_turn_history == 100, "Max turn history should be from config"
        assert director.error_threshold == 10, "Error threshold should be from config"
        
        print("✓ DirectorAgent uses configuration values")
        print(f"  - Campaign log: {director.campaign_log_path}")
        print(f"  - Max turn history: {director.max_turn_history}")
        print(f"  - Error threshold: {director.error_threshold}")
    
    print("DirectorAgent configuration tests passed!\n")

def test_chronicler_agent_config():
    """Test ChroniclerAgent configuration integration."""
    print("Testing ChroniclerAgent configuration integration...")
    
    # Create ChroniclerAgent with configuration
    chronicler = ChroniclerAgent()
    
    # Verify configuration values are used
    assert chronicler.output_directory == "demo_narratives", "Output directory should be from config"
    assert chronicler.max_events_per_batch == 50, "Max events per batch should be from config"
    assert chronicler.narrative_style == "grimdark_dramatic", "Narrative style should be from config"
    
    print("✓ ChroniclerAgent uses configuration values")
    print(f"  - Output directory: {chronicler.output_directory}")
    print(f"  - Max events per batch: {chronicler.max_events_per_batch}")
    print(f"  - Narrative style: {chronicler.narrative_style}")
    
    print("ChroniclerAgent configuration tests passed!\n")

def test_config_fallbacks():
    """Test configuration fallback behavior when config file is missing."""
    print("Testing configuration fallback behavior...")
    
    # Create a new ConfigLoader instance with non-existent config file
    loader = ConfigLoader()
    loader.config_file_path = "non_existent_config.yaml"
    
    # Should fall back to defaults without crashing
    config = loader.load_config(force_reload=True)
    assert config is not None, "Should create default configuration"
    assert config.simulation.turns == 3, "Should use default turns value"
    
    print("✓ Fallback to defaults when config file missing")
    print("Configuration fallback tests passed!\n")

def test_environment_overrides():
    """Test environment variable overrides."""
    print("Testing environment variable overrides...")
    
    # Set environment variable
    os.environ['W40K_SIMULATION_TURNS'] = '5'
    
    try:
        # Create a new ConfigLoader instance to pick up environment variable
        loader = ConfigLoader()
        loader.config_file_path = "config.yaml"
        loader._config = None  # Clear cached config
        
        config = loader.load_config(force_reload=True)
        
        # Check if environment override was applied
        assert config.simulation.turns == 5, f"Expected 5 turns from env var, got {config.simulation.turns}"
        print("✓ Environment variable override working")
        print(f"  - Turns override: {config.simulation.turns}")
        
    finally:
        # Clean up environment variable
        if 'W40K_SIMULATION_TURNS' in os.environ:
            del os.environ['W40K_SIMULATION_TURNS']
    
    print("Environment override tests passed!\n")

def main():
    """Run all configuration integration tests."""
    print("Configuration Integration Test Suite")
    print("=" * 50)
    
    try:
        test_config_loading()
        test_director_agent_config()
        test_chronicler_agent_config()
        test_config_fallbacks()
        test_environment_overrides()
        
        print("=" * 50)
        print("🎯 ALL CONFIGURATION TESTS PASSED!")
        print("The centralized configuration system is working correctly.")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)