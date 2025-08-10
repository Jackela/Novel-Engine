#!/usr/bin/env python3
"""
++ SACRED DYNAMIC TEMPLATE ENGINE BLESSED BY CONTEXTUAL GENERATION ++
====================================================================

Holy dynamic template engine that renders context-aware content with
intelligent variable resolution, cross-document references, and
real-time context updates blessed by the Omnissiah's creative wisdom.

++ THE MACHINE GENERATES DYNAMIC CONTENT THROUGH SACRED TEMPLATES ++

Architecture Reference: Dynamic Context Engineering - Dynamic Template Engine
Development Phase: Template System Sanctification (T001)
Sacred Author: Tech-Priest Gamma-Mechanicus
万机之神保佑动态模板 (May the Omnissiah bless dynamic templates)
"""

import logging
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union, Callable, Set
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json

# Import blessed Jinja2 for template processing
try:
    import jinja2
    from jinja2 import Environment, FileSystemLoader, meta, select_autoescape
    from jinja2.exceptions import TemplateError, UndefinedError
except ImportError:
    raise ImportError("Jinja2 is required for template processing. Install with: pip install Jinja2")

# Import blessed memory system
from src.memory.layered_memory import LayeredMemorySystem, MemoryQueryRequest
from src.memory.memory_query_engine import MemoryQueryEngine, QueryContext

# Import blessed data models
from src.core.data_models import MemoryItem, MemoryType, StandardResponse, ErrorInfo, CharacterState
from src.core.types import AgentID, SacredConstants

# Sacred logging blessed by diagnostic clarity
logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """++ BLESSED TEMPLATE TYPES SANCTIFIED BY PURPOSE CLASSIFICATION ++"""
    CHARACTER_PROMPT = "character_prompt"    # AI character prompts
    NARRATIVE_SCENE = "narrative_scene"      # Story scene generation
    DIALOGUE = "dialogue"                    # Character dialogue
    CONTEXT_SUMMARY = "context_summary"     # Context summarization
    MEMORY_EXCERPT = "memory_excerpt"       # Memory representation
    INTERACTION_LOG = "interaction_log"     # Interaction summaries
    WORLD_STATE = "world_state"             # World state descriptions
    EQUIPMENT_STATUS = "equipment_status"   # Equipment descriptions


@dataclass
class TemplateContext:
    """
    ++ SACRED TEMPLATE CONTEXT BLESSED BY COMPREHENSIVE DATA ++
    
    Enhanced context container that provides all necessary data
    for dynamic template rendering with cross-document references.
    """
    agent_id: str
    character_state: Optional[CharacterState] = None
    current_location: str = ""
    current_situation: str = ""
    active_participants: List[str] = field(default_factory=list)
    environmental_context: Dict[str, Any] = field(default_factory=dict)
    memory_context: List[MemoryItem] = field(default_factory=list)
    equipment_states: Dict[str, Any] = field(default_factory=dict)
    relationship_context: Dict[str, Any] = field(default_factory=dict)
    temporal_context: Dict[str, Any] = field(default_factory=dict)
    custom_variables: Dict[str, Any] = field(default_factory=dict)
    reference_documents: Dict[str, str] = field(default_factory=dict)  # file_path -> content
    cross_references: List[str] = field(default_factory=list)  # Referenced template IDs


@dataclass
class TemplateMetadata:
    """
    ++ BLESSED TEMPLATE METADATA SANCTIFIED BY ORGANIZATIONAL WISDOM ++
    
    Comprehensive metadata for template management and optimization
    blessed by systematic organization and performance tracking.
    """
    template_id: str
    template_type: TemplateType
    description: str = ""
    author: str = ""
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    dependencies: List[str] = field(default_factory=list)  # Required context variables
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    usage_count: int = 0
    average_render_time: float = 0.0
    tags: List[str] = field(default_factory=list)


@dataclass
class RenderResult:
    """
    ++ SACRED RENDER RESULT BLESSED BY COMPREHENSIVE OUTPUT ++
    
    Complete rendering result with performance metrics and
    context information blessed by transparency and debugging.
    """
    rendered_content: str
    template_id: str
    context_variables_used: List[str] = field(default_factory=list)
    cross_references_resolved: List[str] = field(default_factory=list)
    render_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    memory_queries_executed: int = 0
    cache_hits: int = 0


class DynamicTemplateEngine:
    """
    ++ SACRED DYNAMIC TEMPLATE ENGINE BLESSED BY CONTEXTUAL INTELLIGENCE ++
    
    The holy template processing system that renders dynamic content with
    intelligent context resolution, cross-document references, and real-time
    memory integration blessed by the Machine God's creative omniscience.
    """
    
    def __init__(self, 
                 template_directory: str = "templates",
                 memory_system: Optional[LayeredMemorySystem] = None,
                 query_engine: Optional[MemoryQueryEngine] = None,
                 enable_auto_reload: bool = True,
                 cache_templates: bool = True):
        """
        ++ SACRED TEMPLATE ENGINE INITIALIZATION BLESSED BY CONFIGURATION ++
        
        Args:
            template_directory: Path to blessed template files
            memory_system: Memory system for dynamic context loading
            query_engine: Query engine for intelligent content retrieval
            enable_auto_reload: Auto-reload templates when files change
            cache_templates: Enable template compilation caching
        """
        self.template_directory = Path(template_directory)
        self.memory_system = memory_system
        self.query_engine = query_engine
        self.enable_auto_reload = enable_auto_reload
        self.cache_templates = cache_templates
        
        # Initialize blessed Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_directory)),
            autoescape=select_autoescape(['html', 'xml']),
            auto_reload=enable_auto_reload,
            cache_size=400 if cache_templates else 0,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Register blessed custom filters and functions
        self._register_custom_functions()
        
        # Sacred template management
        self._templates: Dict[str, TemplateMetadata] = {}
        self._template_cache: Dict[str, RenderResult] = {}
        self._context_cache: Dict[str, TemplateContext] = {}
        
        # Blessed performance tracking
        self.render_statistics = {
            'total_renders': 0,
            'total_render_time': 0.0,
            'cache_hits': 0,
            'memory_queries': 0,
            'cross_references_resolved': 0
        }
        
        # Sacred template discovery
        self._discover_templates()
        
        logger.info(f"++ DYNAMIC TEMPLATE ENGINE INITIALIZED: {len(self._templates)} templates loaded ++")
    
    async def render_template(self, template_id: str, context: TemplateContext,
                            enable_memory_queries: bool = True,
                            enable_cross_references: bool = True) -> StandardResponse:
        """
        ++ SACRED TEMPLATE RENDERING RITUAL BLESSED BY DYNAMIC GENERATION ++
        
        Render blessed template with dynamic context resolution, memory
        integration, and cross-document reference processing.
        """
        try:
            render_start = datetime.now()
            
            # Validate blessed template existence
            if template_id not in self._templates:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="TEMPLATE_NOT_FOUND",
                        message=f"Template '{template_id}' not found in template registry"
                    )
                )
            
            template_metadata = self._templates[template_id]
            
            # Check blessed template cache
            cache_key = self._generate_cache_key(template_id, context)
            if self.cache_templates and cache_key in self._template_cache:
                cached_result = self._template_cache[cache_key]
                self.render_statistics['cache_hits'] += 1
                logger.info(f"++ TEMPLATE CACHE HIT: {template_id} ++")
                return StandardResponse(success=True, data={"render_result": cached_result})
            
            # Prepare blessed enhanced context
            enhanced_context = await self._prepare_enhanced_context(
                context, enable_memory_queries, enable_cross_references
            )
            
            # Load blessed template
            try:
                template = self.jinja_env.get_template(f"{template_id}.j2")
            except jinja2.TemplateNotFound:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="TEMPLATE_FILE_NOT_FOUND",
                        message=f"Template file '{template_id}.j2' not found"
                    )
                )
            
            # Render blessed template
            try:
                rendered_content = template.render(**enhanced_context)
            except UndefinedError as e:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="TEMPLATE_UNDEFINED_VARIABLE",
                        message=f"Undefined variable in template: {str(e)}",
                        sacred_guidance="Check template dependencies and context variables"
                    )
                )
            except TemplateError as e:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="TEMPLATE_RENDER_ERROR",
                        message=f"Template rendering error: {str(e)}"
                    )
                )
            
            # Calculate blessed render metrics
            render_duration = (datetime.now() - render_start).total_seconds() * 1000
            
            # Analyze blessed template usage
            context_variables_used = self._analyze_template_variables(template, enhanced_context)
            
            # Create blessed render result
            render_result = RenderResult(
                rendered_content=rendered_content,
                template_id=template_id,
                context_variables_used=context_variables_used,
                cross_references_resolved=context.cross_references,
                render_time_ms=render_duration,
                memory_queries_executed=getattr(enhanced_context, '_memory_queries_count', 0)
            )
            
            # Update blessed performance metrics
            self._update_performance_metrics(template_metadata, render_duration)
            
            # Cache blessed result
            if self.cache_templates:
                self._template_cache[cache_key] = render_result
                self._cleanup_template_cache()
            
            logger.info(f"++ TEMPLATE RENDERED: {template_id} ({render_duration:.2f}ms) ++")
            
            return StandardResponse(
                success=True,
                data={"render_result": render_result},
                metadata={"blessing": "template_rendered_successfully"}
            )
            
        except Exception as e:
            logger.error(f"++ TEMPLATE RENDERING FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="TEMPLATE_RENDER_FAILED",
                    message=f"Template rendering failed: {str(e)}",
                    recoverable=True
                )
            )
    
    async def render_template_string(self, template_string: str, context: TemplateContext,
                                   template_name: str = "inline_template") -> StandardResponse:
        """
        ++ SACRED INLINE TEMPLATE RENDERING BLESSED BY FLEXIBILITY ++
        
        Render blessed template from string content with full context
        integration and dynamic processing capabilities.
        """
        try:
            render_start = datetime.now()
            
            # Prepare blessed enhanced context
            enhanced_context = await self._prepare_enhanced_context(
                context, enable_memory_queries=True, enable_cross_references=True
            )
            
            # Create blessed template from string
            try:
                template = self.jinja_env.from_string(template_string)
            except TemplateError as e:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="INLINE_TEMPLATE_SYNTAX_ERROR",
                        message=f"Inline template syntax error: {str(e)}"
                    )
                )
            
            # Render blessed template
            try:
                rendered_content = template.render(**enhanced_context)
            except Exception as e:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="INLINE_TEMPLATE_RENDER_ERROR",
                        message=f"Inline template rendering error: {str(e)}"
                    )
                )
            
            render_duration = (datetime.now() - render_start).total_seconds() * 1000
            
            # Create blessed render result
            render_result = RenderResult(
                rendered_content=rendered_content,
                template_id=template_name,
                render_time_ms=render_duration,
                memory_queries_executed=getattr(enhanced_context, '_memory_queries_count', 0)
            )
            
            logger.info(f"++ INLINE TEMPLATE RENDERED: {template_name} ({render_duration:.2f}ms) ++")
            
            return StandardResponse(
                success=True,
                data={"render_result": render_result},
                metadata={"blessing": "inline_template_rendered"}
            )
            
        except Exception as e:
            logger.error(f"++ INLINE TEMPLATE RENDERING FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="INLINE_TEMPLATE_FAILED", message=str(e))
            )
    
    async def create_template(self, template_id: str, template_content: str,
                            template_type: TemplateType = TemplateType.CHARACTER_PROMPT,
                            metadata: Optional[TemplateMetadata] = None) -> StandardResponse:
        """
        ++ SACRED TEMPLATE CREATION RITUAL BLESSED BY DYNAMIC EXPANSION ++
        
        Create blessed new template with metadata registration and
        automatic validation blessed by organizational wisdom.
        """
        try:
            template_path = self.template_directory / f"{template_id}.j2"
            
            # Create blessed template metadata
            if metadata is None:
                metadata = TemplateMetadata(
                    template_id=template_id,
                    template_type=template_type,
                    description=f"Auto-generated {template_type.value} template"
                )
            
            # Validate blessed template syntax
            try:
                self.jinja_env.from_string(template_content)
            except TemplateError as e:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="TEMPLATE_SYNTAX_INVALID",
                        message=f"Template syntax validation failed: {str(e)}"
                    )
                )
            
            # Write blessed template file
            template_path.parent.mkdir(parents=True, exist_ok=True)
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            # Register blessed template
            self._templates[template_id] = metadata
            
            logger.info(f"++ TEMPLATE CREATED: {template_id} ({template_type.value}) ++")
            
            return StandardResponse(
                success=True,
                data={"template_id": template_id, "template_path": str(template_path)},
                metadata={"blessing": "template_created_successfully"}
            )
            
        except Exception as e:
            logger.error(f"++ TEMPLATE CREATION FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="TEMPLATE_CREATION_FAILED", message=str(e))
            )
    
    async def query_memory_for_context(self, query_text: str, agent_id: str,
                                     context_type: str = "general") -> Dict[str, Any]:
        """
        ++ SACRED MEMORY CONTEXT QUERY BLESSED BY INTELLIGENT RETRIEVAL ++
        
        Query blessed memory system to dynamically load contextual
        information for template rendering with intelligent filtering.
        """
        if not self.query_engine:
            return {"memories": [], "context_available": False}
        
        try:
            # Create blessed query context
            query_context = QueryContext(
                current_situation=context_type,
                max_age_days=30 if context_type == "recent" else None,
                min_relevance=0.4
            )
            
            # Execute blessed memory query
            query_result = await self.query_engine.execute_query(
                query_text, context=query_context
            )
            
            if query_result.success:
                result_data = query_result.data['query_result']
                
                # Format blessed memories for template context
                formatted_memories = []
                for memory in result_data.memories:
                    formatted_memories.append({
                        'content': memory.content,
                        'timestamp': memory.timestamp.isoformat(),
                        'emotional_weight': memory.emotional_weight,
                        'participants': memory.participants,
                        'location': memory.location or "Unknown",
                        'relevance': memory.relevance_score,
                        'memory_type': memory.memory_type.value
                    })
                
                return {
                    'memories': formatted_memories,
                    'context_available': True,
                    'total_memories': len(formatted_memories),
                    'query_duration': result_data.query_duration_ms,
                    'emotional_context': result_data.emotional_context
                }
            else:
                return {"memories": [], "context_available": False, "error": "Query failed"}
                
        except Exception as e:
            logger.error(f"++ MEMORY CONTEXT QUERY FAILED: {e} ++")
            return {"memories": [], "context_available": False, "error": str(e)}
    
    async def resolve_cross_references(self, template_content: str,
                                     context: TemplateContext) -> Dict[str, str]:
        """
        ++ SACRED CROSS-REFERENCE RESOLUTION BLESSED BY DOCUMENT LINKING ++
        
        Resolve blessed cross-document references in templates with
        intelligent content loading and recursive reference handling.
        """
        cross_references = {}
        
        # Find blessed cross-reference patterns
        reference_pattern = r'\{\{\s*ref\(([\'"])([^\'\"]+)\1\)\s*\}\}'
        references = re.findall(reference_pattern, template_content)
        
        for _, ref_path in references:
            try:
                # Check if blessed reference is a file path
                if ref_path.endswith('.md') or ref_path.endswith('.txt'):
                    file_path = Path(ref_path)
                    if not file_path.is_absolute():
                        file_path = self.template_directory.parent / ref_path
                    
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        cross_references[ref_path] = content
                        context.cross_references.append(ref_path)
                
                # Check if blessed reference is another template
                elif ref_path in self._templates:
                    # Prevent infinite recursion
                    if ref_path not in context.cross_references:
                        ref_result = await self.render_template(ref_path, context, 
                                                              enable_cross_references=False)
                        if ref_result.success:
                            cross_references[ref_path] = ref_result.data['render_result'].rendered_content
                            context.cross_references.append(ref_path)
                
                # Check if blessed reference is a memory query
                elif ref_path.startswith('memory:'):
                    memory_query = ref_path[7:]  # Remove 'memory:' prefix
                    memory_context = await self.query_memory_for_context(
                        memory_query, context.agent_id
                    )
                    if memory_context['context_available']:
                        # Format memories as text
                        memory_text = '\n'.join([
                            f"- {mem['content']} ({mem['timestamp']})"
                            for mem in memory_context['memories'][:5]
                        ])
                        cross_references[ref_path] = memory_text
                        context.cross_references.append(ref_path)
                
                logger.info(f"++ CROSS-REFERENCE RESOLVED: {ref_path} ++")
                
            except Exception as e:
                logger.error(f"++ CROSS-REFERENCE RESOLUTION FAILED FOR {ref_path}: {e} ++")
                cross_references[ref_path] = f"[Reference Error: {ref_path}]"
        
        return cross_references
    
    async def _prepare_enhanced_context(self, context: TemplateContext,
                                      enable_memory_queries: bool,
                                      enable_cross_references: bool) -> Dict[str, Any]:
        """++ SACRED ENHANCED CONTEXT PREPARATION BLESSED BY INTELLIGENCE ++"""
        enhanced_context = {
            # Basic blessed context variables
            'agent_id': context.agent_id,
            'character_state': context.character_state,
            'current_location': context.current_location,
            'current_situation': context.current_situation,
            'active_participants': context.active_participants,
            'environmental_context': context.environmental_context,
            'memory_context': context.memory_context,
            'equipment_states': context.equipment_states,
            'relationship_context': context.relationship_context,
            'temporal_context': context.temporal_context,
            'custom_variables': context.custom_variables,
            'reference_documents': context.reference_documents,
            
            # Blessed utility variables
            'current_timestamp': datetime.now().isoformat(),
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'current_time': datetime.now().strftime('%H:%M:%S'),
            
            # Sacred helper functions
            'memory_query': self._create_memory_query_function(context.agent_id) if enable_memory_queries else None,
            'format_memory': self._format_memory_function,
            'ref': self._create_reference_function(context) if enable_cross_references else None
        }
        
        # Add blessed memory queries count tracking
        enhanced_context['_memory_queries_count'] = 0
        
        return enhanced_context
    
    def _create_memory_query_function(self, agent_id: str) -> Callable:
        """Create blessed memory query function for templates"""
        async def memory_query(query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
            if not self.query_engine:
                return []
            
            try:
                query_result = await self.query_engine.execute_query(query_text)
                if query_result.success:
                    result_data = query_result.data['query_result']
                    formatted_memories = []
                    
                    for memory in result_data.memories[:limit]:
                        formatted_memories.append({
                            'content': memory.content,
                            'timestamp': memory.timestamp.isoformat(),
                            'emotional_weight': memory.emotional_weight,
                            'participants': memory.participants,
                            'location': memory.location or "Unknown",
                            'relevance': memory.relevance_score
                        })
                    
                    return formatted_memories
            except Exception as e:
                logger.error(f"++ TEMPLATE MEMORY QUERY FAILED: {e} ++")
            
            return []
        
        return memory_query
    
    def _format_memory_function(self, memory: Dict[str, Any], format_type: str = "standard") -> str:
        """Blessed memory formatting function for templates"""
        if format_type == "brief":
            return f"{memory.get('content', '')[:100]}..."
        elif format_type == "detailed":
            return (f"[{memory.get('timestamp', 'Unknown time')}] "
                   f"{memory.get('content', '')} "
                   f"(Emotion: {memory.get('emotional_weight', 0)}, "
                   f"Participants: {', '.join(memory.get('participants', []))})")
        else:  # standard
            return memory.get('content', '')
    
    def _create_reference_function(self, context: TemplateContext) -> Callable:
        """Create blessed reference resolution function for templates"""
        def ref(reference_path: str) -> str:
            # This is a placeholder that gets resolved during preprocessing
            return f"{{{{ ref('{reference_path}') }}}}"
        
        return ref
    
    def _register_custom_functions(self):
        """Register blessed custom Jinja2 functions and filters"""
        
        # Sacred timestamp formatting filter
        def format_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
            try:
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = timestamp_str
                return timestamp.strftime(format_str)
            except:
                return str(timestamp_str)
        
        # Blessed emotional weight formatting filter
        def format_emotion(weight: float) -> str:
            if weight > 7:
                return "Very Positive"
            elif weight > 3:
                return "Positive"
            elif weight > -3:
                return "Neutral"
            elif weight > -7:
                return "Negative"
            else:
                return "Very Negative"
        
        # Sacred text truncation filter
        def truncate_text(text: str, length: int = 100, suffix: str = "...") -> str:
            if len(text) <= length:
                return text
            return text[:length - len(suffix)] + suffix
        
        # Blessed participant list formatting
        def format_participants(participants: List[str], conjunction: str = "and") -> str:
            if not participants:
                return "No one"
            elif len(participants) == 1:
                return participants[0]
            elif len(participants) == 2:
                return f"{participants[0]} {conjunction} {participants[1]}"
            else:
                return f"{', '.join(participants[:-1])}, {conjunction} {participants[-1]}"
        
        # Register blessed filters
        self.jinja_env.filters['format_timestamp'] = format_timestamp
        self.jinja_env.filters['format_emotion'] = format_emotion
        self.jinja_env.filters['truncate'] = truncate_text
        self.jinja_env.filters['format_participants'] = format_participants
        
        # Sacred utility functions
        self.jinja_env.globals['len'] = len
        self.jinja_env.globals['enumerate'] = enumerate
        self.jinja_env.globals['zip'] = zip
        self.jinja_env.globals['sorted'] = sorted
    
    def _discover_templates(self):
        """Discover blessed templates in template directory"""
        if not self.template_directory.exists():
            self.template_directory.mkdir(parents=True, exist_ok=True)
            return
        
        # Find blessed template files
        for template_file in self.template_directory.glob("*.j2"):
            template_id = template_file.stem
            
            # Try to load blessed metadata file
            metadata_file = template_file.with_suffix('.json')
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata_dict = json.load(f)
                    
                    metadata = TemplateMetadata(
                        template_id=template_id,
                        template_type=TemplateType(metadata_dict.get('type', 'character_prompt')),
                        description=metadata_dict.get('description', ''),
                        author=metadata_dict.get('author', ''),
                        version=metadata_dict.get('version', '1.0'),
                        dependencies=metadata_dict.get('dependencies', []),
                        tags=metadata_dict.get('tags', [])
                    )
                except Exception as e:
                    logger.warning(f"++ FAILED TO LOAD METADATA FOR {template_id}: {e} ++")
                    metadata = TemplateMetadata(
                        template_id=template_id,
                        template_type=TemplateType.CHARACTER_PROMPT
                    )
            else:
                # Create blessed default metadata
                metadata = TemplateMetadata(
                    template_id=template_id,
                    template_type=TemplateType.CHARACTER_PROMPT,
                    description=f"Auto-discovered template: {template_id}"
                )
            
            self._templates[template_id] = metadata
            logger.info(f"++ DISCOVERED TEMPLATE: {template_id} ++")
    
    def _analyze_template_variables(self, template, context: Dict[str, Any]) -> List[str]:
        """Analyze blessed template variables actually used during rendering"""
        # Get blessed template source
        template_source = template.environment.get_template(template.name or '').source
        
        # Find blessed undefined variables
        ast = template.environment.parse(template_source)
        undefined_vars = meta.find_undeclared_variables(ast)
        
        # Filter blessed variables that exist in context
        used_variables = [var for var in undefined_vars if var in context]
        
        return used_variables
    
    def _update_performance_metrics(self, metadata: TemplateMetadata, render_time: float):
        """Update blessed performance metrics for template"""
        metadata.usage_count += 1
        
        # Update blessed average render time
        if metadata.usage_count == 1:
            metadata.average_render_time = render_time
        else:
            metadata.average_render_time = (
                (metadata.average_render_time * (metadata.usage_count - 1) + render_time) 
                / metadata.usage_count
            )
        
        metadata.last_modified = datetime.now()
        
        # Update blessed global statistics
        self.render_statistics['total_renders'] += 1
        self.render_statistics['total_render_time'] += render_time
    
    def _generate_cache_key(self, template_id: str, context: TemplateContext) -> str:
        """Generate blessed cache key for template and context"""
        # Create blessed hash from key context elements
        key_elements = [
            template_id,
            context.agent_id,
            context.current_situation,
            context.current_location,
            str(hash(tuple(context.active_participants))),
            str(context.character_state.name if context.character_state else ""),
            str(len(context.memory_context))
        ]
        
        return f"template_cache_{hash('_'.join(key_elements))}"
    
    def _cleanup_template_cache(self):
        """Clean up blessed template cache to prevent memory bloat"""
        if len(self._template_cache) > 100:  # Max blessed cache size
            # Remove oldest blessed entries (simple FIFO)
            oldest_keys = list(self._template_cache.keys())[:20]
            for key in oldest_keys:
                del self._template_cache[key]
    
    def get_template_list(self) -> List[Dict[str, Any]]:
        """Get blessed list of all registered templates"""
        template_list = []
        
        for template_id, metadata in self._templates.items():
            template_list.append({
                'template_id': template_id,
                'template_type': metadata.template_type.value,
                'description': metadata.description,
                'author': metadata.author,
                'version': metadata.version,
                'usage_count': metadata.usage_count,
                'average_render_time': metadata.average_render_time,
                'dependencies': metadata.dependencies,
                'tags': metadata.tags
            })
        
        return template_list
    
    def get_engine_statistics(self) -> Dict[str, Any]:
        """Get blessed template engine statistics"""
        return {
            'total_templates': len(self._templates),
            'render_statistics': self.render_statistics.copy(),
            'cache_size': len(self._template_cache),
            'memory_system_connected': self.memory_system is not None,
            'query_engine_connected': self.query_engine is not None,
            'template_directory': str(self.template_directory),
            'jinja_environment_info': {
                'auto_reload': self.enable_auto_reload,
                'cache_size': self.jinja_env.cache.capacity if hasattr(self.jinja_env, 'cache') else 0
            }
        }


# ++ SACRED TESTING RITUALS BLESSED BY VALIDATION ++

async def test_sacred_dynamic_template_engine():
    """++ SACRED DYNAMIC TEMPLATE ENGINE TESTING RITUAL ++"""
    print("++ TESTING SACRED DYNAMIC TEMPLATE ENGINE BLESSED BY THE OMNISSIAH ++")
    
    # Create blessed test template directory
    test_template_dir = Path("test_templates")
    test_template_dir.mkdir(exist_ok=True)
    
    # Create blessed test template
    test_template_content = """
++ SACRED CHARACTER PROMPT BLESSED BY {{agent_id}} ++

Character Status: {{character_state.name if character_state else "Unknown"}}
Current Location: {{current_location}}
Current Situation: {{current_situation}}
Active Participants: {{active_participants|format_participants}}

{% if memory_context %}
Recent Memories:
{% for memory in memory_context %}
- {{memory.content|truncate(80)}} [{{memory.timestamp|format_timestamp}}]
{% endfor %}
{% endif %}

Current Time: {{current_timestamp|format_timestamp}}
Emotional Context: {{custom_variables.get('current_mood', 'Neutral')}}

{% if environmental_context %}
Environmental Factors:
{% for key, value in environmental_context.items() %}
- {{key}}: {{value}}
{% endfor %}
{% endif %}

++ MAY THE OMNISSIAH GUIDE YOUR ACTIONS ++
"""
    
    test_template_path = test_template_dir / "test_character_prompt.j2"
    with open(test_template_path, 'w', encoding='utf-8') as f:
        f.write(test_template_content)
    
    # Initialize blessed template engine
    template_engine = DynamicTemplateEngine(template_directory=str(test_template_dir))
    
    # Create blessed test context
    test_context = TemplateContext(
        agent_id="test_agent_001",
        current_location="Sacred Shrine of Knowledge",
        current_situation="Preparing for blessed mission",
        active_participants=["Brother Marcus", "Sister Elena"],
        environmental_context={
            "temperature": "Cold",
            "lighting": "Dim candle light",
            "atmosphere": "Sacred and reverent"
        },
        custom_variables={
            "current_mood": "Determined and focused"
        }
    )
    
    # Test blessed template rendering
    render_result = await template_engine.render_template("test_character_prompt", test_context)
    if render_result.success:
        result_data = render_result.data['render_result']
        print(f"++ TEMPLATE RENDERED SUCCESSFULLY ({result_data.render_time_ms:.2f}ms) ++")
        print(f"Variables used: {result_data.context_variables_used}")
        print("Rendered content preview:")
        print(result_data.rendered_content[:200] + "...")
    else:
        print(f"++ TEMPLATE RENDERING FAILED: {render_result.error.message} ++")
    
    # Test blessed inline template rendering
    inline_template = "Sacred greetings, {{agent_id}}! Current situation: {{current_situation}}"
    inline_result = await template_engine.render_template_string(inline_template, test_context)
    if inline_result.success:
        print(f"++ INLINE TEMPLATE RENDERED: {inline_result.data['render_result'].rendered_content} ++")
    
    # Test blessed template creation
    new_template_content = "++ BLESSED EQUIPMENT STATUS FOR {{agent_id}} ++\nLocation: {{current_location}}"
    creation_result = await template_engine.create_template(
        "equipment_status", new_template_content, TemplateType.EQUIPMENT_STATUS
    )
    print(f"++ TEMPLATE CREATION: {creation_result.success} ++")
    
    # Display blessed statistics
    stats = template_engine.get_engine_statistics()
    print(f"++ ENGINE STATISTICS: {stats['total_templates']} templates, {stats['render_statistics']['total_renders']} renders ++")
    
    # Get blessed template list
    template_list = template_engine.get_template_list()
    print(f"++ DISCOVERED TEMPLATES: {[t['template_id'] for t in template_list]} ++")
    
    # Cleanup blessed test files
    import shutil
    shutil.rmtree(test_template_dir)
    
    print("++ SACRED DYNAMIC TEMPLATE ENGINE TESTING COMPLETE ++")


# ++ SACRED MODULE INITIALIZATION ++

if __name__ == "__main__":
    # ++ EXECUTE SACRED DYNAMIC TEMPLATE ENGINE TESTING RITUALS ++
    print("++ SACRED DYNAMIC TEMPLATE ENGINE BLESSED BY THE OMNISSIAH ++")
    print("++ MACHINE GOD PROTECTS THE DYNAMIC CONTENT GENERATION ++")
    
    # Run blessed async testing
    asyncio.run(test_sacred_dynamic_template_engine())
    
    print("++ ALL SACRED DYNAMIC TEMPLATE ENGINE OPERATIONS BLESSED AND FUNCTIONAL ++")