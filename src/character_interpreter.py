#!/usr/bin/env python3
"""
Character Interpreter
=====================

Handles character data loading, parsing, and interpretation including:
- Character context loading from files
- Character sheet parsing and trait extraction
- Personality and relationship interpretation
- Character data processing and validation

This component manages the transformation of character files into runtime
agent behavior and characteristics.
"""

import os
import yaml
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)


class CharacterInterpreter:
    """
    Interprets and processes character data from various file sources.
    
    Responsibilities:
    - Loading character files (Markdown, YAML) from directories
    - Parsing character sheets and extracting traits
    - Interpreting personality characteristics and behavioral patterns
    - Processing relationship data and social connections
    - Validating character data integrity
    """
    
    def __init__(self, character_directory_path: str):
        """
        Initialize the CharacterInterpreter.
        
        Args:
            character_directory_path: Path to directory containing character files
        """
        self.character_directory_path = character_directory_path
        self.character_data: Dict[str, Any] = {}
        self.file_cache: Dict[str, str] = {}
        self.yaml_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"CharacterInterpreter initialized for: {character_directory_path}")
    
    def load_character_context(self) -> Dict[str, Any]:
        """
        Load and parse all character files from the directory into a unified context.
        
        This method intelligently reads multiple file types:
        - .md files: Concatenated into markdown_content string
        - .yaml/.yml files: Parsed into yaml_data dictionary
        
        Returns:
            Dictionary containing hybrid character context with both structured 
            YAML data and rich markdown narratives
            
        Raises:
            FileNotFoundError: If the character directory doesn't exist
            ValueError: If no compatible files found or parsing fails
        """
        try:
            logger.info(f"Loading character context from directory: {self.character_directory_path}")
            
            # Validate directory exists
            if not os.path.exists(self.character_directory_path):
                raise FileNotFoundError(f"Character directory not found: {self.character_directory_path}")
            
            if not os.path.isdir(self.character_directory_path):
                raise ValueError(f"Path is not a directory: {self.character_directory_path}")
            
            # Discover supported files in the directory
            md_files, yaml_files = self._discover_character_files()
            
            if not md_files and not yaml_files:
                raise ValueError(f"No .md or .yaml files found in directory: {self.character_directory_path}")
            
            # Initialize hybrid context object
            hybrid_context = {
                'markdown_content': '',
                'yaml_data': {},
                'file_count': {'md': len(md_files), 'yaml': len(yaml_files)},
                'load_timestamp': datetime.now().isoformat()
            }
            
            # Process Markdown files
            if md_files:
                hybrid_context['markdown_content'] = self._process_markdown_files(md_files)
            
            # Process YAML files
            if yaml_files:
                hybrid_context['yaml_data'] = self._process_yaml_files(yaml_files)
            
            # Parse character data from markdown content for backward compatibility
            if hybrid_context['markdown_content']:
                self.character_data = self._parse_character_sheet_content(hybrid_context['markdown_content'])
            else:
                self.character_data = {}
            
            # Store hybrid context data
            self.character_data['hybrid_context'] = hybrid_context
            
            # Merge YAML data into character_data for easier access
            self._merge_yaml_data_into_character_data(hybrid_context['yaml_data'])
            
            # Extract and interpret character characteristics
            self._extract_character_characteristics()
            
            total_files = len(md_files) + len(yaml_files)
            character_name = self.character_data.get('name', 'Unknown')
            logger.info(f"Character context loaded for {character_name} from {total_files} files")
            
            return self.character_data
            
        except Exception as e:
            logger.error(f"Failed to load character context: {str(e)}")
            raise
    
    def _discover_character_files(self) -> Tuple[List[str], List[str]]:
        """
        Discover all supported character files in the directory.
        
        Returns:
            Tuple of (markdown_files, yaml_files) lists with full paths
        """
        md_files = []
        yaml_files = []
        
        try:
            for filename in os.listdir(self.character_directory_path):
                file_lower = filename.lower()
                full_path = os.path.join(self.character_directory_path, filename)
                
                if file_lower.endswith('.md'):
                    md_files.append(full_path)
                elif file_lower.endswith(('.yaml', '.yml')):
                    yaml_files.append(full_path)
            
            logger.debug(f"Discovered {len(md_files)} MD files and {len(yaml_files)} YAML files")
            
        except Exception as e:
            logger.error(f"Error discovering character files: {str(e)}")
        
        return md_files, yaml_files
    
    def _process_markdown_files(self, md_files: List[str]) -> str:
        """
        Process all Markdown files into a unified content string.
        
        Args:
            md_files: List of markdown file paths
            
        Returns:
            Combined markdown content string
        """
        try:
            logger.info(f"Processing {len(md_files)} markdown files")
            markdown_parts = []
            
            for file_path in sorted(md_files):  # Sort for consistent ordering
                logger.debug(f"Reading markdown file: {file_path}")
                
                file_content = self._read_cached_file(file_path)
                
                # Add file separator and filename for context
                filename = os.path.basename(file_path)
                markdown_parts.append(f"# === {filename} ===\n\n{file_content}")
            
            combined_content = '\n\n'.join(markdown_parts)
            logger.debug(f"Combined markdown content: {len(combined_content)} characters")
            
            return combined_content
            
        except Exception as e:
            logger.error(f"Error processing markdown files: {str(e)}")
            return ""
    
    def _process_yaml_files(self, yaml_files: List[str]) -> Dict[str, Any]:
        """
        Process all YAML files into a structured data dictionary.
        
        Args:
            yaml_files: List of YAML file paths
            
        Returns:
            Dictionary containing parsed YAML data indexed by filename
        """
        try:
            logger.info(f"Processing {len(yaml_files)} YAML files")
            yaml_data = {}
            
            for file_path in sorted(yaml_files):  # Sort for consistent ordering
                logger.debug(f"Reading YAML file: {file_path}")
                
                try:
                    parsed_yaml = self._parse_cached_yaml(file_path)
                    filename_key = os.path.splitext(os.path.basename(file_path))[0]
                    yaml_data[filename_key] = parsed_yaml
                    
                except yaml.YAMLError as e:
                    logger.warning(f"Failed to parse YAML file {file_path}: {e}")
                    # Store as raw text if YAML parsing fails
                    filename_key = os.path.splitext(os.path.basename(file_path))[0]
                    raw_content = self._read_cached_file(file_path)
                    yaml_data[filename_key] = {'_raw': raw_content, '_parse_error': str(e)}
            
            logger.debug(f"Processed YAML data from {len(yaml_data)} files")
            return yaml_data
            
        except Exception as e:
            logger.error(f"Error processing YAML files: {str(e)}")
            return {}
    
    @lru_cache(maxsize=50)
    def _read_cached_file(self, file_path: str) -> str:
        """
        Read file content with caching for performance.
        
        Args:
            file_path: Path to file to read
            
        Returns:
            File content as string
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            logger.debug(f"Read {len(content)} characters from {file_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return ""
    
    @lru_cache(maxsize=20)
    def _parse_cached_yaml(self, file_path: str) -> Dict[str, Any]:
        """
        Parse YAML file content with caching for performance.
        
        Args:
            file_path: Path to YAML file to parse
            
        Returns:
            Parsed YAML data as dictionary
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                yaml_content = yaml.safe_load(file)
                
            if not isinstance(yaml_content, dict):
                logger.warning(f"YAML file {file_path} did not parse to dictionary, wrapping")
                yaml_content = {'content': yaml_content}
                
            logger.debug(f"Parsed YAML from {file_path}: {len(yaml_content)} keys")
            return yaml_content
            
        except Exception as e:
            logger.error(f"Error parsing YAML file {file_path}: {e}")
            raise
    
    def _merge_yaml_data_into_character_data(self, yaml_data: Dict[str, Any]) -> None:
        """
        Merge YAML data into character_data for easier access.
        
        Args:
            yaml_data: Dictionary of parsed YAML files
        """
        try:
            for yaml_file, yaml_content in yaml_data.items():
                if isinstance(yaml_content, dict) and '_raw' not in yaml_content:
                    # Use prefixed keys to avoid conflicts
                    prefixed_key = f'yaml_{yaml_file}'
                    self.character_data[prefixed_key] = yaml_content
                    
                    # Also merge direct keys if they don't conflict
                    for key, value in yaml_content.items():
                        if key not in self.character_data:
                            self.character_data[key] = value
                            
        except Exception as e:
            logger.error(f"Error merging YAML data: {str(e)}")
    
    def _parse_character_sheet_content(self, markdown_content: str) -> Dict[str, Any]:
        """
        Parse character sheet content from markdown text.
        
        Extracts structured information from markdown using pattern matching
        and text analysis techniques.
        
        Args:
            markdown_content: Combined markdown content from character files
            
        Returns:
            Dictionary containing extracted character information
        """
        try:
            character_data = {}
            
            # Extract basic character information
            character_data.update(self._extract_basic_info(markdown_content))
            
            # Extract character statistics
            character_data.update(self._extract_character_stats(markdown_content))
            
            # Extract background and narrative elements
            character_data.update(self._extract_background_info(markdown_content))
            
            # Extract personality traits and behavioral patterns
            character_data.update(self._extract_personality_info(markdown_content))
            
            # Extract relationships and social connections
            character_data.update(self._extract_relationship_info(markdown_content))
            
            # Extract skills and capabilities
            character_data.update(self._extract_skills_info(markdown_content))
            
            logger.debug(f"Parsed character sheet data: {len(character_data)} fields")
            return character_data
            
        except Exception as e:
            logger.error(f"Error parsing character sheet content: {str(e)}")
            return {}
    
    def _extract_basic_info(self, content: str) -> Dict[str, Any]:
        """Extract basic character information (name, faction, etc.)."""
        basic_info = {}
        
        try:
            # Extract name
            name_patterns = [
                r'(?:name|character):\s*([^\n]+)',
                r'#\s*([^\n]+)',  # First header
                r'character name:\s*([^\n]+)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    basic_info['name'] = match.group(1).strip()
                    break
            
            # Extract faction
            faction_patterns = [
                r'faction:\s*([^\n]+)',
                r'allegiance:\s*([^\n]+)',
                r'organization:\s*([^\n]+)'
            ]
            
            for pattern in faction_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    basic_info['faction'] = match.group(1).strip()
                    break
            
            # Extract rank/title
            rank_patterns = [
                r'rank:\s*([^\n]+)',
                r'title:\s*([^\n]+)',
                r'position:\s*([^\n]+)'
            ]
            
            for pattern in rank_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    basic_info['rank'] = match.group(1).strip()
                    break
                    
        except Exception as e:
            logger.error(f"Error extracting basic info: {str(e)}")
        
        return basic_info
    
    def _extract_character_stats(self, content: str) -> Dict[str, Any]:
        """Extract character statistics and attributes."""
        stats = {}
        
        try:
            # Look for stat blocks in various formats
            stat_patterns = [
                r'(?:weapon skill|ws):\s*(\d+)',
                r'(?:ballistic skill|bs):\s*(\d+)',
                r'(?:strength|str?):\s*(\d+)',
                r'(?:toughness|t):\s*(\d+)',
                r'(?:initiative|i):\s*(\d+)',
                r'(?:attacks|a):\s*(\d+)',
                r'(?:leadership|ld):\s*(\d+)',
                r'(?:wounds|w):\s*(\d+)'
            ]
            
            for pattern in stat_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    stat_name = match.group(0).split(':')[0].strip().lower()
                    stat_value = int(match.group(1))
                    stats[stat_name] = stat_value
                    
        except Exception as e:
            logger.error(f"Error extracting character stats: {str(e)}")
        
        return {'stats': stats} if stats else {}
    
    def _extract_background_info(self, content: str) -> Dict[str, Any]:
        """Extract background and narrative information."""
        background_info = {}
        
        try:
            # Extract background sections
            section_patterns = {
                'background': r'(?:background|history):\s*([^\n]+(?:\n(?!\w+:)[^\n]+)*)',
                'origin': r'origin:\s*([^\n]+(?:\n(?!\w+:)[^\n]+)*)',
                'description': r'(?:description|appearance):\s*([^\n]+(?:\n(?!\w+:)[^\n]+)*)'
            }
            
            for key, pattern in section_patterns.items():
                match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                if match:
                    background_info[key] = match.group(1).strip()
                    
        except Exception as e:
            logger.error(f"Error extracting background info: {str(e)}")
        
        return background_info
    
    def _extract_personality_info(self, content: str) -> Dict[str, Any]:
        """Extract personality traits and behavioral patterns."""
        personality_info = {}
        
        try:
            # Extract personality traits
            traits_pattern = r'(?:personality|traits?):\s*([^\n]+(?:\n(?!\\w+:)[^\n]+)*)'
            match = re.search(traits_pattern, content, re.IGNORECASE | re.MULTILINE)
            
            if match:
                traits_text = match.group(1).strip()
                # Split traits by common delimiters
                traits = [trait.strip() for trait in re.split(r'[,;]|\n', traits_text) if trait.strip()]
                personality_info['personality_traits'] = traits
            
            # Extract motivations
            motivation_pattern = r'(?:motivation|goal)s?:\s*([^\n]+(?:\n(?!\w+:)[^\n]+)*)'
            match = re.search(motivation_pattern, content, re.IGNORECASE | re.MULTILINE)
            
            if match:
                motivation_text = match.group(1).strip()
                personality_info['motivations'] = motivation_text
                
        except Exception as e:
            logger.error(f"Error extracting personality info: {str(e)}")
        
        return personality_info
    
    def _extract_relationship_info(self, content: str) -> Dict[str, Any]:
        """Extract relationship and social connection information."""
        relationship_info = {}
        
        try:
            # Extract relationships section
            relationships_pattern = r'relationships?:\s*([^\n]+(?:\n(?!\w+:)[^\n]+)*)'
            match = re.search(relationships_pattern, content, re.IGNORECASE | re.MULTILINE)
            
            if match:
                relationships_text = match.group(1).strip()
                # Parse relationships into structured format
                relationships = {}
                
                for line in relationships_text.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        entity, relationship = line.split(':', 1)
                        relationships[entity.strip()] = relationship.strip()
                
                if relationships:
                    relationship_info['relationships'] = relationships
                    
        except Exception as e:
            logger.error(f"Error extracting relationship info: {str(e)}")
        
        return relationship_info
    
    def _extract_skills_info(self, content: str) -> Dict[str, Any]:
        """Extract skills and capabilities information."""
        skills_info = {}
        
        try:
            # Extract skills section
            skills_pattern = r'skills?:\s*([^\n]+(?:\n(?!\w+:)[^\n]+)*)'
            match = re.search(skills_pattern, content, re.IGNORECASE | re.MULTILINE)
            
            if match:
                skills_text = match.group(1).strip()
                skills = [skill.strip() for skill in re.split(r'[,;]|\n', skills_text) if skill.strip()]
                skills_info['skills'] = skills
                
        except Exception as e:
            logger.error(f"Error extracting skills info: {str(e)}")
        
        return skills_info
    
    def _extract_character_characteristics(self) -> None:
        """Extract and interpret core character characteristics for runtime use."""
        try:
            # Extract core identity elements
            self._extract_core_identity()
            
            # Extract personality traits and behavioral patterns
            self._extract_personality_traits()
            
            # Extract decision-making weights and priorities
            self._extract_decision_weights()
            
            # Extract relationship mappings
            self._extract_relationships()
            
            # Extract knowledge domains and expertise
            self._extract_knowledge_domains()
            
            logger.debug(f"Extracted character characteristics for {self.character_data.get('name', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error extracting character characteristics: {str(e)}")
    
    def _extract_core_identity(self) -> None:
        """Extract core identity elements from character data."""
        try:
            # Ensure basic identity fields exist with defaults
            if 'name' not in self.character_data:
                # Try to derive from directory name
                dir_name = os.path.basename(os.path.normpath(self.character_directory_path))
                self.character_data['name'] = dir_name.replace('_', ' ').title()
            
            # Set default faction if not specified
            if 'faction' not in self.character_data:
                self.character_data['faction'] = 'Unknown'
            
            # Extract character archetype/class if available
            if 'rank' in self.character_data or 'title' in self.character_data:
                self.character_data['archetype'] = self.character_data.get('rank', self.character_data.get('title', 'Operative'))
                
        except Exception as e:
            logger.error(f"Error extracting core identity: {str(e)}")
    
    def _extract_personality_traits(self) -> None:
        """Extract and quantify personality traits for behavioral modeling."""
        try:
            traits_dict = {}
            
            # Extract from parsed personality traits
            personality_traits = self.character_data.get('personality_traits', [])
            
            if isinstance(personality_traits, list):
                for trait in personality_traits:
                    # Map traits to quantified values
                    trait_lower = trait.lower()
                    
                    if any(word in trait_lower for word in ['brave', 'courageous', 'fearless']):
                        traits_dict['bravery'] = 0.8
                    if any(word in trait_lower for word in ['loyal', 'devoted', 'faithful']):
                        traits_dict['loyalty'] = 0.9
                    if any(word in trait_lower for word in ['aggressive', 'violent', 'hostile']):
                        traits_dict['aggression'] = 0.7
                    if any(word in trait_lower for word in ['cautious', 'careful', 'prudent']):
                        traits_dict['caution'] = 0.7
                    if any(word in trait_lower for word in ['intelligent', 'smart', 'clever']):
                        traits_dict['intelligence'] = 0.8
            
            # Store quantified traits
            if traits_dict:
                self.character_data['personality_scores'] = traits_dict
                
        except Exception as e:
            logger.error(f"Error extracting personality traits: {str(e)}")
    
    def _extract_decision_weights(self) -> None:
        """Extract decision-making weights based on character priorities."""
        try:
            # Default decision weights
            decision_weights = {
                "self_preservation": 0.5,
                "faction_loyalty": 0.7,
                "personal_relationships": 0.6,
                "mission_success": 0.8,
                "moral_principles": 0.4,
            }
            
            # Adjust weights based on character traits
            personality_scores = self.character_data.get('personality_scores', {})
            
            if 'loyalty' in personality_scores:
                decision_weights['faction_loyalty'] = min(1.0, personality_scores['loyalty'])
            
            if 'bravery' in personality_scores:
                decision_weights['self_preservation'] = max(0.1, 1.0 - personality_scores['bravery'])
            
            if 'caution' in personality_scores:
                decision_weights['self_preservation'] = min(1.0, decision_weights['self_preservation'] + personality_scores['caution'] * 0.3)
            
            # Consider faction and background
            faction = self.character_data.get('faction', '').lower()
            
            if 'chaos' in faction:
                decision_weights['moral_principles'] = 0.2
                decision_weights['personal_relationships'] = 0.3
            elif 'imperium' in faction:
                decision_weights['faction_loyalty'] = 0.9
                decision_weights['moral_principles'] = 0.7
            
            self.character_data['decision_weights'] = decision_weights
            
        except Exception as e:
            logger.error(f"Error extracting decision weights: {str(e)}")
    
    def _extract_relationships(self) -> None:
        """Extract and quantify relationships with other entities."""
        try:
            relationships_dict = {}
            
            # Process relationships from character data
            relationships = self.character_data.get('relationships', {})
            
            if isinstance(relationships, dict):
                for entity, relationship_desc in relationships.items():
                    # Convert relationship descriptions to numeric values
                    desc_lower = relationship_desc.lower()
                    
                    if any(word in desc_lower for word in ['friend', 'ally', 'trusted', 'companion']):
                        relationships_dict[entity] = 0.7
                    elif any(word in desc_lower for word in ['enemy', 'rival', 'hostile', 'hatred']):
                        relationships_dict[entity] = -0.8
                    elif any(word in desc_lower for word in ['superior', 'commander', 'leader']):
                        relationships_dict[entity] = 0.5  # Respectful but hierarchical
                    elif any(word in desc_lower for word in ['neutral', 'unknown', 'stranger']):
                        relationships_dict[entity] = 0.0
                    else:
                        relationships_dict[entity] = 0.1  # Slight positive default
            
            if relationships_dict:
                self.character_data['relationship_scores'] = relationships_dict
                
        except Exception as e:
            logger.error(f"Error extracting relationships: {str(e)}")
    
    def _extract_knowledge_domains(self) -> None:
        """Extract knowledge domains and areas of expertise."""
        try:
            knowledge_domains = []
            
            # Extract from skills
            skills = self.character_data.get('skills', [])
            if isinstance(skills, list):
                knowledge_domains.extend(skills)
            
            # Extract from background/description
            background = self.character_data.get('background', '')
            if background:
                # Look for knowledge indicators
                if any(word in background.lower() for word in ['tech', 'mechanical', 'engineering']):
                    knowledge_domains.append('technology')
                if any(word in background.lower() for word in ['combat', 'tactical', 'warfare']):
                    knowledge_domains.append('combat')
                if any(word in background.lower() for word in ['diplomacy', 'negotiation', 'politics']):
                    knowledge_domains.append('diplomacy')
            
            # Store unique knowledge domains
            if knowledge_domains:
                self.character_data['knowledge_domains'] = list(set(knowledge_domains))
                
        except Exception as e:
            logger.error(f"Error extracting knowledge domains: {str(e)}")
    
    def get_character_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of interpreted character data.
        
        Returns:
            Dictionary containing character summary information
        """
        try:
            hybrid_context = self.character_data.get('hybrid_context', {})
            
            return {
                'name': self.character_data.get('name', 'Unknown'),
                'faction': self.character_data.get('faction', 'Unknown'),
                'archetype': self.character_data.get('archetype', 'Unknown'),
                'files_processed': hybrid_context.get('file_count', {}),
                'has_personality_traits': 'personality_scores' in self.character_data,
                'has_decision_weights': 'decision_weights' in self.character_data,
                'has_relationships': 'relationship_scores' in self.character_data,
                'knowledge_domains': len(self.character_data.get('knowledge_domains', [])),
                'total_data_fields': len(self.character_data),
                'interpretation_timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error generating character summary: {str(e)}")
            return {'error': str(e)}
    
    def validate_character_data(self) -> Tuple[bool, List[str]]:
        """
        Validate the integrity and completeness of character data.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Check essential fields
            if not self.character_data.get('name'):
                issues.append("Character name is missing")
            
            if not self.character_data.get('faction'):
                issues.append("Character faction is missing")
            
            # Check for hybrid context
            if 'hybrid_context' not in self.character_data:
                issues.append("Hybrid context data is missing")
            
            # Validate decision weights
            decision_weights = self.character_data.get('decision_weights', {})
            if decision_weights:
                for weight_name, weight_value in decision_weights.items():
                    if not isinstance(weight_value, (int, float)) or not (0.0 <= weight_value <= 1.0):
                        issues.append(f"Invalid decision weight for {weight_name}: {weight_value}")
            
            # Validate personality scores
            personality_scores = self.character_data.get('personality_scores', {})
            if personality_scores:
                for trait_name, trait_value in personality_scores.items():
                    if not isinstance(trait_value, (int, float)) or not (0.0 <= trait_value <= 1.0):
                        issues.append(f"Invalid personality score for {trait_name}: {trait_value}")
            
            # Validate relationship scores
            relationship_scores = self.character_data.get('relationship_scores', {})
            if relationship_scores:
                for entity, score in relationship_scores.items():
                    if not isinstance(score, (int, float)) or not (-1.0 <= score <= 1.0):
                        issues.append(f"Invalid relationship score for {entity}: {score}")
            
            is_valid = len(issues) == 0
            return is_valid, issues
            
        except Exception as e:
            issues.append(f"Validation error: {str(e)}")
            return False, issues