#!/usr/bin/env python3
"""
Character Sheet Parser Module
=============================

Handles parsing and validation of character sheet data for PersonaAgent.
Separated from the main PersonaAgent to follow Single Responsibility Principle.
"""

import re
import logging
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class CharacterSheetParser:
    """
    Handles parsing of character sheet files and extracting structured data.
    
    This class encapsulates all character sheet parsing logic that was previously
    part of the PersonaAgent class, improving maintainability and testability.
    """
    
    def __init__(self, character_directory_path: str):
        """
        Initialize the character sheet parser.
        
        Args:
            character_directory_path: Path to character directory
        """
        self.character_directory_path = Path(character_directory_path)
        self._file_cache: Dict[str, str] = {}
        self._yaml_cache: Dict[str, Dict[str, Any]] = {}
    
    def parse_character_sheet(self, sheet_path: str) -> Dict[str, Any]:
        """
        Parse character sheet and return structured data.
        
        Args:
            sheet_path: Path to character sheet file
            
        Returns:
            Dictionary containing parsed character data
        """
        content = self._read_cached_file(sheet_path)
        if not content:
            logger.warning(f"No character sheet content found at {sheet_path}")
            return {}
        
        return self._parse_character_sheet_content(content)
    
    def parse_character_context(self, context_path: str) -> str:
        """
        Parse character context file.
        
        Args:
            context_path: Path to character context file
            
        Returns:
            Character context string
        """
        return self._read_cached_file(context_path)
    
    def parse_yaml_file(self, yaml_path: str) -> Dict[str, Any]:
        """
        Parse YAML configuration file.
        
        Args:
            yaml_path: Path to YAML file
            
        Returns:
            Parsed YAML data
        """
        return self._parse_cached_yaml(yaml_path)
    
    def _read_cached_file(self, file_path: str) -> str:
        """Read file with caching for performance."""
        if file_path in self._file_cache:
            return self._file_cache[file_path]
        
        try:
            full_path = self.character_directory_path / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self._file_cache[file_path] = content
            return content
        except (FileNotFoundError, IOError) as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return ""
    
    def _parse_cached_yaml(self, file_path: str) -> Dict[str, Any]:
        """Parse YAML file with caching for performance."""
        if file_path in self._yaml_cache:
            return self._yaml_cache[file_path]
        
        try:
            content = self._read_cached_file(file_path)
            if content:
                data = yaml.safe_load(content)
                self._yaml_cache[file_path] = data or {}
                return self._yaml_cache[file_path]
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
        
        return {}
    
    def _parse_character_sheet_content(self, content: str) -> Dict[str, Any]:
        """Parse character sheet content into structured data."""
        character_data = {}
        
        # Parse different sections
        sections = {
            'identity': self._parse_identity_section,
            'psychological': self._parse_psychological_section,
            'behavioral': self._parse_behavioral_section,
            'knowledge': self._parse_knowledge_section,
            'social': self._parse_social_section,
            'capabilities': self._parse_capabilities_section
        }
        
        for section_name, parser_func in sections.items():
            section_content = self._extract_section(content, section_name)
            if section_content:
                character_data[section_name] = parser_func(section_content)
        
        return character_data
    
    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract a specific section from character sheet content."""
        pattern = rf"#{section_name.upper()}.*?\n(.*?)(?=\n#|\Z)"
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None
    
    def _parse_identity_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the identity section of character sheet."""
        identity_data = {}
        
        # Extract basic identity fields
        fields = ['name', 'rank_role', 'faction', 'homeworld', 'age']
        for field in fields:
            pattern = rf"{field}:\s*(.+)"
            match = re.search(pattern, section_content, re.IGNORECASE)
            if match:
                identity_data[field] = match.group(1).strip()
        
        return identity_data
    
    def _parse_psychological_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the psychological section of character sheet."""
        return {
            'traits': self._extract_bullet_points(section_content),
            'motivations': self._extract_weighted_items(section_content)
        }
    
    def _parse_behavioral_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the behavioral section of character sheet."""
        return {
            'behaviors': self._extract_bullet_points(section_content),
            'decision_factors': self._extract_weighted_items(section_content)
        }
    
    def _parse_knowledge_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the knowledge section of character sheet."""
        return self._parse_simple_field_format(section_content)
    
    def _parse_social_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the social section of character sheet."""
        return self._parse_simple_field_format(section_content)
    
    def _parse_capabilities_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the capabilities section of character sheet."""
        return self._parse_simple_field_format(section_content)
    
    def _extract_bullet_points(self, content: str) -> Dict[str, str]:
        """Extract bullet points from content."""
        bullet_points = {}
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                # Remove bullet point marker
                text = line[1:].strip()
                if ':' in text:
                    key, value = text.split(':', 1)
                    bullet_points[key.strip().lower().replace(' ', '_')] = value.strip()
                else:
                    # Use the text as both key and value
                    key = text.lower().replace(' ', '_')
                    bullet_points[key] = text
        
        return bullet_points
    
    def _extract_weighted_items(self, content: str) -> Dict[str, float]:
        """Extract weighted items from content."""
        weighted_items = {}
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for patterns like "Item (weight)" or "Item: weight"
            weight_match = re.search(r'(.+?)\s*[\(:]\s*([0-9.]+)\s*[\)]?', line)
            if weight_match:
                item = weight_match.group(1).strip()
                weight = float(weight_match.group(2))
                key = item.lower().replace(' ', '_')
                weighted_items[key] = weight
        
        return weighted_items
    
    def _parse_simple_field_format(self, content: str) -> Dict[str, Any]:
        """Parse simple field: value format."""
        parsed_data = {}
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                parsed_data[key] = value
        
        return parsed_data