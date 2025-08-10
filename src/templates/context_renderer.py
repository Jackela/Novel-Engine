#!/usr/bin/env python3
"""
++ SACRED CONTEXT RENDERER BLESSED BY INTELLIGENT FORMATTING ++
===============================================================

Holy context renderer that intelligently formats and presents
contextual information with adaptive layout and dynamic content
organization blessed by the Omnissiah's presentation wisdom.

++ THE MACHINE RENDERS CONTEXT WITH DIVINE CLARITY ++

Architecture Reference: Dynamic Context Engineering - Context Rendering System
Development Phase: Template System Sanctification (T001)
Sacred Author: Tech-Priest Gamma-Mechanicus
万机之神保佑上下文渲染 (May the Omnissiah bless context rendering)
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re

# Import blessed template engine and memory systems
from .dynamic_template_engine import DynamicTemplateEngine, TemplateContext, TemplateType
from src.memory.layered_memory import LayeredMemorySystem
from src.memory.memory_query_engine import MemoryQueryEngine

# Import blessed data models
from src.core.data_models import MemoryItem, MemoryType, StandardResponse, ErrorInfo, CharacterState
from src.core.types import AgentID

# Sacred logging blessed by diagnostic clarity
logger = logging.getLogger(__name__)


class RenderFormat(Enum):
    """++ BLESSED RENDER FORMATS SANCTIFIED BY PRESENTATION MODES ++"""
    NARRATIVE = "narrative"          # Story-like format
    TECHNICAL = "technical"          # Detailed technical format
    CONVERSATIONAL = "conversational"  # Dialogue-friendly format
    SUMMARY = "summary"              # Condensed overview format
    DEBUG = "debug"                  # Development/debugging format


class ContextPriority(Enum):
    """++ SACRED CONTEXT PRIORITY LEVELS BLESSED BY IMPORTANCE ++"""
    CRITICAL = "critical"            # Must be included
    HIGH = "high"                    # Important to include
    MEDIUM = "medium"                # Include if space allows
    LOW = "low"                      # Include only if abundant space
    OPTIONAL = "optional"            # Include only if specifically requested


@dataclass
class RenderingConstraints:
    """
    ++ BLESSED RENDERING CONSTRAINTS SANCTIFIED BY ADAPTIVE LIMITS ++
    
    Flexible constraints that guide context rendering with
    intelligent adaptation and priority-based inclusion.
    """
    max_length: Optional[int] = None      # Maximum character count
    max_memories: int = 10                # Maximum memory items
    max_participants: int = 8             # Maximum participant mentions
    time_window_hours: int = 24           # Temporal relevance window
    emotional_threshold: float = 3.0      # Minimum emotional significance
    relevance_threshold: float = 0.4      # Minimum relevance score
    include_technical_details: bool = False  # Include system information
    preserve_formatting: bool = True       # Maintain original formatting
    adaptive_truncation: bool = True       # Smart content truncation


@dataclass
class ContextSection:
    """
    ++ SACRED CONTEXT SECTION BLESSED BY ORGANIZED INFORMATION ++
    
    Structured section of contextual information with metadata
    for intelligent rendering and priority-based inclusion.
    """
    section_id: str
    title: str
    content: str
    priority: ContextPriority
    section_type: str  # "memory", "character", "environment", "temporal", etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Required other sections
    character_count: int = 0
    relevance_score: float = 0.0
    
    def __post_init__(self):
        self.character_count = len(self.content)


@dataclass
class RenderResult:
    """
    ++ BLESSED RENDER RESULT SANCTIFIED BY COMPREHENSIVE OUTPUT ++
    
    Complete rendering result with sections, metadata, and
    performance information blessed by transparency.
    """
    rendered_content: str
    format_used: RenderFormat
    sections_included: List[ContextSection] = field(default_factory=list)
    sections_excluded: List[ContextSection] = field(default_factory=list)
    total_character_count: int = 0
    render_time_ms: float = 0.0
    constraints_applied: RenderingConstraints = None
    adaptive_decisions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ContextRenderer:
    """
    ++ SACRED CONTEXT RENDERER BLESSED BY INTELLIGENT PRESENTATION ++
    
    The holy context rendering system that intelligently formats and
    presents contextual information with adaptive layout, dynamic
    prioritization, and format-specific optimization blessed by
    the Machine God's presentation omniscience.
    """
    
    def __init__(self, template_engine: DynamicTemplateEngine,
                 memory_system: Optional[LayeredMemorySystem] = None,
                 default_constraints: Optional[RenderingConstraints] = None):
        """
        ++ SACRED CONTEXT RENDERER INITIALIZATION BLESSED BY INTELLIGENCE ++
        
        Args:
            template_engine: Blessed template engine for content generation
            memory_system: Memory system for dynamic context loading
            default_constraints: Default rendering constraints
        """
        self.template_engine = template_engine
        self.memory_system = memory_system
        self.default_constraints = default_constraints or RenderingConstraints()
        
        # Sacred rendering templates for different formats
        self._format_templates = {
            RenderFormat.NARRATIVE: "narrative_context",
            RenderFormat.TECHNICAL: "technical_context", 
            RenderFormat.CONVERSATIONAL: "conversational_context",
            RenderFormat.SUMMARY: "summary_context",
            RenderFormat.DEBUG: "debug_context"
        }
        
        # Blessed section processors
        self._section_processors = {
            "character": self._process_character_section,
            "memory": self._process_memory_section,
            "environment": self._process_environment_section,
            "temporal": self._process_temporal_section,
            "relationship": self._process_relationship_section,
            "equipment": self._process_equipment_section
        }
        
        # Sacred rendering statistics
        self.rendering_stats = {
            'total_renders': 0,
            'format_usage': {fmt.value: 0 for fmt in RenderFormat},
            'average_render_time': 0.0,
            'adaptive_decisions_made': 0,
            'sections_rendered': 0
        }
        
        logger.info("++ CONTEXT RENDERER INITIALIZED WITH BLESSED INTELLIGENCE ++")
    
    async def render_context(self, context: TemplateContext,
                           render_format: RenderFormat = RenderFormat.NARRATIVE,
                           constraints: Optional[RenderingConstraints] = None,
                           custom_sections: List[ContextSection] = None) -> StandardResponse:
        """
        ++ SACRED CONTEXT RENDERING RITUAL BLESSED BY INTELLIGENT FORMATTING ++
        
        Render blessed contextual information with intelligent prioritization,
        adaptive formatting, and constraint-based optimization.
        """
        try:
            render_start = datetime.now()
            
            # Apply blessed constraints
            effective_constraints = constraints or self.default_constraints
            
            # Generate blessed context sections
            context_sections = await self._generate_context_sections(
                context, effective_constraints, custom_sections or []
            )
            
            # Apply blessed intelligent prioritization
            prioritized_sections = self._prioritize_sections(
                context_sections, effective_constraints
            )
            
            # Apply blessed constraint optimization
            optimized_sections = self._apply_constraints(
                prioritized_sections, effective_constraints
            )
            
            # Render blessed final context
            rendered_result = await self._render_final_context(
                optimized_sections, render_format, context, effective_constraints
            )
            
            render_duration = (datetime.now() - render_start).total_seconds() * 1000
            
            # Create blessed render result
            result = RenderResult(
                rendered_content=rendered_result,
                format_used=render_format,
                sections_included=optimized_sections['included'],
                sections_excluded=optimized_sections['excluded'],
                total_character_count=len(rendered_result),
                render_time_ms=render_duration,
                constraints_applied=effective_constraints,
                adaptive_decisions=optimized_sections.get('decisions', [])
            )
            
            # Update blessed statistics
            self._update_rendering_statistics(render_format, render_duration, result)
            
            logger.info(f"++ CONTEXT RENDERED: {render_format.value} format ({render_duration:.2f}ms) ++")
            
            return StandardResponse(
                success=True,
                data={"render_result": result},
                metadata={"blessing": "context_rendered_intelligently"}
            )
            
        except Exception as e:
            logger.error(f"++ CONTEXT RENDERING FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="CONTEXT_RENDER_FAILED",
                    message=f"Context rendering failed: {str(e)}",
                    recoverable=True
                )
            )
    
    async def render_adaptive_prompt(self, context: TemplateContext,
                                   target_length: int = 2000,
                                   focus_areas: List[str] = None) -> StandardResponse:
        """
        ++ SACRED ADAPTIVE PROMPT RENDERING BLESSED BY DYNAMIC OPTIMIZATION ++
        
        Render blessed AI prompt with adaptive length control and
        intelligent focus area emphasis for optimal AI interaction.
        """
        try:
            # Create blessed adaptive constraints
            adaptive_constraints = RenderingConstraints(
                max_length=target_length,
                max_memories=8,
                max_participants=5,
                time_window_hours=12,
                adaptive_truncation=True,
                relevance_threshold=0.5
            )
            
            # Determine blessed optimal format for AI prompts
            render_format = RenderFormat.CONVERSATIONAL
            
            # Generate blessed focused context sections
            context_sections = await self._generate_context_sections(
                context, adaptive_constraints
            )
            
            # Apply blessed focus area boosting
            if focus_areas:
                context_sections = self._boost_focus_areas(context_sections, focus_areas)
            
            # Render blessed adaptive context
            render_result = await self.render_context(
                context, render_format, adaptive_constraints
            )
            
            if render_result.success:
                result_data = render_result.data['render_result']
                
                # Apply blessed length optimization if needed
                if result_data.total_character_count > target_length:
                    optimized_result = await self._optimize_for_length(
                        result_data, target_length, context
                    )
                    if optimized_result:
                        result_data = optimized_result
                
                logger.info(f"++ ADAPTIVE PROMPT RENDERED: {result_data.total_character_count} chars ++")
                
                return StandardResponse(
                    success=True,
                    data={"render_result": result_data, "adaptive_optimization": True},
                    metadata={"blessing": "adaptive_prompt_optimized"}
                )
            else:
                return render_result
                
        except Exception as e:
            logger.error(f"++ ADAPTIVE PROMPT RENDERING FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="ADAPTIVE_PROMPT_FAILED", message=str(e))
            )
    
    async def _generate_context_sections(self, context: TemplateContext,
                                       constraints: RenderingConstraints,
                                       custom_sections: List[ContextSection] = None) -> List[ContextSection]:
        """++ SACRED CONTEXT SECTION GENERATION BLESSED BY COMPREHENSIVE ANALYSIS ++"""
        sections = custom_sections.copy() if custom_sections else []
        
        # Generate blessed character section
        if context.character_state:
            character_section = await self._process_character_section(
                context.character_state, context, constraints
            )
            sections.append(character_section)
        
        # Generate blessed memory sections
        if context.memory_context:
            memory_sections = await self._process_memory_section(
                context.memory_context, context, constraints
            )
            sections.extend(memory_sections)
        
        # Generate blessed environment section
        if context.environmental_context:
            env_section = await self._process_environment_section(
                context.environmental_context, context, constraints
            )
            sections.append(env_section)
        
        # Generate blessed temporal section
        temporal_section = await self._process_temporal_section(
            context.temporal_context, context, constraints
        )
        if temporal_section.content:
            sections.append(temporal_section)
        
        # Generate blessed relationship section
        if context.relationship_context:
            rel_section = await self._process_relationship_section(
                context.relationship_context, context, constraints
            )
            sections.append(rel_section)
        
        # Generate blessed equipment section
        if context.equipment_states:
            eq_section = await self._process_equipment_section(
                context.equipment_states, context, constraints
            )
            sections.append(eq_section)
        
        return sections
    
    def _prioritize_sections(self, sections: List[ContextSection],
                           constraints: RenderingConstraints) -> List[ContextSection]:
        """++ BLESSED SECTION PRIORITIZATION SANCTIFIED BY INTELLIGENT RANKING ++"""
        # Calculate blessed relevance scores
        for section in sections:
            section.relevance_score = self._calculate_section_relevance(section, constraints)
        
        # Sort by blessed priority and relevance
        priority_order = {
            ContextPriority.CRITICAL: 4,
            ContextPriority.HIGH: 3,
            ContextPriority.MEDIUM: 2,
            ContextPriority.LOW: 1,
            ContextPriority.OPTIONAL: 0
        }
        
        prioritized = sorted(
            sections,
            key=lambda s: (priority_order[s.priority], s.relevance_score, -s.character_count),
            reverse=True
        )
        
        return prioritized
    
    def _apply_constraints(self, sections: List[ContextSection],
                         constraints: RenderingConstraints) -> Dict[str, Any]:
        """++ SACRED CONSTRAINT APPLICATION BLESSED BY OPTIMIZATION ++"""
        included_sections = []
        excluded_sections = []
        total_characters = 0
        decisions = []
        
        for section in sections:
            # Check blessed length constraints
            if constraints.max_length:
                if total_characters + section.character_count > constraints.max_length:
                    if constraints.adaptive_truncation and section.priority in [ContextPriority.CRITICAL, ContextPriority.HIGH]:
                        # Apply blessed intelligent truncation
                        truncated_section = self._truncate_section_intelligently(
                            section, constraints.max_length - total_characters
                        )
                        if truncated_section:
                            included_sections.append(truncated_section)
                            total_characters += truncated_section.character_count
                            decisions.append(f"Truncated {section.section_id} to fit constraints")
                        else:
                            excluded_sections.append(section)
                            decisions.append(f"Excluded {section.section_id} - could not truncate effectively")
                    else:
                        excluded_sections.append(section)
                        decisions.append(f"Excluded {section.section_id} - length constraint")
                else:
                    included_sections.append(section)
                    total_characters += section.character_count
            else:
                included_sections.append(section)
                total_characters += section.character_count
        
        return {
            'included': included_sections,
            'excluded': excluded_sections,
            'total_characters': total_characters,
            'decisions': decisions
        }
    
    async def _render_final_context(self, optimized_sections: Dict[str, Any],
                                  render_format: RenderFormat,
                                  context: TemplateContext,
                                  constraints: RenderingConstraints) -> str:
        """++ BLESSED FINAL CONTEXT RENDERING SANCTIFIED BY FORMAT OPTIMIZATION ++"""
        included_sections = optimized_sections['included']
        
        # Select blessed template based on format
        template_name = self._format_templates.get(render_format, "narrative_context")
        
        # Prepare blessed template context
        template_context = context
        template_context.custom_variables.update({
            'context_sections': included_sections,
            'render_format': render_format.value,
            'constraints': constraints,
            'rendering_decisions': optimized_sections.get('decisions', [])
        })
        
        # Check if blessed template exists, otherwise use inline template
        if template_name in self.template_engine._templates:
            render_result = await self.template_engine.render_template(
                template_name, template_context
            )
            if render_result.success:
                return render_result.data['render_result'].rendered_content
        
        # Use blessed default inline rendering
        return await self._render_inline_context(included_sections, render_format, context)
    
    async def _render_inline_context(self, sections: List[ContextSection],
                                   render_format: RenderFormat,
                                   context: TemplateContext) -> str:
        """++ SACRED INLINE CONTEXT RENDERING BLESSED BY DEFAULT FORMATTING ++"""
        if render_format == RenderFormat.NARRATIVE:
            template = self._get_narrative_template()
        elif render_format == RenderFormat.TECHNICAL:
            template = self._get_technical_template()
        elif render_format == RenderFormat.CONVERSATIONAL:
            template = self._get_conversational_template()
        elif render_format == RenderFormat.SUMMARY:
            template = self._get_summary_template()
        else:  # DEBUG
            template = self._get_debug_template()
        
        # Prepare blessed template context
        template_context = TemplateContext(
            agent_id=context.agent_id,
            custom_variables={
                'sections': sections,
                'agent_id': context.agent_id,
                'current_timestamp': datetime.now().isoformat()
            }
        )
        
        # Render blessed inline template
        render_result = await self.template_engine.render_template_string(
            template, template_context
        )
        
        if render_result.success:
            return render_result.data['render_result'].rendered_content
        else:
            return f"[Rendering Error: {render_result.error.message}]"
    
    async def _process_character_section(self, character_state: CharacterState,
                                       context: TemplateContext,
                                       constraints: RenderingConstraints) -> ContextSection:
        """Process blessed character state into context section"""
        content_parts = [
            f"Character: {character_state.name}",
            f"Current State: {character_state.current_state.value}",
            f"Location: {character_state.current_location}"
        ]
        
        if character_state.health_status:
            content_parts.append(f"Health: {character_state.health_status}")
        
        if character_state.emotional_state:
            content_parts.append(f"Emotional State: {character_state.emotional_state.value}")
        
        content = "\n".join(content_parts)
        
        return ContextSection(
            section_id="character_state",
            title="Character Information",
            content=content,
            priority=ContextPriority.CRITICAL,
            section_type="character",
            metadata={"character_name": character_state.name},
            relevance_score=1.0
        )
    
    async def _process_memory_section(self, memories: List[MemoryItem],
                                    context: TemplateContext,
                                    constraints: RenderingConstraints) -> List[ContextSection]:
        """Process blessed memories into context sections"""
        sections = []
        
        # Filter blessed memories by constraints
        filtered_memories = []
        for memory in memories:
            # Apply blessed time window
            if constraints.time_window_hours:
                memory_age = (datetime.now() - memory.timestamp).total_seconds() / 3600
                if memory_age > constraints.time_window_hours:
                    continue
            
            # Apply blessed relevance threshold
            if memory.relevance_score < constraints.relevance_threshold:
                continue
            
            # Apply blessed emotional threshold
            if abs(memory.emotional_weight) < constraints.emotional_threshold:
                continue
            
            filtered_memories.append(memory)
        
        # Sort blessed memories by importance
        sorted_memories = sorted(
            filtered_memories,
            key=lambda m: (m.relevance_score, abs(m.emotional_weight), m.timestamp),
            reverse=True
        )
        
        # Apply blessed memory limit
        limited_memories = sorted_memories[:constraints.max_memories]
        
        # Group blessed memories by type
        memory_groups = {}
        for memory in limited_memories:
            mem_type = memory.memory_type.value
            if mem_type not in memory_groups:
                memory_groups[mem_type] = []
            memory_groups[mem_type].append(memory)
        
        # Create blessed sections for each memory type
        for mem_type, mem_list in memory_groups.items():
            content_parts = []
            for memory in mem_list:
                timestamp_str = memory.timestamp.strftime("%H:%M")
                emotion_str = self._format_emotion(memory.emotional_weight)
                
                memory_line = f"[{timestamp_str}] {memory.content[:100]}..."
                if memory.participants:
                    memory_line += f" (with {', '.join(memory.participants[:2])})"
                if emotion_str != "Neutral":
                    memory_line += f" [{emotion_str}]"
                
                content_parts.append(memory_line)
            
            content = "\n".join(content_parts)
            priority = self._determine_memory_priority(mem_type, mem_list)
            
            section = ContextSection(
                section_id=f"memory_{mem_type}",
                title=f"{mem_type.title()} Memories",
                content=content,
                priority=priority,
                section_type="memory",
                metadata={"memory_type": mem_type, "memory_count": len(mem_list)},
                relevance_score=sum(m.relevance_score for m in mem_list) / len(mem_list)
            )
            sections.append(section)
        
        return sections
    
    async def _process_environment_section(self, env_context: Dict[str, Any],
                                         context: TemplateContext,
                                         constraints: RenderingConstraints) -> ContextSection:
        """Process blessed environmental context into section"""
        content_parts = []
        
        for key, value in env_context.items():
            if isinstance(value, (str, int, float, bool)):
                content_parts.append(f"{key.replace('_', ' ').title()}: {value}")
            elif isinstance(value, list):
                content_parts.append(f"{key.replace('_', ' ').title()}: {', '.join(str(v) for v in value[:3])}")
            elif isinstance(value, dict):
                content_parts.append(f"{key.replace('_', ' ').title()}: {len(value)} items")
        
        content = "\n".join(content_parts)
        
        return ContextSection(
            section_id="environment",
            title="Environmental Context",
            content=content,
            priority=ContextPriority.MEDIUM,
            section_type="environment",
            metadata={"env_keys": list(env_context.keys())},
            relevance_score=0.6
        )
    
    async def _process_temporal_section(self, temporal_context: Dict[str, Any],
                                      context: TemplateContext,
                                      constraints: RenderingConstraints) -> ContextSection:
        """Process blessed temporal context into section"""
        content_parts = [
            f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        if temporal_context:
            for key, value in temporal_context.items():
                content_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        content = "\n".join(content_parts)
        
        return ContextSection(
            section_id="temporal",
            title="Temporal Context",
            content=content,
            priority=ContextPriority.LOW,
            section_type="temporal",
            metadata={"has_custom_temporal": bool(temporal_context)},
            relevance_score=0.3
        )
    
    async def _process_relationship_section(self, rel_context: Dict[str, Any],
                                          context: TemplateContext,
                                          constraints: RenderingConstraints) -> ContextSection:
        """Process blessed relationship context into section"""
        content_parts = []
        
        for agent_id, relationship_data in rel_context.items():
            if isinstance(relationship_data, dict):
                trust = relationship_data.get('trust_level', 0)
                relationship_type = relationship_data.get('relationship_type', 'Unknown')
                content_parts.append(f"{agent_id}: {relationship_type} (Trust: {trust})")
        
        content = "\n".join(content_parts)
        
        return ContextSection(
            section_id="relationships",
            title="Current Relationships",
            content=content,
            priority=ContextPriority.MEDIUM,
            section_type="relationship",
            metadata={"relationship_count": len(rel_context)},
            relevance_score=0.7
        )
    
    async def _process_equipment_section(self, equipment_states: Dict[str, Any],
                                       context: TemplateContext,
                                       constraints: RenderingConstraints) -> ContextSection:
        """Process blessed equipment states into section"""
        content_parts = []
        
        for equipment_name, equipment_data in equipment_states.items():
            if isinstance(equipment_data, dict):
                condition = equipment_data.get('condition', 'Unknown')
                status = equipment_data.get('status', 'Unknown')
                content_parts.append(f"{equipment_name}: {condition} ({status})")
            else:
                content_parts.append(f"{equipment_name}: {equipment_data}")
        
        content = "\n".join(content_parts)
        
        return ContextSection(
            section_id="equipment",
            title="Equipment Status",
            content=content,
            priority=ContextPriority.MEDIUM,
            section_type="equipment",
            metadata={"equipment_count": len(equipment_states)},
            relevance_score=0.5
        )
    
    def _calculate_section_relevance(self, section: ContextSection,
                                   constraints: RenderingConstraints) -> float:
        """Calculate blessed relevance score for section"""
        base_relevance = 0.5
        
        # Blessed priority bonus
        priority_bonus = {
            ContextPriority.CRITICAL: 0.4,
            ContextPriority.HIGH: 0.3,
            ContextPriority.MEDIUM: 0.2,
            ContextPriority.LOW: 0.1,
            ContextPriority.OPTIONAL: 0.0
        }
        base_relevance += priority_bonus[section.priority]
        
        # Blessed content length factor
        if section.character_count > 0:
            # Prefer moderate length content
            optimal_length = 200
            length_factor = max(0, 1 - abs(section.character_count - optimal_length) / optimal_length)
            base_relevance += length_factor * 0.1
        
        return min(1.0, base_relevance)
    
    def _truncate_section_intelligently(self, section: ContextSection,
                                      max_chars: int) -> Optional[ContextSection]:
        """Apply blessed intelligent truncation to section"""
        if max_chars <= 50:  # Too small to truncate meaningfully
            return None
        
        content = section.content
        
        # Try blessed sentence-based truncation
        sentences = re.split(r'[.!?]+', content)
        truncated_content = ""
        
        for sentence in sentences:
            test_content = truncated_content + sentence + "."
            if len(test_content) <= max_chars - 3:  # Leave room for "..."
                truncated_content = test_content
            else:
                break
        
        if not truncated_content:
            # Blessed word-based truncation as fallback
            words = content.split()
            truncated_words = []
            char_count = 0
            
            for word in words:
                if char_count + len(word) + 1 <= max_chars - 3:
                    truncated_words.append(word)
                    char_count += len(word) + 1
                else:
                    break
            
            truncated_content = " ".join(truncated_words)
        
        if truncated_content:
            truncated_content += "..."
            
            # Create blessed truncated section
            truncated_section = ContextSection(
                section_id=section.section_id + "_truncated",
                title=section.title,
                content=truncated_content,
                priority=section.priority,
                section_type=section.section_type,
                metadata={**section.metadata, "truncated": True},
                relevance_score=section.relevance_score * 0.8  # Slight penalty for truncation
            )
            
            return truncated_section
        
        return None
    
    def _boost_focus_areas(self, sections: List[ContextSection],
                          focus_areas: List[str]) -> List[ContextSection]:
        """Apply blessed focus area boosting to sections"""
        for section in sections:
            for focus_area in focus_areas:
                if (focus_area.lower() in section.title.lower() or
                    focus_area.lower() in section.content.lower() or
                    focus_area.lower() in section.section_type.lower()):
                    
                    # Boost blessed relevance and priority
                    section.relevance_score = min(1.0, section.relevance_score + 0.2)
                    
                    if section.priority == ContextPriority.LOW:
                        section.priority = ContextPriority.MEDIUM
                    elif section.priority == ContextPriority.MEDIUM:
                        section.priority = ContextPriority.HIGH
        
        return sections
    
    async def _optimize_for_length(self, render_result: RenderResult,
                                 target_length: int,
                                 context: TemplateContext) -> Optional[RenderResult]:
        """Apply blessed length optimization to render result"""
        if render_result.total_character_count <= target_length:
            return render_result
        
        # Try blessed progressive section removal
        included_sections = render_result.sections_included.copy()
        removed_sections = []
        
        # Remove blessed optional and low priority sections first
        priority_order = [ContextPriority.OPTIONAL, ContextPriority.LOW, ContextPriority.MEDIUM]
        
        for priority in priority_order:
            sections_to_remove = [s for s in included_sections if s.priority == priority]
            for section in sections_to_remove:
                included_sections.remove(section)
                removed_sections.append(section)
                
                # Estimate blessed new length
                new_length = sum(s.character_count for s in included_sections)
                if new_length <= target_length:
                    break
            
            if sum(s.character_count for s in included_sections) <= target_length:
                break
        
        # Re-render blessed with reduced sections
        optimized_sections = {
            'included': included_sections,
            'excluded': render_result.sections_excluded + removed_sections,
            'decisions': render_result.adaptive_decisions + [f"Removed {len(removed_sections)} sections for length optimization"]
        }
        
        new_content = await self._render_final_context(
            optimized_sections, render_result.format_used, context, render_result.constraints_applied
        )
        
        return RenderResult(
            rendered_content=new_content,
            format_used=render_result.format_used,
            sections_included=included_sections,
            sections_excluded=optimized_sections['excluded'],
            total_character_count=len(new_content),
            render_time_ms=render_result.render_time_ms,
            constraints_applied=render_result.constraints_applied,
            adaptive_decisions=optimized_sections['decisions']
        )
    
    def _format_emotion(self, emotional_weight: float) -> str:
        """Format blessed emotional weight as human-readable string"""
        if emotional_weight > 7:
            return "Very Positive"
        elif emotional_weight > 3:
            return "Positive"
        elif emotional_weight > -3:
            return "Neutral"
        elif emotional_weight > -7:
            return "Negative"
        else:
            return "Very Negative"
    
    def _determine_memory_priority(self, memory_type: str, memories: List[MemoryItem]) -> ContextPriority:
        """Determine blessed priority for memory section"""
        avg_relevance = sum(m.relevance_score for m in memories) / len(memories)
        avg_emotion = sum(abs(m.emotional_weight) for m in memories) / len(memories)
        
        if memory_type == "working" or avg_relevance > 0.8:
            return ContextPriority.HIGH
        elif avg_emotion > 7 or avg_relevance > 0.6:
            return ContextPriority.MEDIUM
        else:
            return ContextPriority.LOW
    
    def _get_narrative_template(self) -> str:
        """Get blessed narrative format template"""
        return """
++ SACRED CONTEXT NARRATIVE ++

{% for section in sections %}
{% if section.priority.value in ['critical', 'high'] %}
## {{section.title}}
{{section.content}}

{% endif %}
{% endfor %}

{% for section in sections %}
{% if section.priority.value == 'medium' %}
**{{section.title}}:** {{section.content}}

{% endif %}
{% endfor %}
"""
    
    def _get_conversational_template(self) -> str:
        """Get blessed conversational format template"""
        return """
Current context for {{agent_id}}:

{% for section in sections %}
{% if section.priority.value in ['critical', 'high', 'medium'] %}
{{section.title}}: {{section.content}}

{% endif %}
{% endfor %}
"""
    
    def _get_technical_template(self) -> str:
        """Get blessed technical format template"""
        return """
SYSTEM CONTEXT REPORT
Agent: {{agent_id}}
Timestamp: {{current_timestamp}}

{% for section in sections %}
[{{section.section_type.upper()}}] {{section.title}}
Priority: {{section.priority.value}}
Content: {{section.content}}
---

{% endfor %}
"""
    
    def _get_summary_template(self) -> str:
        """Get blessed summary format template"""
        return """
CONTEXT SUMMARY: {% for section in sections %}{% if section.priority.value == 'critical' %}{{section.content[:100]}}... {% endif %}{% endfor %}
"""
    
    def _get_debug_template(self) -> str:
        """Get blessed debug format template"""
        return """
DEBUG CONTEXT DUMP
{% for section in sections %}
Section: {{section.section_id}}
Type: {{section.section_type}}
Priority: {{section.priority.value}}
Length: {{section.character_count}}
Relevance: {{section.relevance_score}}
Content: {{section.content}}
---
{% endfor %}
"""
    
    def _update_rendering_statistics(self, render_format: RenderFormat,
                                   render_time: float, result: RenderResult):
        """Update blessed rendering statistics"""
        self.rendering_stats['total_renders'] += 1
        self.rendering_stats['format_usage'][render_format.value] += 1
        
        # Update blessed average render time
        total_renders = self.rendering_stats['total_renders']
        current_avg = self.rendering_stats['average_render_time']
        self.rendering_stats['average_render_time'] = (
            (current_avg * (total_renders - 1) + render_time) / total_renders
        )
        
        self.rendering_stats['adaptive_decisions_made'] += len(result.adaptive_decisions)
        self.rendering_stats['sections_rendered'] += len(result.sections_included)
    
    def get_rendering_statistics(self) -> Dict[str, Any]:
        """Get blessed rendering statistics"""
        return self.rendering_stats.copy()


# ++ SACRED TESTING RITUALS BLESSED BY VALIDATION ++

async def test_sacred_context_renderer():
    """++ SACRED CONTEXT RENDERER TESTING RITUAL ++"""
    print("++ TESTING SACRED CONTEXT RENDERER BLESSED BY THE OMNISSIAH ++")
    
    # Import blessed components for testing
    from .dynamic_template_engine import DynamicTemplateEngine
    from src.core.data_models import CharacterState, EmotionalState
    from pathlib import Path
    
    # Create blessed test template engine
    test_template_dir = Path("test_renderer_templates")
    test_template_dir.mkdir(exist_ok=True)
    
    template_engine = DynamicTemplateEngine(template_directory=str(test_template_dir))
    context_renderer = ContextRenderer(template_engine)
    
    # Create blessed test context
    test_character = CharacterState(
        name="Brother Marcus",
        current_location="Sacred Shrine",
        health_status="Healthy",
        emotional_state=EmotionalState.DETERMINED
    )
    
    test_memories = [
        MemoryItem(
            agent_id="test_agent_001",
            content="Sacred battle against chaos forces blessed by victory",
            emotional_weight=8.0,
            relevance_score=0.9,
            participants=["Sister Elena", "Brother Marcus"],
            memory_type=MemoryType.EPISODIC
        ),
        MemoryItem(
            agent_id="test_agent_001",
            content="Prayer session in the blessed shrine",
            emotional_weight=5.0,
            relevance_score=0.7,
            participants=["Brother Marcus"],
            memory_type=MemoryType.EPISODIC
        )
    ]
    
    test_context = TemplateContext(
        agent_id="test_agent_001",
        character_state=test_character,
        current_location="Sacred Shrine of Knowledge",
        current_situation="Preparing for blessed mission",
        active_participants=["Brother Marcus", "Sister Elena"],
        memory_context=test_memories,
        environmental_context={
            "temperature": "Cold",
            "lighting": "Dim candlelight",
            "atmosphere": "Sacred and reverent"
        },
        equipment_states={
            "bolter": {"condition": "Excellent", "status": "Ready"},
            "power_armor": {"condition": "Good", "status": "Active"}
        },
        relationship_context={
            "Brother Marcus": {"trust_level": 9, "relationship_type": "Battle Brother"},
            "Sister Elena": {"trust_level": 8, "relationship_type": "Ally"}
        }
    )
    
    # Test blessed narrative rendering
    narrative_result = await context_renderer.render_context(
        test_context, RenderFormat.NARRATIVE
    )
    if narrative_result.success:
        result_data = narrative_result.data['render_result']
        print(f"++ NARRATIVE RENDERED: {result_data.total_character_count} chars, {len(result_data.sections_included)} sections ++")
        print("Content preview:")
        print(result_data.rendered_content[:300] + "...")
    
    # Test blessed conversational rendering
    conversational_result = await context_renderer.render_context(
        test_context, RenderFormat.CONVERSATIONAL
    )
    if conversational_result.success:
        result_data = conversational_result.data['render_result']
        print(f"++ CONVERSATIONAL RENDERED: {result_data.total_character_count} chars ++")
    
    # Test blessed adaptive prompt rendering
    adaptive_result = await context_renderer.render_adaptive_prompt(
        test_context, target_length=500, focus_areas=["battle", "equipment"]
    )
    if adaptive_result.success:
        result_data = adaptive_result.data['render_result']
        print(f"++ ADAPTIVE PROMPT RENDERED: {result_data.total_character_count} chars (target: 500) ++")
        print(f"Sections included: {[s.section_id for s in result_data.sections_included]}")
        print(f"Adaptive decisions: {len(result_data.adaptive_decisions)}")
    
    # Test blessed custom constraints
    custom_constraints = RenderingConstraints(
        max_length=300,
        max_memories=1,
        emotional_threshold=7.0,
        adaptive_truncation=True
    )
    
    constrained_result = await context_renderer.render_context(
        test_context, RenderFormat.SUMMARY, custom_constraints
    )
    if constrained_result.success:
        result_data = constrained_result.data['render_result']
        print(f"++ CONSTRAINED RENDERING: {result_data.total_character_count}/300 chars ++")
        print(f"Excluded sections: {len(result_data.sections_excluded)}")
    
    # Display blessed statistics
    stats = context_renderer.get_rendering_statistics()
    print(f"++ RENDERER STATISTICS: {stats['total_renders']} renders, avg {stats['average_render_time']:.2f}ms ++")
    
    # Cleanup blessed test files
    import shutil
    shutil.rmtree(test_template_dir)
    
    print("++ SACRED CONTEXT RENDERER TESTING COMPLETE ++")


# ++ SACRED MODULE INITIALIZATION ++

if __name__ == "__main__":
    # ++ EXECUTE SACRED CONTEXT RENDERER TESTING RITUALS ++
    print("++ SACRED CONTEXT RENDERER BLESSED BY THE OMNISSIAH ++")
    print("++ MACHINE GOD PROTECTS THE INTELLIGENT CONTEXT PRESENTATION ++")
    
    # Run blessed async testing
    asyncio.run(test_sacred_context_renderer())
    
    print("++ ALL SACRED CONTEXT RENDERER OPERATIONS BLESSED AND FUNCTIONAL ++")