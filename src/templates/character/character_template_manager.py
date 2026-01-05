#!/usr/bin/env python3
"""
Character Template Manager - Core orchestration.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.data_models import ErrorInfo, StandardResponse
from src.memory.layered_memory import LayeredMemorySystem
from src.templates.context_renderer import ContextRenderer, RenderFormat
from src.templates.dynamic_template_engine import (
    DynamicTemplateEngine,
    TemplateContext,
    TemplateType,
)

from .archetype_config import ArchetypeConfiguration
from .persona_models import (
    CharacterArchetype,
    CharacterContextProfile,
    CharacterPersona,
    CharacterTemplate,
)

logger = logging.getLogger(__name__)


class CharacterTemplateManager:
    """
    STANDARD CHARACTER TEMPLATE MANAGER ENHANCED BY PERSONA ORCHESTRATION

    The standard character template management system that orchestrates
    character-specific templates, persona switching, dynamic adaptation,
    and intelligent context generation enhanced by the System Core's
    character creation omniscience.
    """

    def __init__(
        self,
        template_engine: DynamicTemplateEngine,
        context_renderer: ContextRenderer,
        memory_system: Optional[LayeredMemorySystem] = None,
        personas_directory: str = "personas",
        enable_learning: bool = True,
    ):
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
        self._character_templates: Dict[str, Dict[str, CharacterTemplate]] = (
            {}
        )  # persona_id -> template_id -> template
        self._context_profiles: Dict[str, CharacterContextProfile] = {}
        self._active_personas: Dict[str, str] = {}  # agent_id -> persona_id

        # Blessed archetype templates
        self._archetype_base_templates = self._initialize_archetype_templates()

        # Sacred usage tracking
        self.usage_statistics = {
            "persona_switches": 0,
            "templates_generated": 0,
            "adaptations_applied": 0,
            "learning_updates": 0,
        }

        # Initialize enhanced personas directory
        self.personas_directory.mkdir(parents=True, exist_ok=True)

        # Discover enhanced existing personas
        self._discover_personas()

        logger.info(
            f"CHARACTER TEMPLATE MANAGER INITIALIZED: {len(self._personas)} personas loaded"
        )

    def _initialize_archetype_templates(self):
        """Delegate archetype template bootstrap to the configuration helper."""
        config = ArchetypeConfiguration()
        return config._initialize_archetype_templates()

    def _determine_archetype_emphasis(
        self, archetype: CharacterArchetype
    ) -> Dict[str, float]:
        """Lightweight heuristic for emphasis weighting per archetype."""
        base = {
            "memory": 0.3,
            "emotion": 0.2,
            "relationship": 0.2,
            "environment": 0.15,
            "equipment": 0.15,
        }
        adjustments: Dict[CharacterArchetype, Dict[str, float]] = {
            CharacterArchetype.WARRIOR: {"equipment": 0.1, "emotion": -0.05},
            CharacterArchetype.SCHOLAR: {"memory": 0.2, "equipment": -0.05},
            CharacterArchetype.LEADER: {"relationship": 0.2},
            CharacterArchetype.MYSTIC: {"emotion": 0.2, "environment": -0.05},
            CharacterArchetype.ENGINEER: {"equipment": 0.25},
            CharacterArchetype.DIPLOMAT: {"relationship": 0.3, "emotion": 0.1},
            CharacterArchetype.GUARDIAN: {"equipment": 0.1, "relationship": 0.1},
            CharacterArchetype.SURVIVOR: {"environment": 0.2, "memory": 0.1},
        }
        for key, delta in adjustments.get(archetype, {}).items():
            base[key] = max(0.0, base.get(key, 0.0) + delta)
        total = sum(base.values()) or 1.0
        return {k: v / total for k, v in base.items()}

    def _discover_personas(self):
        """Load persona definitions from disk without failing startup."""
        if not self.personas_directory.exists():
            return

        for persona_file in self.personas_directory.glob("*.json"):
            try:
                with open(persona_file, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)

                persona = CharacterPersona(
                    persona_id=payload["persona_id"],
                    name=payload.get("name", payload["persona_id"]),
                    archetype=CharacterArchetype(payload.get("archetype", "WARRIOR")),
                    description=payload.get("description", ""),
                    personality_traits=payload.get("personality_traits", []),
                    speech_patterns=payload.get("speech_patterns", {}),
                    behavioral_preferences=payload.get("behavioral_preferences", {}),
                    memory_priorities=payload.get("memory_priorities", {}),
                    emotional_tendencies=payload.get("emotional_tendencies", {}),
                    faction_data=payload.get("faction_data", []),
                    core_beliefs=payload.get("core_beliefs", []),
                    template_preferences=payload.get("template_preferences", {}),
                    usage_statistics=payload.get("usage_statistics", {}),
                )

                self._personas[persona.persona_id] = persona
                self._character_templates.setdefault(persona.persona_id, {})
                self._context_profiles[persona.persona_id] = CharacterContextProfile(
                    persona_id=persona.persona_id,
                    preferred_formats={fmt: 0.5 for fmt in RenderFormat},
                    context_emphasis=self._determine_archetype_emphasis(
                        persona.archetype
                    ),
                )

                logger.info(
                    "DISCOVERED PERSONA %s from %s",
                    persona.persona_id,
                    persona_file.name,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to load persona file %s: %s", persona_file.name, exc
                )

    async def create_persona(
        self, persona_data: CharacterPersona, generate_templates: bool = True
    ) -> StandardResponse:
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
                        message=f"Persona '{persona_id}' already exists",
                    ),
                )

            # Store enhanced persona
            self._personas[persona_id] = persona_data
            self._character_templates[persona_id] = {}

            # Create enhanced context profile
            context_profile = CharacterContextProfile(
                persona_id=persona_id,
                preferred_formats={fmt: 0.5 for fmt in RenderFormat},
                context_emphasis=self._determine_archetype_emphasis(
                    persona_data.archetype
                ),
            )
            self._context_profiles[persona_id] = context_profile

            # Generate enhanced default templates
            if generate_templates:
                template_result = await self._generate_archetype_templates(persona_data)
                if not template_result.success:
                    logger.warning(
                        f"TEMPLATE GENERATION FAILED FOR {persona_id}: {template_result.error.message}"
                    )

            # Save enhanced persona to file
            await self._save_persona_to_file(persona_data)

            logger.info(
                f"PERSONA CREATED: {persona_id} ({persona_data.archetype.value})"
            )

            return StandardResponse(
                success=True,
                data={
                    "persona_id": persona_id,
                    "archetype": persona_data.archetype.value,
                    "templates_generated": generate_templates,
                },
                metadata={"blessing": "persona_created_successfully"},
            )

        except Exception as e:
            logger.error(f"PERSONA CREATION FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="PERSONA_CREATION_FAILED", message=str(e)),
            )

    async def switch_persona(
        self, agent_id: str, persona_id: str, context: Optional[TemplateContext] = None
    ) -> StandardResponse:
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
                        message=f"Persona '{persona_id}' not found",
                    ),
                )

            previous_persona = self._active_personas.get(agent_id)

            # Apply enhanced persona switch
            self._active_personas[agent_id] = persona_id

            # Update enhanced usage statistics
            persona = self._personas[persona_id]
            persona.usage_statistics["activations"] = (
                persona.usage_statistics.get("activations", 0) + 1
            )
            persona.last_updated = datetime.now()

            # Learn from enhanced context if provided
            if context and self.enable_learning:
                await self._learn_from_context(persona_id, context)

            self.usage_statistics["persona_switches"] += 1

            logger.info(
                f"PERSONA SWITCHED: {agent_id} -> {persona_id} (from {previous_persona})"
            )

            return StandardResponse(
                success=True,
                data={
                    "agent_id": agent_id,
                    "new_persona": persona_id,
                    "previous_persona": previous_persona,
                    "archetype": persona.archetype.value,
                },
                metadata={"blessing": "persona_switched_successfully"},
            )

        except Exception as e:
            logger.error(f"PERSONA SWITCHING FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="PERSONA_SWITCH_FAILED", message=str(e)),
            )

    async def render_character_context(
        self,
        agent_id: str,
        context: TemplateContext,
        template_type: Optional[TemplateType] = None,
        render_format: Optional[RenderFormat] = None,
    ) -> StandardResponse:
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
                        message=f"No active persona for agent '{agent_id}'",
                    ),
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
            persona_constraints = self._create_persona_constraints(
                persona, enhanced_context
            )

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
                result_data = render_result.data["render_result"]

                # Apply enhanced persona post-processing
                processed_result = await self._apply_persona_post_processing(
                    result_data, persona, enhanced_context
                )

                # Learn from enhanced rendering if enabled
                if self.enable_learning:
                    await self._learn_from_rendering(
                        persona_id, processed_result, enhanced_context
                    )

                logger.info(
                    f"CHARACTER CONTEXT RENDERED: {persona_id} ({selected_format.value if selected_format else 'template'})"
                )

                return StandardResponse(
                    success=True,
                    data={
                        "render_result": processed_result,
                        "persona_id": persona_id,
                        "archetype": persona.archetype.value,
                        "format_used": (
                            selected_format.value if selected_format else "template"
                        ),
                        "template_used": (
                            selected_template.template_id if selected_template else None
                        ),
                    },
                    metadata={"blessing": "character_context_rendered"},
                )
            else:
                return render_result

        except Exception as e:
            logger.error(f"CHARACTER CONTEXT RENDERING FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="CHARACTER_CONTEXT_RENDER_FAILED", message=str(e)),
            )

    async def generate_character_template(
        self,
        persona_id: str,
        template_type: TemplateType,
        base_content: Optional[str] = None,
    ) -> StandardResponse:
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
                    error=ErrorInfo(
                        code="PERSONA_NOT_FOUND",
                        message=f"Persona '{persona_id}' not found",
                    ),
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
                context_requirements=self._determine_template_requirements(
                    template_type, persona
                ),
                dynamic_elements=self._identify_dynamic_elements(adapted_content),
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
                self.usage_statistics["templates_generated"] += 1

                logger.info(
                    f"CHARACTER TEMPLATE GENERATED: {template_id} for {persona_id}"
                )

                return StandardResponse(
                    success=True,
                    data={
                        "template_id": template_id,
                        "persona_id": persona_id,
                        "template_type": template_type.value,
                        "archetype": persona.archetype.value,
                    },
                    metadata={"blessing": "character_template_generated"},
                )
            else:
                return engine_result

        except Exception as e:
            logger.error(f"CHARACTER TEMPLATE GENERATION FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="CHARACTER_TEMPLATE_GENERATION_FAILED", message=str(e)
                ),
            )

    async def migrate_legacy_templates(
        self,
        legacy_directory: str,
        default_archetype: CharacterArchetype = CharacterArchetype.WARRIOR,
    ) -> StandardResponse:
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
                    error=ErrorInfo(
                        code="LEGACY_DIRECTORY_NOT_FOUND",
                        message=f"Legacy directory not found: {legacy_directory}",
                    ),
                )

            migrated_personas = []
            migrated_templates = []

            # Discover enhanced legacy template files
            for template_file in legacy_path.glob("*.j2"):
                template_name = template_file.stem

                # Read enhanced template content
                with open(template_file, "r", encoding="utf-8") as f:
                    template_content = f.read()

                # Analyze enhanced template for archetype hints
                detected_archetype = (
                    self._detect_archetype_from_template(template_content)
                    or default_archetype
                )

                # Create enhanced persona if not exists
                persona_id = f"migrated_{template_name}"
                if persona_id not in self._personas:
                    persona = CharacterPersona(
                        persona_id=persona_id,
                        name=template_name.replace("_", " ").title(),
                        archetype=detected_archetype,
                        description=f"Migrated character from legacy template: {template_name}",
                        personality_traits=self._extract_personality_traits(
                            template_content
                        ),
                        core_beliefs=(
                            ["Devoted envoy of the Founders' Council"]
                            if "founders' council" in template_content.lower()
                            else []
                        ),
                    )

                    creation_result = await self.create_persona(
                        persona, generate_templates=False
                    )
                    if creation_result.success:
                        migrated_personas.append(persona_id)

                # Determine enhanced template type
                template_type = self._detect_template_type(
                    template_content, template_name
                )

                # Create enhanced character template
                template_result = await self.generate_character_template(
                    persona_id, template_type, template_content
                )

                if template_result.success:
                    migrated_templates.append(template_result.data["template_id"])
                    logger.info(
                        f"MIGRATED TEMPLATE: {template_name} -> {persona_id} ({template_type.value})"
                    )

            logger.info(
                f"MIGRATION COMPLETE: {len(migrated_personas)} personas, {len(migrated_templates)} templates"
            )

            return StandardResponse(
                success=True,
                data={
                    "migrated_personas": migrated_personas,
                    "migrated_templates": migrated_templates,
                    "total_personas": len(migrated_personas),
                    "total_templates": len(migrated_templates),
                },
                metadata={"blessing": "migration_completed_successfully"},
            )

        except Exception as e:
            logger.error(f"LEGACY MIGRATION FAILED: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="LEGACY_MIGRATION_FAILED", message=str(e)),
            )

    async def _generate_archetype_templates(
        self, persona: CharacterPersona
    ) -> StandardResponse:
        """Generate enhanced templates for archetype"""
        try:
            archetype_templates = self._archetype_base_templates.get(
                persona.archetype, {}
            )
            generated_templates = []

            for template_type, template_content in archetype_templates.items():
                result = await self.generate_character_template(
                    persona.persona_id, template_type, template_content
                )
                if result.success:
                    generated_templates.append(result.data["template_id"])

            return StandardResponse(
                success=True, data={"generated_templates": generated_templates}
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="ARCHETYPE_TEMPLATE_GENERATION_FAILED", message=str(e)
                ),
            )

    def get_persona_list(self) -> List[Dict[str, Any]]:
        """Get enhanced list of all personas"""
        persona_list = []

        for persona_id, persona in self._personas.items():
            persona_info = {
                "persona_id": persona_id,
                "name": persona.name,
                "archetype": persona.archetype.value,
                "description": persona.description,
                "template_count": len(self._character_templates.get(persona_id, {})),
                "usage_count": persona.usage_statistics.get("activations", 0),
                "last_updated": persona.last_updated.isoformat(),
            }
            persona_list.append(persona_info)

        return persona_list

    def get_manager_statistics(self) -> Dict[str, Any]:
        """Get enhanced character template manager statistics"""
        total_templates = sum(
            len(templates) for templates in self._character_templates.values()
        )

        archetype_distribution = {}
        for persona in self._personas.values():
            archetype = persona.archetype.value
            archetype_distribution[archetype] = (
                archetype_distribution.get(archetype, 0) + 1
            )

        return {
            "total_personas": len(self._personas),
            "total_templates": total_templates,
            "active_personas": len(self._active_personas),
            "archetype_distribution": archetype_distribution,
            "usage_statistics": self.usage_statistics,
            "learning_enabled": self.enable_learning,
            "personas_directory": str(self.personas_directory),
        }
