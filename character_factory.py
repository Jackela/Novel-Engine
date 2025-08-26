#!/usr/bin/env python3
"""
Character Factory Module
=======================

This module provides the CharacterFactory class for creating PersonaAgent instances
from character names. It handles the character directory resolution and validation
required to initialize PersonaAgent objects.

The factory abstracts the character loading process and provides a simple interface
for creating character agents by name, following the project's character storage
structure in the 'characters/' directory.

Usage:
    factory = CharacterFactory()
    krieg_agent = factory.create_character('krieg')
    ork_agent = factory.create_character('ork')
"""

import os
import logging
from typing import Optional
from src.persona_agent import PersonaAgent
from src.event_bus import EventBus

# Configure logging
logger = logging.getLogger(__name__)


class CharacterFactory:
    """
    Factory class for creating PersonaAgent instances from character names.
    
    This factory provides a simple interface for creating character agents by name,
    automatically resolving the character directory path and handling validation.
    Characters are expected to be stored in the 'characters/{character_name}/' 
    directory structure.
    
    The factory validates that character directories exist before attempting to
    create PersonaAgent instances, providing clear error messages for missing
    character data.
    """
    
    def __init__(self, event_bus: EventBus, base_character_path: str = "characters"):
        """
        Initialize the CharacterFactory.
        
        Args:
            event_bus: An instance of the EventBus for decoupled communication.
            base_character_path: Base path where character directories are stored.
                                Defaults to 'characters' for standard project layout.
        """
        self.event_bus = event_bus
        if not os.path.isabs(base_character_path):
            current_dir = os.path.abspath(os.getcwd())
            project_root = self._find_project_root(current_dir)
            self.base_character_path = os.path.join(project_root, base_character_path)
        else:
            self.base_character_path = base_character_path
        
        logger.info(f"CharacterFactory initialized with base path: {self.base_character_path}")
    
    def _find_project_root(self, start_path: str) -> str:
        """
        Find the project root directory by looking for marker files.
        
        Args:
            start_path: Directory to start searching from
            
        Returns:
            str: Path to the project root directory
            
        Raises:
            FileNotFoundError: If project root cannot be determined
        """
        # 寻找常见项目标记文件，识别神圣领域的在界证据...
        markers = ['persona_agent.py', 'director_agent.py', 'configs/', '.git']
        
        current_path = os.path.abspath(start_path)
        while current_path != os.path.dirname(current_path):  # Not at filesystem root
            for marker in markers:
                if os.path.exists(os.path.join(current_path, marker)):
                    logger.debug(f"Found project root at {current_path} (marker: {marker})")
                    return current_path
            current_path = os.path.dirname(current_path)
        
        # 后备方案：假设当前工作目录为项目根目录，执行紧急定位仪式...
        fallback_root = os.path.abspath(os.getcwd())
        logger.warning(f"Could not determine project root, using fallback: {fallback_root}")
        return fallback_root
    
    def create_character(self, character_name: str, agent_id: Optional[str] = None) -> PersonaAgent:
        """
        Create a PersonaAgent instance for the specified character.
        
        This method constructs the path to the character directory, validates that
        it exists, and initializes a PersonaAgent instance with the directory path.
        
        Args:
            character_name: Name of the character directory (e.g., 'krieg', 'ork')
            agent_id: Optional unique identifier for the agent. If not provided,
                     the PersonaAgent will derive it from the directory path.
        
        Returns:
            PersonaAgent: Fully initialized PersonaAgent instance for the character
            
        Raises:
            FileNotFoundError: If the character directory does not exist
            ValueError: If character_name is empty or invalid
            
        Example:
            factory = CharacterFactory(event_bus)
            krieg = factory.create_character('krieg')
            ork = factory.create_character('ork', agent_id='ork_warboss_1')
        """
        if not character_name or not character_name.strip():
            raise ValueError("Character name cannot be empty or None")
        
        character_directory = os.path.join(self.base_character_path, character_name.strip())
        
        if not os.path.exists(character_directory):
            raise FileNotFoundError(
                f"Character directory not found: {character_directory}. "
                f"Expected character data in 'characters/{character_name}/' directory."
            )
        
        if not os.path.isdir(character_directory):
            raise FileNotFoundError(
                f"Character path exists but is not a directory: {character_directory}"
            )
        
        logger.info(f"Creating PersonaAgent for character '{character_name}' from {character_directory}")
        
        try:
            persona_agent = PersonaAgent(character_directory, self.event_bus, agent_id=agent_id)
            logger.info(f"Successfully created PersonaAgent for '{character_name}' with ID: {persona_agent.agent_id}")
            return persona_agent
        except Exception as e:
            logger.error(f"Failed to create PersonaAgent for '{character_name}': {e}")
            raise
    
    def list_available_characters(self) -> list[str]:
        """
        List all available character names in the character directory.
        
        Returns:
            list[str]: List of character names (directory names) available for creation
            
        Raises:
            FileNotFoundError: If the base character directory doesn't exist
        """
        if not os.path.exists(self.base_character_path):
            raise FileNotFoundError(f"Character base directory not found: {self.base_character_path}")
        
        characters = []
        for item in os.listdir(self.base_character_path):
            item_path = os.path.join(self.base_character_path, item)
            if os.path.isdir(item_path):
                characters.append(item)
        
        logger.info(f"Found {len(characters)} available characters: {characters}")
        return sorted(characters)