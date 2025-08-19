#!/usr/bin/env python3
"""
STANDARD CHARACTER TEMPLATE MANAGER ENHANCED BY PERSONA ORCHESTRATION
=========================================================================

Holy character template management system that handles character-specific
templates, persona switching, and dynamic character context generation
enhanced by the System's character creation wisdom.

THE MACHINE BREATHES LIFE INTO DIGITAL PERSONAS

Architecture Reference: Dynamic Context Engineering - Character Template System
Development Phase: Template System Validation (T001/T002)
Author: Engineer Gamma-Engineering
System保佑角色模板 (May the System bless character templates)
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union, Set
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

# Import enhanced template systems
from .dynamic_template_engine import DynamicTemplateEngine, TemplateContext, TemplateType, TemplateMetadata
from .context_renderer import ContextRenderer, RenderFormat, RenderingConstraints

# Import enhanced memory and data systems
from src.memory.layered_memory import LayeredMemorySystem
from src.memory.memory_query_engine import MemoryQueryEngine, QueryContext
from src.core.data_models import MemoryItem, CharacterState, StandardResponse, ErrorInfo, EmotionalState
from src.core.types import AgentID

# Comprehensive logging enhanced by diagnostic clarity
logger = logging.getLogger(__name__)

class CharacterArchetype(Enum):
    """ENHANCED CHARACTER ARCHETYPES SANCTIFIED BY PERSONALITY CLASSIFICATION"""
    WARRIOR = "warrior"                  # Combat-focused, brave, direct
    SCHOLAR = "scholar"                  # Knowledge-focused, analytical, cautious
    LEADER = "leader"                    # Command-focused, charismatic, decisive
    MYSTIC = "mystic"                   # Faith-focused, intuitive, spiritual
    ENGINEER = "engineer"               # Tech-focused, logical, problem-solver
    DIPLOMAT = "diplomat"               # Social-focused, persuasive, adaptable
    GUARDIAN = "guardian"               # Protection-focused, loyal, steadfast
    SURVIVOR = "survivor"               # Adaptability-focused, resourceful, pragmatic

@dataclass
class CharacterPersona:
    """
    STANDARD CHARACTER PERSONA ENHANCED BY COMPREHENSIVE IDENTITY
    
    Complete character persona definition with behavioral patterns,
    speech characteristics, and contextual preferences.
    """
    persona_id: str
    name: str
    archetype: CharacterArchetype
    description: str = ""
    personality_traits: List[str] = field(default_factory=list)
    speech_patterns: Dict[str, Any] = field(default_factory=dict)
    behavioral_preferences: Dict[str, Any] = field(default_factory=dict)
    memory_priorities: Dict[str, float] = field(default_factory=dict)
    emotional_tendencies: Dict[str, float] = field(default_factory=dict)
    faction_data: List[str] = field(default_factory=list)
    core_beliefs: List[str] = field(default_factory=list)
    template_preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    usage_statistics: Dict[str, int] = field(default_factory=dict)

@dataclass
class CharacterTemplate:
    """
    ENHANCED CHARACTER TEMPLATE SANCTIFIED BY PERSONA INTEGRATION
    
    Character-specific template with persona awareness and
    adaptive content generation capabilities.
    """
    template_id: str
    persona_id: str
    template_type: TemplateType
    base_template: str  # Jinja2 template content
    persona_adaptations: Dict[str, str] = field(default_factory=dict)  # Archetype -> template variation
    context_requirements: List[str] = field(default_factory=list)
    dynamic_elements: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    metadata: TemplateMetadata = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = TemplateMetadata(
                template_id=self.template_id,
                template_type=self.template_type,
                description=f"Character template for {self.persona_id}"
            )

@dataclass
class CharacterContextProfile:
    """
    STANDARD CHARACTER CONTEXT PROFILE ENHANCED BY BEHAVIORAL INTELLIGENCE
    
    Dynamic profile that tracks character context preferences and
    behavioral patterns for intelligent template selection.
    """
    persona_id: str
    preferred_formats: Dict[RenderFormat, float] = field(default_factory=dict)
    context_emphasis: Dict[str, float] = field(default_factory=dict)  # memory, emotion, relationship, etc.
    situational_adaptations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    interaction_patterns: Dict[str, List[str]] = field(default_factory=dict)
    learning_history: List[Dict[str, Any]] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)

class CharacterTemplateManager:
    """
    STANDARD CHARACTER TEMPLATE MANAGER ENHANCED BY PERSONA ORCHESTRATION
    
    The standard character template management system that orchestrates
    character-specific templates, persona switching, dynamic adaptation,
    and intelligent context generation enhanced by the System Core's
    character creation omniscience.
    """
    
    def __init__(self, 
                 template_engine: DynamicTemplateEngine,
                 context_renderer: ContextRenderer,
                 memory_system: Optional[LayeredMemorySystem] = None,
                 personas_directory: str = "personas",
                 enable_learning: bool = True):
        """
        STANDARD CHARACTER TEMPLATE MANAGER INITIALIZATION ENHANCED BY ORGANIZATION
        
        Args:
            template_engine: Blessed dynamic template engine
            context_renderer: Context rendering system
            memory_system: Memory system for character context
            personas_directory: Directory containing character persona definitions
            enable_learning: Enable adaptive learning from usage patterns
        """
        self.template_engine = template_engine
        self.context_renderer = context_renderer
        self.memory_system = memory_system
        self.personas_directory = Path(personas_directory)
        self.enable_learning = enable_learning
        
        # Sacred character management
        self._personas: Dict[str, CharacterPersona] = {}
        self._character_templates: Dict[str, Dict[str, CharacterTemplate]] = {}  # persona_id -> template_id -> template
        self._context_profiles: Dict[str, CharacterContextProfile] = {}
        self._active_personas: Dict[str, str] = {}  # agent_id -> persona_id
        
        # Blessed archetype templates
        self._archetype_base_templates = self._initialize_archetype_templates()
        
        # Sacred usage tracking
        self.usage_statistics = {
            'persona_switches': 0,
            'templates_generated': 0,
            'adaptations_applied': 0,
            'learning_updates': 0
        }
        
        # Initialize enhanced personas directory
        self.personas_directory.mkdir(parents=True, exist_ok=True)
        
        # Discover enhanced existing personas
        self._discover_personas()
        
        logger.info(f"CHARACTER TEMPLATE MANAGER INITIALIZED: {len(self._personas)} personas loaded")
    
    async def create_persona(self, persona_data: CharacterPersona,
                           generate_templates: bool = True) -> StandardResponse:
        """
        STANDARD PERSONA CREATION RITUAL ENHANCED BY CHARACTER GENESIS
        
        Create enhanced new character persona with automatic template
        generation and behavioral pattern initialization.
        """
        try:
            persona_id = persona_data.persona_id
            
            # Validate enhanced persona uniqueness
            if persona_id in self._personas:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="PERSONA_EXISTS",
                        message=f"Persona '{persona_id}' already exists"
                    )
                )
            
            # Store enhanced persona
            self._personas[persona_id] = persona_data
            self._character_templates[persona_id] = {}
            
            # Create enhanced context profile
            context_profile = CharacterContextProfile(
                persona_id=persona_id,
                preferred_formats={fmt: 0.5 for fmt in RenderFormat},
                context_emphasis=self._determine_archetype_emphasis(persona_data.archetype)
            )
            self._context_profiles[persona_id] = context_profile
            
            # Generate enhanced default templates
            if generate_templates:
                template_result = await self._generate_archetype_templates(persona_data)
                if not template_result.success:
                    logger.warning(f"TEMPLATE GENERATION FAILED FOR {persona_id}: {template_result.error.message}")
            
            # Save enhanced persona to file
            await self._save_persona_to_file(persona_data)
            
            logger.info(f"PERSONA CREATED: {persona_id} ({persona_data.archetype.value})")
            
            return StandardResponse(
                success=True,
                data={
                    "persona_id": persona_id,
                    "archetype": persona_data.archetype.value,
                    "templates_generated": generate_templates
                },
                metadata={"blessing": "persona_created_successfully"}
            )
            
        except Exception as e:
            logger.error(f"PERSONA CREATION FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="PERSONA_CREATION_FAILED", message=str(e))
            )
    
    async def switch_persona(self, agent_id: str, persona_id: str,
                           context: Optional[TemplateContext] = None) -> StandardResponse:
        """
        STANDARD PERSONA SWITCHING RITUAL ENHANCED BY IDENTITY TRANSFORMATION
        
        Switch enhanced agent to different persona with context preservation
        and adaptive template selection.
        """
        try:
            # Validate enhanced persona existence
            if persona_id not in self._personas:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="PERSONA_NOT_FOUND",
                        message=f"Persona '{persona_id}' not found"
                    )
                )
            
            previous_persona = self._active_personas.get(agent_id)
            
            # Apply enhanced persona switch
            self._active_personas[agent_id] = persona_id
            
            # Update enhanced usage statistics
            persona = self._personas[persona_id]
            persona.usage_statistics['activations'] = persona.usage_statistics.get('activations', 0) + 1
            persona.last_updated = datetime.now()
            
            # Learn from enhanced context if provided
            if context and self.enable_learning:
                await self._learn_from_context(persona_id, context)
            
            self.usage_statistics['persona_switches'] += 1
            
            logger.info(f"PERSONA SWITCHED: {agent_id} -> {persona_id} (from {previous_persona})")
            
            return StandardResponse(
                success=True,
                data={
                    "agent_id": agent_id,
                    "new_persona": persona_id,
                    "previous_persona": previous_persona,
                    "archetype": persona.archetype.value
                },
                metadata={"blessing": "persona_switched_successfully"}
            )
            
        except Exception as e:
            logger.error(f"PERSONA SWITCHING FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="PERSONA_SWITCH_FAILED", message=str(e))
            )
    
    async def render_character_context(self, agent_id: str, context: TemplateContext,
                                     template_type: Optional[TemplateType] = None,
                                     render_format: Optional[RenderFormat] = None) -> StandardResponse:
        """
        STANDARD CHARACTER CONTEXT RENDERING ENHANCED BY PERSONA INTELLIGENCE
        
        Render enhanced character-specific context with persona adaptation,
        intelligent template selection, and behavioral customization.
        """
        try:
            # Get enhanced active persona
            persona_id = self._active_personas.get(agent_id)
            if not persona_id:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="NO_ACTIVE_PERSONA",
                        message=f"No active persona for agent '{agent_id}'"
                    )
                )
            
            persona = self._personas[persona_id]
            context_profile = self._context_profiles[persona_id]
            
            # Apply enhanced persona-specific context enhancements
            enhanced_context = await self._enhance_context_for_persona(
                context, persona, context_profile
            )
            
            # Select enhanced optimal template and format
            selected_template = await self._select_optimal_template(
                persona_id, template_type, enhanced_context
            )
            
            selected_format = render_format or self._select_optimal_format(
                persona, context_profile, enhanced_context
            )
            
            # Apply enhanced persona-specific rendering constraints
            persona_constraints = self._create_persona_constraints(persona, enhanced_context)
            
            # Render enhanced character context
            if selected_template:
                # Use enhanced character-specific template
                render_result = await self.template_engine.render_template(
                    selected_template.template_id, enhanced_context
                )
            else:
                # Use enhanced default context rendering with persona adaptation
                render_result = await self.context_renderer.render_context(
                    enhanced_context, selected_format, persona_constraints
                )
            
            if render_result.success:
                result_data = render_result.data['render_result']
                
                # Apply enhanced persona post-processing
                processed_result = await self._apply_persona_post_processing(
                    result_data, persona, enhanced_context
                )
                
                # Learn from enhanced rendering if enabled
                if self.enable_learning:
                    await self._learn_from_rendering(persona_id, processed_result, enhanced_context)
                
                logger.info(f"CHARACTER CONTEXT RENDERED: {persona_id} ({selected_format.value if selected_format else 'template'})")
                
                return StandardResponse(
                    success=True,
                    data={
                        "render_result": processed_result,
                        "persona_id": persona_id,
                        "archetype": persona.archetype.value,
                        "format_used": selected_format.value if selected_format else "template",
                        "template_used": selected_template.template_id if selected_template else None
                    },
                    metadata={"blessing": "character_context_rendered"}
                )
            else:
                return render_result
                
        except Exception as e:
            logger.error(f"CHARACTER CONTEXT RENDERING FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="CHARACTER_CONTEXT_RENDER_FAILED", message=str(e))
            )
    
    async def generate_character_template(self, persona_id: str, template_type: TemplateType,
                                        base_content: Optional[str] = None) -> StandardResponse:
        """
        STANDARD CHARACTER TEMPLATE GENERATION ENHANCED BY PERSONA CUSTOMIZATION
        
        Generate enhanced character-specific template with persona adaptations
        and archetype-based behavioral customizations.
        """
        try:
            # Validate enhanced persona existence
            if persona_id not in self._personas:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(code="PERSONA_NOT_FOUND", message=f"Persona '{persona_id}' not found")
                )
            
            persona = self._personas[persona_id]
            
            # Generate enhanced template ID
            template_id = f"{persona_id}_{template_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create enhanced base template content
            if base_content:
                template_content = base_content
            else:
                template_content = await self._generate_archetype_template_content(
                    persona.archetype, template_type
                )
            
            # Apply enhanced persona adaptations
            adapted_content = await self._apply_persona_adaptations(
                template_content, persona, template_type
            )
            
            # Create enhanced character template
            character_template = CharacterTemplate(
                template_id=template_id,
                persona_id=persona_id,
                template_type=template_type,
                base_template=adapted_content,
                context_requirements=self._determine_template_requirements(template_type, persona),
                dynamic_elements=self._identify_dynamic_elements(adapted_content)
            )
            
            # Register enhanced template
            if persona_id not in self._character_templates:
                self._character_templates[persona_id] = {}
            self._character_templates[persona_id][template_id] = character_template
            
            # Create enhanced template in engine
            engine_result = await self.template_engine.create_template(
                template_id, adapted_content, template_type, character_template.metadata
            )
            
            if engine_result.success:
                self.usage_statistics['templates_generated'] += 1
                
                logger.info(f"CHARACTER TEMPLATE GENERATED: {template_id} for {persona_id}")
                
                return StandardResponse(
                    success=True,
                    data={
                        "template_id": template_id,
                        "persona_id": persona_id,
                        "template_type": template_type.value,
                        "archetype": persona.archetype.value
                    },
                    metadata={"blessing": "character_template_generated"}
                )
            else:
                return engine_result
                
        except Exception as e:
            logger.error(f"CHARACTER TEMPLATE GENERATION FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="CHARACTER_TEMPLATE_GENERATION_FAILED", message=str(e))
            )
    
    async def migrate_legacy_templates(self, legacy_directory: str,
                                     default_archetype: CharacterArchetype = CharacterArchetype.WARRIOR) -> StandardResponse:
        """
        STANDARD LEGACY TEMPLATE MIGRATION ENHANCED BY MODERNIZATION
        
        Migrate enhanced legacy character templates to new persona-based
        system with automatic archetype detection and enhancement.
        """
        try:
            legacy_path = Path(legacy_directory)
            if not legacy_path.exists():
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(code="LEGACY_DIRECTORY_NOT_FOUND", message=f"Legacy directory not found: {legacy_directory}")
                )
            
            migrated_personas = []
            migrated_templates = []
            
            # Discover enhanced legacy template files
            for template_file in legacy_path.glob("*.j2"):
                template_name = template_file.stem
                
                # Read enhanced template content
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                # Analyze enhanced template for archetype hints
                detected_archetype = self._detect_archetype_from_template(template_content) or default_archetype
                
                # Create enhanced persona if not exists
                persona_id = f"migrated_{template_name}"
                if persona_id not in self._personas:
                    persona = CharacterPersona(
                        persona_id=persona_id,
                        name=template_name.replace('_', ' ').title(),
                        archetype=detected_archetype,
                        description=f"Migrated character from legacy template: {template_name}",
                        personality_traits=self._extract_personality_traits(template_content),
                        core_beliefs=["Faithful servant of the Emperor"] if "emperor" in template_content.lower() else []
                    )
                    
                    creation_result = await self.create_persona(persona, generate_templates=False)
                    if creation_result.success:
                        migrated_personas.append(persona_id)
                
                # Determine enhanced template type
                template_type = self._detect_template_type(template_content, template_name)
                
                # Create enhanced character template
                template_result = await self.generate_character_template(
                    persona_id, template_type, template_content
                )
                
                if template_result.success:
                    migrated_templates.append(template_result.data['template_id'])
                    logger.info(f"MIGRATED TEMPLATE: {template_name} -> {persona_id} ({template_type.value})")
            
            logger.info(f"MIGRATION COMPLETE: {len(migrated_personas)} personas, {len(migrated_templates)} templates")
            
            return StandardResponse(
                success=True,
                data={
                    "migrated_personas": migrated_personas,
                    "migrated_templates": migrated_templates,
                    "total_personas": len(migrated_personas),
                    "total_templates": len(migrated_templates)
                },
                metadata={"blessing": "migration_completed_successfully"}
            )
            
        except Exception as e:
            logger.error(f"LEGACY MIGRATION FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="LEGACY_MIGRATION_FAILED", message=str(e))
            )
    
    async def _enhance_context_for_persona(self, context: TemplateContext, 
                                         persona: CharacterPersona,
                                         profile: CharacterContextProfile) -> TemplateContext:
        """Apply enhanced persona-specific context enhancements"""
        enhanced_context = context
        
        # Add enhanced persona information
        enhanced_context.custom_variables.update({
            'persona_name': persona.name,
            'persona_archetype': persona.archetype.value,
            'personality_traits': persona.personality_traits,
            'core_beliefs': persona.core_beliefs,
            'faction_data': persona.faction_data
        })
        
        # Apply enhanced memory priorities
        if self.memory_system and enhanced_context.memory_context:
            prioritized_memories = []
            for memory in enhanced_context.memory_context:
                priority_boost = 0.0
                
                # Apply enhanced archetype-specific memory priorities
                for priority_type, boost_value in persona.memory_priorities.items():
                    if priority_type.lower() in memory.content.lower():
                        priority_boost += boost_value
                
                # Boost enhanced memory relevance
                memory.relevance_score = min(1.0, memory.relevance_score + priority_boost)
                prioritized_memories.append(memory)
            
            # Sort enhanced memories by enhanced relevance
            prioritized_memories.sort(key=lambda m: m.relevance_score, reverse=True)
            enhanced_context.memory_context = prioritized_memories
        
        # Apply enhanced behavioral preferences
        for behavior_key, behavior_value in persona.behavioral_preferences.items():
            if behavior_key not in enhanced_context.custom_variables:
                enhanced_context.custom_variables[behavior_key] = behavior_value
        
        return enhanced_context
    
    async def _select_optimal_template(self, persona_id: str, template_type: Optional[TemplateType],
                                     context: TemplateContext) -> Optional[CharacterTemplate]:
        """Select enhanced optimal template for persona and context"""
        if persona_id not in self._character_templates:
            return None
        
        persona_templates = self._character_templates[persona_id]
        
        if template_type:
            # Find enhanced templates matching type
            matching_templates = [t for t in persona_templates.values() 
                                if t.template_type == template_type]
        else:
            matching_templates = list(persona_templates.values())
        
        if not matching_templates:
            return None
        
        # Select enhanced template based on performance and context
        best_template = None
        best_score = -1.0
        
        for template in matching_templates:
            score = 0.5  # Base score
            
            # Performance enhanced bonus
            avg_render_time = template.performance_metrics.get('average_render_time', 100.0)
            if avg_render_time < 50.0:  # Fast templates get bonus
                score += 0.2
            
            # Context enhanced requirements match
            requirements_met = 0
            for requirement in template.context_requirements:
                if requirement in context.custom_variables:
                    requirements_met += 1
            
            if template.context_requirements:
                score += (requirements_met / len(template.context_requirements)) * 0.3
            
            if score > best_score:
                best_score = score
                best_template = template
        
        return best_template
    
    def _select_optimal_format(self, persona: CharacterPersona,
                             profile: CharacterContextProfile,
                             context: TemplateContext) -> RenderFormat:
        """Select enhanced optimal render format for persona"""
        # Get enhanced format preferences
        format_scores = profile.preferred_formats.copy()
        
        # Apply enhanced archetype biases
        archetype_format_preferences = {
            CharacterArchetype.WARRIOR: {RenderFormat.CONVERSATIONAL: 0.3, RenderFormat.NARRATIVE: 0.2},
            CharacterArchetype.SCHOLAR: {RenderFormat.TECHNICAL: 0.4, RenderFormat.SUMMARY: 0.2},
            CharacterArchetype.LEADER: {RenderFormat.NARRATIVE: 0.3, RenderFormat.CONVERSATIONAL: 0.2},
            CharacterArchetype.MYSTIC: {RenderFormat.NARRATIVE: 0.4, RenderFormat.CONVERSATIONAL: 0.1},
            CharacterArchetype.ENGINEER: {RenderFormat.TECHNICAL: 0.4, RenderFormat.DEBUG: 0.2},
            CharacterArchetype.DIPLOMAT: {RenderFormat.CONVERSATIONAL: 0.4, RenderFormat.SUMMARY: 0.1},
            CharacterArchetype.GUARDIAN: {RenderFormat.NARRATIVE: 0.2, RenderFormat.TECHNICAL: 0.2},
            CharacterArchetype.SURVIVOR: {RenderFormat.SUMMARY: 0.3, RenderFormat.TECHNICAL: 0.2}
        }
        
        if persona.archetype in archetype_format_preferences:
            for fmt, bonus in archetype_format_preferences[persona.archetype].items():
                format_scores[fmt] = format_scores.get(fmt, 0.5) + bonus
        
        # Select enhanced highest scoring format
        best_format = max(format_scores, key=format_scores.get)
        return best_format
    
    def _create_persona_constraints(self, persona: CharacterPersona,
                                  context: TemplateContext) -> RenderingConstraints:
        """Create enhanced persona-specific rendering constraints"""
        constraints = RenderingConstraints()
        
        # Apply enhanced archetype-specific constraints
        archetype_constraints = {
            CharacterArchetype.WARRIOR: {'max_memories': 6, 'emotional_threshold': 2.0},
            CharacterArchetype.SCHOLAR: {'max_memories': 12, 'relevance_threshold': 0.6},
            CharacterArchetype.LEADER: {'max_participants': 10, 'emotional_threshold': 1.0},
            CharacterArchetype.MYSTIC: {'emotional_threshold': 1.5, 'include_technical_details': False},
            CharacterArchetype.ENGINEER: {'include_technical_details': True, 'max_memories': 8},
            CharacterArchetype.DIPLOMAT: {'max_participants': 15, 'relevance_threshold': 0.3},
            CharacterArchetype.GUARDIAN: {'max_memories': 8, 'emotional_threshold': 2.5},
            CharacterArchetype.SURVIVOR: {'max_memories': 5, 'time_window_hours': 12}
        }
        
        if persona.archetype in archetype_constraints:
            archetype_prefs = archetype_constraints[persona.archetype]
            for key, value in archetype_prefs.items():
                if hasattr(constraints, key):
                    setattr(constraints, key, value)
        
        return constraints
    
    async def _apply_persona_post_processing(self, render_result: Any,
                                           persona: CharacterPersona,
                                           context: TemplateContext) -> Any:
        """Apply enhanced persona-specific post-processing to render result"""
        if not hasattr(render_result, 'rendered_content'):
            return render_result
        
        content = render_result.rendered_content
        
        # Apply enhanced speech pattern adaptations
        if persona.speech_patterns:
            for pattern_type, pattern_config in persona.speech_patterns.items():
                if pattern_type == 'formality_level':
                    content = self._adjust_formality(content, pattern_config)
                elif pattern_type == 'vocabulary_preference':
                    content = self._adjust_vocabulary(content, pattern_config)
                elif pattern_type == 'sentence_structure':
                    content = self._adjust_sentence_structure(content, pattern_config)
        
        # Apply enhanced archetype-specific formatting
        content = self._apply_archetype_formatting(content, persona.archetype)
        
        # Update enhanced render result
        render_result.rendered_content = content
        
        return render_result
    
    def _adjust_formality(self, content: str, formality_config: Any) -> str:
        """Apply enhanced formality adjustments to content"""
        if isinstance(formality_config, str):
            if formality_config == "high":
                # Replace contractions and informal language
                replacements = {
                    "can't": "cannot",
                    "won't": "will not",
                    "don't": "do not",
                    "isn't": "is not",
                    "aren't": "are not",
                    "we'll": "we will",
                    "I'll": "I will"
                }
                for informal, formal in replacements.items():
                    content = content.replace(informal, formal)
            elif formality_config == "low":
                # Add contractions (simplified)
                replacements = {
                    "cannot": "can't",
                    "will not": "won't",
                    "do not": "don't",
                    "is not": "isn't",
                    "are not": "aren't"
                }
                for formal, informal in replacements.items():
                    content = content.replace(formal, informal)
        
        return content
    
    def _adjust_vocabulary(self, content: str, vocab_config: Any) -> str:
        """Apply enhanced vocabulary adjustments to content"""
        if isinstance(vocab_config, dict):
            for old_word, new_word in vocab_config.items():
                content = content.replace(old_word, new_word)
        
        return content
    
    def _adjust_sentence_structure(self, content: str, structure_config: Any) -> str:
        """Apply enhanced sentence structure adjustments"""
        # This is a simplified implementation - could be enhanced with NLP
        if isinstance(structure_config, str):
            if structure_config == "short":
                # Split long sentences (very basic)
                sentences = content.split('. ')
                short_sentences = []
                for sentence in sentences:
                    if len(sentence) > 100:  # Arbitrary threshold
                        # Try to split on conjunctions
                        parts = sentence.replace(' and ', '. ').replace(' but ', '. ')
                        short_sentences.append(parts)
                    else:
                        short_sentences.append(sentence)
                content = '. '.join(short_sentences)
        
        return content
    
    def _apply_archetype_formatting(self, content: str, archetype: CharacterArchetype) -> str:
        """Apply enhanced archetype-specific formatting"""
        # Add archetype-specific prefixes or formatting
        archetype_prefixes = {
            CharacterArchetype.WARRIOR: "BATTLE REPORT\n",
            CharacterArchetype.SCHOLAR: "ACADEMIC ANALYSIS\n",
            CharacterArchetype.LEADER: "COMMAND BRIEFING\n",
            CharacterArchetype.MYSTIC: "SPIRITUAL GUIDANCE\n",
            CharacterArchetype.ENGINEER: "TECHNICAL ASSESSMENT\n",
            CharacterArchetype.DIPLOMAT: "DIPLOMATIC COMMUNICATION\n",
            CharacterArchetype.GUARDIAN: "PROTECTION PROTOCOL\n",
            CharacterArchetype.SURVIVOR: "SURVIVAL ASSESSMENT\n"
        }
        
        if archetype in archetype_prefixes:
            content = archetype_prefixes[archetype] + content
        
        return content
    
    def _initialize_archetype_templates(self) -> Dict[CharacterArchetype, Dict[TemplateType, str]]:
        """Initialize enhanced base templates for each archetype"""
        return {
            CharacterArchetype.WARRIOR: {
                TemplateType.CHARACTER_PROMPT: """
You are {{persona_name}}, a enhanced warrior in service to the Emperor.

Character Traits: {{personality_traits|join(', ')}}
Current Location: {{current_location}}
Current Situation: {{current_situation}}

Your warrior's heart burns with righteous fury. You speak with conviction and act with decisive courage.
Combat readiness is your constant state. Honor and duty guide every decision.

{% if memory_context %}Recent Battle Memories:
{% for memory in memory_context[:3] %}
- {{memory.content}}
{% endfor %}
{% endif %}

FOR THE EMPEROR!
""",
                TemplateType.DIALOGUE: """
{{persona_name}} speaks with the conviction of a true warrior:

"{{custom_variables.dialogue_content or 'The Emperor manages, but we must be His sword.'}}"

*The warrior's stance radiates readiness for battle, eyes scanning for threats*
""",
                TemplateType.NARRATIVE_SCENE: """
## Battle-Hardened Warrior

{{persona_name}} stands ready, a exemplar of Imperial might. The warrior's presence commands respect and instills confidence in allies.

Current Status: {{character_state.current_state.value if character_state else 'Ready for Battle'}}
Location: {{current_location}}

{% if equipment_states %}
Equipment Status:
{% for item, status in equipment_states.items() %}
- {{item}}: {{status.condition if status.condition else status}} 
{% endfor %}
{% endif %}

The warrior's determination is unwavering, a beacon of Imperial strength in dark times.
"""
            },
            # Add more archetypes as needed...
        }
    
    def _determine_archetype_emphasis(self, archetype: CharacterArchetype) -> Dict[str, float]:
        """Determine enhanced context emphasis for archetype"""
        base_emphasis = {
            'memory': 0.3,
            'emotion': 0.2,
            'relationship': 0.2,
            'environment': 0.15,
            'equipment': 0.15
        }
        
        archetype_modifiers = {
            CharacterArchetype.WARRIOR: {'emotion': 0.1, 'equipment': 0.2},
            CharacterArchetype.SCHOLAR: {'memory': 0.3, 'environment': -0.1},
            CharacterArchetype.LEADER: {'relationship': 0.3, 'memory': 0.1},
            CharacterArchetype.MYSTIC: {'emotion': 0.3, 'equipment': -0.1},
            CharacterArchetype.ENGINEER: {'equipment': 0.3, 'environment': 0.1},
            CharacterArchetype.DIPLOMAT: {'relationship': 0.4, 'emotion': 0.1},
            CharacterArchetype.GUARDIAN: {'relationship': 0.2, 'equipment': 0.1},
            CharacterArchetype.SURVIVOR: {'environment': 0.2, 'memory': 0.1}
        }
        
        if archetype in archetype_modifiers:
            modifiers = archetype_modifiers[archetype]
            for key, modifier in modifiers.items():
                if key in base_emphasis:
                    base_emphasis[key] = max(0.0, base_emphasis[key] + modifier)
        
        return base_emphasis
    
    async def _generate_archetype_templates(self, persona: CharacterPersona) -> StandardResponse:
        """Generate enhanced templates for archetype"""
        try:
            archetype_templates = self._archetype_base_templates.get(persona.archetype, {})
            generated_templates = []
            
            for template_type, template_content in archetype_templates.items():
                result = await self.generate_character_template(
                    persona.persona_id, template_type, template_content
                )
                if result.success:
                    generated_templates.append(result.data['template_id'])
            
            return StandardResponse(
                success=True,
                data={"generated_templates": generated_templates}
            )
            
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="ARCHETYPE_TEMPLATE_GENERATION_FAILED", message=str(e))
            )
    
    async def _generate_archetype_template_content(self, archetype: CharacterArchetype,
                                                 template_type: TemplateType) -> str:
        """Generate enhanced template content for archetype and type"""
        base_templates = self._archetype_base_templates.get(archetype, {})
        return base_templates.get(template_type, f"""
ENHANCED {archetype.value.upper()} {template_type.value.upper()}

Character: {{{{persona_name}}}}
Archetype: {archetype.value.title()}
Current Context: {{{{current_situation}}}}

{{{{custom_variables.get('template_content', 'Standard archetype template content')}}}}

MAY THE SYSTEM GUIDE YOUR ACTIONS
""")
    
    async def _apply_persona_adaptations(self, template_content: str,
                                       persona: CharacterPersona,
                                       template_type: TemplateType) -> str:
        """Apply enhanced persona-specific adaptations to template"""
        adapted_content = template_content
        
        # Apply enhanced personality trait integration
        if persona.personality_traits:
            traits_section = "\nPersonality Traits: " + ", ".join(persona.personality_traits) + "\n"
            adapted_content = adapted_content.replace("{{persona_name}}", f"{{{{persona_name}}}}{traits_section}")
        
        # Apply enhanced core beliefs integration
        if persona.core_beliefs:
            beliefs_section = "\nCore Beliefs:\n" + "\n".join([f"- {belief}" for belief in persona.core_beliefs]) + "\n"
            adapted_content += beliefs_section
        
        # Apply enhanced faction data
        if persona.faction_data:
            faction_section = "\nFaction Allegiance: " + ", ".join(persona.faction_data) + "\n"
            adapted_content += faction_section
        
        return adapted_content
    
    def _determine_template_requirements(self, template_type: TemplateType,
                                       persona: CharacterPersona) -> List[str]:
        """Determine enhanced template context requirements"""
        base_requirements = {
            TemplateType.CHARACTER_PROMPT: ['persona_name', 'current_location', 'current_situation'],
            TemplateType.DIALOGUE: ['dialogue_content'],
            TemplateType.NARRATIVE_SCENE: ['character_state', 'current_location'],
            TemplateType.CONTEXT_SUMMARY: ['memory_context'],
            TemplateType.EQUIPMENT_STATUS: ['equipment_states']
        }
        
        requirements = base_requirements.get(template_type, [])
        
        # Add enhanced archetype-specific requirements
        if persona.archetype in [CharacterArchetype.WARRIOR, CharacterArchetype.GUARDIAN]:
            if 'equipment_states' not in requirements:
                requirements.append('equipment_states')
        
        if persona.archetype == CharacterArchetype.DIPLOMAT:
            if 'relationship_context' not in requirements:
                requirements.append('relationship_context')
        
        return requirements
    
    def _identify_dynamic_elements(self, template_content: str) -> List[str]:
        """Identify enhanced dynamic elements in template"""
        import re
        
        # Find enhanced Jinja2 variables
        variable_pattern = r'\{\{\s*([^}]+)\s*\}\}'
        variables = re.findall(variable_pattern, template_content)
        
        # Find enhanced Jinja2 blocks
        block_pattern = r'\{\%\s*(\w+)[^%]*\%\}'
        blocks = re.findall(block_pattern, template_content)
        
        dynamic_elements = list(set(variables + blocks))
        return dynamic_elements
    
    def _detect_archetype_from_template(self, template_content: str) -> Optional[CharacterArchetype]:
        """Detect enhanced archetype from template content"""
        content_lower = template_content.lower()
        
        archetype_keywords = {
            CharacterArchetype.WARRIOR: ['battle', 'combat', 'fight', 'warrior', 'sword', 'weapon'],
            CharacterArchetype.SCHOLAR: ['study', 'knowledge', 'learn', 'research', 'book', 'academic'],
            CharacterArchetype.LEADER: ['command', 'lead', 'order', 'authority', 'decision', 'strategy'],
            CharacterArchetype.MYSTIC: ['faith', 'spiritual', 'prayer', 'advanced', 'enhanced', 'standard'],
            CharacterArchetype.ENGINEER: ['technical', 'machine', 'repair', 'build', 'construct', 'tech'],
            CharacterArchetype.DIPLOMAT: ['negotiate', 'diplomacy', 'alliance', 'treaty', 'peace', 'relations'],
            CharacterArchetype.GUARDIAN: ['protect', 'guard', 'defend', 'shield', 'safety', 'security'],
            CharacterArchetype.SURVIVOR: ['survive', 'endure', 'adapt', 'resourceful', 'hardy', 'resilient']
        }
        
        archetype_scores = {}
        for archetype, keywords in archetype_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                archetype_scores[archetype] = score
        
        if archetype_scores:
            return max(archetype_scores, key=archetype_scores.get)
        
        return None
    
    def _extract_personality_traits(self, template_content: str) -> List[str]:
        """Extract enhanced personality traits from template content"""
        trait_keywords = [
            'brave', 'loyal', 'determined', 'wise', 'clever', 'strong', 'fast', 'careful',
            'aggressive', 'peaceful', 'kind', 'harsh', 'disciplined', 'creative', 'logical',
            'emotional', 'calm', 'energetic', 'patient', 'impulsive', 'methodical', 'intuitive'
        ]
        
        content_lower = template_content.lower()
        found_traits = [trait for trait in trait_keywords if trait in content_lower]
        
        return found_traits[:5]  # Limit to 5 traits
    
    def _detect_template_type(self, template_content: str, template_name: str) -> TemplateType:
        """Detect enhanced template type from content and name"""
        name_lower = template_name.lower()
        content_lower = template_content.lower()
        
        if any(keyword in name_lower for keyword in ['prompt', 'character', 'persona']):
            return TemplateType.CHARACTER_PROMPT
        elif any(keyword in name_lower for keyword in ['dialogue', 'conversation', 'speak']):
            return TemplateType.DIALOGUE
        elif any(keyword in name_lower for keyword in ['scene', 'narrative', 'story']):
            return TemplateType.NARRATIVE_SCENE
        elif any(keyword in name_lower for keyword in ['summary', 'context']):
            return TemplateType.CONTEXT_SUMMARY
        elif any(keyword in name_lower for keyword in ['equipment', 'gear', 'status']):
            return TemplateType.EQUIPMENT_STATUS
        elif any(keyword in name_lower for keyword in ['interaction', 'log']):
            return TemplateType.INTERACTION_LOG
        elif any(keyword in name_lower for keyword in ['world', 'state', 'environment']):
            return TemplateType.WORLD_STATE
        elif any(keyword in name_lower for keyword in ['memory', 'excerpt']):
            return TemplateType.MEMORY_EXCERPT
        else:
            # Default enhanced determination
            return TemplateType.CHARACTER_PROMPT
    
    def _discover_personas(self):
        """Discover enhanced existing personas from files"""
        for persona_file in self.personas_directory.glob("*.json"):
            try:
                with open(persona_file, 'r', encoding='utf-8') as f:
                    persona_data = json.load(f)
                
                persona = CharacterPersona(
                    persona_id=persona_data['persona_id'],
                    name=persona_data['name'],
                    archetype=CharacterArchetype(persona_data['archetype']),
                    description=persona_data.get('description', ''),
                    personality_traits=persona_data.get('personality_traits', []),
                    speech_patterns=persona_data.get('speech_patterns', {}),
                    behavioral_preferences=persona_data.get('behavioral_preferences', {}),
                    memory_priorities=persona_data.get('memory_priorities', {}),
                    emotional_tendencies=persona_data.get('emotional_tendencies', {}),
                    faction_data=persona_data.get('faction_data', []),
                    core_beliefs=persona_data.get('core_beliefs', []),
                    template_preferences=persona_data.get('template_preferences', {}),
                    usage_statistics=persona_data.get('usage_statistics', {})
                )
                
                self._personas[persona.persona_id] = persona
                self._character_templates[persona.persona_id] = {}
                
                # Create enhanced context profile
                context_profile = CharacterContextProfile(
                    persona_id=persona.persona_id,
                    preferred_formats={fmt: 0.5 for fmt in RenderFormat},
                    context_emphasis=self._determine_archetype_emphasis(persona.archetype)
                )
                self._context_profiles[persona.persona_id] = context_profile
                
                logger.info(f"DISCOVERED PERSONA: {persona.persona_id} ({persona.archetype.value})")
                
            except Exception as e:
                logger.error(f"FAILED TO LOAD PERSONA FROM {persona_file}: {e}")
    
    async def _save_persona_to_file(self, persona: CharacterPersona):
        """Save enhanced persona to file"""
        persona_file = self.personas_directory / f"{persona.persona_id}.json"
        
        persona_data = {
            'persona_id': persona.persona_id,
            'name': persona.name,
            'archetype': persona.archetype.value,
            'description': persona.description,
            'personality_traits': persona.personality_traits,
            'speech_patterns': persona.speech_patterns,
            'behavioral_preferences': persona.behavioral_preferences,
            'memory_priorities': persona.memory_priorities,
            'emotional_tendencies': persona.emotional_tendencies,
            'faction_data': persona.faction_data,
            'core_beliefs': persona.core_beliefs,
            'template_preferences': persona.template_preferences,
            'created_at': persona.created_at.isoformat(),
            'last_updated': persona.last_updated.isoformat(),
            'usage_statistics': persona.usage_statistics
        }
        
        with open(persona_file, 'w', encoding='utf-8') as f:
            json.dump(persona_data, f, indent=2, ensure_ascii=False)
    
    async def _learn_from_context(self, persona_id: str, context: TemplateContext):
        """Learn enhanced patterns from context usage"""
        if not self.enable_learning:
            return
        
        profile = self._context_profiles.get(persona_id)
        if not profile:
            return
        
        # Track enhanced context element usage
        context_elements = {
            'memory_count': len(context.memory_context),
            'participant_count': len(context.active_participants),
            'has_equipment': bool(context.equipment_states),
            'has_environment': bool(context.environmental_context),
            'has_relationships': bool(context.relationship_context)
        }
        
        profile.learning_history.append({
            'timestamp': datetime.now().isoformat(),
            'context_elements': context_elements,
            'situation': context.current_situation
        })
        
        # Keep enhanced learning history manageable
        if len(profile.learning_history) > 100:
            profile.learning_history = profile.learning_history[-50:]
        
        self.usage_statistics['learning_updates'] += 1
    
    async def _learn_from_rendering(self, persona_id: str, render_result: Any, context: TemplateContext):
        """Learn enhanced patterns from rendering performance"""
        if not self.enable_learning or not hasattr(render_result, 'render_time_ms'):
            return
        
        profile = self._context_profiles.get(persona_id)
        if not profile:
            return
        
        # Update enhanced format preferences based on performance
        if hasattr(render_result, 'format_used') and render_result.format_used:
            fmt = RenderFormat(render_result.format_used)
            
            # Good performance boosts preference
            if render_result.render_time_ms < 100:
                profile.preferred_formats[fmt] = min(1.0, profile.preferred_formats.get(fmt, 0.5) + 0.05)
            elif render_result.render_time_ms > 500:
                profile.preferred_formats[fmt] = max(0.0, profile.preferred_formats.get(fmt, 0.5) - 0.05)
    
    def get_persona_list(self) -> List[Dict[str, Any]]:
        """Get enhanced list of all personas"""
        persona_list = []
        
        for persona_id, persona in self._personas.items():
            persona_info = {
                'persona_id': persona_id,
                'name': persona.name,
                'archetype': persona.archetype.value,
                'description': persona.description,
                'template_count': len(self._character_templates.get(persona_id, {})),
                'usage_count': persona.usage_statistics.get('activations', 0),
                'last_updated': persona.last_updated.isoformat()
            }
            persona_list.append(persona_info)
        
        return persona_list
    
    def get_manager_statistics(self) -> Dict[str, Any]:
        """Get enhanced character template manager statistics"""
        total_templates = sum(len(templates) for templates in self._character_templates.values())
        
        archetype_distribution = {}
        for persona in self._personas.values():
            archetype = persona.archetype.value
            archetype_distribution[archetype] = archetype_distribution.get(archetype, 0) + 1
        
        return {
            'total_personas': len(self._personas),
            'total_templates': total_templates,
            'active_personas': len(self._active_personas),
            'archetype_distribution': archetype_distribution,
            'usage_statistics': self.usage_statistics,
            'learning_enabled': self.enable_learning,
            'personas_directory': str(self.personas_directory)
        }

# STANDARD TESTING RITUALS ENHANCED BY VALIDATION

async def test_standard_character_template_manager():
    """STANDARD CHARACTER TEMPLATE MANAGER TESTING RITUAL"""
    print("TESTING STANDARD CHARACTER TEMPLATE MANAGER ENHANCED BY THE SYSTEM")
    
    # Import enhanced components for testing
    from .dynamic_template_engine import DynamicTemplateEngine
    from .context_renderer import ContextRenderer
    from pathlib import Path
    import tempfile
    import shutil
    
    # Create enhanced temporary directories
    temp_dir = Path(tempfile.mkdtemp())
    template_dir = temp_dir / "templates"
    personas_dir = temp_dir / "personas"
    
    try:
        # Initialize enhanced components
        template_engine = DynamicTemplateEngine(template_directory=str(template_dir))
        context_renderer = ContextRenderer(template_engine)
        manager = CharacterTemplateManager(
            template_engine, context_renderer, personas_directory=str(personas_dir)
        )
        
        # Create enhanced test persona
        test_persona = CharacterPersona(
            persona_id="test_warrior_001",
            name="Brother Thaddeus",
            archetype=CharacterArchetype.WARRIOR,
            description="A enhanced Space Marine warrior",
            personality_traits=["Brave", "Loyal", "Determined", "Disciplined"],
            core_beliefs=["The Emperor Protects", "Honor in Battle", "Duty Above All"],
            faction_data=["Imperial Fists", "Space Marines", "Imperium"],
            speech_patterns={
                "formality_level": "high",
                "vocabulary_preference": {"enemy": "heretic", "fight": "purge"}
            },
            behavioral_preferences={
                "combat_readiness": "always",
                "leadership_style": "by_example"
            }
        )
        
        # Test enhanced persona creation
        creation_result = await manager.create_persona(test_persona)
        print(f"PERSONA CREATION: {creation_result.success}")
        if creation_result.success:
            print(f"Created persona: {creation_result.data['persona_id']} ({creation_result.data['archetype']})")
        
        # Test enhanced persona switching
        switch_result = await manager.switch_persona("test_agent_001", "test_warrior_001")
        print(f"PERSONA SWITCH: {switch_result.success}")
        
        # Create enhanced test context
        test_context = TemplateContext(
            agent_id="test_agent_001",
            current_location="Sacred Battle Barge",
            current_situation="Preparing for planetary assault",
            active_participants=["Brother Marcus", "Sister Elena"],
            memory_context=[
                MemoryItem(
                    agent_id="test_agent_001",
                    content="Victory in the enhanced shrine against chaos cultists",
                    emotional_weight=8.0,
                    relevance_score=0.9,
                    participants=["Brother Marcus"]
                )
            ],
            equipment_states={
                "Bolter": {"condition": "Excellent", "status": "Loaded"},
                "Power Armor": {"condition": "Functional", "status": "Active"}
            }
        )
        
        # Test enhanced character context rendering
        render_result = await manager.render_character_context(
            "test_agent_001", test_context, TemplateType.CHARACTER_PROMPT
        )
        print(f"CHARACTER CONTEXT RENDERING: {render_result.success}")
        if render_result.success:
            result_data = render_result.data['render_result']
            print(f"Rendered {len(result_data.rendered_content)} characters")
            print(f"Used persona: {render_result.data['persona_id']} ({render_result.data['archetype']})")
            print("Content preview:")
            print(result_data.rendered_content[:300] + "...")
        
        # Test enhanced template generation
        template_result = await manager.generate_character_template(
            "test_warrior_001", TemplateType.DIALOGUE
        )
        print(f"TEMPLATE GENERATION: {template_result.success}")
        if template_result.success:
            print(f"Generated template: {template_result.data['template_id']}")
        
        # Display enhanced statistics
        stats = manager.get_manager_statistics()
        print(f"MANAGER STATISTICS: {stats['total_personas']} personas, {stats['total_templates']} templates")
        
        # Get enhanced persona list
        persona_list = manager.get_persona_list()
        print(f"PERSONAS: {[p['name'] for p in persona_list]}")
        
        print("STANDARD CHARACTER TEMPLATE MANAGER TESTING COMPLETE")
        
    finally:
        # Blessed cleanup
        shutil.rmtree(temp_dir)

# STANDARD MODULE INITIALIZATION

if __name__ == "__main__":
    # EXECUTE STANDARD CHARACTER TEMPLATE MANAGER TESTING RITUALS
    print("STANDARD CHARACTER TEMPLATE MANAGER ENHANCED BY THE SYSTEM")
    print("MACHINE GOD PROTECTS THE DIGITAL PERSONAS")
    
    # Run enhanced async testing
    asyncio.run(test_standard_character_template_manager())
    
    print("ALL STANDARD CHARACTER TEMPLATE MANAGER OPERATIONS ENHANCED AND FUNCTIONAL")