from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from fastapi import FastAPI

from src.api.services.paths import find_project_root
from src.api.settings import APISettings
from src.core.config.config_loader import get_config
from src.core.service_container import get_service_container
from src.core.system_orchestrator import OrchestratorConfig, SystemOrchestrator
from src.services.api_service import ApiOrchestrationService
from src.workspaces import (
    FilesystemCharacterStore,
    FilesystemWorkspaceStore,
    GuestSessionManager,
)

logger = logging.getLogger(__name__)


def ensure_workspace_services(
    app: FastAPI, settings: Optional[APISettings] = None
) -> None:
    """Prepare workspace persistence stores and guest sessions."""

    resolved_settings = settings or APISettings.from_env()
    is_testing = os.getenv("ORCHESTRATOR_MODE", "").lower() == "testing"

    if getattr(app.state, "workspace_store", None) is None:
        try:
            workspace_root = find_project_root(os.getcwd()) / "data" / "workspaces"
            workspace_store = FilesystemWorkspaceStore(workspace_root)
            character_store = FilesystemCharacterStore(workspace_store)
            guest_session_manager = GuestSessionManager(
                workspace_store,
                secret_key=resolved_settings.jwt_secret_key,
                algorithm=resolved_settings.jwt_algorithm,
            )
            app.state.workspace_store = workspace_store
            app.state.workspace_character_store = character_store
            app.state.guest_session_manager = guest_session_manager
            if is_testing and not getattr(app.state, "default_workspace_id", None):
                app.state.default_workspace_id = workspace_store.create().id
            logger.info("Guest workspace store initialized")
        except Exception as exc:
            logger.error(
                "Failed to initialize guest workspace store: %s", exc, exc_info=True
            )
            app.state.workspace_store = None
            app.state.workspace_character_store = None
            app.state.guest_session_manager = None
    else:
        logger.info("Guest workspace store preconfigured; skipping initialization")


async def initialize_app_state(app: FastAPI) -> None:
    logger.info("Starting StoryForge AI API server...")
    settings: APISettings = getattr(app.state, "settings", APISettings.from_env())
    app.state.settings = settings

    get_config()

    container = get_service_container()

    ensure_workspace_services(app, settings)

    global_event_bus: Optional[object] = None
    try:
        from src.events.event_bus import EventBus

        global_event_bus = EventBus()
        app.state.event_bus = global_event_bus
        container.register_singleton(EventBus, global_event_bus)
        logger.info("Global EventBus (Enterprise) initialized and registered")
    except Exception as exc:
        logger.warning("Could not initialize EventBus: %s", exc)
        app.state.event_bus = None

    # Wire event bus to world_time router
    if global_event_bus is not None:
        try:
            from src.api.routers.world_time import set_event_bus

            set_event_bus(global_event_bus)
            logger.info("Event bus wired to world_time router")
        except ImportError:
            logger.warning("world_time router not available for event bus wiring")

        # Register event handlers
        try:
            from src.contexts.world.application.handlers import TimeAdvancedHandler

            time_handler = TimeAdvancedHandler()
            global_event_bus.register_handler(time_handler)
            logger.info("TimeAdvancedHandler registered with EventBus")
        except Exception as exc:
            logger.warning("Could not register TimeAdvancedHandler: %s", exc)

        # Register FactionIntentRepository in DI container
        try:
            from src.contexts.world.domain.ports.faction_intent_repository import (
                FactionIntentRepository,
            )
            from src.contexts.world.infrastructure.persistence.in_memory_faction_intent_repository import (
                InMemoryFactionIntentRepository,
            )

            intent_repository = InMemoryFactionIntentRepository()
            container.register_singleton(FactionIntentRepository, intent_repository)
            app.state.faction_intent_repository = intent_repository
            app.state.faction_intent_repository_available = True
            logger.info("FactionIntentRepository registered in DI container")
        except Exception as exc:
            app.state.faction_intent_repository_available = False
            logger.warning("Could not register FactionIntentRepository: %s", exc)

        # Register RetrievalService reference for FactionDecisionService
        try:
            from src.contexts.knowledge.application.services.retrieval_service import (
                RetrievalService,
            )

            retrieval_service = container.try_get(RetrievalService)
            if retrieval_service:
                app.state.retrieval_service = retrieval_service
                logger.info("RetrievalService available for FactionDecisionService")
            else:
                app.state.retrieval_service = None
                logger.warning(
                    "RetrievalService not available - RAG context enrichment disabled"
                )
        except Exception as exc:
            app.state.retrieval_service = None
            logger.warning("Could not retrieve RetrievalService: %s", exc)

        # EventBus is now accessed via request.app.state.event_bus
        # No global set_event_bus() call needed - see Issue 6 fix
        logger.info("EventBus available at app.state.event_bus for faction_intel router")

    orchestrator: Optional[SystemOrchestrator] = None
    try:
        if global_event_bus is not None:
            orchestrator = SystemOrchestrator(
                event_bus=global_event_bus,
                config=OrchestratorConfig(debug_logging=True),
            )
            await orchestrator.startup()
            container.register_singleton(SystemOrchestrator, orchestrator)
            logger.info("System Orchestrator initialized")
    except Exception as exc:
        logger.error("Failed to initialize SystemOrchestrator: %s", exc, exc_info=True)
        orchestrator = None

    try:
        if orchestrator is not None and global_event_bus is not None:
            from src.config.character_factory import CharacterFactory

            character_factory = CharacterFactory(global_event_bus)
            api_service = ApiOrchestrationService(
                orchestrator, global_event_bus, character_factory
            )
            container.register_singleton(ApiOrchestrationService, api_service)
            app.state.api_service = api_service
            logger.info("ApiOrchestrationService initialized")
        else:
            app.state.api_service = None
            logger.info("ApiOrchestrationService skipped due to missing dependencies")
    except Exception as exc:
        logger.error(
            "Failed to initialize ApiOrchestrationService: %s", exc, exc_info=True
        )
        app.state.api_service = None

    try:
        app.state.main_loop = asyncio.get_running_loop()
    except RuntimeError:
        app.state.main_loop = None

    if getattr(app.state, "prompts_router_available", False):
        try:
            from src.api.prompts_router import ensure_templates_registered

            ensure_templates_registered()
        except Exception as exc:
            logger.warning("Prompt templates registration failed: %s", exc)

    if getattr(app.state, "decision_router_available", False):
        try:
            from src.api.routers.events import broadcast_sse_event
            from src.decision import (
                DecisionPointDetector,
                InteractionPauseController,
                NegotiationEngine,
                initialize_decision_system,
            )

            pause_controller = InteractionPauseController(default_timeout=120)
            detector = DecisionPointDetector(
                tension_threshold=7.0,
                intensity_threshold=7.0,
                always_detect_interval=3,
            )
            negotiation_engine = NegotiationEngine()

            initialize_decision_system(
                pause_controller=pause_controller,
                decision_detector=detector,
                negotiation_engine=negotiation_engine,
                broadcast_sse_event=lambda event: broadcast_sse_event(app, event),
            )
            logger.info("Decision system initialized with SSE broadcast capability")
        except Exception as exc:
            logger.warning("Failed to initialize decision system: %s", exc)


async def shutdown_app_state(app: FastAPI) -> None:
    logger.info("Shutting down StoryForge AI API server.")
    try:
        api_service = getattr(app.state, "api_service", None)
        if api_service:
            await api_service.stop_simulation()
    except Exception as exc:
        logger.error("Error during shutdown: %s", exc, exc_info=True)
