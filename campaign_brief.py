#!/usr/bin/env python3
"""
Campaign Brief Data Models
==========================

This module implements data models for campaign briefs that define narrative context
for the Warhammer 40k Multi-Agent Simulator. Campaign briefs provide rich story
elements that transform simple battle simulations into narrative-driven experiences.

The campaign brief system supports:
1. YAML and Markdown parsing for campaign definitions
2. Structured narrative events with triggers and character impacts
3. Character ecological context and relationship definitions
4. Environmental story elements and atmosphere settings
5. Story progression markers for dynamic narrative evolution

Architecture Reference: Story 1.1 - Narrative Engine Foundation
Development Phase: Phase 1 - Campaign Brief Infrastructure
"""

import json
import os
import yaml
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re

# Configure campaign brief system logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NarrativeEvent:
    """
    Represents a narrative event that can be triggered during simulation.
    
    Narrative events provide story context and character-specific impacts
    that drive non-combat interactions and story progression.
    """
    trigger_condition: str  # Condition that activates this event
    description: str  # Detailed description of the event
    character_impact: Dict[str, str] = field(default_factory=dict)  # Impact on specific characters
    environmental_change: str = ""  # How the environment changes
    turn_activation: Optional[int] = None  # Specific turn to activate (optional)
    probability: float = 1.0  # Probability of activation when conditions are met


@dataclass
class CampaignBrief:
    """
    Core data structure for campaign narrative context.
    
    Defines all narrative elements needed to transform the simulation
    from combat-focused to story-driven character interactions.
    """
    title: str
    setting: str
    atmosphere: str
    key_events: List[NarrativeEvent] = field(default_factory=list)
    character_ecology: Dict[str, Any] = field(default_factory=dict)
    environmental_elements: List[str] = field(default_factory=list)
    story_progression_markers: List[str] = field(default_factory=list)
    
    # Additional metadata
    created_date: Optional[str] = None
    author: Optional[str] = None
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)


class CampaignBriefLoader:
    """
    Handles loading and parsing of campaign brief documents from YAML or Markdown formats.
    
    Provides robust parsing with validation and error handling to ensure campaign briefs
    are properly structured for use by the DirectorAgent.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.CampaignBriefLoader")
    
    def load_from_file(self, file_path: Union[str, Path]) -> CampaignBrief:
        """
        Load campaign brief from a YAML or Markdown file.
        
        Args:
            file_path: Path to the campaign brief file
            
        Returns:
            CampaignBrief object with parsed data
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid or required fields are missing
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Campaign brief file not found: {file_path}")
        
        self.logger.info(f"Loading campaign brief from: {file_path}")
        
        # Determine file type and parse accordingly
        if file_path.suffix.lower() in ['.yaml', '.yml']:
            return self._parse_yaml_file(file_path)
        elif file_path.suffix.lower() in ['.md', '.markdown']:
            return self._parse_markdown_file(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}. Supported: .yaml, .yml, .md, .markdown")
    
    def _parse_yaml_file(self, file_path: Path) -> CampaignBrief:
        """Parse YAML campaign brief file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            return self._create_campaign_brief_from_dict(data)
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing YAML file {file_path}: {e}")
    
    def _parse_markdown_file(self, file_path: Path) -> CampaignBrief:
        """Parse Markdown campaign brief file with YAML frontmatter."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract YAML frontmatter if present
            frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
            match = re.match(frontmatter_pattern, content, re.DOTALL)
            
            if match:
                yaml_content = match.group(1)
                markdown_content = match.group(2)
                
                # Parse YAML frontmatter
                data = yaml.safe_load(yaml_content)
                
                # Extract additional content from markdown if needed
                data = self._enhance_with_markdown_content(data, markdown_content)
                
            else:
                # No frontmatter found, parse as structured markdown
                data = self._parse_structured_markdown(content)
            
            return self._create_campaign_brief_from_dict(data)
            
        except Exception as e:
            raise ValueError(f"Error parsing Markdown file {file_path}: {e}")
    
    def _enhance_with_markdown_content(self, data: Dict, markdown_content: str) -> Dict:
        """Enhance YAML data with additional content from markdown body."""
        # Extract setting description if not in YAML
        if 'setting' not in data and 'setting' in markdown_content.lower():
            setting_match = re.search(r'## Setting\s*\n(.*?)(?=\n##|\Z)', markdown_content, re.DOTALL | re.IGNORECASE)
            if setting_match:
                data['setting'] = setting_match.group(1).strip()
        
        return data
    
    def _parse_structured_markdown(self, content: str) -> Dict:
        """Parse structured markdown without YAML frontmatter."""
        data = {}
        
        # Extract title from first heading
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            data['title'] = title_match.group(1).strip()
        
        # Extract sections using heading patterns
        sections = {
            'setting': r'## Setting\s*\n(.*?)(?=\n##|\Z)',
            'atmosphere': r'## Atmosphere\s*\n(.*?)(?=\n##|\Z)',
        }
        
        for key, pattern in sections.items():
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()
        
        return data
    
    def _create_campaign_brief_from_dict(self, data: Dict) -> CampaignBrief:
        """Create CampaignBrief object from parsed dictionary data."""
        # Validate required fields
        required_fields = ['title', 'setting', 'atmosphere']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Required field '{field}' missing from campaign brief")
        
        # Parse narrative events
        key_events = []
        if 'key_events' in data:
            for event_data in data['key_events']:
                if isinstance(event_data, dict):
                    event = NarrativeEvent(
                        trigger_condition=event_data.get('trigger_condition', ''),
                        description=event_data.get('description', ''),
                        character_impact=event_data.get('character_impact', {}),
                        environmental_change=event_data.get('environmental_change', ''),
                        turn_activation=event_data.get('turn_activation'),
                        probability=event_data.get('probability', 1.0)
                    )
                    key_events.append(event)
        
        # Create campaign brief
        campaign_brief = CampaignBrief(
            title=data['title'],
            setting=data['setting'],
            atmosphere=data['atmosphere'],
            key_events=key_events,
            character_ecology=data.get('character_ecology', {}),
            environmental_elements=data.get('environmental_elements', []),
            story_progression_markers=data.get('story_progression_markers', []),
            created_date=data.get('created_date'),
            author=data.get('author'),
            version=data.get('version', '1.0'),
            tags=data.get('tags', [])
        )
        
        self.logger.info(f"Successfully parsed campaign brief: {campaign_brief.title}")
        return campaign_brief
    
    def validate_campaign_brief(self, brief: CampaignBrief) -> bool:
        """
        Validate a campaign brief for completeness and consistency.
        
        Args:
            brief: CampaignBrief to validate
            
        Returns:
            True if valid, raises ValueError if invalid
            
        Raises:
            ValueError: If validation fails with specific error message
        """
        # Check required fields
        if not brief.title or not brief.title.strip():
            raise ValueError("Campaign brief title cannot be empty")
        
        if not brief.setting or not brief.setting.strip():
            raise ValueError("Campaign brief setting cannot be empty")
        
        if not brief.atmosphere or not brief.atmosphere.strip():
            raise ValueError("Campaign brief atmosphere cannot be empty")
        
        # Validate narrative events
        for i, event in enumerate(brief.key_events):
            if not event.trigger_condition:
                raise ValueError(f"Narrative event {i} missing trigger_condition")
            
            if not event.description:
                raise ValueError(f"Narrative event {i} missing description")
            
            if event.probability < 0.0 or event.probability > 1.0:
                raise ValueError(f"Narrative event {i} probability must be between 0.0 and 1.0")
        
        self.logger.info(f"Campaign brief validation passed: {brief.title}")
        return True


def create_sample_campaign_brief() -> CampaignBrief:
    """
    Create a sample campaign brief for testing and demonstration purposes.
    
    Returns:
        Sample CampaignBrief for "Shadows of Serenity Station"
    """
    # Sample narrative events
    events = [
        NarrativeEvent(
            trigger_condition="simulation_start",
            description="The station's emergency beacon activates, casting eerie red light through the corridors.",
            character_impact={
                "all": "You notice the emergency lighting and feel tension in the air.",
                "imperial": "Your duty compels you to investigate Imperial distress signals.",
                "ork": "Red lights mean sumfin' gud is about to happen!"
            },
            environmental_change="Emergency lighting activated throughout the station"
        ),
        NarrativeEvent(
            trigger_condition="turn >= 2",
            description="Strange mechanical sounds echo from the station's depths.",
            character_impact={
                "tech_adept": "Your augmetic senses detect anomalous machine signatures.",
                "space_marine": "Your enhanced hearing identifies potential threats below."
            },
            environmental_change="Mechanical sounds provide audio cues about hidden areas"
        ),
        NarrativeEvent(
            trigger_condition="investigation_count >= 3",
            description="A hidden data terminal flickers to life, displaying corrupted logs.",
            character_impact={
                "all": "You discover fragmentary records of the station's final days."
            },
            environmental_change="Data terminal becomes available for interaction",
            probability=0.8
        )
    ]
    
    return CampaignBrief(
        title="Shadows of Serenity Station",
        setting="An abandoned Imperial monitoring station on the edge of the Ghoul Stars, " +
                "where long-range sensors once watched for xenos incursions. The station " +
                "has been silent for months, but recent automated distress signals suggest " +
                "something still moves within its corridors.",
        atmosphere="Tense investigation with gothic horror elements. The station feels " +
                   "haunted by its past, with flickering lights, strange sounds, and " +
                   "the constant sense of being watched. Discovery and dialogue drive " +
                   "the narrative rather than combat.",
        key_events=events,
        character_ecology={
            "factions_present": ["Imperial Guard", "Space Marines", "Adeptus Mechanicus"],
            "npc_archetypes": ["Station Servitors", "Auto-systems", "Hidden Survivors"],
            "relationship_dynamics": {
                "imperial_unity": "Imperial forces must work together to uncover the truth",
                "tech_mysteries": "Mechanicus agents seek to understand what happened to the station's machine spirits"
            }
        },
        environmental_elements=[
            "Flickering emergency lighting",
            "Echoing mechanical sounds",
            "Locked blast doors requiring investigation to open",
            "Hidden data terminals with corrupted logs",
            "Abandoned personal quarters with story clues",
            "Central command center with inactive monitoring systems"
        ],
        story_progression_markers=[
            "Emergency beacon activation",
            "First investigation reveals clues",
            "Hidden areas discovered",
            "Data terminals accessed",
            "Central mystery uncovered",
            "Final revelation and resolution"
        ],
        created_date=datetime.now().isoformat(),
        author="Development Team",
        version="1.0",
        tags=["investigation", "mystery", "non-combat", "imperial", "station"]
    )