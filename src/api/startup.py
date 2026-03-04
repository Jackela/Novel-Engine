from __future__ import annotations

import asyncio
import logging
import os
from typing import List, Optional, Set

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

# Environment variables that are strictly required for the application to function.
# These have no sensible defaults and must be explicitly set.
REQUIRED_ENV_VARS: List[str] = []

# Environment variables required in production mode for security.
PRODUCTION_REQUIRED_ENV_VARS: List[str] = [
    "SECRET_KEY",
    "JWT_SECRET_KEY",
]

# Environment variables that should not be empty if set.
# These are optional but must have non-empty values when present.
NON_EMPTY_WHEN_SET: Set[str] = {
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "BRAIN_SETTINGS_ENCRYPTION_KEY",
}


class EnvironmentValidationError(RuntimeError):
    """Raised when required environment variables are missing or invalid."""

    pass


def validate_environment() -> None:
    """
    Validate all required environment variables are set and non-empty.

    This function checks for:
    1. Absolutely required variables (from REQUIRED_ENV_VARS)
    2. Production-only required variables (from PRODUCTION_REQUIRED_ENV_VARS)
    3. Variables that must be non-empty when explicitly set

    Raises:
        EnvironmentValidationError: If any required variable is missing or empty.
    """
    missing: List[str] = []
    empty: List[str] = []
    warnings: List[str] = []

    # Check absolutely required variables
    for var in REQUIRED_ENV_VARS:
        value = os.getenv(var)
        if value is None:
            missing.append(var)
        elif value == "":
            empty.append(var)

    # Check production-only required variables
    environment = os.getenv("ENVIRONMENT", "development").lower()
    is_production = environment in ("production", "staging")

    if is_production:
        for var in PRODUCTION_REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if value is None:
                missing.append(var)
            elif value == "":
                empty.append(var)

        # Warn about production security settings
        jwt_key = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY", "")
        if jwt_key in (
            "development-secret-key-change-in-production",
            "your-secret-key-here",
            "changeme",
        ):
            warnings.append(
                "JWT_SECRET_KEY is using a development default value in production"
            )
    else:
        # In development, still check if production vars exist but allow defaults
        for var in PRODUCTION_REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if value is None:
                # This is fine in development - APISettings provides a default
                logger.debug(
                    "Optional production variable %s not set (development mode)", var
                )

    # Check that optional API keys are non-empty when set
    for var in NON_EMPTY_WHEN_SET:
        value = os.getenv(var)
        if value == "":
            empty.append(var)
        elif value is not None and value.startswith("your_"):
            # Detect placeholder values
            warnings.append(f"{var} appears to contain a placeholder value")

    # Log warnings
    for warning in warnings:
        logger.warning("Environment validation warning: %s", warning)

    # Raise errors if any critical issues found
    if missing:
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        raise EnvironmentValidationError(error_msg)

    if empty:
        error_msg = f"Empty required environment variables: {', '.join(empty)}"
        logger.error(error_msg)
        raise EnvironmentValidationError(error_msg)

    # Log successful validation
    if is_production:
        logger.info("Environment validation passed (production mode)")
    else:
        logger.info("Environment validation passed (development mode)")


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
    """Initialize application state with environment validation and service setup."""
    # Validate environment variables first - fail fast if configuration is incomplete
    validate_environment()

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

    # EventBus is now accessed via request.app.state.event_bus in routers
    # No global set_event_bus() call needed - routers use DI pattern
    logger.info("EventBus available at app.state.event_bus for routers")

    # Register event handlers
    if global_event_bus is not None:
        try:
            from src.contexts.world.application.handlers import TimeAdvancedHandler

            time_handler = TimeAdvancedHandler()
            global_event_bus.register_handler(time_handler)
            logger.info("TimeAdvancedHandler registered with EventBus")
        except Exception as exc:
            logger.warning("Could not register TimeAdvancedHandler: %s", exc)

        # Note: RumorPropagationHandler is registered after repositories below

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

    # Register CalendarRepository in DI container
    try:
        from src.contexts.world.domain.ports.calendar_repository import (
            CalendarRepository,
        )
        from src.contexts.world.infrastructure.persistence.in_memory_calendar_repository import (
            InMemoryCalendarRepository,
        )

        calendar_repository = InMemoryCalendarRepository()
        container.register_singleton(CalendarRepository, calendar_repository)
        app.state.calendar_repository = calendar_repository
        logger.info("CalendarRepository registered in DI container")
    except Exception as exc:
        app.state.calendar_repository = None
        logger.warning("Could not register CalendarRepository: %s", exc)

    # Register EventRepository in DI container
    try:
        from src.contexts.world.domain.ports.event_repository import EventRepository
        from src.contexts.world.infrastructure.persistence.in_memory_event_repository import (
            InMemoryEventRepository,
        )

        event_repository = InMemoryEventRepository()
        container.register_singleton(EventRepository, event_repository)
        app.state.event_repository = event_repository
        app.state.event_repository_available = True
        logger.info("EventRepository registered in DI container")
    except Exception as exc:
        app.state.event_repository = None
        app.state.event_repository_available = False
        logger.warning("Could not register EventRepository: %s", exc)

    # Register RumorRepository in DI container
    try:
        from src.contexts.world.domain.ports.rumor_repository import RumorRepository
        from src.contexts.world.infrastructure.persistence.in_memory_rumor_repository import (
            InMemoryRumorRepository,
        )

        rumor_repository = InMemoryRumorRepository()
        container.register_singleton(RumorRepository, rumor_repository)
        app.state.rumor_repository = rumor_repository
        app.state.rumor_repository_available = True
        logger.info("RumorRepository registered in DI container")
    except Exception as exc:
        app.state.rumor_repository = None
        app.state.rumor_repository_available = False
        logger.warning("Could not register RumorRepository: %s", exc)

    # Register LocationRepository in DI container
    try:
        from src.contexts.world.domain.ports.location_repository import (
            LocationRepository,
        )
        from src.contexts.world.infrastructure.persistence.in_memory_location_repository import (
            InMemoryLocationRepository,
        )

        location_repository = InMemoryLocationRepository()
        container.register_singleton(LocationRepository, location_repository)
        app.state.location_repository = location_repository
        app.state.location_repository_available = True
        logger.info("LocationRepository registered in DI container")
    except Exception as exc:
        app.state.location_repository = None
        app.state.location_repository_available = False
        logger.warning("Could not register LocationRepository: %s", exc)

    # Register RumorPropagationHandler for rumor propagation on time advance
    # This must happen AFTER repositories are registered above
    if global_event_bus is not None:
        try:
            from src.contexts.world.application.handlers.rumor_propagation_handler import (
                RumorPropagationHandler,
            )

            # Get repositories from app.state (set during registration above)
            location_repo = getattr(app.state, "location_repository", None)
            rumor_repo = getattr(app.state, "rumor_repository", None)

            if location_repo is not None and rumor_repo is not None:
                rumor_handler = RumorPropagationHandler(
                    location_repo=location_repo,
                    rumor_repo=rumor_repo,
                )
                global_event_bus.register_handler(rumor_handler)
                logger.info(
                    "RumorPropagationHandler registered with EventBus "
                    "(with repositories)"
                )
            else:
                logger.warning(
                    "RumorPropagationHandler not registered: "
                    "repositories not available (location_repo=%s, rumor_repo=%s)",
                    location_repo is not None,
                    rumor_repo is not None,
                )
        except Exception as exc:
            logger.warning("Could not register RumorPropagationHandler: %s", exc)

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
